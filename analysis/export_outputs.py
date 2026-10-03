"""Export small mart tables from the DuckDB warehouse to CSV (committed, unlike data/).

Run after `dbt build` (from the repo root):
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
