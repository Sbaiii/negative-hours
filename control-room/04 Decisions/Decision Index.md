# Decision Index

| # | Decision | Status | Date |
|---|----------|--------|------|
| [[ADR-001 Stack]] | Python + DuckDB + dbt + GitHub Actions | accepted | 2026-10-01 |
| [[ADR-002 Bidding Zones]] | 8 zones: ES, PT, FR, DE_LU, NL, BE, PL, IT_NORD | accepted | 2026-10-01 |
| [[ADR-003 Raw Price Storage]] | Parquet per zone per UTC year; resolution inferred; current year always refreshed | accepted | 2026-10-01 |
| [[ADR-004 Resolution Detection]] | resolution_minutes = most common spacing per series and UTC day, gaps logged not stored | accepted | 2026-10-03 |
| [[ADR-005 Negative Hours Metric]] | Q1: duration-weighted hours, local year, < 0 headline and ≤ 0 alongside | accepted | 2026-10-03 |
| [[ADR-006 Hourly Grid and Capture Prices]] | Q2: hourly grid for prices + generation; capture price = MWh-weighted price; tech metrics need 95% coverage | accepted | 2026-10-03 |
| [[ADR-007 Battery Arbitrage Model]] | Q3: 1 MW battery, daily LP on cleared day-ahead prices (perfect foresight), 88% round trip, 1 cycle/day, 1/2/4 h | accepted | 2026-10-03 |
| [[ADR-008 EV Charging Strategies]] | Q4: seasons inside the calendar year; EV 10 kWh/day at 7 kW, continuous block; immediate 18:00 vs overnight vs smart; wholesale only | accepted | 2026-10-03 |
| [[ADR-009 Automated Daily Refresh]] | Daily GitHub Actions refresh at 12:30 UTC; raw data in the Actions cache (full backfill on a miss); commit only CSVs + dashboard JSON; Pages via Actions | accepted | 2026-10-03 |
