"""The battery LP (and the heuristic) on days small enough to check by hand."""

import math

import numpy as np
import pytest

from models.battery import Battery, heuristic_day, optimal_day

HOURLY = np.ones(24)
ETA = math.sqrt(0.88)  # one-way efficiency
TWO_HOURS = Battery(duration_h=2)


def random_day(seed: int, n: int = 24) -> np.ndarray:
    """A day with a morning and an evening peak plus noise, EUR/MWh."""
    rng = np.random.default_rng(seed)
    hours = np.arange(n) * 24 / n
    shape = 40 * np.exp(-((hours - 8) ** 2) / 4) + 60 * np.exp(-((hours - 19) ** 2) / 4)
    return 50 + shape + rng.normal(0, 15, n)


def test_flat_prices_earn_nothing():
    for schedule in (
        optimal_day(np.full(24, 60.0), HOURLY, TWO_HOURS),
        heuristic_day(np.full(24, 60.0), HOURLY, TWO_HOURS),
    ):
        assert schedule.revenue_eur == pytest.approx(0, abs=1e-6)
        assert schedule.charged_mwh == pytest.approx(0, abs=1e-6)


def test_two_price_day_matches_the_hand_calculation():
    # 12 h at 10, then 12 h at 100. The LP fills the 2 MWh store (buying 2/eta MWh)
    # and empties it (selling 2*eta MWh).
    prices = np.array([10.0] * 12 + [100.0] * 12)
    lp = optimal_day(prices, HOURLY, TWO_HOURS)
    assert lp.charged_mwh == pytest.approx(2 / ETA)
    assert lp.discharged_mwh == pytest.approx(2 * ETA)
    assert lp.revenue_eur == pytest.approx(100 * 2 * ETA - 10 * 2 / ETA)  # 166.30

    # The heuristic charges 2 h at 1 MW (2 MWh) and sells 0.88 x 2 MWh.
    rule = heuristic_day(prices, HOURLY, TWO_HOURS)
    assert rule.revenue_eur == pytest.approx(100 * 0.88 * 2 - 10 * 2)  # 156


def test_efficiency_losses_are_respected():
    lp = optimal_day(random_day(1), HOURLY, TWO_HOURS)
    assert lp.charged_mwh > 0
    # Empty at both ends of the day: what comes out is 88% of what went in.
    assert lp.discharged_mwh == pytest.approx(0.88 * lp.charged_mwh)


@pytest.mark.parametrize("duration_h", [1, 2, 4])
def test_state_of_charge_stays_within_capacity(duration_h):
    battery = Battery(duration_h=duration_h)
    for seed in range(20):
        lp = optimal_day(random_day(seed), HOURLY, battery)
        assert lp.soc_mwh.min() >= -1e-6
        assert lp.soc_mwh.max() <= battery.energy_mwh + 1e-6
        assert lp.soc_mwh[-1] == pytest.approx(0, abs=1e-6)  # empty at the end
        assert lp.charge_mw.max() <= battery.power_mw + 1e-6
        assert lp.discharge_mw.max() <= battery.power_mw + 1e-6


def test_cycle_cap_is_respected_and_binds_on_a_two_peak_day():
    # Cheap night, morning peak, cheap midday, evening peak: two cycles would pay.
    prices = np.array([20.0] * 6 + [150.0] * 3 + [10.0] * 6 + [150.0] * 3 + [20.0] * 6)
    one = optimal_day(prices, HOURLY, TWO_HOURS)
    assert one.cycles(TWO_HOURS) == pytest.approx(1.0)
    two = optimal_day(prices, HOURLY, Battery(duration_h=2, max_cycles_per_day=2))
    assert two.cycles(TWO_HOURS) == pytest.approx(2.0)
    assert two.revenue_eur > one.revenue_eur


def test_charging_at_negative_prices_earns_money():
    # Price -50 at midday, 30 otherwise: the battery is paid to charge, then sells.
    prices = np.array([30.0] * 10 + [-50.0] * 4 + [30.0] * 10)
    lp = optimal_day(prices, HOURLY, TWO_HOURS)
    assert lp.charge_cost_eur < 0
    assert lp.charged_negative_mwh == pytest.approx(2 / ETA)
    assert lp.negative_charging_revenue_eur == pytest.approx(50 * 2 / ETA)
    assert lp.revenue_eur == pytest.approx(30 * 2 * ETA + 50 * 2 / ETA)


def test_flat_negative_day_still_pays_through_losses():
    # Buying 2/eta MWh and selling back only 2*eta MWh at the same negative price
    # leaves the battery paid for the energy lost on the way.
    lp = optimal_day(np.full(24, -10.0), HOURLY, TWO_HOURS)
    assert lp.revenue_eur == pytest.approx(10 * 2 * (1 / ETA - ETA))


def test_quarter_hours_give_the_same_answer_as_hours_when_prices_repeat():
    prices = random_day(7)
    hourly = optimal_day(prices, HOURLY, TWO_HOURS)
    quarters = optimal_day(np.repeat(prices, 4), np.full(96, 0.25), TWO_HOURS)
    assert quarters.revenue_eur == pytest.approx(hourly.revenue_eur)


def test_heuristic_only_charges_what_it_can_sell():
    # The most expensive hours come first and the cheapest last (a negative-price
    # evening): energy bought then could never be sold, so none is bought.
    prices = np.array([90.0] * 2 + [50.0] * 18 + [-20.0] * 4)
    rule = heuristic_day(prices, HOURLY, TWO_HOURS)
    assert rule.charged_mwh == pytest.approx(0, abs=1e-9)
    assert rule.revenue_eur == pytest.approx(0, abs=1e-9)


@pytest.mark.parametrize("shift", [0, -60, -110])  # shifts push some hours below 0
def test_lp_never_earns_less_than_the_heuristic(shift):
    for seed in range(30):
        for duration_h in (1, 2, 4):
            battery = Battery(duration_h=duration_h)
            prices = random_day(seed) + shift
            lp = optimal_day(prices, HOURLY, battery)
            rule = heuristic_day(prices, HOURLY, battery)
            assert rule.soc_mwh[-1] == pytest.approx(0, abs=1e-9)  # empty at the end
            assert lp.revenue_eur >= rule.revenue_eur - 1e-6
