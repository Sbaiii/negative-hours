"""Build dashboard/data/dashboard.json from the warehouse (run after dbt and the battery model).

For each zone: year-to-date KPIs against the same dates last year, and the latest
complete day of day-ahead prices. The page (dashboard/index.html) reads only this
file, so it needs no server and no build step.

    uv run python dashboard/build_data.py
"""

import json
from datetime import UTC, datetime
from pathlib import Path

import duckdb

REPO_ROOT = Path(__file__).resolve().parent.parent
WAREHOUSE = REPO_ROOT / "data" / "warehouse.duckdb"
OUTPUT = REPO_ROOT / "dashboard" / "data" / "dashboard.json"

ZONE_COLORS = {  # same as analysis/chart_style.py
    "DE_LU": "#2a78d6",
    "ES": "#eb6834",
    "NL": "#1baf7a",
    "FR": "#4a3aa7",
    "BE": "#e87ba4",
    "PT": "#eda100",
    "PL": "#008300",
    "IT_NORD": "#e34948",
}

# The run's as-of date (warehouse model int_as_of): the last local day on which
# every zone has complete prices and generation. All zones use the same window.
AS_OF_SQL = "select zone, as_of_date as as_of from zones cross join int_as_of"

# One row per zone and window ('current' = 1 Jan to as_of, 'previous' = the same
# dates a year earlier). Definitions match the marts: ADR-005 to ADR-008.
KPI_SQL = """
with as_of as ({as_of_sql}),
windows as (
    select zone, 'current' as period,
        make_date(year(as_of), 1, 1) as first_day, as_of as last_day
    from as_of
    union all
    select zone, 'previous',
        make_date(year(as_of) - 1, 1, 1), cast(as_of - interval 1 year as date)
    from as_of
),
prices as (
    select w.zone, w.period,
        sum(p.duration_h) filter (where p.price_eur_mwh < 0) as negative_hours,
        sum(p.price_eur_mwh * p.duration_h) / sum(p.duration_h) as baseload_price
    from windows w
    join int_prices_local p
        on p.zone = w.zone and p.local_date between w.first_day and w.last_day
    group by w.zone, w.period
),
solar as (
    select w.zone, w.period,
        sum(e.price_eur_mwh * e.solar_mwh) / nullif(sum(e.solar_mwh), 0) as solar_capture_price
    from windows w
    join int_energy_periods e
        on e.zone = w.zone and e.local_date between w.first_day and w.last_day
    group by w.zone, w.period
),
battery as (
    select w.zone, w.period, sum(b.revenue_eur_per_mw) as battery_revenue_eur_per_mw
    from windows w
    join battery.arbitrage_daily b
        on b.zone = w.zone and b.local_date between w.first_day and w.last_day
        and b.battery_duration_h = 2
    group by w.zone, w.period
),
ev as (
    select w.zone, w.period,
        sum(v.immediate_eur - v.smart_eur) as ev_smart_saving_eur,
        sum(v.immediate_eur - v.smart_eur) / nullif(sum(v.immediate_eur), 0) as ev_smart_saving_share
    from windows w
    join int_ev_charging_daily v
        on v.zone = w.zone and v.local_date between w.first_day and w.last_day
    group by w.zone, w.period
)
select
    w.zone, w.period, w.first_day, w.last_day,
    coalesce(prices.negative_hours, 0) as negative_hours,
    solar.solar_capture_price / prices.baseload_price as solar_capture_rate,
    battery.battery_revenue_eur_per_mw,
    ev.ev_smart_saving_eur,
    ev.ev_smart_saving_share
from windows w
left join prices using (zone, period)
left join solar using (zone, period)
left join battery using (zone, period)
left join ev using (zone, period)
order by w.zone, w.period
"""

# The latest local day with a complete set of day-ahead prices, per zone, from all
# published prices (not cut at the as-of date). Run after about 12:30 UTC, this is
# usually tomorrow.
CURVE_SQL = """
with days as (
    select p.zone, p.local_date, sum(p.duration_h) as hours,
        epoch(timezone(z.timezone, (p.local_date + 1)::timestamp)
              - timezone(z.timezone, p.local_date::timestamp)) / 3600 as day_hours
    from int_prices_published p
    join zones z using (zone)
    group by p.zone, p.local_date, z.timezone
),
latest as (
    select zone, max(local_date) as local_date from days where hours = day_hours group by zone
)
select p.zone, p.local_date, strftime(p.ts_local, '%H:%M') as local_time,
    p.resolution_minutes, p.price_eur_mwh
from int_prices_published p
join latest using (zone, local_date)
order by p.zone, p.ts_utc
"""


def kpi(row: dict, name: str, digits: int) -> float | None:
    value = row[name]
    return None if value is None else round(float(value), digits)


def main() -> None:
    with duckdb.connect(str(WAREHOUSE), read_only=True) as con:
        con.execute("set TimeZone = 'UTC'")
        con.execute("set enable_progress_bar = false")
        zones = con.sql("select zone, zone_name from zones order by zone").fetchall()
        kpis = con.sql(KPI_SQL.format(as_of_sql=AS_OF_SQL)).df().to_dict("records")
        as_of = con.sql("select as_of_date from int_as_of").fetchone()[0]
        curves = con.sql(CURVE_SQL).df()

    data = {
        "generated_on": datetime.now(UTC).date().isoformat(),
        "as_of_date": as_of.isoformat(),
        "zones": [],
    }
    for zone, name in zones:
        rows = {r["period"]: r for r in kpis if r["zone"] == zone}
        curve = curves[curves.zone == zone]
        periods = {}
        for period in ("current", "previous"):
            r = rows[period]
            periods[period] = {
                "first_day": r["first_day"].date().isoformat(),
                "last_day": r["last_day"].date().isoformat(),
                "negative_hours": kpi(r, "negative_hours", 2),
                "solar_capture_rate": kpi(r, "solar_capture_rate", 4),
                "battery_revenue_eur_per_mw": kpi(r, "battery_revenue_eur_per_mw", 0),
                "ev_smart_saving_eur": kpi(r, "ev_smart_saving_eur", 2),
                "ev_smart_saving_share": kpi(r, "ev_smart_saving_share", 4),
            }
        data["zones"].append(
            {
                "code": zone,
                "name": name,
                "color": ZONE_COLORS[zone],
                "kpis": periods,
                "prices": {
                    "date": curve.local_date.iloc[0].date().isoformat(),
                    "resolution_minutes": int(curve.resolution_minutes.min()),
                    "points": [
                        [t, round(float(p), 2)]
                        for t, p in zip(curve.local_time, curve.price_eur_mwh)
                    ],
                },
            }
        )

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n")
    print(f"wrote {OUTPUT.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
