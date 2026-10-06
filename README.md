# Negative Hours
### How often is power free in Europe, and who makes money from it?

[![Daily refresh](https://github.com/Sbaiii/negative-hours/actions/workflows/refresh.yml/badge.svg)](https://github.com/Sbaiii/negative-hours/actions/workflows/refresh.yml)

**[Live dashboard](https://sbaiii.github.io/negative-hours/)** (updated daily) · **[Exec memo](docs/exec_memo.md)** (one page, three recommendations)

Solar and wind now push European wholesale electricity prices to **zero or below** for hours at a time. That breaks old business models (solar farms earn less exactly when they produce most) and creates new ones (batteries get paid to absorb free power). This project measures that shift in 8 bidding zones across Europe from 2019 to today, using official grid data from the [ENTSO-E Transparency Platform](https://transparency.entsoe.eu/), and turns it into decisions.

## Key results

![Negative prices went from rare to routine: 5 of 8 zones topped 500 hours in 2025; before 2023 no zone ever exceeded 298](docs/figures/q1_negative_hours_by_zone.svg)

- **Q1 · Negative prices became routine:** 5 of 8 zones topped 500 negative hours in 2025; before 2023 no zone ever exceeded 298.
- **Q2 · Solar earns about half the average price:** 51% to 59% in 5 zones in 2025, down from 92% to 102% in 2019; wind kept 86% to 97%.
- **Q3 · Batteries:** an optimised 2 h battery could have earned up to €85.6k per MW in Poland in 2025, €76.1k in Germany and the Netherlands, €36.6k in North Italy.
- **Q4 · EV charging moved to midday:** the cheapest hour moved from 03:00 or 04:00 (2019) to 12:00 to 14:00 (2025); smart charging cut the wholesale cost by 67% to 74% in 7 zones.

What it means and what to do about it: **[exec memo](docs/exec_memo.md)**.

<details>
<summary><b>All results by question</b> (charts, numbers, caveats)</summary>

Full years (2019 to 2025) are compared with full years. **2026 is not over: its figures are as of 2 Oct 2026** (the last day with complete prices and generation in all 8 zones) and are only compared with the **same dates of earlier years**, never with a full year. They are frozen in [`analysis/outputs/snapshots/2026-10-02/`](analysis/outputs/snapshots/2026-10-02/); a test checks every number quoted below and in the finding notes against it. Current values: the [live dashboard](https://sbaiii.github.io/negative-hours/) and `analysis/outputs/*.csv`.

#### Q1 · How often are prices negative?

- **Rare → routine.** In 2025, 5 of the 8 zones had more than 500 negative hours (hourly mean price below 0, the convention of RTE and REE); before 2023 no zone ever exceeded 298 (Germany, 2020). Checked against RTE (France 2023 to 2025 exact) and published German counts (2019 to 2024 exact).
- **2026, like for like.** From 1 Jan to 2 Oct, 2026 had more negative hours than the same dates of 2025 in Spain (747 vs 535), Portugal, France and Poland, and fewer in Germany (471 vs 525), the Netherlands and Belgium.
- **Frequency ≠ depth.** Spain had nearly as many negative hours as Germany in 2025 (556 vs 576), but they averaged −2.11 €/MWh vs −10.92.
- **Spain and Portugal split in 2025.** Portugal had 200 negative hours to Spain's 556, mostly because of May 2025, when imports from Spain were capped after the 28 April blackout (REN, via Bloomberg).
- **North Italy never goes negative, by rule.** No negative price from 2019 to 2 Oct 2026: GME accepts day-ahead offers only at or above 0 €/MWh ([DTF n. 12 MPE](https://www.mercatoelettrico.org/portals/0/Documents/it-IT/20150220DTF12MPE.pdf)). Its place in rankings partly reflects market design.

Notebook: [`analysis/q1_negative_hours.ipynb`](analysis/q1_negative_hours.ipynb) · Metric: [ADR-005](control-room/04%20Decisions/ADR-005%20Negative%20Hours%20Metric.md)

#### Q2 · Does solar cannibalise its own value?

![In 2025 solar earned only 51% to 59% of the average power price in 5 of 8 zones, down from 92% to 102% in 2019](docs/figures/q2_solar_capture_rate_by_zone.svg)

- **Solar earns about half the average price.** In 2025 its capture rate was 51 to 59% in Belgium, Germany, Portugal, Spain and France, down from 92 to 102% in 2019. Germany's 2024 solar capture price (46.23 €/MWh) matches the published German solar market value.
- **More solar, less value, everywhere.** In all 7 zones with usable data (the Netherlands left out; Poland from 2021, its first full year of solar data), solar's share rose and its capture rate fell from 2019 to 2025 (Spain: 6% solar at 102% → 20% at 55%).
- **2026, like for like.** Over the same dates (1 Jan to 2 Oct), the solar capture rate rose in 2026 in Belgium (47.6% → 55.7%), Germany (48.0% → 51.8%), the Netherlands and North Italy, and fell in Spain, Portugal, France and Poland. No cause is claimed.
- **Wind holds up.** Wind kept 86 to 97% of the average price in 2025 in 7 zones. North Italy's 102% is left out: wind is 0.3% of its reported generation, too little to compare.
- **2022 was a timing effect.** Capture rates jumped in 2022 outside Iberia because the most expensive months (July to September) were also the sunniest; in Spain and Portugal prices peaked in January to March and fell after the Iberian gas price cap started (15 June 2022). The within-month erosion kept going every year.
- **Local or regional?** France's and Belgium's capture rates track the coupled region's solar share as closely as their own; with yearly data the two can't be separated (inconclusive).
- **Caveat:** generation is *as reported to ENTSO-E*. For France it is 6% below the national figure (23.3 vs 24.8 TWh of solar in 2024, RTE); the Netherlands' solar series misses ~98% of Dutch solar, so NL solar figures are indicative only (its wind series is usable). Capture prices match each generation period to the price over the same span (15-min where both are 15-min, from Oct 2025).

Notebook: [`analysis/q2_capture_prices.ipynb`](analysis/q2_capture_prices.ipynb) · Method: [ADR-006](control-room/04%20Decisions/ADR-006%20Hourly%20Grid%20and%20Capture%20Prices.md)

#### Q3 · Where is a battery worth the most?

![Day-ahead arbitrage paid most in Poland in 2025: up to €86k per MW, vs €37k in North Italy](docs/figures/q3_revenue_by_zone_2025.svg)

- **Up to €86k per MW in 2025.** A 1 MW / 2 MWh battery trading the day-ahead market could have earned at most €85.6k per MW in Poland, €76.1k in Germany and the Netherlands, and €36.6k in North Italy. Germany 2024 (€66k) is the same order of magnitude as a published day-ahead-only estimate (~€70k, Gridcog; its assumptions are not published).
- **2026, like for like.** From 1 Jan to 2 Oct, a battery earned more in 2026 than over the same dates of 2025 in all 8 zones: +23% to +52% at 15-min prices, and +16% to +42% when 2026 is re-solved on hourly prices (15-minute products add 2 to 10%).
- **Negative hours are a signal, not the money.** Zones and years with more negative hours earned more: r = 0.40 across all 55 full zone-years, 0.76 without 2022. These are not independent points (coupled zones move together) and both series trend upward, so part of this is a shared time trend, not a link. Being paid to charge was at most 11% of a year's revenue.
- **Longer batteries earn more, less per hour added.** In 2025, 4 hours earned 64 to 76% more than 2 hours.
- **North Italy:** North Italy's day-ahead market accepts no offers below 0 €/MWh (GME rule), so it can never go negative; its place in rankings partly reflects market design.
- **Caveat:** an upper bound for one market: perfect foresight on cleared day-ahead prices, 1 cycle a day, 88% round trip. Excludes intraday, balancing and capacity markets, degradation, grid fees and all costs. Not investment advice.

Notebook: [`analysis/q3_battery_arbitrage.ipynb`](analysis/q3_battery_arbitrage.ipynb) · Model: [ADR-007](control-room/04%20Decisions/ADR-007%20Battery%20Arbitrage%20Model.md), [`battery/model.py`](battery/model.py)

#### Q4 · When should EVs charge?

![Smart charging cut an EV's wholesale cost by 67% to 74% in 2025, except in North Italy (39%)](docs/figures/q4_smart_charging_savings_2025.svg)

- **The cheap hours moved to midday.** The cheapest hour of the day started at 03:00 or 04:00 in 2019 in every zone, and at 12:00 to 14:00 in 2025; from March to September 2025 it fell between 12:00 and 16:00 everywhere.
- **Smart charging cuts the wholesale cost by about 70%.** For 10 kWh a day at 7 kW, charging in the cheapest block of the day instead of at 18:00 saved €182 to €368 a year in 2025 (67% to 74%; North Italy 39%).
- **"Charge at night" is losing its edge.** Overnight charging got 88% to 100% of the smart saving in 2019, only 23% to 67% in 2025. In Spain, from 1 Jan to 2 Oct 2026, it cost 34.9% more than charging at 18:00; over the same dates of 2025 it was still 4.1% cheaper.
- **North Italy:** North Italy's day-ahead market accepts no offers below 0 €/MWh (GME rule), so it can never go negative; its place in rankings partly reflects market design.
- **Caveat:** wholesale day-ahead price only: retail margins, taxes and grid fees are excluded, so these are not household bills.

Notebook: [`analysis/q4_ev_charging.ipynb`](analysis/q4_ev_charging.ipynb) · Method: [ADR-008](control-room/04%20Decisions/ADR-008%20EV%20Charging%20Strategies.md)

All findings, with exact numbers and caveats: [`control-room/06 Findings/`](control-room/06%20Findings/)

</details>

## Questions

| # | Question | Business output |
|---|----------|-----------------|
| Q1 | How often are prices negative, by zone and year? | Trend and zone ranking |
| Q2 | Does solar cannibalise its own value? | Solar capture price and capture rate |
| Q3 | Where should you build a battery? | Estimated €/MW/year arbitrage revenue by zone |
| Q4 | When should EVs and fleets charge? | Cheapest charging windows by zone and season |

## Architecture

```
            ┌──────────── GitHub Actions, daily 12:30 UTC (refresh.yml) ────────────┐
            │                                                                       │
ENTSO-E API ──► pipeline/ (Python) ──► data/raw (Parquet, kept in the Actions cache)
            │                                │                                      │
            │                                ▼                                      │
            │                     warehouse/ (DuckDB + dbt, tests)                  │
            │                     staging → intermediate → marts                    │
            │                                │                                      │
            │                     models/ (battery LP) ──► battery.arbitrage_daily  │
            │                                │                                      │
            │               ┌────────────────┴────────────────┐                     │
            │               ▼                                 ▼                     │
            │   analysis/outputs/*.csv            dashboard/data/dashboard.json     │
            │   (committed if changed)            (committed if changed)            │
            └───────────────────────────────────────────────┬───────────────────────┘
                                                            ▼
                    analysis/ (notebooks, docs/figures)   dashboard/ ──► GitHub Pages (pages.yml)
```

## How to run

You need [uv](https://docs.astral.sh/uv/) and a free ENTSO-E API token
(create an account on the [Transparency Platform](https://transparency.entsoe.eu/), then request
"Restful API access" by email; the token appears in your account settings once approved).

```bash
git clone https://github.com/Sbaiii/negative-hours.git
cd negative-hours
uv sync                       # creates .venv with Python 3.12 and all dependencies
cp .env.example .env          # then paste your token after ENTSOE_API_KEY=
```

**Download the data** (8 bidding zones, 2019 → today):

```bash
uv run python -m pipeline.extract                                      # everything
uv run python -m pipeline.extract --datasets prices                    # one dataset
uv run python -m pipeline.extract --zones ES DE_LU --start-year 2024   # a subset
uv run python -m pipeline.extract --force                              # re-download existing files
```

| `--datasets` | ENTSO-E source | Columns |
|---|---|---|
| `prices` | Day-ahead prices | `ts_utc` · `zone` · `price_eur_mwh` · `resolution_minutes` |
| `generation` | Actual generation per production type | `ts_utc` · `zone` · `production_type` · `generation_mw` · `resolution_minutes` |
| `load` | Actual total load | `ts_utc` · `zone` · `load_mw` · `resolution_minutes` |

Output is one Parquet file per dataset, zone and year, e.g.
`data/raw/generation/zone=ES/year=2024.parquet`.

- Timestamps are UTC (start of the period); a "year" is a UTC calendar year.
- `resolution_minutes` is read from the data, never assumed. Prices are 60 until the market
  switched to 15-minute products on 2025-10-01, then 15; generation and load vary by zone
  (and by production type).
- Generation is in long format (one row per type per period) and keeps only what plants
  feed in: pumped-storage *consumption* is dropped.
- Files for past years are skipped if they already exist; the current year is always refreshed.
- Prices are requested a year at a time, generation and load a month at a time; each
  request is retried with backoff on rate limits and server errors.

**Build the warehouse** (dbt + DuckDB, run from `warehouse/`):

```bash
cd warehouse
uv run dbt build --exclude source:battery+   # seed, models and tests → data/warehouse.duckdb
cd ..
uv run python -m battery.run          # battery LP for every zone-day (~3 min) → battery.arbitrage_daily
cd warehouse
uv run dbt build --select source:battery+    # Q3 mart from the LP results
uv run dbt docs generate    # then `uv run dbt docs serve` to browse model docs
cd ..
uv run python analysis/export_outputs.py   # marts → analysis/outputs/*.csv
uv run python analysis/run_notebooks.py    # re-run the four notebooks, re-export the charts
uv run python dashboard/build_data.py      # → dashboard/data/dashboard.json
```

**Preview the dashboard** (it fetches its JSON, so open it through a local server, not as a file):

```bash
python3 -m http.server 8000 --directory dashboard   # then open http://localhost:8000
```

## Repo layout

| Folder | What lives there |
|--------|------------------|
| `pipeline/` | Data extraction from the ENTSO-E Transparency Platform |
| `warehouse/` | dbt project: models, tests, documentation |
| `models/` | Python models: battery arbitrage linear program (Q3) |
| `analysis/` | Notebooks answering Q1 to Q4, `outputs/` (CSVs and the frozen snapshots) |
| `dashboard/` | Live dashboard: static page + `build_data.py` (writes `data/dashboard.json`) |
| `tests/` | `pytest`: pipeline and model tests, and the check of every quoted number |
| `.github/workflows/` | Daily refresh and dashboard deployment ([ADR-009](control-room/04%20Decisions/ADR-009%20Automated%20Daily%20Refresh.md)) |
| `docs/` | [Exec memo](docs/exec_memo.md) and the charts used in the README and finding notes (`docs/figures/`, SVG and PNG) |
| `control-room/` | Obsidian vault: project brief, roadmap, decision log, daily log |

## Decisions

Every non-trivial choice (tool, metric definition, scope cut) has a decision record in [`control-room/04 Decisions/`](control-room/04%20Decisions/):

| ADR | Decision |
|-----|----------|
| [ADR-001](control-room/04%20Decisions/ADR-001%20Stack.md) | Stack: Python, DuckDB, dbt, GitHub Actions |
| [ADR-002](control-room/04%20Decisions/ADR-002%20Bidding%20Zones.md) | The 8 bidding zones: ES, PT, FR, DE_LU, NL, BE, PL, IT_NORD |
| [ADR-003](control-room/04%20Decisions/ADR-003%20Raw%20Price%20Storage.md) | Raw data as Parquet per zone and UTC year |
| [ADR-004](control-room/04%20Decisions/ADR-004%20Resolution%20Detection.md) | Price resolution (hourly or 15-minute) read from the data, never assumed |
| [ADR-005](control-room/04%20Decisions/ADR-005%20Negative%20Hours%20Metric.md) | Negative hours: hours whose hourly mean price is below 0 (RTE and REE convention) |
| [ADR-006](control-room/04%20Decisions/ADR-006%20Hourly%20Grid%20and%20Capture%20Prices.md) | Solar and wind capture prices, matched on the generation period |
| [ADR-007](control-room/04%20Decisions/ADR-007%20Battery%20Arbitrage%20Model.md) | Battery arbitrage: daily linear program with perfect foresight |
| [ADR-008](control-room/04%20Decisions/ADR-008%20EV%20Charging%20Strategies.md) | EV charging strategies: at 18:00, overnight, smart |
| [ADR-009](control-room/04%20Decisions/ADR-009%20Automated%20Daily%20Refresh.md) | Automated daily refresh and dashboard deployment |

## Validation

- **Negative hours match official statistics:** Germany 2019 to 2024 and France 2023 to 2025 exactly (published German counts, RTE), Spain 2025 within one hour of pv-magazine's count.
- **Solar value:** Germany's 2024 solar capture price matches the published German solar market value to within one cent (46.24); France's solar output on ENTSO-E is checked against RTE's national figure.
- **Battery revenue:** Germany 2024 is the same order of magnitude as a published day-ahead-only estimate (Gridcog).
- **Automated checks:** dbt tests on every model (uniqueness, ranges, completeness, hourly vs quarter-hour counts), and `pytest` checks that every number in this README, the finding notes and the exec memo matches the frozen snapshot in [`analysis/outputs/snapshots/`](analysis/outputs/snapshots/).

## Caveats

- **Generation is as reported to ENTSO-E.** It is below national statistics for France and far below for the Netherlands, so Dutch solar figures are indicative only.
- **Day-ahead market only.** Battery revenue is an upper bound (perfect foresight, no intraday, balancing or capacity revenue, no costs). Not investment advice.
- **Wholesale prices only.** EV costs exclude taxes, grid fees and retail margins, so they are not household bills.
- **North Italy's price floor.** Its day-ahead market accepts no offers below 0 €/MWh, so it can never go negative.
- **2026 is not over.** Its figures are compared only with the same dates of earlier years.

---

Built by [Abdellah Sbai](https://sbaiii.com) · [LinkedIn](https://www.linkedin.com/in/sbaiii/)
