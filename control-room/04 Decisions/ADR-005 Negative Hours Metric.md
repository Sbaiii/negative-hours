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

## Why
- **Durations, not rows:** since 2025-10-01 a period is 15 min, so counting rows inflates recent years 4×: ES 2026 has 2,737 negative rows but 684.25 negative hours; DE_LU 2025 has 724 rows vs 574.75 h. Durations make 2019 and 2026 comparable.
- **Local year:** a "2024" that starts at 01:00 on 1 January (CET) would confuse anyone reading the numbers. DST is handled by working in UTC instants: 23- and 25-hour days still sum to 8,760 / 8,784 hours.
- **< 0 and ≤ 0:** Iberia often clears at exactly 0 (ES 2023: 0 negative hours, 109 zero-or-negative). "< 0" is the standard definition and matches published counts; "≤ 0" shows the free-power hours that matter for batteries and EV charging (Q3, Q4).
- **Checked:** DE_LU gives 211, 298, 139, 69, 301 and 457 negative hours for 2019–2024, the figures published for Germany. An independent recount from raw Parquet gives the same 574.75 h for DE_LU 2025.

## Consequences
- 2019 is 1 hour short in CET zones (data starts 2019-01-01 00:00 UTC = 01:00 CET): completeness 0.9999.
- PL 2019 only covers 2019-11-20 → 12-31, because earlier PL prices are in PLN (left out in `stg_prices`); its completeness test warns, by design.
- Tables keyed by local year can't be compared 1:1 with the UTC-year raw files.
