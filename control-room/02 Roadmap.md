# Roadmap

Target: **3 weeks** (2026-10-01 → 2026-10-21). One commit minimum every working day.

## Phase 0 — Setup (Day 1) ✅
- [x] Create repo `negative-hours`
- [x] Scaffold folders, README, .gitignore
- [x] Create Obsidian vault `control-room`
- [x] Publish repo to GitHub (public) & first push
- [x] Register on ENTSO-E Transparency Platform + request API key
- [ ] Receive API approval → generate token → put in `.env` (waiting, ~3 working days)
- [x] Install `uv` on the Mac, open repo in VS Code
- [x] Decide bidding zones → [[04 Decisions/Decision Index|decision]]

## Phase 1 — Ingestion (Days 2–4)
- [x] `pyproject.toml` with dependencies (entsoe-py, pandas, pyarrow, duckdb, python-dotenv)
- [x] `pipeline/extract.py`: day-ahead prices per zone, per year → Parquet
- [x] Add generation per type (solar, wind) and load
- [x] Handle 60-min vs 15-min resolution, DST, missing data → [[04 Decisions/ADR-004 Resolution Detection|ADR-004]]; gaps logged, completeness tests in dbt
- [x] Backfill 2019 → today: prices, generation and load for all 8 zones (generation re-fetched for FR, BE, IT_NORD, ES 2022, NL 2019 after the resolution fix)
- [x] Data quality notes in [[03 Data/Data Dictionary]]

## Phase 2 — Warehouse (Days 5–7) ← we are here
- [x] dbt-duckdb project in `warehouse/`
- [x] Staging models (prices, generation, load)
- [ ] Marts: `fct_prices_hourly`, `fct_negative_hours` ✅, `fct_capture_prices` ✅, `fct_battery_arbitrage` ✅
- [x] Tests (not null, unique, accepted ranges) + `dbt docs`

## Phase 3 — Analysis (Days 8–12)
- [x] Q1 Negative hours → `analysis/q1_negative_hours.ipynb`, 3 charts in `docs/figures/`
- [x] Q2 Solar capture rate → `analysis/q2_capture_prices.ipynb`, 4 charts in `docs/figures/`; 2022 and regional hypotheses tested
- [x] Q3 Battery arbitrage value → daily LP (`models/battery.py`, ADR-007), `analysis/q3_battery_arbitrage.ipynb`, 4 charts in `docs/figures/`
- [ ] Q4 EV charging windows
- [ ] One finding note per insight in `06 Findings/` (Q1: 3 notes ✅, Q2: 5 notes ✅, Q3: 4 notes ✅)

## Phase 4 — Ship (Days 13–16)
- [ ] Dashboard (live, embedded on sbaiii.com)
- [ ] GitHub Actions: scheduled refresh
- [ ] Architecture diagram

## Phase 5 — Story (Days 17–21)
- [ ] Exec memo (1 page, 3 recommendations)
- [ ] Final README with headline numbers + screenshots
- [ ] Project page on sbaiii.com
- [ ] LinkedIn post
