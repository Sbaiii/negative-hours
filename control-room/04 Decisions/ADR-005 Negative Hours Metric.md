# ADR-005: Negative-hours metric (Q1)

**Date:** 2026-10-03 · **Status:** accepted

## Context
Q1 asks how often day-ahead prices are negative, by zone and year. Three choices change the answer: what counts as "an hour", which year a period belongs to, and whether a price of exactly 0 counts.

## Options
1. Count rows (periods) with price < 0, grouped by UTC year
2. Sum period **durations**, grouped by **local** calendar year, and report both < 0 and ≤ 0

## Decision
Option 2, in `fct_negative_hours` (one row per zone × local year):
- `negative_hours` = Σ `duration_h` where price **< 0**: the headline number.
- `zero_or_negative_hours` = Σ `duration_h` where price **≤ 0**: reported next to it.
- `duration_h` = `resolution_minutes` / 60.
- The year is the **local** calendar year of the period start, in the zone's IANA time zone (seed `zones`).
- `completeness` = covered hours / hours in the local year (current year: up to the end of the last period). Averages are duration-weighted too.
- `is_partial_year` = current year **or** completeness < 0.98; `partial_reason` says why (`current_year`, `pln_prices_excluded`). Cross-zone and year-on-year comparisons use full years only.

## Why
- **Durations, not rows:** since 2025-10-01 a period is 15 min, so counting rows inflates recent years 4×: ES 2026 has 2,737 negative rows but 684.25 negative hours; DE_LU 2025 has 724 rows vs 574.75 h. Durations make 2019 and 2026 comparable.
- **Local year:** a "2024" that starts at 01:00 on 1 January (CET) would confuse anyone reading the numbers. DST is handled by working in UTC instants: 23- and 25-hour days still sum to 8,760 / 8,784 hours.
- **< 0 and ≤ 0:** Iberia often clears at exactly 0 (ES 2023: 0 negative hours, 109 zero-or-negative). "< 0" is the standard definition used in published counts (see Checked); "≤ 0" shows the free-power hours that matter for batteries and EV charging (Q3, Q4).
- **Checked against published counts:**
  - Germany (DE_LU) 2019 to 2024: 211, 298, 139, 69, 301, 457 hours, exactly the published figures. An independent recount from raw Parquet gives the same 574.75 h for 2025.
  - France 2023: 147 hours, exactly RTE's figure (53 in the first half, also exact) ([RTE, Bilan du fonctionnement du système électrique, premier semestre 2024](https://assets.rte-france.com/prod/public/2024-08/2024-08-02-bilan-s1-2024-fr.pdf)).
  - France 2024: 352 hours vs 359 published by RTE (−1.9%) ([RTE, Bilan électrique 2024, fiche prix](https://assets.rte-france.com/prod/public/2025-02/Bilan-electrique-2024-Fiche-prix.pdf)). The whole gap is in the first half: 226 vs RTE's 233 for H1 2024 (same S1 2024 report); the second half has no gap. Unexplained: it could be a difference in source series or in counting exact-zero hours; not resolved.

## Consequences
- 2019 is 1 hour short in CET zones (data starts 2019-01-01 00:00 UTC = 01:00 CET): completeness 0.9999.
- PL 2019 only covers 2019-11-20 → 12-31, because earlier PL prices are in PLN (see the update below).
- Tables keyed by local year can't be compared 1:1 with the UTC-year raw files.

## Update 2026-10-03: Polish prices before 2019-11-20
- **Decision:** keep excluding PL prices before 2019-11-19 23:00 UTC (delivery day 2019-11-20, when Poland joined European market coupling). ENTSO-E publishes them in PLN; we do **not** convert them with FX rates.
- **Why:** a conversion adds an outside dataset and a choice of rate (daily ECB fix? which hour?) for 10.5 months of one zone, and it can't change the Q1 answer: every PLN price was positive, so PL 2019 has 0 negative hours either way.
- **Consequence:** PL analysis starts in **2020**. PL 2019 stays in `fct_negative_hours` but only as a partial year (`is_partial_year = true`, `partial_reason = 'pln_prices_excluded'`, completeness 0.12) and is left out of charts and comparisons. The cut-off is one dbt var (`pl_eur_prices_start_utc`) used by both `stg_prices` and the mart.

## Update 2026-10-04: one as-of date for the current year, and an hourly-average column
- **As-of date.** Each build fixes one date (`int_as_of`): the last local day on which all 8 zones have a complete day of day-ahead prices **and** of generation. `int_prices_local` stops there, so every current-year number in every mart (and the battery model and dashboard) covers exactly the same days in every zone; a partly published day (tomorrow's prices, generation still arriving) never enters a metric. A dbt test fails if any zone's prices or generation stop before the as-of date or its as-of day is incomplete. Marts carry `data_through_date` (31 December, or the as-of date for the current year).
- **Real current-year completeness.** `expected_hours` for the current year now runs to the end of the as-of date, a calendar fact, instead of to the last period in the data. Before, completeness was 1.0 by construction for the current year; now a missing period lowers it.
- **Written numbers.** Prose and finding notes quote 2026 numbers "as of" a date, from a frozen snapshot (`analysis/outputs/snapshots/<as-of date>/`); a test checks every quoted 2026 number against it. The live CSVs and the dashboard keep moving.
- **`negative_hours_hourly_avg`.** Hours whose hourly **mean** price is below 0, for comparison with sources that publish hourly figures. The headline stays `negative_hours` (quarter-hours count as 0.25 h). The two are identical before 1 Oct 2025 (tested). In 2026 to 2 Oct the hourly-mean count differs by −1.9% (BE) to +11.3% (PT): +9.2% in ES, +5.5% in FR, +4.2% in PL, +1.7% in DE_LU, −1.3% in NL. It is higher where an hour mixes negative quarter-hours with quarter-hours at exactly 0, as in Iberia.
