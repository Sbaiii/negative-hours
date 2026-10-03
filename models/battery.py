"""A battery trading on the day-ahead market, one local day at a time (Q3, ADR-007).

Two ways to schedule the same battery on the same day of prices:

- `optimal_day`: the best possible schedule, solved as a linear program (HiGHS).
  It sees the whole day's cleared prices in advance (perfect foresight), so its
  revenue is an upper bound for day-ahead arbitrage.
- `heuristic_day`: a simple rule of thumb to compare with: charge in the cheapest
  N hours of the day, discharge in the most expensive N hours (N = duration).

Prices come at their native resolution: `durations_h` gives each period's length
(1.0 for hourly, 0.25 for 15-min), so revenue is price x power x hours.
"""

import math
from dataclasses import dataclass

import numpy as np
from scipy.optimize import linprog
from scipy.sparse import diags, eye, hstack

# Values below this (MW, MWh) are solver noise, not trades.
TOLERANCE = 1e-6


@dataclass(frozen=True)
class Battery:
    """A battery and its operating limits. Defaults are the ADR-007 assumptions."""

    duration_h: float = 2.0
    power_mw: float = 1.0
    round_trip_efficiency: float = 0.88
    max_cycles_per_day: float = 1.0

    @property
    def energy_mwh(self) -> float:
        return self.power_mw * self.duration_h

    @property
    def one_way_efficiency(self) -> float:
        # Losses split evenly between charging and discharging.
        return math.sqrt(self.round_trip_efficiency)


@dataclass
class DaySchedule:
    """Power per period (MW, grid side) and the state of charge after each period."""

    prices: np.ndarray  # EUR/MWh
    durations_h: np.ndarray  # hours
    charge_mw: np.ndarray
    discharge_mw: np.ndarray
    soc_mwh: np.ndarray

    @property
    def charged_mwh(self) -> float:
        """Energy bought from the grid."""
        return float(np.sum(self.charge_mw * self.durations_h))

    @property
    def discharged_mwh(self) -> float:
        """Energy sold to the grid."""
        return float(np.sum(self.discharge_mw * self.durations_h))

    @property
    def charge_cost_eur(self) -> float:
        """What charging cost; negative when the battery was paid to charge."""
        return float(np.sum(self.prices * self.charge_mw * self.durations_h))

    @property
    def discharge_value_eur(self) -> float:
        return float(np.sum(self.prices * self.discharge_mw * self.durations_h))

    @property
    def revenue_eur(self) -> float:
        return self.discharge_value_eur - self.charge_cost_eur

    @property
    def charged_negative_mwh(self) -> float:
        """Energy bought in periods with a negative price."""
        negative = self.prices < 0
        return float(np.sum((self.charge_mw * self.durations_h)[negative]))

    @property
    def negative_charging_revenue_eur(self) -> float:
        """Money received for charging when the price was negative (>= 0)."""
        negative = self.prices < 0
        return float(
            -np.sum((self.prices * self.charge_mw * self.durations_h)[negative])
        )

    @property
    def simultaneous_mwh(self) -> float:
        """Energy charged in periods that also discharge (should be ~0)."""
        both = (self.charge_mw > TOLERANCE) & (self.discharge_mw > TOLERANCE)
        return float(np.sum((self.charge_mw * self.durations_h)[both]))

    def cycles(self, battery: Battery) -> float:
        """Full equivalent cycles: energy drawn from storage / capacity."""
        drawn = self.discharged_mwh / battery.one_way_efficiency
        return drawn / battery.energy_mwh


def optimal_day(
    prices: np.ndarray, durations_h: np.ndarray, battery: Battery
) -> DaySchedule:
    """Revenue-maximising schedule for one day, as a linear program.

    Variables per period t (T periods): charge c_t and discharge x_t in MW (grid
    side), and the state of charge s_t in MWh at the end of t.

        maximise    sum_t price_t * (x_t - c_t) * d_t
        subject to  s_t = s_{t-1} + eta * c_t * d_t - x_t * d_t / eta,  s_{-1} = 0
                    0 <= c_t, x_t <= P
                    0 <= s_t <= E,  s_{T-1} = 0          (empty at both ends of the day)
                    sum_t x_t * d_t / eta <= cycles * E    (energy drawn from storage)

    with eta the one-way efficiency, P the power and E the energy capacity.
    """
    prices = np.asarray(prices, dtype=float)
    d = np.asarray(durations_h, dtype=float)
    n = len(prices)
    eta = battery.one_way_efficiency

    # linprog minimises: cost of charging minus value of discharging.
    objective = np.concatenate([prices * d, -prices * d, np.zeros(n)])

    # State of charge balance, one row per period:
    # -eta*d_t*c_t + (d_t/eta)*x_t + s_t - s_{t-1} = 0
    soc_change = eye(n, format="csr") - eye(n, k=-1, format="csr")
    a_eq = hstack([diags(-eta * d), diags(d / eta), soc_change], format="csr")
    b_eq = np.zeros(n)

    # Cycle cap on the energy drawn from storage.
    a_ub = np.concatenate([np.zeros(n), d / eta, np.zeros(n)])[np.newaxis, :]
    b_ub = [battery.max_cycles_per_day * battery.energy_mwh]

    power = (0.0, battery.power_mw)
    soc = [(0.0, battery.energy_mwh)] * (n - 1) + [(0.0, 0.0)]
    bounds = [power] * (2 * n) + soc

    result = linprog(
        objective,
        A_ub=a_ub,
        b_ub=b_ub,
        A_eq=a_eq,
        b_eq=b_eq,
        bounds=bounds,
        method="highs",
    )
    if result.status != 0:
        raise RuntimeError(f"battery LP failed: {result.message}")

    z = np.where(np.abs(result.x) < TOLERANCE, 0.0, result.x)
    return DaySchedule(prices, d, z[:n], z[n : 2 * n], z[2 * n :])


def heuristic_day(
    prices: np.ndarray, durations_h: np.ndarray, battery: Battery
) -> DaySchedule:
    """Rule of thumb: charge in the cheapest N hours, discharge in the most expensive N.

    N is the battery's duration. The two sets of periods are picked by price alone,
    then played in time order: charge at full power, discharge at full power while
    there is energy. The battery stays idle all day if the expensive hours, after
    losses, don't pay for the cheap ones. Picking by price ignores order (the
    cheapest hours can come after the most expensive ones), so a first pass finds
    how much energy can actually be sold and a second pass charges only that much:
    like the LP, the battery is empty at the end of the day.
    """
    prices = np.asarray(prices, dtype=float)
    d = np.asarray(durations_h, dtype=float)
    n = len(prices)
    eta = battery.one_way_efficiency
    order = np.argsort(prices, kind="stable")

    def take(candidates) -> list[int]:
        picked, hours = [], 0.0
        for t in candidates:
            if hours >= battery.duration_h - TOLERANCE:
                break
            picked.append(int(t))
            hours += d[t]
        return picked

    cheap = set(take(order))
    expensive = set(take(t for t in order[::-1] if t not in cheap))

    def mean_price(periods: set[int]) -> float:
        index = sorted(periods)
        return float(np.average(prices[index], weights=d[index]))

    def play(charge_limit_mwh: float):
        """Charge until `charge_limit_mwh` has been stored, sell while energy lasts."""
        charge, discharge, soc = np.zeros(n), np.zeros(n), np.zeros(n)
        stored = stored_total = 0.0
        for t in range(n):
            if t in cheap:
                room = min(battery.energy_mwh - stored, charge_limit_mwh - stored_total)
                charge[t] = min(battery.power_mw, max(room, 0.0) / (eta * d[t]))
                stored += eta * charge[t] * d[t]
                stored_total += eta * charge[t] * d[t]
            elif t in expensive:
                discharge[t] = min(battery.power_mw, stored * eta / d[t])
                stored -= discharge[t] * d[t] / eta
            soc[t] = stored
        return charge, discharge, soc

    trades = (
        cheap
        and expensive
        and mean_price(expensive) * battery.round_trip_efficiency > mean_price(cheap)
    )
    if not trades:
        return DaySchedule(prices, d, np.zeros(n), np.zeros(n), np.zeros(n))
    _, first_discharge, _ = play(charge_limit_mwh=battery.energy_mwh)
    sold_from_storage = float(np.sum(first_discharge * d)) / eta
    charge, discharge, soc = play(charge_limit_mwh=sold_from_storage)
    return DaySchedule(prices, d, charge, discharge, np.maximum(soc, 0.0))
