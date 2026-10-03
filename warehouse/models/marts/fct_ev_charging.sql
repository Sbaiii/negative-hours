-- Q4: what an EV pays for its electricity (wholesale component only) under three
-- charging strategies, per zone, local year and season (ADR-008). The daily
-- costs and strategy definitions are in int_ev_charging_daily.

{% set energy_kwh = 10.0 %}

with daily as (
    select * from {{ ref('int_ev_charging_daily') }}
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
    select zone, local_year, completeness, partial_reason, data_through_date
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
    year_coverage.partial_reason,
    year_coverage.data_through_date
from by_period
inner join year_coverage using (zone, local_year)
