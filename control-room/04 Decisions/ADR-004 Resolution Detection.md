# ADR-004: How `resolution_minutes` is detected

**Date:** 2026-10-03 · **Status:** accepted (replaces the resolution bullet of [[ADR-003 Raw Price Storage]])

## Context
`resolution_minutes` says how long each period lasts, so MW can be turned into MWh. ADR-003 inferred it per row from the spacing to the nearest neighbouring timestamp. The overnight generation backfill showed that breaks for **sparse series**: pumped storage, offshore wind and hard coal in FR/BE/IT_NORD only have rows while producing, so gaps were written as resolutions (120, 3405, 29535 min), and a lone timestamp got 0.

## Options
1. Keep per-row spacing, but cap it at 60 min
2. Most common spacing per series and **calendar month** (first proposal)
3. Most common spacing per series and **UTC day**, with fallbacks and a rule for switches inside a day

## Decision
Option 3. For each series (zone, or zone + production type):
1. Spacings of 60 min or less between consecutive timestamps are evidence; longer ones are gaps.
2. Each UTC day takes its most common spacing, snapped to 15/30/60.
3. A series needs **at least 3 timestamps on a day** to set that day's value (with fewer, its one spacing is as likely a gap: IT_NORD storage had a single point on 2026-10-03, 60 min after the previous one). Such a day, or one with no evidence, borrows, in order: the zone's value that day, the series' value that month, the zone's value that month. If none exists, the row is dropped with a warning (we never assume hourly).
4. If a row's spacing to the next timestamp is a standard interval *shorter* than its day's value, the shorter one wins.

Gaps are logged as counts of missing periods, never stored as a resolution. Duplicate timestamps are dropped (keep first) and logged.

## Why
- **Not months:** the data has mid-month switches from 60 to 15 min: ES load and generation on 2022-05-23, FR generation in Dec 2024, PL load on 2024-06-13. Because 15-min data has 4× the rows, a monthly majority would label ES's 22 hourly days in May 2022 as 15 min, a 4× error in energy.
- **UTC days:** the TSO switches above all happen at 00:00 UTC.
- **Rule 4:** the day-ahead price switch happened at CET midnight (2025-09-30 22:00 UTC), *inside* a UTC day. Gaps only make spacings longer, so they can't trigger the rule.
- **Zone before month:** checked on all 16.3M generation rows: on any given day, every type in a zone reports at the zone's interval.
- **Not option 1:** a lone point has no usable neighbour at all, and a single missing quarter makes a 30-min spacing in a 15-min series.

## Consequences
- Re-labelling every existing price and load file with the new rule changed **0 rows**. Only generation needed a re-fetch: FR, BE, IT_NORD (all years), ES 2022, plus NL 2019 (one Waste row labelled 30). Afterwards, re-labelling every raw file (2.2M price/load + 16.3M generation rows) with the final rule changes nothing, and only 15 and 60 occur.
- Tests in `tests/test_resolution.py` pin each rule (sparse series, lone points, duplicates, mid-month and mid-day switches).
- If a zone ever switches *coarser* (15 → 60) in the middle of a day, the switch day's minority part would be mislabelled. This has never happened in this data.
