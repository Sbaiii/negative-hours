select
    zone::varchar as zone,
    ts_utc::timestamptz as ts_utc,
    price_eur_mwh::double as price_eur_mwh,
    resolution_minutes::integer as resolution_minutes
from {{ source('raw', 'prices') }}
