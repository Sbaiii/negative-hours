# A third of Spain's zero-or-negative hours in 2026 were exactly zero

**Question:** Q1 · **Date:** 2026-10-03

## Headline
From 1 January to 3 October 2026, Spain's day-ahead price was ≤ 0 €/MWh in 15.4% of hours (1,020.25 of 6,623 h), and a third of those hours (336 h, 32.9%) were at **exactly** 0 rather than below it.

## Evidence
![Hours at or below zero, 2026 YTD, split into below 0 and exactly 0](../../docs/figures/q1_share_at_or_below_zero_2026.png)

| Zone | Hours < 0 | Hours = 0 | Hours ≤ 0 | Share of hours ≤ 0 | …of which exactly 0 |
|---|---:|---:|---:|---:|---:|
| ES | 684.25 | 336 | 1,020.25 | 15.4% | 32.9% |
| PT | 538 | 334.5 | 872.5 | 13.2% | 38.3% |
| FR | 533.75 | 259.75 | 793.5 | 12.0% | 32.7% |
| DE_LU | 463.25 | 87.75 | 551 | 8.3% | 15.9% |
| NL | 393 | 59.5 | 452.5 | 6.8% | 13.1% |
| PL | 301.25 | 80.5 | 381.75 | 5.8% | 21.1% |
| BE | 303.75 | 45 | 348.75 | 5.3% | 12.9% |
| IT_NORD | 0 | 21.5 | 21.5 | 0.3% | 100% |

Hours covered: 6,623 for every zone except PT (6,622: its local year, Europe/Lisbon, starts one hour later in UTC).

- In Spain, Portugal and France about a third of the zero-or-negative hours are at exactly 0 (32.7–38.3%); in Germany, the Netherlands and Belgium only 12.9–15.9%.
- Ranked by truly negative hours only, the order changes little at the top (ES 10.3% of hours, PT and FR 8.1%), but the gap to Germany (7.0%) is much smaller than the ≤ 0 shares suggest.
- North Italy's 21.5 h are all at exactly 0; it is drawn in neutral grey because it has no negative hours at all.

## Method
`fct_negative_hours`, local year 2026: below 0 = `negative_hours`, exactly 0 = `zero_or_negative_hours − negative_hours`, both divided by `covered_hours`. Notebook chart 3 (stacked bar).

## Caveats
- Year to date (`is_partial_year`, `partial_reason = 'current_year'`): a share for 1 Jan – 3 Oct is not a full-year share and should not be compared with full years.
- "At or below zero" (≤ 0) is wider than the headline Q1 metric (< 0); see [[04 Decisions/ADR-005 Negative Hours Metric|ADR-005]].

## Open question: why is North Italy never negative?
North Italy had **no** negative price in any year from 2019 to 2026. Its lowest price is exactly 0 €/MWh, reached in 2020 (5 h), 2025 (10 h) and 2026 (21.5 h). This data alone can't say why. To check before writing anything about it:
- Do the Italian bidding zones apply a 0 €/MWh price floor in the day-ahead market (GME / SDAC rules), and has that changed over time?
- Is the IT_NORD series on ENTSO-E the same SDAC price as for the other zones?

Until answered, report IT_NORD as "no negative prices observed" with no explanation.

## So what?
In Spain, Portugal and France, free or negative power was available in about 1 of every 8 hours this year (12.0–15.4%). That is the size of the window Q4 (EV charging) can target.
