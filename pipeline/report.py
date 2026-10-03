"""Print a Markdown summary of the raw data and the warehouse (for the CI job summary).

uv run python -m pipeline.report >> "$GITHUB_STEP_SUMMARY"
"""

import duckdb

from pipeline.config import RAW_DIR, REPO_ROOT

WAREHOUSE = REPO_ROOT / "data" / "warehouse.duckdb"
DATASETS = ("prices", "generation", "load")
TABLES = (
    "fct_negative_hours",
    "fct_capture_prices",
    "fct_battery_arbitrage",
    "fct_hourly_profile",
    "fct_ev_charging",
    "battery.arbitrage_daily",
)


def main() -> None:
    con = duckdb.connect(str(WAREHOUSE), read_only=True)
    con.execute("set TimeZone = 'UTC'")
    con.execute("set enable_progress_bar = false")

    as_of, limiting_zone, last_price_day, _ = con.sql(
        "select * from int_as_of"
    ).fetchone()
    print(
        f"**As-of date: {as_of}** (all current-year numbers stop here; limited by {limiting_zone})."
    )
    print(f"Prices are complete in every zone up to {last_price_day}.\n")

    print("### Raw data (Parquet)\n")
    print("| Dataset | Rows | Zones | First period (UTC) | Last period (UTC) |")
    print("|---|---:|---:|---|---|")
    for name in DATASETS:
        rows, zones, first, last = con.sql(
            f"select count(*), count(distinct zone), min(ts_utc), max(ts_utc) "
            f"from read_parquet('{RAW_DIR / name}/**/*.parquet', hive_partitioning = true)"
        ).fetchone()
        print(
            f"| {name} | {rows:,} | {zones} | {first:%Y-%m-%d %H:%M} | {last:%Y-%m-%d %H:%M} |"
        )

    print("\n### Latest day-ahead prices per zone\n")
    print("| Zone | Last local day | Periods that day |")
    print("|---|---|---:|")
    for zone, day, periods in con.sql(
        "select zone, local_date, count(*) from int_prices_local "
        "where (zone, local_date) in (select zone, max(local_date) from int_prices_local group by zone) "
        "group by zone, local_date order by zone"
    ).fetchall():
        print(f"| {zone} | {day} | {periods} |")

    print("\n### Warehouse tables\n")
    print("| Table | Rows |")
    print("|---|---:|")
    for table in TABLES:
        print(
            f"| {table} | {con.sql(f'select count(*) from {table}').fetchone()[0]:,} |"
        )
    con.close()


if __name__ == "__main__":
    main()
