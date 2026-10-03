-- Q1: how often are day-ahead prices negative, per zone and local year?
-- Time is measured as summed period duration (hours), not row counts, so 15-min
-- and 60-min periods are comparable (ADR-005).

with periods as (
    select * from {{ ref('int_prices_local') }}
),

by_year as (
    select
        zone,
        local_year,
        any_value(timezone) as timezone,
        sum(duration_h) as covered_hours,
        coalesce(sum(duration_h) filter (where price_eur_mwh < 0), 0) as negative_hours,
        coalesce(sum(duration_h) filter (where price_eur_mwh <= 0), 0) as zero_or_negative_hours,
        min(price_eur_mwh) as min_price,
        -- Duration-weighted, so a 15-min period counts a quarter of an hourly one.
        sum(price_eur_mwh * duration_h) / sum(duration_h) as avg_price,
        sum(price_eur_mwh * duration_h) filter (where price_eur_mwh < 0)
            / nullif(sum(duration_h) filter (where price_eur_mwh < 0), 0) as avg_price_negative_periods,
        max(ts_utc + to_minutes(resolution_minutes)) as data_end_utc
    from periods
    group by zone, local_year
),

with_bounds as (
    select
        *,
        -- Local midnight on 1 January, as an instant.
        timezone(timezone, make_timestamp(local_year, 1, 1, 0, 0, 0)) as year_start_utc,
        timezone(timezone, make_timestamp(local_year + 1, 1, 1, 0, 0, 0)) as year_end_utc,
        local_year = year(timezone(timezone, now())) as is_current_year
    from by_year
),

with_completeness as (
    select
        *,
        -- Full years: the whole local year. Current year: up to the end of the last
        -- period we have (day-ahead data runs into tomorrow).
        epoch(
            case when is_current_year then least(data_end_utc, year_end_utc) else year_end_utc end
            - year_start_utc
        ) / 3600 as expected_hours
    from with_bounds
)

select
    zone,
    local_year,
    negative_hours,
    zero_or_negative_hours,
    covered_hours,
    expected_hours,
    round(covered_hours / expected_hours, 4) as completeness,
    round(min_price, 2) as min_price,
    round(avg_price, 2) as avg_price,
    round(avg_price_negative_periods, 2) as avg_price_negative_periods,
    -- Partial = not a full year of data. Every partial year must have a reason
    -- (tested); a new, unexplained gap fails the build instead of being labelled.
    is_current_year or covered_hours / expected_hours < 0.98 as is_partial_year,
    case
        when is_current_year then 'current_year'
        when zone = 'PL'
            and year_start_utc < timestamptz '{{ var("pl_eur_prices_start_utc") }}'
            then 'pln_prices_excluded'
    end as partial_reason
from with_completeness
