-- Day-ahead prices with each zone's local time and the period length in hours.
-- ts_utc stays the key; local columns are for grouping (local day / year) only.
-- At the autumn DST change the local wall clock repeats an hour, so ts_local is
-- not unique.

with prices as (
    select * from {{ ref('stg_prices') }}
),

zones as (
    select zone, timezone from {{ ref('zones') }}
)

select
    prices.zone,
    prices.ts_utc,
    timezone(zones.timezone, prices.ts_utc) as ts_local,
    cast(timezone(zones.timezone, prices.ts_utc) as date) as local_date,
    year(timezone(zones.timezone, prices.ts_utc)) as local_year,
    zones.timezone,
    -- Exact decimals (prices have 2, durations are 0.25 or 1): sums of price x
    -- duration are then exact and identical on every build, so averages never
    -- flip at a rounding boundary.
    cast(prices.price_eur_mwh as decimal(12, 2)) as price_eur_mwh,
    prices.resolution_minutes,
    cast(prices.resolution_minutes / 60.0 as decimal(4, 2)) as duration_h
from prices
inner join zones using (zone)
