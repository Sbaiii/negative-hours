# ENTSO-E Transparency Platform

- **URL:** https://transparency.entsoe.eu/
- **Who:** European Network of Transmission System Operators for Electricity — the official source.
- **Access:** free account → request REST API access → personal security token (store in `.env` as `ENTSOE_API_KEY`).
- **Python client:** `entsoe-py` (`EntsoePandasClient`).

## Datasets we use
| Dataset | entsoe-py method | Granularity |
|---|---|---|
| Day-ahead prices | `query_day_ahead_prices` | 60 min → 15 min (2025) |
| Actual generation per type | `query_generation` | 15–60 min, zone-dependent |
| Actual total load | `query_load` | 15–60 min |

## Gotchas to watch
- Requests are limited in size → query **per zone, per year** (or smaller).
- Timestamps come timezone-aware → convert to UTC on ingest.
- Resolution differs by zone and changed over time.
- DST days have 23 / 25 hours.
- Gaps and revisions happen — log them in [[Data Dictionary]].
