# ADR-006: Hourly grid and capture-price definitions (Q2)

**Date:** 2026-10-03 · **Status:** accepted

## Context
Q2 compares what solar (and wind) earn with the average price. That needs prices and generation side by side, but they come at different intervals: prices are hourly until the 2025-10-01 switch to 15 min; generation is 15 min in some zones since 2019 (DE_LU, NL, BE), hourly in others, switching at different dates (ADR-004).

## Options
1. Native resolution: join each generation period to the price period that contains it
2. A common **15-min** grid (split hourly values into quarters)
3. A common **hourly** grid

## Decision
Option 3, in `int_energy_hourly` (one row per zone × UTC hour):
- **Price:** duration-weighted mean of the price periods in the hour (one period before 2025-10-01, four after).
- **Generation:** energy, MWh = MW × `duration_h`, summed over the periods in the hour; solar = `Solar`, wind = `Wind Onshore` + `Wind Offshore`, total = all reported types.
- **Matched hours only:** an hour is kept if it has both a price and some generation. Coverage columns record how much of each hour was reported.

In `fct_capture_prices` (zone × local year):
- `baseload_price` = time-weighted mean price over **all** price periods of the zone-year, the same as Q1's `avg_price` (tested). *(Changed 2026-10-03: it was over matched hours only.)*
- `capture_price` = Σ(price × MWh) / Σ(MWh); `capture_rate` = capture / baseload.
- `solar_share` = solar MWh / total reported MWh.
- **Technology coverage rule:** solar (or wind) metrics are null when that series exists in < 95% of matched hours. Only PL 2019–2020 solar is affected (reported from 2020-04-10).
- Partial years use the same rule as Q1 (`int_zone_years`): current year, a known reason, or coverage < 0.98.

## Why
- **One grid for 2019–2026:** an hourly grid treats every year the same way. A 15-min grid would invent sub-hour detail for every hourly year (2019–Sep 2025 prices, hourly generation zones), while native joins would mean a different method per zone and year.
- **Little lost:** hourly averaging smooths intra-hour price swings since Oct 2025, but a capture price is a yearly weighted average and the effect is small; it is the same for every zone.
- **Matched hours** for capture prices: generation is only known there. **All hours** for baseload: "the average price" should mean the same in Q1 and Q2. The difference is small: at most 0.49 €/MWh (2026, where generation ends a day before prices); capture rates moved by at most 0.33 points (solar) and 0.59 points (wind).
- **Checked:** DE_LU 2024 solar capture price 46.23 €/MWh vs the published German solar market value of 4.624 ct/kWh (Netztransparenz).

## Consequences
- Generation is **as reported to ENTSO-E**. In the Netherlands it misses almost all solar: 0.49 TWh in 2024 vs 22 TWh in national statistics (CBS). NL `solar_share` is not usable and NL capture rates are indicative only (see Data Dictionary).
- Intra-hour (15-min) price shape after Oct 2025 was not captured; fixed by the update below.
- `int_energy_hourly` was a table (~536k rows); replaced by `int_energy_periods` (update below).

## Update 2026-10-04: match on the generation period (15-min where both are 15-min)
- **Change.** `int_energy_hourly` is replaced by `int_energy_periods`: one row per zone and **generation period**, with the duration-weighted price over exactly that period. Where both prices and generation are 15-min (DE_LU, ES, FR, IT_NORD, NL, PL since 1 Oct 2025) solar and wind are priced quarter-hour by quarter-hour; where generation is hourly (BE, PT) each hour gets its mean price, as before; where prices are hourly (before Oct 2025) each 15-min generation period gets its hour's price, which gives the same result as the hourly grid. A zone never mixes 15-min and hourly generation within an hour (checked), so periods don't overlap. Prices and energy are exact decimals, so sums are identical on every build.
- **Why.** Solar output and quarter-hour prices both move within the hour; averaging prices to the hour hid part of the solar discount after the switch.
- **Measured effect** (same data, native match minus hourly grid, solar capture rate): 2026 to 2 Oct: −1.0 to −1.1 points in DE_LU, ES, FR and NL, −0.8 in PL, −0.4 in IT_NORD, 0 in BE and PT (hourly generation). 2025: −0.1 to −0.2 points (only Oct to Dec is 15-min). Wind: under 0.15 points everywhere. Years before 2025: no change.
- Coverage columns are now time-weighted (`matched_hours` = hours of generation periods with a price), with the same 95% rule.
