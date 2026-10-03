# Overnight charging is losing its edge; in Spain it now costs more than charging at 18:00

**Question:** Q4 · **Date:** 2026-10-03

## Headline
In 2019, charging overnight (22:00 to 07:00) got **88% to 100%** of the saving that smart charging got (e.g. DE_LU 42.9% vs 49.0% of the 18:00 cost). In 2025 it got only **23% to 67%** of it (DE_LU 39.3% vs 72.0%), and in Spain in 2026 to 2 Oct (as-of date; snapshot `analysis/outputs/snapshots/2026-10-02/`) overnight charging costs **34.9% more** than plugging in at 18:00.

## Evidence

Savings vs charging at 18:00 (share of the 18:00 cost):

| Zone | Overnight 2019 | Smart 2019 | Overnight 2025 | Smart 2025 | Overnight 2026 to 2 Oct | Smart 2026 to 2 Oct |
|---|---:|---:|---:|---:|---:|---:|
| BE | 44.3% | 47.1% | 37.1% | 72.1% | 26.9% | 74.5% |
| DE_LU | 42.9% | 49.0% | 39.3% | 72.0% | 27.0% | 79.0% |
| ES | 19.8% | 22.1% | 15.3% | 67.2% | −34.9% | 77.5% |
| FR | 43.2% | 45.3% | 46.9% | 71.7% | 29.8% | 82.6% |
| IT_NORD | 34.8% | 36.6% | 26.3% | 39.1% | 21.2% | 42.0% |
| NL | 36.8% | 38.4% | 38.9% | 73.7% | 26.4% | 77.9% |
| PL* | 29.6% | 29.6% | 40.5% | 67.2% | 33.9% | 77.2% |
| PT | 22.3% | 24.0% | 33.7% | 72.4% | 10.3% | 83.2% |

\*PL: 2020 instead of 2019.

- Spain, summer 2025: overnight cost 52.9% more than 18:00 (Portugal 2.7% more). In Iberia the 18:00 block still catches the end of the solar trough in summer, while nights are priced higher.
- North Italy: GME accepts day-ahead offers only at or above 0 €/MWh, so prices there cannot go negative ([[Q1-3 Share of hours at or below zero 2026|Q1-3]]); its smaller savings partly reflect that market rule.

## Method
`fct_ev_charging` (seasons and `year`), same definitions as [[Q4-2 Smart charging savings|Q4-2]]. Negative savings are kept, not clipped (ADR-008).

## Caveats
- 2026 is 1 Jan to 2 Oct (275 days), so it is weighted towards spring and summer, when nights compare worst; full-year 2026 will likely look less extreme.
- Wholesale component only.

## So what?
A fixed overnight timer, the classic "off-peak" advice, now leaves most of the saving on the table, and in Iberia it can raise costs. Charging needs to follow the day-ahead price, not the clock.
