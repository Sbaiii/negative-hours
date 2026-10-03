-- fct_capture_prices.baseload_price and fct_negative_hours.avg_price are the same
-- quantity (time-weighted mean over all price periods of a zone-year, ADR-006).
-- Fails for every zone-year where they differ by more than 0.01 EUR/MWh, or where
-- one mart has a zone-year the other lacks.

select
    coalesce(c.zone, n.zone) as zone,
    coalesce(c.local_year, n.local_year) as local_year,
    c.baseload_price,
    n.avg_price
from {{ ref('fct_capture_prices') }} as c
full outer join {{ ref('fct_negative_hours') }} as n
    on c.zone = n.zone and c.local_year = n.local_year
where c.zone is null
    or n.zone is null
    or abs(c.baseload_price - n.avg_price) > 0.01
