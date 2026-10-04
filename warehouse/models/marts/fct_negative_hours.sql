-- Q1: how often are day-ahead prices negative, per zone and local year?
-- Headline (ADR-005, update of 2026-10-04): hours whose HOURLY MEAN price is below
-- 0, the convention of published counts (RTE, REE). The duration of negative
-- periods (15-min periods count 0.25 h) is kept as a secondary column. The two
-- are identical before the 15-min switch on 2025-10-01 (tested).

with periods as (
    select * from {{ ref('int_prices_local') }}
),

hourly as (
    select * from {{ ref('int_prices_hourly') }}
),

zone_years as (
    select * from {{ ref('int_zone_years') }}
),

by_hour as (
    select
        zone,
        local_year,
        coalesce(sum(hours) filter (where hourly_mean_price < 0), 0) as negative_hours,
        coalesce(sum(hours) filter (where hourly_mean_price <= 0), 0) as zero_or_negative_hours
    from hourly
    group by zone, local_year
),

by_period as (
    select
        zone,
        local_year,
        sum(duration_h) as covered_hours,
        coalesce(sum(duration_h) filter (where price_eur_mwh < 0), 0) as negative_period_hours,
        coalesce(sum(duration_h) filter (where price_eur_mwh <= 0), 0) as zero_or_negative_period_hours,
        min(price_eur_mwh) as min_price,
        -- Duration-weighted, so a 15-min period counts a quarter of an hourly one.
        sum(price_eur_mwh * duration_h) / sum(duration_h) as avg_price,
        sum(price_eur_mwh * duration_h) filter (where price_eur_mwh < 0)
            / nullif(sum(duration_h) filter (where price_eur_mwh < 0), 0) as avg_price_negative_periods
    from periods
    group by zone, local_year
)

select
    by_period.zone,
    by_period.local_year,
    by_hour.negative_hours,
    by_hour.zero_or_negative_hours,
    by_period.negative_period_hours,
    by_period.zero_or_negative_period_hours,
    by_period.covered_hours,
    zone_years.expected_hours,
    round(by_period.covered_hours / zone_years.expected_hours, 4) as completeness,
    round(by_period.min_price, 2) as min_price,
    round(by_period.avg_price, 2) as avg_price,
    round(by_period.avg_price_negative_periods, 2) as avg_price_negative_periods,
    zone_years.known_partial_reason is not null
        or by_period.covered_hours / zone_years.expected_hours < 0.98 as is_partial_year,
    zone_years.known_partial_reason as partial_reason,
    zone_years.data_through_date
from by_period
inner join zone_years using (zone, local_year)
inner join by_hour using (zone, local_year)
