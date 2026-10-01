# Roadmap

Target: **3 weeks** (2026-10-01 → 2026-10-21). One commit minimum every working day.

## Phase 0 — Setup (Day 1) ← we are here
- [x] Create repo `negative-hours`
- [x] Scaffold folders, README, .gitignore
- [x] Create Obsidian vault `control-room`
- [x] Publish repo to GitHub (public) & first push
- [ ] Register on ENTSO-E Transparency Platform + request API key
- [ ] Install `uv` on the Mac, open repo in VS Code
- [ ] Decide bidding zones → [[04 Decisions/Decision Index|decision]]

## Phase 1 — Ingestion (Days 2–4)
- [ ] `pyproject.toml` with dependencies (entsoe-py, pandas, pyarrow, duckdb, python-dotenv)
- [ ] `pipeline/extract.py`: day-ahead prices per zone, per year → Parquet
- [ ] Add generation per type (solar, wind) and load
- [ ] Handle 60-min vs 15-min resolution, DST, missing data
- [ ] Backfill 2019 → today
- [ ] Data quality notes in [[03 Data/Data Dictionary]]

## Phase 2 — Warehouse (Days 5–7)
- [ ] dbt-duckdb project in `warehouse/`
- [ ] Staging models (prices, generation, load)
- [ ] Marts: `fct_prices_hourly`, `fct_negative_hours`, `fct_capture_prices`, `fct_battery_arbitrage`
- [ ] Tests (not null, unique, accepted ranges) + `dbt docs`

## Phase 3 — Analysis (Days 8–12)
- [ ] Q1 Negative hours
- [ ] Q2 Solar capture rate
- [ ] Q3 Battery arbitrage value
- [ ] Q4 EV charging windows
- [ ] One finding note per insight in `06 Findings/`

## Phase 4 — Ship (Days 13–16)
- [ ] Dashboard (live, embedded on sbaiii.com)
- [ ] GitHub Actions: scheduled refresh
- [ ] Architecture diagram

## Phase 5 — Story (Days 17–21)
- [ ] Exec memo (1 page, 3 recommendations)
- [ ] Final README with headline numbers + screenshots
- [ ] Project page on sbaiii.com
- [ ] LinkedIn post
