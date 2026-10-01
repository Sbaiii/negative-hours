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

_Instructions added once the pipeline exists._

---

Built by [Abdellah Sbai](https://sbaiii.com)
