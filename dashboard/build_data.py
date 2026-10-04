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

# Year-to-date KPIs come straight from the warehouse mart fct_ytd_comparison: every
# year cut to the same window (1 Jan to the as-of date's day and month), so this
# year is only ever compared with the same dates last year (ADR-005).
KPI_SQL = """
select
    y.zone,
    case when y.local_year = year(a.as_of_date) then 'current' else 'previous' end as period,
    make_date(y.local_year, 1, 1) as first_day,
    y.window_end_date as last_day,
    y.negative_hours,
    y.solar_capture_rate,
    y.battery_revenue_eur_per_mw,
    y.ev_smart_saving_eur,
    y.ev_smart_saving_share
from fct_ytd_comparison y
cross join int_as_of a
where y.local_year in (year(a.as_of_date), year(a.as_of_date) - 1)
order by y.zone, y.local_year
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
        kpis = con.sql(KPI_SQL).df().to_dict("records")
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
                "first_day": r["first_day"].isoformat()[:10],
                "last_day": r["last_day"].isoformat()[:10],
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
