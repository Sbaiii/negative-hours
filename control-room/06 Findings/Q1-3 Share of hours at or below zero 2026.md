# So far in 2026, Spain's price was at or below zero 15% of the time

**Question:** Q1 · **Date:** 2026-10-03

## Headline
From 1 January to 3 October 2026, Spain's day-ahead price was ≤ 0 €/MWh in 15.4% of hours (1,020.25 of 6,623 h). North Italy: 0.3%.

## Evidence
![Share of hours at or below zero, 2026 YTD](../../docs/figures/q1_share_at_or_below_zero_2026.png)

| Zone | Hours ≤ 0 | Hours covered | Share |
|---|---:|---:|---:|
| ES | 1,020.25 | 6,623 | 15.4% |
| PT | 872.5 | 6,622 | 13.2% |
| FR | 793.5 | 6,623 | 12.0% |
| DE_LU | 551 | 6,623 | 8.3% |
| NL | 452.5 | 6,623 | 6.8% |
| PL | 381.75 | 6,623 | 5.8% |
| BE | 348.75 | 6,623 | 5.3% |
| IT_NORD | 21.5 | 6,623 | 0.3% |

- In Spain, 336 of those 1,020.25 hours were at **exactly** 0 (684.25 were below 0). Zero prices make up a large part of the Iberian total.
- PT covers 6,622 h, one less than the others: its local year (Europe/Lisbon) starts one hour later in UTC.

## Method
`fct_negative_hours`, local year 2026: `zero_or_negative_hours / covered_hours`. Notebook chart 3.

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
