-- Q1: how often are day-ahead prices negative, per zone and local year?
-- Time is measured as summed period duration (hours), not row counts, so 15-min
-- and 60-min periods are comparable (ADR-005).

with periods as (
    select * from {{ ref('int_prices_local') }}
),

zone_years as (
    select * from {{ ref('int_zone_years') }}
),

-- Same count on hourly means, comparable with hourly-only sources: an hour counts
-- (for the part of it with prices) when the mean of its periods is below 0. Before
-- 2025-10-01 every period is an hour, so this equals negative_hours.
hourly as (
    select
        zone,
        local_year,
        sum(price_eur_mwh * duration_h) / sum(duration_h) as hourly_mean_price,
        sum(duration_h) as hours
    from periods
    group by zone, local_year, date_trunc('hour', ts_utc)
),

hourly_by_year as (
    select
        zone,
        local_year,
        coalesce(sum(hours) filter (where hourly_mean_price < 0), 0) as negative_hours_hourly_avg
    from hourly
    group by zone, local_year
),

by_year as (
    select
        zone,
        local_year,
        sum(duration_h) as covered_hours,
        coalesce(sum(duration_h) filter (where price_eur_mwh < 0), 0) as negative_hours,
        coalesce(sum(duration_h) filter (where price_eur_mwh <= 0), 0) as zero_or_negative_hours,
        min(price_eur_mwh) as min_price,
        -- Duration-weighted, so a 15-min period counts a quarter of an hourly one.
        sum(price_eur_mwh * duration_h) / sum(duration_h) as avg_price,
        sum(price_eur_mwh * duration_h) filter (where price_eur_mwh < 0)
            / nullif(sum(duration_h) filter (where price_eur_mwh < 0), 0) as avg_price_negative_periods
    from periods
    group by zone, local_year
)

select
    by_year.zone,
    by_year.local_year,
    by_year.negative_hours,
    hourly_by_year.negative_hours_hourly_avg,
    by_year.zero_or_negative_hours,
    by_year.covered_hours,
    zone_years.expected_hours,
    round(by_year.covered_hours / zone_years.expected_hours, 4) as completeness,
    round(by_year.min_price, 2) as min_price,
    round(by_year.avg_price, 2) as avg_price,
    round(by_year.avg_price_negative_periods, 2) as avg_price_negative_periods,
    zone_years.known_partial_reason is not null
        or by_year.covered_hours / zone_years.expected_hours < 0.98 as is_partial_year,
    zone_years.known_partial_reason as partial_reason,
    zone_years.data_through_date
from by_year
inner join zone_years using (zone, local_year)
inner join hourly_by_year using (zone, local_year)
