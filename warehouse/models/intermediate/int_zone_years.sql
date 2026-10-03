-- One row per zone and local calendar year that has prices: the year's bounds,
-- how many hours it should have, and any known reason it is not a full year.
-- Shared by every mart keyed by zone x local year, so they agree on what a
-- "partial year" is.

with periods as (
    select * from {{ ref('int_prices_local') }}
),

years as (
    select
        zone,
        local_year,
        any_value(timezone) as timezone,
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
    from years
)

select
    zone,
    local_year,
    timezone,
    year_start_utc,
    year_end_utc,
    is_current_year,
    -- Full years: the whole local year. Current year: up to the end of the last
    -- price period (day-ahead data runs into tomorrow).
    epoch(
        case when is_current_year then least(data_end_utc, year_end_utc) else year_end_utc end
        - year_start_utc
    ) / 3600 as expected_hours,
    -- Known reasons a year is not a full year of data. Marts flag a year as partial
    -- when it has one of these OR its coverage is below 0.98; a test then requires
    -- a reason, so an unexplained gap fails the build instead of being labelled.
    case
        when is_current_year then 'current_year'
        when zone = 'PL'
            and year_start_utc < timestamptz '{{ var("pl_eur_prices_start_utc") }}'
            then 'pln_prices_excluded'
    end as known_partial_reason
from with_bounds
