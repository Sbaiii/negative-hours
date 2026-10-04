-- Solar capture price per zone and LOCAL calendar month. Used to test where a
-- year's capture rate comes from: which months were expensive vs which were sunny.
-- Same definitions as fct_capture_prices (ADR-006): baseload over all price
-- periods of the month, capture price over matched generation periods.

with prices as (
    select
        zone,
        local_year,
        cast(date_trunc('month', local_date) as date) as local_month,
        sum(price_eur_mwh * duration_h) / sum(duration_h) as baseload_price
    from {{ ref('int_prices_local') }}
    group by zone, local_year, local_month
),

solar as (
    select
        zone,
        cast(date_trunc('month', local_date) as date) as local_month,
        sum(solar_mwh) as solar_mwh,
        sum(price_eur_mwh * solar_mwh) / nullif(sum(solar_mwh), 0) as solar_capture_price,
        coalesce(sum(duration_h) filter (where solar_mwh is not null), 0) / sum(duration_h)
            as solar_coverage
    from {{ ref('int_energy_periods') }}
    group by zone, local_month
)

select
    prices.zone,
    prices.local_year,
    prices.local_month,
    round(prices.baseload_price, 2) as baseload_price,
    round(solar.solar_mwh, 3) as solar_mwh,
    round(solar.solar_capture_price, 2) as solar_capture_price,
    round(solar.solar_capture_price / prices.baseload_price, 6) as solar_capture_rate,
    round(solar.solar_coverage, 6) as solar_coverage
from prices
left join solar using (zone, local_month)
