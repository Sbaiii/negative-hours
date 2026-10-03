# ADR-009: Automated daily refresh and dashboard publishing

**Date:** 2026-10-03 · **Status:** accepted

## Context
The project should stay current without anyone running it: new day-ahead prices every day, a rebuilt warehouse, and a public dashboard. Raw data (123 MB of Parquet) and the DuckDB warehouse are deliberately not in git, so a fresh CI runner starts with nothing.

## Options
1. Commit raw Parquet to git (or Git LFS)
2. Re-download everything on every run (~3 hours)
3. Keep raw data in the GitHub Actions cache; refresh only the current year; commit only small outputs

## Decision
Option 3, in `.github/workflows/refresh.yml` (daily) and `.github/workflows/pages.yml` (dashboard).

**Schedule:** daily at **12:30 UTC**, plus manual runs (`workflow_dispatch`). Day-ahead results for tomorrow are published around 12:45 CET/CEST (10:45 to 11:45 UTC), so 12:30 UTC leaves a margin in both winter and summer. One run at a time (`concurrency`).

**Cache strategy (data/raw):**
- Restore the newest cache entry (`restore-keys: raw-`), and save a new one under a unique key (`raw-<run id>-<attempt>`) after the download. Cache entries can't be overwritten, so a unique key per run is the only way to keep it current; GitHub evicts the oldest entries (10 GB repo limit, 7 days without use), and a daily run keeps the newest one warm.
- **Cache miss** (first run, or after 7 days without a run): full backfill 2019 to today (~3 h: prices 26 min, generation + load 2 h 12 min locally), flagged as a notice and in the job summary. Job timeout 330 min.
- **Cache hit:** re-download the **current year** only (the extractor always refreshes it, picking up late TSO revisions). In the first 7 days of January also re-download last year with `--force`, because its last day was fetched before it ended.
- The cache is saved even if a later step fails (`!cancelled()`), so a failed dbt test doesn't throw away a 3-hour backfill.

**Build:** `uv sync --locked` (lockfile), unit tests, `dbt build --exclude source:battery+` → `models.run_battery` → `dbt build --select source:battery+`. Any failing test fails the job, and nothing is committed.

**What gets committed:** only `analysis/outputs/*.csv` (the marts, ~1 MB) and `dashboard/data/` (one JSON, ~40 KB), and only if they changed, as `data: daily refresh YYYY-MM-DD` by `github-actions[bot]`. CSV values are rounded per column type and computed from exact decimal sums, so an unchanged input gives byte-identical files (no noise commits).

**Not committed:** raw Parquet, the DuckDB file, notebooks and charts (those are analysis snapshots, re-run by hand when a question is revisited).

**Dashboard:** static files in `dashboard/` (HTML, CSS, vanilla JS, inline SVG; no build step) deployed with GitHub Pages "Source: GitHub Actions". `pages.yml` runs on pushes that touch `dashboard/`, by hand, and is called by the refresh job, because a push made with the workflow's own `GITHUB_TOKEN` does not trigger other workflows. Only `index.html`, `style.css`, `app.js` and `data/` are published.

**Runner and action versions:**
- `runs-on: ubuntu-24.04`, not `ubuntu-latest`: GitHub moves `ubuntu-latest` to Ubuntu 26 from 19 Oct 2026, which would change Python builds, system libraries and tools under a pipeline that hasn't changed. Moving to a newer image is a deliberate commit.
- Each action is pinned to the latest **major tag that exists** in its repository, checked with `git ls-remote --tags` (not the latest release number): `actions/checkout@v7`, `actions/cache/restore@v6` and `actions/cache/save@v6`, `actions/configure-pages@v6`, `actions/upload-pages-artifact@v5`, `actions/deploy-pages@v5`, `astral-sh/setup-uv@v7`. setup-uv stopped publishing major tags after v7 (releases v8 to v10 only have full `vX.Y.Z` tags); moving past v7 means pinning a full version.

**Secret:** `ENTSOE_API_KEY` is a repository secret, passed as an environment variable. GitHub masks it in logs, and the extractor's log formatter also replaces `securityToken=…` with `***` (requests puts the full URL in error messages).

## Why
- Raw data in git would bloat history daily and breaks the "never commit data/" rule; LFS adds quota and cost.
- A full download every day would take ~3 h of runner time and put ~2,000 requests a day on ENTSO-E for data that doesn't change.
- Committing the small outputs gives a readable daily history of the headline numbers in git, and lets the dashboard be a plain static site.

## Consequences
- If the cache is evicted, one run takes ~3 h (still within limits).
- Past years are never re-checked automatically; a TSO correction to an old year needs a manual `--force` run.
- Notebooks and charts can drift behind the CSVs until re-run; the dashboard and CSVs are the "live" outputs.
- Each daily commit lands on `main`; pull before pushing local work.
