# Data Dictionary

Raw tables (Parquet, written by `pipeline/`) first, then the dbt warehouse (`warehouse/`, DuckDB file `data/warehouse.duckdb`). Full column docs: `cd warehouse && uv run dbt docs generate && uv run dbt docs serve`. Staging views read `data/raw` through an absolute path (macro `raw_source`), so they can be queried from any directory.

## raw_prices
| Column | Type | Description |
|---|---|---|
| ts_utc | timestamp | Start of the period, UTC |
| zone | text | Bidding zone code |
| price_eur_mwh | double | Day-ahead price |
| resolution_minutes | int | 60 or 15 |

Source: `query_day_ahead_prices`. File: `data/raw/prices/zone=<ZONE>/year=<YYYY>.parquet`.

## raw_generation
| Column | Type | Description |
|---|---|---|
| ts_utc | timestamp | Start of the period, UTC |
| zone | text | Bidding zone code |
| production_type | text | ENTSO-E production type as named by entsoe-py (e.g. `Solar`, `Wind Onshore`, `Fossil Gas`, `Hydro Pumped Storage`) |
| generation_mw | double | Average power fed into the grid over the period (ENTSO-E "Actual Aggregated") |
| resolution_minutes | int | 15, 30 or 60; can differ between zones and between types in one zone |

Source: `query_generation`. File: `data/raw/generation/zone=<ZONE>/year=<YYYY>.parquet`.
Long format: one row per zone × type × period. "Actual Consumption" (e.g. pumped storage while pumping) is **not** kept.
Grain/key: (zone, production_type, ts_utc).

## raw_load
| Column | Type | Description |
|---|---|---|
| ts_utc | timestamp | Start of the period, UTC |
| zone | text | Bidding zone code |
| load_mw | double | Actual total load, average MW over the period |
| resolution_minutes | int | 15, 30 or 60, zone-dependent |

Source: `query_load` (process type A16, realised). File: `data/raw/load/zone=<ZONE>/year=<YYYY>.parquet`.

## Notes for all raw tables
- MW values are average power over the period → energy (MWh) = MW × resolution_minutes / 60.
- Gaps are dropped, not stored as NULL: test completeness in dbt.

## Warehouse (dbt)
| Model | Layer | Grain | What it adds |
|---|---|---|---|
| `zones` | seed | zone | Zone name, country, IANA time zone (PT Europe/Lisbon, others CET) |
| `stg_prices` | staging (view) | zone × ts_utc | Typed raw prices. **Leaves out PL before 2019-11-19 23:00 UTC** (prices in PLN; dbt var `pl_eur_prices_start_utc`). PL analysis starts 2020 (ADR-005) |
| `stg_load` | staging (view) | zone × ts_utc | Typed raw load |
| `stg_generation` | staging (view) | zone × production_type × ts_utc | Typed raw generation; drops types never non-zero in a zone (BE Fossil Hard coal; ES Coal-derived gas, Oil shale, Peat, Geothermal, Marine, Wind Offshore; IT_NORD Geothermal; NL Hydro Run-of-river; PL Energy storage) |
| `int_prices_published` | intermediate (view) | zone × ts_utc | Every published price with `ts_local`, `local_date`, `local_year`, `duration_h` (exact decimals). Runs into tomorrow; only EV overnight charging reads it directly |
| `int_as_of` | intermediate (table) | one row | The run's **as-of date**: last local day with complete prices and generation in all 8 zones; also `limiting_zone` (ADR-005) |
| `int_prices_hourly` | intermediate (view) | zone × hour_utc | Hourly mean price up to the as-of date: basis of the headline negative-hour count (ADR-005) |
| `int_prices_local` | intermediate (view) | zone × ts_utc | `int_prices_published` up to the as-of date: the price table every mart and the battery model read |
| `int_zone_years` | intermediate (view) | zone × local_year | Year bounds (local midnight as UTC), `expected_hours`, `known_partial_reason`. Shared by all zone-year marts |
| `int_energy_periods` | intermediate (table) | zone × generation period | Solar / wind / total MWh per generation period and the price over exactly that period (15-min match where both are 15-min); replaced `int_energy_hourly` on 2026-10-04 (ADR-006) |
| `fct_ytd_comparison` | mart (table) | zone × local_year | Every year cut to 1 Jan to the as-of date's day and month: negative hours, solar capture rate, 2 h battery revenue, EV costs. The only place 2026 is compared with other years (ADR-005). Exported |
| `fct_negative_hours` | mart (table) | zone × local_year | Q1 metrics, see below. Exported to `analysis/outputs/fct_negative_hours.csv` |
| `fct_capture_prices` | mart (table) | zone × local_year | Q2 metrics, see below. Exported to `analysis/outputs/fct_capture_prices.csv` |
| `battery.arbitrage_daily` | source (table, written by `battery/run.py`) | zone × local_date × battery_duration_h | Daily optimal (LP) and heuristic schedule results for a 1 MW battery (ADR-007). Incomplete price days skipped |
| `fct_battery_arbitrage` | mart (table) | zone × local_year × battery_duration_h | Q3 metrics, see below. Exported to `analysis/outputs/fct_battery_arbitrage.csv` |
| `fct_hourly_profile` | mart (table) | zone × local_year × season × local_hour | Q4: mean / median price and share of time ≤ 0 by hour of day and season (ADR-008). Exported |
| `fct_ev_charging` | mart (table) | zone × local_year × season (+ `year`) | Q4: wholesale cost of 10 kWh/day at 7 kW, immediate (18:00) vs overnight vs smart, € per year and savings (ADR-008). Exported |
| `fct_solar_monthly` | mart (table) | zone × local_month | Monthly baseload (all price periods), solar MWh and capture price; used to split annual capture rates into seasonal and within-month parts |

### fct_negative_hours
| Column | Type | Description |
|---|---|---|
| zone | text | Bidding zone code |
| local_year | int | Calendar year in the zone's local time |
| negative_hours | double | **Headline:** hours whose hourly mean price is < 0 (the RTE/REE convention) |
| zero_or_negative_hours | double | Hours whose hourly mean price is ≤ 0 |
| negative_period_hours | double | Σ duration (h) of price periods < 0 (15-min periods count 0.25 h); equals negative_hours before 2025-10-01 |
| zero_or_negative_period_hours | double | Σ duration (h) of price periods ≤ 0 |
| covered_hours | double | Σ duration (h) of periods with a price |
| expected_hours | double | Hours in the local year (current year: up to the end of the last period) |
| completeness | double | covered_hours / expected_hours |
| min_price | double | Lowest price, EUR/MWh |
| avg_price | double | Duration-weighted average price, EUR/MWh |
| avg_price_negative_periods | double | Duration-weighted average over negative periods; null if none |
| is_partial_year | bool | Not a full year of data: current year **or** completeness < 0.98 |
| partial_reason | text | `current_year` / `pln_prices_excluded` / null (full year). Every partial year must have one (tested) |

Definitions: [[04 Decisions/ADR-005 Negative Hours Metric|ADR-005]].

### fct_capture_prices
| Column | Type | Description |
|---|---|---|
| zone, local_year | | Key |
| baseload_price | double | Time-weighted mean price over **all** price periods, EUR/MWh (= `fct_negative_hours.avg_price`, tested) |
| solar_mwh / wind_mwh | double | Energy in the year, **as reported to ENTSO-E**, MWh (wind = onshore + offshore) |
| solar_capture_price / wind_capture_price | double | Σ(price × MWh) / Σ(MWh), EUR/MWh |
| solar_capture_rate / wind_capture_rate | double | Capture price / baseload price |
| solar_share / wind_share | double | Share of total reported generation (not of consumption) |
| total_generation_mwh | double | All reported production types, MWh |
| matched_hours, expected_hours, coverage | | Hours with both price and generation; coverage = matched / expected |
| solar_coverage / wind_coverage | double | Share of matched hours with that series; metrics are null below 0.95 |
| is_partial_year, partial_reason | | Same rule as fct_negative_hours (`int_zone_years`) |

Definitions: [[04 Decisions/ADR-006 Hourly Grid and Capture Prices|ADR-006]].

**Caveat: "as reported to ENTSO-E".** ENTSO-E's Solar series is not national solar output everywhere. Order-of-magnitude check, 2024:

| Zone | ENTSO-E Solar | National figure | Verdict |
|---|---:|---:|---|
| NL | 0.49 TWh (0.46% of reported generation) | 22 TWh (CBS) | **~2% of real output: NL `solar_share` unusable, capture rate indicative only** |
| DE_LU | 63.4 TWh (14.45%) | 59.8 TWh net public, 72.2 TWh incl. self-consumption; 14% of public generation (Fraunhofer ISE) | Consistent |
| FR | 23.3 TWh (4.45% of reported generation) | 24.8 TWh, 4.6% of national production of 539.0 TWh ([RTE, Bilan électrique 2024, principaux résultats](https://assets.rte-france.com/analyse-et-donnees/2025-09/BE2024%20-%20Principaux%20R%C3%A9sultats.pdf)) | ENTSO-E is 6% below RTE (total generation 523.7 vs 539.0 TWh, −2.8%); consistent in shape, slightly low in level |
| others | | not checked against national statistics | Use with the label "as reported" |

Capture *rates* are less exposed than shares: they depend on the shape of the solar profile, not its size. But a series that covers 2% of a country's panels may not have the national shape.

### fct_battery_arbitrage
| Column | Type | Description |
|---|---|---|
| zone, local_year, battery_duration_h | | Key (duration 1, 2 or 4 h; power 1 MW) |
| revenue_eur_per_mw | double | Σ daily optimal day-ahead revenue, € per MW (year to date for the current year) |
| avg_daily_revenue_eur_per_mw | double | revenue / days_solved |
| avg_spread_captured_eur_mwh | double | Energy-weighted avg sell price − avg buy price, €/MWh (before losses) |
| avg_sell_price / avg_buy_price | double | €/MWh; the buy price can be negative |
| cycles / avg_daily_cycles | double | Full equivalent cycles (energy drawn from storage / capacity); ≤ 1 per day |
| charged_negative_mwh | double | Energy bought at negative prices, MWh per MW |
| negative_charging_revenue_eur | double | Money received for charging at negative prices, € per MW |
| negative_revenue_share | double | negative_charging_revenue_eur / revenue_eur_per_mw |
| heuristic_revenue_eur_per_mw | double | Cheapest-N / dearest-N rule, € per MW |
| lp_uplift | double | LP revenue / heuristic revenue − 1 |
| days_solved, expected_hours, coverage | | Complete days solved; coverage = their hours / expected hours |
| is_partial_year, partial_reason | | Same rule as the other marts (`int_zone_years`) |

Perfect foresight on cleared day-ahead prices, 1 cycle a day, 88% round trip: an **upper bound for day-ahead arbitrage only** (no intraday, balancing, capacity markets, degradation or grid fees). Definitions: [[04 Decisions/ADR-007 Battery Arbitrage Model|ADR-007]].

### fct_ev_charging
| Column | Type | Description |
|---|---|---|
| zone, local_year, season | | Key; season = winter (Jan, Feb, Dec) / spring / summer / autumn, or `year` |
| days | int | Local days with prices for all three strategies |
| immediate / overnight / smart _eur_per_year | double | Wholesale cost, € per year (average daily cost × 365) |
| overnight / smart _savings_eur_per_year | double | Immediate cost − strategy cost; overnight can be negative |
| overnight / smart _savings_share | double | Savings / immediate cost |
| immediate / overnight / smart _price_eur_mwh | double | Average wholesale price paid, €/MWh |
| is_partial_year, partial_reason | | Same rule as fct_negative_hours |

Wholesale day-ahead component only: no retail margin, taxes or grid fees. Definitions: [[04 Decisions/ADR-008 EV Charging Strategies|ADR-008]].

### Current year, as-of date and snapshots
- Rates and shares are stored and exported with 6 decimals (prices 2, MWh 3), so a percentage rounded to 1 decimal can't land on a rounding boundary.
- Every mart row has `data_through_date`: 31 December, or the as-of date (`int_as_of`) for the current year. The current year's `expected_hours` runs to the end of the as-of date, so its completeness is real.
- `analysis/outputs/*.csv` and the dashboard are live (updated by the daily refresh). Numbers written in the README and finding notes come from a frozen copy, `analysis/outputs/snapshots/<as-of date>/`, which also holds the notebook tables the notes quote (`q1_*`, `q2_*`, `q3_*`, `q4_*`) and `quoted_numbers.csv`: every number in the README and finding notes, the text around it, its position and how to recompute it (or why it is a constant or an external figure). `tests/test_quoted_numbers.py` checks it and fails on any unregistered number.
- `analysis/outputs/q3_hourly_resolve_ytd.csv` is written by the Q3 notebook (2026 battery revenue re-solved on hourly prices), not by the daily refresh.

## Data quality log
| Date found | Zone | Issue | How handled |
|---|---|---|---|
| 2026-10-02 | all 8 | Prices 2019 → 2026-10-03 complete: 94,486 rows per zone, no gaps, no duplicate timestamps | None needed |
| 2026-10-02 | ES | Load 2025: 34,898 of 35,040 expected 15-min rows (~35 h missing) | Kept as is; completeness test + gap handling in dbt staging |
| 2026-10-02 | ES | Generation 2025 reports 21 production types; 7 are all zero (Fossil Peat, Fossil Oil shale, Marine, Geothermal, Wind Offshore, Fossil Coal-derived gas, Fossil Brown coal/Lignite) | Filter near-empty types in staging |
| 2026-10-02 | all | Storage "Actual Consumption" columns (e.g. pumped storage pumping) dropped at extraction (ADR-003) | Accepted for now; may matter for battery analysis (Q3): re-extract if needed |
| 2026-10-03 | FR, BE, IT_NORD, ES | **Bug:** for sparse generation types (Hydro Pumped Storage, Wind Offshore, Fossil Hard coal…) `resolution_minutes` held gaps (120, 3405, 29535 min); BE 2024 Energy storage had 0 (a lone timestamp, not a duplicate) | Fixed: resolution = most common spacing per series and UTC day, gaps logged as missing periods ([[ADR-004 Resolution Detection]]). Duplicates now dropped (keep first). Generation re-fetched for FR, BE, IT_NORD (all years), ES 2022 and NL 2019 (one Waste row labelled 30); no warnings. All raw data now has only 15 and 60 |
| 2026-10-03 | ES, FR, IT_NORD, PL | Reporting interval switches from 60 to 15 min **mid-month**, at 00:00 UTC: ES load + generation 2022-05-23, FR generation Dec 2024, FR and IT_NORD load 2024-12-31, PL load 2024-06-13 | Handled by per-day detection (ADR-004) |
| 2026-10-03 | FR | Load gaps 2019–2023: 8 h, 2 h, 9 h, 21 h, 5 h per year (3–11 separate gaps a year); 2025: 3.8 h | Kept as is; completeness test in dbt staging |
| 2026-10-03 | ES | Load 2025: one ~35.5 h gap (34,898 of 35,040 rows). Single missing quarters in 2023, 2024, 2026 | Same |
| 2026-10-03 | PT | Load is **hourly** in every year (2019–2026), while load in other zones is 15-min (DE_LU, NL, BE since 2019; ES from 2022-05-23; PL 2024-06-13; FR and IT_NORD 2024-12-31). 2026 has 4× fewer rows than other zones for that reason; no rows missing | None: `resolution_minutes` = 60. Normalise to energy (MWh) before comparing zones |
| 2026-10-03 | NL | Reports an "Actual Consumption" column for every production type | Only "Actual Aggregated" kept (ADR-003) |
| 2026-10-03 | DE_LU | Nuclear generation ends 2023-04-15 21:45 UTC | Expected (nuclear phase-out); not a data gap |
| 2026-10-03 | BE, IT_NORD, FR, ES, PL | "Energy storage" type appears from 2025: BE and IT_NORD 2025-01-01 (CET), FR 2025-05, ES 2025-10, PL 2026-09 | New series, not a gap; Q3 must not read its absence before 2025 as zero storage |
| 2026-10-03 | PL | **Prices before delivery day 2019-11-20 are in PLN**, not EUR (monthly avg ~200–270 vs ~45 after; Poland joined market coupling that day). entsoe-py ignores the currency field | Left out in `stg_prices`, **not converted** (ADR-005 update). PL 2019 is flagged partial (`pln_prices_excluded`); PL analysis starts 2020. Negative-hour counts unaffected (all PLN prices > 0) |
| 2026-10-03 | 7 CET zones | Local year 2019 is missing its first hour (data starts 2019-01-01 00:00 UTC = 01:00 CET) | Completeness 0.9999; accepted |
| 2026-10-03 | IT_NORD | No negative prices 2019–2026; zero prices in 2020, 2025, 2026 | Real data, not a gap: report as such in Q1 |
| 2026-10-03 | ES, PT | No price below 0 before 2024 but many at exactly 0 (ES 2023: 109 h) | Report `zero_or_negative_hours` next to `negative_hours` (ADR-005) |
| 2026-10-03 | NL | ENTSO-E "Solar" covers ~2% of Dutch solar output (0.49 TWh vs 22 TWh CBS, 2024): mostly missing rooftop/small PV | NL solar_share flagged unusable; NL solar capture rate indicative only; NL left out of the share-based Q2 chart |
| 2026-10-03 | PL | Solar reported only from 2020-04-10 (none in 2019, 73% of 2020 hours) | PL 2019–2020 solar metrics null (coverage < 0.95, ADR-006) |
| 2026-10-03 | FR, PT, PL | Wind Offshore appears mid-series (FR 2023-06, PT 2020-06, PL 2026-07): new farms, not gaps | Combined with onshore as `wind` |
| 2026-10-03 | all | Generation for the current day ends ~1 day before prices (day-ahead prices cover tomorrow) | 2026 coverage 0.993 to 0.997; only matched hours used |
| 2026-10-04 | all | Current-year metrics ran to different days per zone and mart (prices to tomorrow, generation ~1 day behind, PT's last day partly published), and current-year completeness was 1.0 by construction | One run-wide as-of date (`int_as_of`), all current-year data cut there; expected hours to the end of that date (ADR-005 update) |
| 2026-10-04 | ES, PT | May 2025: prices split in 389 hours (6 to 136 in other months); ES 239 negative hours, PT 4. Follows the 28 Apr 2025 blackout: ES→PT trading halted, then REN capped imports from Spain (Bloomberg, 18 May 2025) | Kept; disclosed in Q1-2 and README; ES and PT not treated as one block for 2025 |
| 2026-10-04 | FR | 2024 negative hours 352 vs 359 published by RTE; gap entirely in H1 (226 vs 233); 2023 matches exactly (147) | Unexplained; disclosed in ADR-005 |
| 2026-10-04 | IT_NORD | No negative price ever; lowest price exactly 0 | Market rule: GME day-ahead offers must be ≥ 0 €/MWh (DTF n. 12 MPE); noted wherever IT_NORD is ranked |
