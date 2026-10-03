# By 2 October, 2026 had already earned more than all of 2025 in every zone; on hourly prices (like for like), in 4 of 8

**Question:** Q3 · **Date:** 2026-10-03

## Headline
As of 2 Oct 2026, a 2-hour battery's day-ahead revenue for 1 Jan to 2 Oct already exceeds its full-year 2025 revenue in all 8 zones (DE_LU: €78,911 vs €76,060), at native 15-min prices. On hourly prices, like for like with the hourly years, it does so in only 4 of 8 (BE, ES, FR, IT_NORD). 2022 remains the record year in 5 zones; in Spain, Portugal and Poland, 2026 to date is already the highest.

## Evidence
![Revenue by zone, 2019 to 2026](../../docs/figures/q3_revenue_by_zone_over_time.png)

| Zone | 2019 | 2022 | 2023 | 2025 | 2026 to 2 Oct | 2026 on hourly prices | Added by 15-min |
|---|---:|---:|---:|---:|---:|---:|---:|
| PL | (PLN) | 79,785 | 36,674 | 85,640 | 87,529 | 82,126 | 6.6% |
| DE_LU | 16,471 | 102,138 | 55,478 | 76,060 | 78,911 | 75,007 | 5.2% |
| NL | 13,822 | 114,276 | 62,405 | 76,053 | 78,382 | 74,041 | 5.9% |
| BE | 16,572 | 107,719 | 51,210 | 68,212 | 73,257 | 68,539 | 6.9% |
| ES | 7,226 | 47,693 | 41,684 | 60,742 | 62,771 | 61,464 | 2.1% |
| PT | 6,879 | 47,111 | 39,241 | 58,915 | 59,843 | 58,637 | 2.1% |
| FR | 14,799 | 92,181 | 47,065 | 55,340 | 66,218 | 61,947 | 6.9% |
| IT_NORD | 14,326 | 81,296 | 40,609 | 36,558 | 40,188 | 36,588 | 9.8% |

(€ per MW, 2-hour battery. 2026 to 2 Oct, the as-of date; snapshot `analysis/outputs/snapshots/2026-10-02/`.)

- Revenue rose 2.6× (IT_NORD) to 8.6× (PT) from 2019 to 2025.
- **15-minute prices** (since 1 Oct 2025) add 2.1% (PT) to 9.8% (IT_NORD) to 2026 revenue. Re-solved on hourly averages, 2026 to date is still ahead of all of 2025 in 4 zones (BE, ES, FR, IT_NORD) but not in the other 4. So part of the "already beaten" headline is the finer resolution, and part is wider daily spreads (DE_LU: €273 a day on hourly prices in 2026 vs €208 in 2025).
- 2025 is not purely hourly either: its last quarter (1 Oct to 31 Dec 2025) already uses 15-min prices.

## Method
`fct_battery_arbitrage` (2 h). The hourly comparison re-solves every 2026 day in the notebook with prices averaged per hour (section "How much of 2026 comes from 15-minute prices?").

## Caveats
- 2026 is 275 days (to 2 Oct); the comparison is year to date vs a full year, which makes the 2026 figure conservative, not inflated.
- North Italy: GME accepts day-ahead offers only at or above 0 €/MWh, so prices there cannot go negative ([[Q1-3 Share of hours at or below zero 2026|Q1-3]]); its place in this ranking partly reflects that market rule.
- Same upper-bound caveats as [[Q3-1 Where day-ahead arbitrage paid most in 2025|Q3-1]].
- No claim is made here about why 2026 daily spreads are wider.

## So what?
Day-ahead arbitrage value is not fading: on these numbers it has grown every year since 2023 in every zone except France and North Italy, which dipped in 2024. The move to 15-minute products is worth a few percent on top.
