# A third of Spain's zero-or-negative hours in 2026 were exactly zero

**Question:** Q1 · **Date:** 2026-10-03

## Headline
From 1 January to 2 October 2026 (as-of date), Spain's day-ahead price was ≤ 0 €/MWh in 15.5% of hours (1,020.25 of 6,599 h), and a third of those hours (336 h, 32.9%) were at **exactly** 0 rather than below it.

## Evidence
![Hours at or below zero, 2026 YTD, split into below 0 and exactly 0](../../docs/figures/q1_share_at_or_below_zero_2026.png)

| Zone (2026 to 2 Oct) | Hours < 0 | Hours = 0 | Hours ≤ 0 | Share of hours ≤ 0 | …of which exactly 0 |
|---|---:|---:|---:|---:|---:|
| ES | 684.25 | 336 | 1,020.25 | 15.5% | 32.9% |
| PT | 538 | 334.5 | 872.5 | 13.2% | 38.3% |
| FR | 533.75 | 259.75 | 793.5 | 12.0% | 32.7% |
| DE_LU | 463.25 | 87.75 | 551 | 8.3% | 15.9% |
| NL | 393 | 59.5 | 452.5 | 6.9% | 13.1% |
| PL | 301.25 | 80.5 | 381.75 | 5.8% | 21.1% |
| BE | 303.75 | 45 | 348.75 | 5.3% | 12.9% |
| IT_NORD | 0 | 21.5 | 21.5 | 0.3% | 100% |

Hours covered in 2026: 6,599 for every zone (1 Jan to 2 Oct; all zones cut at the same as-of date, ADR-005). Snapshot: `analysis/outputs/snapshots/2026-10-02/`.

- In 2026, in Spain, Portugal and France about a third of the zero-or-negative hours are at exactly 0 (32.7% to 38.3%); in Germany, the Netherlands and Belgium only 12.9% to 15.9%.
- Ranked by truly negative hours only in 2026, the order changes little at the top (ES 10.4% of hours, PT 8.2%, FR 8.1%), but the gap to Germany (7.0%) is much smaller than the ≤ 0 shares suggest.
- North Italy's 21.5 h in 2026 are all at exactly 0: a market rule, not a data gap (below).

## Method
`fct_negative_hours`, local year 2026: below 0 = `negative_hours`, exactly 0 = `zero_or_negative_hours − negative_hours`, both divided by `covered_hours`. Notebook chart 3 (stacked bar).

## Caveats
- Year to date (`is_partial_year`, `partial_reason = 'current_year'`): a share for 1 Jan to 2 Oct is not a full-year share and should not be compared with full years.
- "At or below zero" (≤ 0) is wider than the headline Q1 metric (< 0); see [[04 Decisions/ADR-005 Negative Hours Metric|ADR-005]].

## Why North Italy is never negative: a market rule
North Italy had no negative price in any year from 2019 to 2 Oct 2026; its lowest price is exactly 0 €/MWh, reached in 2020 (5 h), 2025 (10 h) and 2026 (21.5 h to 2 Oct). That is what the Italian rules allow:
- GME's technical rule on price limits for the day-ahead (MGP) and intraday markets requires sale offers **greater than or equal to 0 €/MWh** and purchase offers greater than 0 (a purchase offer at 0 means "no price limit"). So no Italian offer can clear below 0. Source: [GME, Disposizione tecnica di funzionamento n. 12 MPE, "Limiti di prezzo", published 24 Feb 2015](https://www.mercatoelettrico.org/portals/0/Documents/it-IT/20150220DTF12MPE.pdf), issued under article 26.2 of GME's market rules ([Testo integrato della Disciplina del mercato elettrico](https://www.mercatoelettrico.org/Portals/0/Documents/it-it/20241001_Testo_Integrato_ME.pdf)).
- The regulator ARERA consulted in 2015 on adding a −500 €/MWh floor in MGP and MI to align with the rest of the coupled European market ([ARERA consultation 605/2015/R/eel, 14 Dec 2015](https://www.arera.it/en/schede-tecniche/dettaglio/it/schedetecniche/15/605-15st)). We found no primary source showing it was adopted, or a date for allowing negative prices; GME's January 2026 vademecum of the power exchange describes no change. Market commentary expects negative prices after the TIDE dispatching reform, but we could not confirm this in a GME or ARERA document, so no date is given here.
- Consistent with the data: exact-zero prices occur (the floor binds), negatives never do.

So IT_NORD's position in any ranking of negative hours, battery value (Q3) or EV savings (Q4) partly reflects this market design, not only how much solar or wind it has.

## So what?
In Spain, Portugal and France, free or negative power was available in about 1 of every 8 hours in 2026 to 2 Oct (12.0% to 15.5%). That is the size of the window Q4 (EV charging) can target.
