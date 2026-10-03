-- Stored as a table: it aggregates ~15M generation rows, and marts, tests and
-- notebooks read it many times.
{{ config(materialized='table') }}

-- Prices and generation on one HOURLY grid per zone (ADR-006).
-- Prices: duration-weighted mean of the periods in the hour (4 quarter-hours after
-- the 2025 switch, 1 period before). Generation: energy, MWh = MW x duration_h,
-- summed over the periods in the hour. Only hours with BOTH a price and some
-- generation are kept; coverage columns say how much of each hour was reported.

with prices as (
    select
        zone,
        date_trunc('hour', ts_utc) as hour_utc,
        sum(price_eur_mwh * duration_h) / sum(duration_h) as price_eur_mwh,
        sum(duration_h) as price_hours_covered
    from {{ ref('int_prices_local') }}
    group by zone, hour_utc
),

generation as (
    select
        zone,
        date_trunc('hour', ts_utc) as hour_utc,
        sum(generation_mw * resolution_minutes / 60.0)
            filter (where production_type = 'Solar') as solar_mwh,
        sum(generation_mw * resolution_minutes / 60.0)
            filter (where production_type in ('Wind Onshore', 'Wind Offshore')) as wind_mwh,
        sum(generation_mw * resolution_minutes / 60.0) as total_generation_mwh
    from {{ ref('stg_generation') }}
    group by zone, hour_utc
),

-- Share of the hour covered by generation periods (all types share the zone's
-- reporting interval, see ADR-004).
generation_coverage as (
    select
        zone,
        date_trunc('hour', ts_utc) as hour_utc,
        sum(resolution_minutes) / 60.0 as generation_hours_covered
    from (select distinct zone, ts_utc, resolution_minutes from {{ ref('stg_generation') }})
    group by zone, hour_utc
),

zones as (
    select zone, timezone from {{ ref('zones') }}
)

select
    prices.zone,
    prices.hour_utc,
    timezone(zones.timezone, prices.hour_utc) as hour_local,
    cast(timezone(zones.timezone, prices.hour_utc) as date) as local_date,
    year(timezone(zones.timezone, prices.hour_utc)) as local_year,
    prices.price_eur_mwh,
    prices.price_hours_covered,
    generation_coverage.generation_hours_covered,
    -- Null when the zone reported no Solar (or Wind) row in that hour.
    generation.solar_mwh,
    generation.wind_mwh,
    generation.total_generation_mwh
from prices
inner join generation using (zone, hour_utc)
inner join generation_coverage using (zone, hour_utc)
inner join zones using (zone)
