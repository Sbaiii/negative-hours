-- Day-ahead prices up to and including the run's as-of date (int_as_of): the
-- price table every mart and the battery model read. Same columns as
-- int_prices_published; days after the as-of date are left out, so all zones
-- and all marts cover the same days.

select prices.*
from {{ ref('int_prices_published') }} as prices
where prices.local_date <= (select as_of_date from {{ ref('int_as_of') }})
