-- Q4: the shape of a day's prices per zone, local year, season and local hour.
-- Seasons are meteorological and stay inside the local calendar year (winter =
-- Jan, Feb and Dec of the same year), so the four seasons add up to the year
-- (ADR-008). Mean and share are duration-weighted over native periods; the
-- median is over hourly values (one per day and hour), so 15-min and 60-min
-- years count each hour once.

with periods as (
    select
        *,
        hour(ts_local) as local_hour,
        case
            when month(ts_local) in (12, 1, 2) then 'winter'
            when month(ts_local) in (3, 4, 5) then 'spring'
            when month(ts_local) in (6, 7, 8) then 'summer'
            else 'autumn'
        end as season
    from {{ ref('int_prices_local') }}
),

-- One price per local date and hour (the mean of its 15-min periods after the
-- switch). At the autumn DST change the repeated hour gives two values.
hourly as (
    select
        zone,
        local_year,
        season,
        local_hour,
        sum(price_eur_mwh * duration_h) / sum(duration_h) as hourly_price
    from periods
    group by zone, local_year, season, local_hour, local_date, date_trunc('hour', ts_utc)
),

medians as (
    select
        zone,
        local_year,
        season,
        local_hour,
        median(hourly_price) as median_price
    from hourly
    group by zone, local_year, season, local_hour
),

by_hour as (
    select
        zone,
        local_year,
        season,
        local_hour,
        sum(duration_h) as covered_hours,
        sum(price_eur_mwh * duration_h) / sum(duration_h) as mean_price,
        coalesce(sum(duration_h) filter (where price_eur_mwh <= 0), 0) / sum(duration_h)
            as share_at_or_below_zero
    from periods
    group by zone, local_year, season, local_hour
),


-- Partial years: same rule as the other marts, on the whole year's coverage.
year_coverage as (
    select zone, local_year, completeness, partial_reason, data_through_date
    from {{ ref('fct_negative_hours') }}
)

select
    by_hour.zone,
    by_hour.local_year,
    by_hour.season,
    by_hour.local_hour,
    round(by_hour.mean_price, 2) as mean_price,
    round(medians.median_price, 2) as median_price,
    round(by_hour.share_at_or_below_zero, 4) as share_at_or_below_zero,
    by_hour.covered_hours,
    year_coverage.partial_reason is not null or year_coverage.completeness < 0.98
        as is_partial_year,
    year_coverage.partial_reason,
    year_coverage.data_through_date
from by_hour
inner join medians using (zone, local_year, season, local_hour)
inner join year_coverage using (zone, local_year)
