select
    zone::varchar as zone,
    ts_utc::timestamptz as ts_utc,
    load_mw::double as load_mw,
    resolution_minutes::integer as resolution_minutes
from {{ source('raw', 'load') }}
