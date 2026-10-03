# Data Dictionary

_Filled in during Phase 1–2._

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
