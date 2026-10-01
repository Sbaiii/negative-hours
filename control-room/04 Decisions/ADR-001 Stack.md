# ADR-001: Stack

**Date:** 2026-10-01 · **Status:** accepted

## Context
Need a stack that is free, runs on a laptop and in GitHub Actions, and matches what European data teams use.

## Options
1. Python + DuckDB + dbt (local, free)
2. BigQuery + dbt (cloud, free tier, needs GCP setup)
3. Python + pandas only (simple, but no modelling layer)

## Decision
Option 1: Python (`uv`) for extraction → Parquet → DuckDB + `dbt-duckdb` for modelling → GitHub Actions for refresh.

## Why
- Zero cost, zero cloud credentials to manage.
- dbt shows analytics-engineering skills (layered models, tests, docs) — highly valued in EU job ads.
- DuckDB handles millions of rows on a laptop easily.

## Consequences
- Easy to migrate to BigQuery/Snowflake later (dbt models are portable).
- Dashboard must read from exported files, not a live DB server.
