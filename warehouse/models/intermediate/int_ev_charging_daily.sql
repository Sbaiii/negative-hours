-- Stored as a table: the block search joins every price period to the periods
-- after it, and both fct_ev_charging and the dashboard read the result.
{{ config(materialized='table') }}

-- Q4: what an EV pays each day for its electricity (wholesale component only)
-- under three charging strategies (ADR-008). One row per zone and local day.
--
-- Each day the car needs 10 kWh at 7 kW: 1 h 25 m 43 s of charging in one
-- continuous block. A block can start at any price period and its last period
-- is charged only partly. The three strategies pick, for each local day D:
--   immediate: the block that starts at 18:00 (plug in after work, charge now)
--   overnight: the cheapest block inside 22:00 on D to 07:00 on D+1
--   smart:     the cheapest block inside D (00:00 to 24:00)
-- Prices are known in advance: day-ahead prices for D+1 are published around
-- noon on D, before any of these windows opens.

{% set energy_kwh = 10.0 %}
{% set power_kw = 7.0 %}
{% set charge_hours = energy_kwh / power_kw %}

with periods as (
    select
        zone,
        ts_utc,
        local_date,
        timezone,
        price_eur_mwh,
        duration_h
    from {{ ref('int_prices_local') }}
),

-- Every period start is a candidate start of a charging block. Join the periods
-- the block covers and the energy charged in each (full power until 10 kWh).
block_periods as (
    select
        s.zone,
        s.ts_utc as start_utc,
        t.price_eur_mwh,
        {{ power_kw }} * greatest(0, least(
            t.duration_h,
            {{ charge_hours }} - epoch(t.ts_utc - s.ts_utc) / 3600
        )) as energy_kwh
    from periods as s
    inner join periods as t
        on t.zone = s.zone
        and t.ts_utc >= s.ts_utc
        and t.ts_utc < s.ts_utc + to_microseconds(cast({{ charge_hours * 3600 * 1000000 }} as bigint))
),

blocks as (
    select
        zone,
        start_utc,
        start_utc + to_microseconds(cast({{ charge_hours * 3600 * 1000000 }} as bigint)) as end_utc,
        sum(energy_kwh * price_eur_mwh) / 1000 as cost_eur
    from block_periods
    group by zone, start_utc
    -- A block over a gap in the prices would charge less than 10 kWh: drop it.
    having abs(sum(energy_kwh) - {{ energy_kwh }}) < 0.000001
),

days as (
    select distinct zone, local_date, timezone from periods
),

-- First and last instant with prices per zone: a window must lie inside them,
-- or a strategy would choose from fewer hours than it is allowed.
data_bounds as (
    select
        zone,
        min(ts_utc) as data_start,
        max(ts_utc + to_microseconds(cast(duration_h * 3600 * 1000000 as bigint))) as data_end
    from periods
    group by zone
),

-- Allowed charging window per day and strategy, as UTC instants.
windows as (
    select zone, local_date, 'immediate' as strategy,
        timezone(timezone, local_date + interval 18 hour) as window_start,
        timezone(timezone, local_date + interval 18 hour) as latest_start,
        timezone(timezone, local_date + interval 1 day + interval 18 hour) as window_end
    from days
    union all
    select zone, local_date, 'overnight',
        timezone(timezone, local_date + interval 22 hour),
        timezone(timezone, local_date + interval 1 day + interval 7 hour),
        timezone(timezone, local_date + interval 1 day + interval 7 hour)
    from days
    union all
    select zone, local_date, 'smart',
        timezone(timezone, local_date::timestamp),
        timezone(timezone, local_date + interval 1 day),
        timezone(timezone, local_date + interval 1 day)
    from days
),

best as (
    select
        windows.zone,
        windows.local_date,
        windows.strategy,
        min(blocks.cost_eur) as cost_eur
    from windows
    inner join data_bounds
        on data_bounds.zone = windows.zone
        and windows.window_start >= data_bounds.data_start
        and (windows.strategy = 'immediate' or windows.window_end <= data_bounds.data_end)
    inner join blocks
        on blocks.zone = windows.zone
        and blocks.start_utc >= windows.window_start
        and blocks.start_utc <= windows.latest_start
        and blocks.end_utc <= windows.window_end
    group by windows.zone, windows.local_date, windows.strategy
),

-- Keep only days where all three strategies have their whole window priced
-- (drops the last day, whose night needs tomorrow's prices, and 2019-01-01 in
-- CET zones, whose prices start at 01:00).
daily as (
    select
        zone,
        local_date,
        year(local_date) as local_year,
        case
            when month(local_date) in (12, 1, 2) then 'winter'
            when month(local_date) in (3, 4, 5) then 'spring'
            when month(local_date) in (6, 7, 8) then 'summer'
            else 'autumn'
        end as season,
        max(cost_eur) filter (where strategy = 'immediate') as immediate_eur,
        max(cost_eur) filter (where strategy = 'overnight') as overnight_eur,
        max(cost_eur) filter (where strategy = 'smart') as smart_eur
    from best
    group by zone, local_date
    having count(*) = 3
)

select * from daily
