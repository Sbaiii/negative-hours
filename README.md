# Negative Hours
### Europe's electricity market in the renewables era

> How often is power free in Europe — and what is a battery worth in each country?

**Status:** 🚧 In progress (started 2026-10-01) · Live dashboard: _coming soon_ · Write-up: _coming soon_

---

## The problem

Solar and wind now push European wholesale electricity prices to **zero or below** for hours at a time. That breaks old business models (solar farms earn less exactly when they produce most) and creates new ones (batteries get paid to absorb free power). This project measures how big that shift is, country by country, and turns it into decisions.

## Questions

| # | Question | Business output |
|---|----------|-----------------|
| Q1 | How often are prices negative, by country and year? | Trend + country ranking |
| Q2 | Does solar cannibalise its own value? | Solar capture price & capture rate |
| Q3 | Where should you build a battery? | Estimated €/MW/year arbitrage revenue by country |
| Q4 | When should EVs and fleets charge? | Cheapest charging windows by country & season |

## Architecture

```
ENTSO-E API ──► pipeline/ (Python) ──► data/raw (Parquet)
                                         │
                                         ▼
                              warehouse/ (DuckDB + dbt)
                              staging → intermediate → marts
                                         │
                       ┌─────────────────┴─────────────────┐
                       ▼                                   ▼
                analysis/ (notebooks)              dashboard/ (live)
                       │
                       ▼
                docs/ (exec memo)
        Scheduled refresh: GitHub Actions
```

## Repo layout

| Folder | What lives there |
|--------|------------------|
| `pipeline/` | Data extraction from the ENTSO-E Transparency Platform |
| `warehouse/` | dbt project: models, tests, documentation |
| `analysis/` | Notebooks answering Q1–Q4 |
| `dashboard/` | Live dashboard source |
| `docs/` | Exec memo, figures, methodology |
| `control-room/` | Obsidian vault: project brief, roadmap, decision log, daily log |

## Data source

[ENTSO-E Transparency Platform](https://transparency.entsoe.eu/) — official European grid data (day-ahead prices, generation by source, load).

## Run it locally

You need [uv](https://docs.astral.sh/uv/) and a free ENTSO-E API token
(create an account on the [Transparency Platform](https://transparency.entsoe.eu/), then request
"Restful API access" by email; the token appears in your account settings once approved).

```bash
git clone https://github.com/Sbaiii/negative-hours.git
cd negative-hours
uv sync                       # creates .venv with Python 3.12 and all dependencies
cp .env.example .env          # then paste your token after ENTSOE_API_KEY=
```

**Download day-ahead prices** (8 bidding zones, 2019 → today):

```bash
uv run python -m pipeline.extract                                  # everything
uv run python -m pipeline.extract --zones ES DE_LU --start-year 2024  # a subset
uv run python -m pipeline.extract --force                          # re-download existing files
```

Output is one Parquet file per zone and year:

```
data/raw/prices/zone=ES/year=2024.parquet
  ts_utc · zone · price_eur_mwh · resolution_minutes
```

Timestamps are UTC (period start). `resolution_minutes` is 60 until the market switched to
15-minute products on 2025-10-01, then 15. Files for past years are skipped if they already
exist; the current year is always refreshed. A full backfill takes a few minutes.

---

Built by [Abdellah Sbai](https://sbaiii.com)
