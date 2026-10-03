-- Q3: what a battery could earn from day-ahead arbitrage, per zone, local year
-- and battery duration (ADR-007). One 1 MW battery, at most one full cycle a day,
-- empty at the start and end of each local day, perfect foresight on cleared
-- day-ahead prices: an upper bound for this one market, not a business case.

-- Days after the as-of date are left out, even if the battery table was built
-- from newer prices, so the current year matches the other marts.
with days as (
    select *
    from {{ source('battery', 'arbitrage_daily') }}
    where local_date <= (select as_of_date from {{ ref('int_as_of') }})
),

zone_years as (
    select * from {{ ref('int_zone_years') }}
),

by_year as (
    select
        zone,
        local_year,
        battery_duration_h,
        count(*) as days_solved,
        sum(day_hours) as solved_hours,
        sum(revenue_eur_per_mw) as revenue,
        sum(heuristic_revenue_eur_per_mw) as heuristic_revenue,
        sum(cycles) as cycles,
        sum(charged_mwh) as charged_mwh,
        sum(discharged_mwh) as discharged_mwh,
        sum(discharge_value_eur) / nullif(sum(discharged_mwh), 0) as avg_sell_price,
        sum(charge_cost_eur) / nullif(sum(charged_mwh), 0) as avg_buy_price,
        sum(charged_negative_mwh) as charged_negative_mwh,
        sum(negative_charging_revenue_eur) as negative_charging_revenue
    from days
    group by zone, local_year, battery_duration_h
)

select
    by_year.zone,
    by_year.local_year,
    by_year.battery_duration_h,
    round(by_year.revenue, 0) as revenue_eur_per_mw,
    round(by_year.revenue / by_year.days_solved, 2) as avg_daily_revenue_eur_per_mw,
    -- Energy-weighted: average price sold at minus average price bought at.
    round(by_year.avg_sell_price - by_year.avg_buy_price, 2) as avg_spread_captured_eur_mwh,
    round(by_year.avg_sell_price, 2) as avg_sell_price,
    round(by_year.avg_buy_price, 2) as avg_buy_price,
    round(by_year.cycles, 1) as cycles,
    round(by_year.cycles / by_year.days_solved, 3) as avg_daily_cycles,
    round(by_year.charged_negative_mwh, 3) as charged_negative_mwh,
    round(by_year.negative_charging_revenue, 0) as negative_charging_revenue_eur,
    -- Share of the year's revenue that was paid to the battery for charging at
    -- negative prices (the rest comes from selling above the purchase price).
    round(by_year.negative_charging_revenue / nullif(by_year.revenue, 0), 4)
        as negative_revenue_share,
    round(by_year.heuristic_revenue, 0) as heuristic_revenue_eur_per_mw,
    round(by_year.revenue / nullif(by_year.heuristic_revenue, 0) - 1, 4) as lp_uplift,
    by_year.days_solved,
    zone_years.expected_hours,
    round(by_year.solved_hours / zone_years.expected_hours, 4) as coverage,
    zone_years.known_partial_reason is not null
        or by_year.solved_hours / zone_years.expected_hours < 0.98 as is_partial_year,
    zone_years.known_partial_reason as partial_reason,
    zone_years.data_through_date
from by_year
inner join zone_years using (zone, local_year)
