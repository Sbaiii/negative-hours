# Decision Index

| # | Decision | Status | Date |
|---|----------|--------|------|
| [[ADR-001 Stack]] | Python + DuckDB + dbt + GitHub Actions | accepted | 2026-10-01 |
| [[ADR-002 Bidding Zones]] | 8 zones: ES, PT, FR, DE_LU, NL, BE, PL, IT_NORD | accepted | 2026-10-01 |
| [[ADR-003 Raw Price Storage]] | Parquet per zone per UTC year; resolution inferred; current year always refreshed | accepted | 2026-10-01 |
| [[ADR-004 Resolution Detection]] | resolution_minutes = most common spacing per series and UTC day, gaps logged not stored | accepted | 2026-10-03 |
| [[ADR-005 Negative Hours Metric]] | Q1: duration-weighted hours, local year, < 0 headline and ≤ 0 alongside | accepted | 2026-10-03 |
