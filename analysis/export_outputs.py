"""Export small mart tables from the DuckDB warehouse to CSV (committed, unlike data/).

Run after `dbt build` and `python -m models.run_battery` (from the repo root):
    uv run python analysis/export_outputs.py
"""

from pathlib import Path

import duckdb

REPO_ROOT = Path(__file__).resolve().parent.parent
WAREHOUSE = REPO_ROOT / "data" / "warehouse.duckdb"
OUTPUTS = REPO_ROOT / "analysis" / "outputs"

# table -> sort order
EXPORTS = {
    "fct_negative_hours": "zone, local_year",
    "fct_capture_prices": "zone, local_year",
    "fct_battery_arbitrage": "zone, local_year, battery_duration_h",
    "fct_hourly_profile": "zone, local_year, season, local_hour",
    "fct_ev_charging": "zone, local_year, season",
}


def main() -> None:
    OUTPUTS.mkdir(parents=True, exist_ok=True)
    with duckdb.connect(str(WAREHOUSE), read_only=True) as con:
        for table, order_by in EXPORTS.items():
            path = OUTPUTS / f"{table}.csv"
            con.sql(
                f"copy (select * from {table} order by {order_by}) to '{path}' (header)"
            )
            print(f"wrote {path.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
