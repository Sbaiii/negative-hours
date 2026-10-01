# ADR-003: Raw price storage layout

**Date:** 2026-10-01 · **Status:** accepted

## Context
`pipeline/extract.py` saves day-ahead prices one file per zone per year. We need to decide which "year" (UTC or local), how to record resolution, and how reruns behave.

## Options
1. Partition by **local** calendar year of each zone
2. Partition by **UTC** calendar year
3. One file per zone, rewritten each run

## Decision
Option 2. Files live at `data/raw/prices/zone=<ZONE>/year=<YYYY>.parquet`, with years running 00:00 UTC Jan 1 to 00:00 UTC Jan 1, start inclusive and end exclusive.
- `resolution_minutes` is inferred per row from the spacing to neighbouring timestamps, not hard-coded from the 2025-10-01 switch date.
- Missing prices are dropped and logged, not stored as NULL.
- Past years are skipped if the file exists; the **current year is always re-downloaded**.

## Why
- Matches the "everything in UTC" convention; local years would put the first 1–2 hours of Jan 1 in the previous file depending on the zone.
- Per-year files keep each API request small and make reruns cheap.
- The current year is still growing, so a "skip if exists" rule would freeze it.
- Inferring resolution survives zones that switch on a different date.

## Consequences
- Local-time analyses (e.g. "hours in 2024, Spanish time") must read neighbouring year files; handle that in dbt, not in raw.
- Gaps show up as missing timestamps, so data quality checks in dbt must test for completeness.

## Update 2026-10-01: generation and load
The same layout and rules now apply to `data/raw/generation/` and `data/raw/load/`.
- Generation is stored **long** (zone × production_type × period) and keeps only "Actual Aggregated"; consumption columns (pumped storage pumping) are dropped. Net pumped-storage flows can't be rebuilt from raw; re-extract if that's ever needed.
- Generation resolution is inferred **per production type**, because types within one zone can report at different intervals.
- Generation and load are fetched a month at a time (the ENTSO-E limit) with retries per month, so one failed request doesn't redo the whole year.
