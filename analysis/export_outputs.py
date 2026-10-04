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
    "fct_ytd_comparison": "zone, local_year",
}


def decimals(column: str) -> int:
    """Decimal places for a numeric column, by what it measures."""
    name = column.lower()
    if "price" in name or "eur" in name:
        return 2  # prices (EUR/MWh) and money (EUR)
    if "mwh" in name:
        return 3  # energy
    if "hours" in name:
        return 2  # durations: multiples of 0.25 h
    # Rates, shares, coverage, cycles and other ratios: 6 decimals, so a percentage
    # rounded to 1 decimal from the CSV can't land on a rounding boundary.
    return 6


def rounded_select(con: duckdb.DuckDBPyConnection, table: str) -> str:
    """SELECT list with every non-integer number cast to a fixed number of decimals.

    Fixed decimals make the CSV text identical across rebuilds (no 0.1 vs
    0.10000000000000001), so a daily refresh only commits real changes.
    """
    columns = []
    for name, dtype, *_ in con.sql(f"describe {table}").fetchall():
        if dtype in ("DOUBLE", "FLOAT") or dtype.startswith("DECIMAL"):
            d = decimals(name)
            columns.append(f"cast(round({name}, {d}) as decimal(38, {d})) as {name}")
        else:
            columns.append(name)
    return ", ".join(columns)


def main() -> None:
    OUTPUTS.mkdir(parents=True, exist_ok=True)
    with duckdb.connect(str(WAREHOUSE), read_only=True) as con:
        for table, order_by in EXPORTS.items():
            path = OUTPUTS / f"{table}.csv"
            query = f"select {rounded_select(con, table)} from {table} order by {order_by}"
            con.sql(f"copy ({query}) to '{path}' (header)")
            print(f"wrote {path.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
