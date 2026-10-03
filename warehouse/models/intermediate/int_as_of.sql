-- A table, not a view: the date is fixed once per build, so every model in the
-- run uses the same date even if raw files change while dbt is running.
{{ config(materialized='table') }}

-- The run's as-of date: the last local day on which EVERY zone has a complete
-- day of day-ahead prices AND a complete day of generation (ADR-005, update of
-- 2026-10-04). Every current-year number in every mart stops at this date, so
-- zones are always compared over the same days, and a partly published day
-- (e.g. tomorrow's prices before all zones have cleared, or generation that is
-- still arriving) never enters a metric.
-- One row. Only the last 60 days of data are scanned; that is enough, because
-- the date is about the newest data.

with zones as (
    select zone, timezone from {{ ref('zones') }}
),

recent_generation as (
    select distinct zone, ts_utc, resolution_minutes
    from {{ ref('stg_generation') }}
    where ts_utc >= (select max(ts_utc) from {{ ref('stg_generation') }}) - interval 60 day
),

recent_prices as (
    select zone, local_date, sum(duration_h) as hours
    from {{ ref('int_prices_published') }}
    where ts_utc >= (select max(ts_utc) from {{ ref('stg_prices') }}) - interval 60 day
    group by zone, local_date
),

generation_days as (
    select
        g.zone,
        cast(timezone(zones.timezone, g.ts_utc) as date) as local_date,
        sum(g.resolution_minutes) / 60.0 as hours
    from recent_generation as g
    inner join zones using (zone)
    group by g.zone, local_date
),

-- Length of each local day in hours: 23, 24 or 25 (DST changes).
day_lengths as (
    select
        zone,
        local_date,
        epoch(
            timezone(zones.timezone, (local_date + 1)::timestamp)
            - timezone(zones.timezone, local_date::timestamp)
        ) / 3600 as day_hours
    from recent_prices
    inner join zones using (zone)
),

per_zone as (
    select
        day_lengths.zone,
        max(day_lengths.local_date) filter (where recent_prices.hours = day_lengths.day_hours)
            as last_price_day,
        max(day_lengths.local_date) filter (
            where recent_prices.hours = day_lengths.day_hours
            and generation_days.hours = day_lengths.day_hours
        ) as last_complete_day
    from day_lengths
    inner join recent_prices using (zone, local_date)
    left join generation_days using (zone, local_date)
    group by day_lengths.zone
)

select
    min(last_complete_day) as as_of_date,
    -- Diagnostics: which zone holds the date back, and how far prices run.
    arg_min(zone, last_complete_day) as limiting_zone,
    min(last_price_day) as last_complete_price_day_all_zones,
    count(*) as zones
from per_zone
