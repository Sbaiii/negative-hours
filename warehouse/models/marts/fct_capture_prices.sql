-- Q2: solar (and wind) capture prices per zone and local year (ADR-006).
-- Capture price = generation-weighted average price: what one MWh of solar earned
-- on the day-ahead market. Capture rate = capture price / baseload price.
-- Generation is "as reported to ENTSO-E" (may miss rooftop PV in some zones).

with periods as (
    select * from {{ ref('int_energy_periods') }}
),

-- Baseload = time-weighted mean over ALL price periods of the zone-year, the same
-- definition as fct_negative_hours.avg_price (tested). Capture prices below use
-- only the matched generation periods, where generation is known (ADR-006).
baseload as (
    select
        zone,
        local_year,
        sum(price_eur_mwh * duration_h) / sum(duration_h) as baseload_price
    from {{ ref('int_prices_local') }}
    group by zone, local_year
),

zone_years as (
    select * from {{ ref('int_zone_years') }}
),

by_year as (
    select
        zone,
        local_year,
        sum(duration_h) as matched_hours,

        sum(solar_mwh) as solar_mwh,
        sum(price_eur_mwh * solar_mwh) / nullif(sum(solar_mwh), 0) as solar_capture_price,
        coalesce(sum(duration_h) filter (where solar_mwh is not null), 0) / sum(duration_h)
            as solar_coverage,

        sum(wind_mwh) as wind_mwh,
        sum(price_eur_mwh * wind_mwh) / nullif(sum(wind_mwh), 0) as wind_capture_price,
        coalesce(sum(duration_h) filter (where wind_mwh is not null), 0) / sum(duration_h)
            as wind_coverage,

        sum(total_generation_mwh) as total_generation_mwh
    from periods
    group by zone, local_year
),

metrics as (
    select
        *,
        -- A technology's metrics need its series in at least 95% of the matched time
        -- (ADR-006). Only PL 2019-2020 solar fails this (reported from 2020-04-10).
        solar_coverage >= 0.95 as solar_ok,
        wind_coverage >= 0.95 as wind_ok
    from by_year
    inner join baseload using (zone, local_year)
)

select
    metrics.zone,
    metrics.local_year,
    round(metrics.baseload_price, 2) as baseload_price,

    case when solar_ok then round(metrics.solar_mwh, 3) end as solar_mwh,
    case when solar_ok then round(metrics.solar_capture_price, 2) end as solar_capture_price,
    case when solar_ok then round(metrics.solar_capture_price / metrics.baseload_price, 4) end
        as solar_capture_rate,
    case when solar_ok then round(metrics.solar_mwh / metrics.total_generation_mwh, 4) end
        as solar_share,

    case when wind_ok then round(metrics.wind_mwh, 3) end as wind_mwh,
    case when wind_ok then round(metrics.wind_capture_price, 2) end as wind_capture_price,
    case when wind_ok then round(metrics.wind_capture_price / metrics.baseload_price, 4) end
        as wind_capture_rate,
    case when wind_ok then round(metrics.wind_mwh / metrics.total_generation_mwh, 4) end
        as wind_share,

    round(metrics.total_generation_mwh, 3) as total_generation_mwh,
    metrics.matched_hours,
    zone_years.expected_hours,
    round(metrics.matched_hours / zone_years.expected_hours, 4) as coverage,
    round(metrics.solar_coverage, 4) as solar_coverage,
    round(metrics.wind_coverage, 4) as wind_coverage,
    zone_years.known_partial_reason is not null
        or metrics.matched_hours / zone_years.expected_hours < 0.98 as is_partial_year,
    zone_years.known_partial_reason as partial_reason,
    zone_years.data_through_date
from metrics
inner join zone_years using (zone, local_year)
