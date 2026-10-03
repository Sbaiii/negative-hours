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

-- Energy is computed in exact decimals: ENTSO-E reports MW with up to 6 decimals
-- and periods are 0.25, 0.5 or 1 h, so MWh is exact at 8 decimals. Floating-point
-- sums run in parallel and can differ in the last bit between builds, which flips
-- totals that sit exactly on a rounding boundary (e.g. 82,793,393.55 MWh).
energy as (
    select
        zone,
        ts_utc,
        production_type,
        cast(generation_mw as decimal(18, 6))
            * cast(resolution_minutes / 60.0 as decimal(4, 2)) as mwh
    from {{ ref('stg_generation') }}
),

generation as (
    select
        zone,
        date_trunc('hour', ts_utc) as hour_utc,
        sum(mwh) filter (where production_type = 'Solar') as solar_mwh,
        sum(mwh) filter (where production_type in ('Wind Onshore', 'Wind Offshore')) as wind_mwh,
        sum(mwh) as total_generation_mwh
    from energy
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
