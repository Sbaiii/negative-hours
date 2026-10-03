-- Every zone's prices and generation must run to the as-of date, and that day
-- must be complete in both. Fails for every zone that stops early or whose
-- as-of day is only partly published, so zones are never compared over
-- different periods (ADR-005).

with as_of as (
    select as_of_date from {{ ref('int_as_of') }}
),

zones as (
    select zone, timezone from {{ ref('zones') }}
),

day_length as (
    select
        zones.zone,
        epoch(
            timezone(zones.timezone, (as_of.as_of_date + 1)::timestamp)
            - timezone(zones.timezone, as_of.as_of_date::timestamp)
        ) / 3600 as day_hours
    from zones
    cross join as_of
),

prices as (
    select zone, max(local_date) as last_day,
        sum(duration_h) filter (where local_date = (select as_of_date from as_of)) as hours
    from {{ ref('int_prices_local') }}
    group by zone
),

generation as (
    select zone, max(local_date) as last_day,
        sum(duration_h) filter (where local_date = (select as_of_date from as_of)) as hours
    from {{ ref('int_energy_periods') }}
    group by zone
)

select
    day_length.zone,
    prices.last_day as last_price_day,
    prices.hours as price_hours,
    generation.last_day as last_generation_day,
    generation.hours as generation_hours,
    day_length.day_hours
from day_length
left join prices using (zone)
left join generation using (zone)
cross join as_of
where prices.last_day is distinct from as_of.as_of_date
    or generation.last_day is distinct from as_of.as_of_date
    or prices.hours is distinct from day_length.day_hours
    or generation.hours is distinct from day_length.day_hours
