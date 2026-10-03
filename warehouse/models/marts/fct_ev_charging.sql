-- Q4: what an EV pays for its electricity (wholesale component only) under three
-- charging strategies, per zone, local year and season (ADR-008).
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
    inner join blocks
        on blocks.zone = windows.zone
        and blocks.start_utc >= windows.window_start
        and blocks.start_utc <= windows.latest_start
        and blocks.end_utc <= windows.window_end
    group by windows.zone, windows.local_date, windows.strategy
),

-- Keep only days where all three strategies have prices (drops e.g. the last
-- day, whose overnight window needs tomorrow's prices).
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
),

-- Seasons, plus the whole year as season 'year'.
by_period as (
    select zone, local_year, season, count(*) as days,
        avg(immediate_eur) as immediate, avg(overnight_eur) as overnight, avg(smart_eur) as smart
    from daily
    group by zone, local_year, season
    union all
    select zone, local_year, 'year', count(*),
        avg(immediate_eur), avg(overnight_eur), avg(smart_eur)
    from daily
    group by zone, local_year
),

year_coverage as (
    select zone, local_year, completeness, partial_reason
    from {{ ref('fct_negative_hours') }}
)

select
    zone,
    local_year,
    season,
    days,
    -- EUR per year at this period's average daily cost, for 365 charging days.
    round(immediate * 365, 2) as immediate_eur_per_year,
    round(overnight * 365, 2) as overnight_eur_per_year,
    round(smart * 365, 2) as smart_eur_per_year,
    round((immediate - overnight) * 365, 2) as overnight_savings_eur_per_year,
    round((immediate - smart) * 365, 2) as smart_savings_eur_per_year,
    round((immediate - overnight) / nullif(immediate, 0), 4) as overnight_savings_share,
    round((immediate - smart) / nullif(immediate, 0), 4) as smart_savings_share,
    -- Average wholesale price paid per MWh charged.
    round(immediate * 1000 / {{ energy_kwh }}, 2) as immediate_price_eur_mwh,
    round(overnight * 1000 / {{ energy_kwh }}, 2) as overnight_price_eur_mwh,
    round(smart * 1000 / {{ energy_kwh }}, 2) as smart_price_eur_mwh,
    year_coverage.partial_reason is not null or year_coverage.completeness < 0.98
        as is_partial_year,
    year_coverage.partial_reason
from by_period
inner join year_coverage using (zone, local_year)
