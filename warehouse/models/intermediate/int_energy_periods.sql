-- Stored as a table: it aggregates ~16M generation rows, and marts, tests and
-- the dashboard read it many times.
{{ config(materialized='table') }}

-- Prices and generation matched on the GENERATION period (ADR-006, update of
-- 2026-10-04). One row per zone and generation period: its energy per
-- technology, and the price over exactly that period = duration-weighted mean of
-- the price periods overlapping it. So:
--   generation 15 min, prices 15 min (most zones since 2025-10-01): 15-min match
--   generation 15 min, prices hourly: each quarter gets its hour's price
--   generation hourly (BE, PT), prices 15 min: the hour's mean price
-- A zone never mixes 15-min and hourly generation within an hour (checked), so
-- periods don't overlap. Only periods with a price are kept (up to the as-of
-- date, through int_prices_local).

-- Energy is computed in exact decimals: ENTSO-E reports MW with up to 6 decimals
-- and periods are 0.25, 0.5 or 1 h, so MWh is exact at 8 decimals. Floating-point
-- sums run in parallel and can differ in the last bit between builds, which flips
-- totals that sit exactly on a rounding boundary (e.g. 82,793,393.55 MWh).
with energy as (
    select
        zone,
        ts_utc,
        resolution_minutes,
        production_type,
        cast(generation_mw as decimal(18, 6))
            * cast(resolution_minutes / 60.0 as decimal(4, 2)) as mwh
    from {{ ref('stg_generation') }}
),

generation as (
    select
        zone,
        ts_utc as period_start_utc,
        ts_utc + to_minutes(resolution_minutes) as period_end_utc,
        resolution_minutes,
        sum(mwh) filter (where production_type = 'Solar') as solar_mwh,
        sum(mwh) filter (where production_type in ('Wind Onshore', 'Wind Offshore')) as wind_mwh,
        sum(mwh) as total_generation_mwh
    from energy
    group by zone, ts_utc, resolution_minutes
),

prices as (
    select
        zone,
        ts_utc,
        ts_utc + to_minutes(resolution_minutes) as end_utc,
        price_eur_mwh
    from {{ ref('int_prices_local') }}
),

-- Price over each generation period, weighted by how long each price period
-- overlaps it (exact decimals: overlaps are whole quarter-hours).
priced as (
    select
        g.zone,
        g.period_start_utc,
        sum(p.price_eur_mwh * o.overlap_h) as price_x_hours,
        sum(o.overlap_h) as price_hours_covered
    from generation as g
    inner join prices as p
        on p.zone = g.zone
        and p.ts_utc < g.period_end_utc
        and p.end_utc > g.period_start_utc
    cross join lateral (
        select cast(
            epoch(least(p.end_utc, g.period_end_utc) - greatest(p.ts_utc, g.period_start_utc)) / 3600
            as decimal(6, 4)
        ) as overlap_h
    ) as o
    group by g.zone, g.period_start_utc
),

zones as (
    select zone, timezone from {{ ref('zones') }}
)

select
    generation.zone,
    generation.period_start_utc,
    timezone(zones.timezone, generation.period_start_utc) as period_start_local,
    cast(timezone(zones.timezone, generation.period_start_utc) as date) as local_date,
    year(timezone(zones.timezone, generation.period_start_utc)) as local_year,
    generation.resolution_minutes,
    cast(generation.resolution_minutes / 60.0 as decimal(4, 2)) as duration_h,
    -- Exact: means of 2-decimal prices over whole quarter-hours have <= 4 decimals.
    cast(priced.price_x_hours / priced.price_hours_covered as decimal(14, 4)) as price_eur_mwh,
    priced.price_hours_covered,
    -- Null when the zone reported no Solar (or wind) row in that period.
    generation.solar_mwh,
    generation.wind_mwh,
    generation.total_generation_mwh
from generation
inner join priced using (zone, period_start_utc)
inner join zones using (zone)
