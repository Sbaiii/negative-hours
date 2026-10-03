select
    zone::varchar as zone,
    ts_utc::timestamptz as ts_utc,
    price_eur_mwh::double as price_eur_mwh,
    resolution_minutes::integer as resolution_minutes
from {{ raw_source('prices') }}
-- Before Poland joined European market coupling (delivery day 2019-11-20, CET),
-- ENTSO-E's PL prices are in PLN, not EUR (entsoe-py ignores the currency field).
-- They can't go in a EUR column, so they are left out rather than converted.
where not (zone = 'PL' and ts_utc < timestamptz '2019-11-19 23:00:00+00')
