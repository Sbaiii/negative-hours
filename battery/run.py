"""Run the battery LP for every zone-day and store the daily results in DuckDB.

Reads day-ahead prices from the dbt view int_prices_local (so run `dbt build`
first), solves each complete local day for every battery duration, and writes
battery.arbitrage_daily into data/warehouse.duckdb. dbt then reads that table as
a source for fct_battery_arbitrage (ADR-007).

    uv run python -m battery.run
"""

import logging
import time

import duckdb
import pandas as pd

from battery.model import Battery, heuristic_day, optimal_day
from pipeline.config import REPO_ROOT

WAREHOUSE = REPO_ROOT / "data" / "warehouse.duckdb"
DURATIONS_H = (1, 2, 4)
SCHEMA, TABLE = "battery", "arbitrage_daily"

log = logging.getLogger("battery")

# One row per price period, with the length of its local day in hours (23, 24 or
# 25 at DST changes) and how many hours of that day have a price.
PRICES_SQL = """
    with periods as (
        select
            p.zone,
            p.local_date,
            p.local_year,
            p.ts_utc,
            p.price_eur_mwh,
            p.duration_h,
            epoch(
                timezone(z.timezone, (p.local_date + 1)::timestamp)
                - timezone(z.timezone, p.local_date::timestamp)
            ) / 3600 as day_hours
        from int_prices_local p
        join zones z using (zone)
    )
    select
        *,
        sum(duration_h) over (partition by zone, local_date) as covered_hours
    from periods
    order by zone, ts_utc
"""


def solve_day(zone, local_date, day: pd.DataFrame, battery: Battery) -> dict:
    prices = day.price_eur_mwh.to_numpy()
    durations = day.duration_h.to_numpy()
    lp = optimal_day(prices, durations, battery)
    rule = heuristic_day(prices, durations, battery)
    return {
        "zone": zone,
        "local_date": local_date,
        "local_year": int(day.local_year.iloc[0]),
        "battery_duration_h": battery.duration_h,
        "day_hours": float(day.day_hours.iloc[0]),
        "periods": len(day),
        "revenue_eur_per_mw": lp.revenue_eur / battery.power_mw,
        "charge_cost_eur": lp.charge_cost_eur,
        "discharge_value_eur": lp.discharge_value_eur,
        "charged_mwh": lp.charged_mwh,
        "discharged_mwh": lp.discharged_mwh,
        "cycles": lp.cycles(battery),
        "charged_negative_mwh": lp.charged_negative_mwh,
        "negative_charging_revenue_eur": lp.negative_charging_revenue_eur,
        "simultaneous_mwh": lp.simultaneous_mwh,
        "heuristic_revenue_eur_per_mw": rule.revenue_eur / battery.power_mw,
    }


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    con = duckdb.connect(str(WAREHOUSE))
    con.execute("set TimeZone = 'UTC'")
    con.execute("set enable_progress_bar = false")
    prices = con.sql(PRICES_SQL).df()

    complete = prices.covered_hours == prices.day_hours
    skipped = prices[~complete].groupby(["zone", "local_date"]).size()
    for zone, local_date in skipped.index:
        log.info("skipping %s %s: incomplete day", zone, local_date.date())

    batteries = [Battery(duration_h=h) for h in DURATIONS_H]
    rows = []
    for zone, zone_prices in prices[complete].groupby("zone"):
        started = time.perf_counter()
        days = zone_prices.groupby("local_date", sort=True)
        for local_date, day in days:
            for battery in batteries:
                rows.append(solve_day(zone, local_date, day, battery))
        log.info(
            "%s: %d days x %d durations in %.0f s",
            zone,
            days.ngroups,
            len(batteries),
            time.perf_counter() - started,
        )

    results = pd.DataFrame(rows)  # noqa: F841 (read by DuckDB below)
    con.execute(f"create schema if not exists {SCHEMA}")
    con.execute(
        f"create or replace table {SCHEMA}.{TABLE} as "
        "select * replace (local_date::date as local_date) from results"
    )
    log.info("wrote %s.%s: %d rows", SCHEMA, TABLE, len(rows))
    con.close()


if __name__ == "__main__":
    main()
