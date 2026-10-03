-- One row per zone and local calendar year that has prices: the year's bounds,
-- how many hours it should have, and any known reason it is not a full year.
-- Shared by every mart keyed by zone x local year, so they agree on what a
-- "partial year" is.

with periods as (
    select * from {{ ref('int_prices_local') }}
),

as_of as (
    select as_of_date from {{ ref('int_as_of') }}
),

years as (
    select
        zone,
        local_year,
        any_value(timezone) as timezone
    from periods
    group by zone, local_year
),

with_bounds as (
    select
        *,
        -- Local midnight on 1 January, as an instant.
        timezone(timezone, make_timestamp(local_year, 1, 1, 0, 0, 0)) as year_start_utc,
        timezone(timezone, make_timestamp(local_year + 1, 1, 1, 0, 0, 0)) as year_end_utc,
        -- Local midnight at the end of the as-of date, as an instant.
        timezone(timezone, (as_of.as_of_date + 1)::timestamp) as as_of_end_utc,
        local_year = year(as_of.as_of_date) as is_current_year,
        as_of.as_of_date
    from years
    cross join as_of
)

select
    zone,
    local_year,
    timezone,
    year_start_utc,
    year_end_utc,
    is_current_year,
    -- Last day a year's numbers cover: 31 December, or the as-of date for the
    -- current year. Marts carry it so a reader sees how far a 2026 row runs.
    case
        when is_current_year then as_of_date else make_date(local_year, 12, 31)
    end as data_through_date,
    -- Full years: the whole local year. Current year: up to the end of the as-of
    -- date, a fixed point independent of the data, so missing periods before it
    -- lower completeness instead of being invisible.
    epoch(
        case when is_current_year then least(as_of_end_utc, year_end_utc) else year_end_utc end
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
