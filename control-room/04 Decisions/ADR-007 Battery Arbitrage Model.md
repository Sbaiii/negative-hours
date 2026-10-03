# ADR-007: Battery arbitrage model (Q3)

**Date:** 2026-10-03 · **Status:** accepted

## Context
Q3 asks where a battery is worth the most. We answer one narrow part of that: what a battery could earn by buying and selling on the **day-ahead market**, per zone and year. The answer depends on the battery, how it is allowed to operate, and how well it knows prices, so every assumption is listed here.

## Options
1. A rule of thumb on daily prices (e.g. max − min spread × capacity)
2. An optimisation per day (linear program) on the cleared prices, with a rule of thumb next to it for comparison
3. A multi-market model (day-ahead + intraday + balancing) with forecast error

## Decision
Option 2. `models/battery.py` solves each zone × local day as a linear program (`scipy.optimize.linprog`, HiGHS); `models/run_battery.py` runs it for every day from 2019 and writes `battery.arbitrage_daily` into the warehouse; dbt sums it into `fct_battery_arbitrage` (zone × local year × duration).

**Assumptions**

| | Value |
|---|---|
| Power | 1 MW (results are per MW) |
| Duration | 1 h, **2 h (default)**, 4 h → 1, 2, 4 MWh of storage |
| Round-trip efficiency | 88%, split evenly: √0.88 ≈ 93.8% on charge and on discharge |
| Cycles | at most **1 full cycle per day**: energy drawn from storage ≤ capacity |
| Day boundary | empty at the start and end of each **local** day; days are solved independently |
| Market | day-ahead only, cleared prices at native resolution (60 min, 15 min from 2025-10-01) |
| Role | price-taker: the battery's trades don't move prices |
| Foresight | perfect: the whole day's cleared prices are known when scheduling it |
| Depth of discharge | full (0 to 100%) |
| Not modelled | intraday, balancing and capacity markets; degradation; grid fees and taxes; availability/outages; capex |

**LP per day** (T periods of length d_t hours, price p_t): choose charge c_t and discharge x_t (MW, grid side) and state of charge s_t (MWh) to maximise Σ p_t (x_t − c_t) d_t, subject to s_t = s_{t−1} + η c_t d_t − x_t d_t / η, 0 ≤ c_t, x_t ≤ 1, 0 ≤ s_t ≤ E, s_{−1} = s_{T−1} = 0 and Σ x_t d_t / η ≤ E.

**Heuristic** (for comparison): charge in the cheapest N hours of the day and discharge in the most expensive N (N = duration), played in time order at full power; idle if the expensive hours after losses don't beat the cheap ones; only energy that can be sold later in the day is bought.

**Mart metrics:** revenue €/MW/year (sum of days), average daily revenue, energy-weighted spread captured (avg sell − avg buy price), cycles, energy bought at negative prices and the money received for it (and its share of revenue), heuristic revenue and LP uplift. Partial years use `int_zone_years` like the other marts; incomplete price days (2019-01-01 in CET zones, today's PT day) are skipped.

## Why
- **An LP, not a spread formula:** with efficiency losses, a cycle cap and 15-min prices, the best schedule isn't obvious; an LP gets it exactly and stays fast (~2–4 ms per day, ~3 min for all 67,002 zone-day-durations).
- **A heuristic next to it** shows how much of the value is "being clever" vs "the spread is there": the LP earns 8 to 29% more in full years (2 h).
- **Perfect foresight on day-ahead prices** is the standard upper bound for this market. Real operators bid before prices clear, so they earn less from day-ahead alone, but they also stack other markets. The numbers are an upper bound for one market, not a revenue forecast.
- **One cycle a day, empty at day ends:** a common warranty-style limit, and it keeps days independent. It leaves money on two-peak days (tested: a second cycle would earn more).
- **No simultaneous charge and discharge:** an LP can in principle "burn" energy through losses at negative prices by doing both at once. It never happens in our results (checked on every day, and tested in dbt), so no integer constraint is needed.
- **Native resolution:** since 2025-10-01 a battery can trade 15-min products; using them is the point. Re-solving 2026 days on hourly averages shows the 15-min resolution adds 2 to 10% (ES/PT lowest, IT_NORD highest).

## Validation
No published figure uses exactly these assumptions, so this is a sanity check, not a match:
- **Gridcog** (Mar 2025): a 1 MW / 2 h battery trading **day-ahead only** on 2024 German prices earns "~70k" per year; cycles, efficiency and foresight are not stated. Ours: **€66,047/MW** (DE_LU 2024, 2 h). Same order of magnitude.
- **Enervis BESS index** (Jan 2026): ~**€148,500/MW** for 2025 in Germany, for a 1 MW / 2 MWh battery trading intraday + FCR + aFRR at 1.5 cycles a day, 87% round trip. Not comparable (other markets, more cycles); ours for DE_LU 2025 is €76,060, about half, consistent with day-ahead being only one of several revenue streams.

Sources: [Gridcog, The commercial opportunities for utility-scale batteries in Germany](https://www.gridcog.com/blog/the-commercial-opportunities-for-utility-scale-batteries-in-germany) · [ESS News, Enervis Battery Storage Index, 28 Jan 2026](https://www.ess-news.com/2026/01/28/enervis-battery-storage-index-december-revenues-fall-to-multi-month-low/)

## Consequences
- Results are €/MW/year of **gross day-ahead trading margin**, not profit: no capex, opex, degradation or fees. No IRR or payback is computed.
- Run order: `dbt build` → `python -m models.run_battery` → `dbt build --select fct_battery_arbitrage` (the runner reads `int_prices_local`; the mart reads the runner's table).
- Days are independent: the model can't carry energy overnight (e.g. charge at a negative Sunday noon to sell Monday morning).
