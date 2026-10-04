-- Day-ahead prices as hourly means (up to the as-of date): one row per zone and
-- UTC hour. This is the convention of published negative-hour counts (RTE, REE,
-- most market reports): an hour is negative when its mean price is below 0. Before
-- 2025-10-01 every period is an hour, so the mean is the price itself; after it,
-- the mean of the hour's four quarter-hours (ADR-005).

select
    zone,
    date_trunc('hour', ts_utc) as hour_utc,
    min(local_date) as local_date,
    min(local_year) as local_year,
    sum(price_eur_mwh * duration_h) / sum(duration_h) as hourly_mean_price,
    -- Hours of the hour with a price (1.0 when complete).
    sum(duration_h) as hours
from {{ ref('int_prices_local') }}
group by zone, date_trunc('hour', ts_utc)
