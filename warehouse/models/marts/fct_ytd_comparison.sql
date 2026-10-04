-- Like-for-like year to date: every year cut to the same window as the current
-- year, 1 January to the as-of date's day and month (e.g. 1 Jan to 2 Oct in every
-- year). A partial year is only ever compared with the same window of earlier
-- years, never with a full year (ADR-005 update of 2026-10-04). One row per zone
-- and local year; the definitions are those of the full-year marts.

with as_of as (
    select as_of_date from {{ ref('int_as_of') }}
),

windows as (
    select distinct
        zone,
        local_year,
        -- Same day and month as the as-of date (29 Feb becomes 28 Feb in other years).
        cast(as_of.as_of_date - to_years(year(as_of.as_of_date) - local_year) as date)
            as window_end_date
    from {{ ref('int_zone_years') }}
    cross join as_of
),

prices as (
    select w.zone, w.local_year,
        sum(p.duration_h) as covered_hours,
        sum(p.price_eur_mwh * p.duration_h) / sum(p.duration_h) as baseload_price
    from windows as w
    inner join {{ ref('int_prices_local') }} as p
        on p.zone = w.zone and p.local_year = w.local_year and p.local_date <= w.window_end_date
    group by w.zone, w.local_year
),

hours as (
    select w.zone, w.local_year,
        coalesce(sum(h.hours) filter (where h.hourly_mean_price < 0), 0) as negative_hours,
        coalesce(sum(h.hours) filter (where h.hourly_mean_price <= 0), 0) as zero_or_negative_hours
    from windows as w
    inner join {{ ref('int_prices_hourly') }} as h
        on h.zone = w.zone and h.local_year = w.local_year and h.local_date <= w.window_end_date
    group by w.zone, w.local_year
),

solar as (
    select w.zone, w.local_year,
        sum(e.price_eur_mwh * e.solar_mwh) / nullif(sum(e.solar_mwh), 0) as solar_capture_price,
        coalesce(sum(e.duration_h) filter (where e.solar_mwh is not null), 0) / sum(e.duration_h)
            as solar_coverage
    from windows as w
    inner join {{ ref('int_energy_periods') }} as e
        on e.zone = w.zone and e.local_year = w.local_year and e.local_date <= w.window_end_date
    group by w.zone, w.local_year
),

battery as (
    select w.zone, w.local_year, sum(b.revenue_eur_per_mw) as battery_revenue_eur_per_mw
    from windows as w
    inner join {{ source('battery', 'arbitrage_daily') }} as b
        on b.zone = w.zone and b.local_year = w.local_year and b.local_date <= w.window_end_date
        and b.battery_duration_h = 2
    group by w.zone, w.local_year
),

ev as (
    select w.zone, w.local_year,
        count(*) as ev_days,
        sum(v.immediate_eur) as immediate,
        sum(v.overnight_eur) as overnight,
        sum(v.smart_eur) as smart
    from windows as w
    inner join {{ ref('int_ev_charging_daily') }} as v
        on v.zone = w.zone and v.local_year = w.local_year and v.local_date <= w.window_end_date
    group by w.zone, w.local_year
),

zone_years as (
    select zone, local_year, timezone, year_start_utc, known_partial_reason
    from {{ ref('int_zone_years') }}
)

select
    windows.zone,
    windows.local_year,
    windows.window_end_date,
    hours.negative_hours,
    hours.zero_or_negative_hours,
    prices.covered_hours,
    epoch(timezone(zone_years.timezone, (windows.window_end_date + 1)::timestamp)
        - zone_years.year_start_utc) / 3600 as expected_hours,
    round(prices.baseload_price, 2) as baseload_price,
    case when solar.solar_coverage >= 0.95 then round(solar.solar_capture_price, 2) end
        as solar_capture_price,
    case when solar.solar_coverage >= 0.95
        then round(solar.solar_capture_price / prices.baseload_price, 6) end as solar_capture_rate,
    round(battery.battery_revenue_eur_per_mw, 0) as battery_revenue_eur_per_mw,
    ev.ev_days,
    round(ev.immediate, 2) as ev_immediate_eur,
    round(ev.overnight, 2) as ev_overnight_eur,
    round(ev.smart, 2) as ev_smart_eur,
    round(ev.immediate - ev.smart, 2) as ev_smart_saving_eur,
    round((ev.immediate - ev.smart) / nullif(ev.immediate, 0), 6) as ev_smart_saving_share,
    round((ev.immediate - ev.overnight) / nullif(ev.immediate, 0), 6) as ev_overnight_saving_share,
    coalesce(zone_years.known_partial_reason = 'pln_prices_excluded', false) as is_partial_window,
    case when zone_years.known_partial_reason = 'pln_prices_excluded'
        then 'pln_prices_excluded' end as partial_reason
from windows
inner join zone_years using (zone, local_year)
inner join prices using (zone, local_year)
inner join hours using (zone, local_year)
left join solar using (zone, local_year)
left join battery using (zone, local_year)
left join ev using (zone, local_year)
