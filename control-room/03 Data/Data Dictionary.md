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
