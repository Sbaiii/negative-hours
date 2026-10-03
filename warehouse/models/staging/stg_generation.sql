with source as (
    select
        zone::varchar as zone,
        production_type::varchar as production_type,
        ts_utc::timestamptz as ts_utc,
        generation_mw::double as generation_mw,
        resolution_minutes::integer as resolution_minutes
    from {{ source('raw', 'generation') }}
),

-- ENTSO-E lists production types a zone doesn't have (e.g. Marine in Spain) and
-- reports them as 0 for every period. Drop a type only if it has never been
-- non-zero in that zone, so a new type (e.g. Energy storage) appears as soon as it
-- reports real output.
types_with_output as (
    select zone, production_type
    from source
    group by zone, production_type
    having coalesce(max(abs(generation_mw)), 0) > 0
)

select source.*
from source
inner join types_with_output using (zone, production_type)
