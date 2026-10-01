# Data Dictionary

_Filled in during Phase 1–2._

## raw_prices
| Column | Type | Description |
|---|---|---|
| ts_utc | timestamp | Start of the period, UTC |
| zone | text | Bidding zone code |
| price_eur_mwh | double | Day-ahead price |
| resolution_minutes | int | 60 or 15 |

## Data quality log
| Date found | Zone | Issue | How handled |
|---|---|---|---|
