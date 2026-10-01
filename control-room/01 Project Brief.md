# Project Brief

## One-liner
How often is power free in Europe — and what is a battery worth in each country?

## Why this matters (the business problem)
Solar and wind now push European day-ahead prices to zero or negative for hours at a time.
- **Solar & wind owners** earn less exactly when they produce most ("cannibalisation").
- **Battery developers** can be paid to charge and sell later — but where is it worth it?
- **EV fleets & large consumers** can cut costs by shifting demand into cheap hours.

Target readers: hiring managers at European utilities, energy traders, battery/EV startups, and any data team that values end-to-end analytics.

## Questions
| # | Question | Metric | Deliverable |
|---|----------|--------|-------------|
| Q1 | How often are prices negative? | Negative-price hours per zone per year | Trend chart + ranking |
| Q2 | Does solar eat its own value? | Solar capture price & capture rate | Capture-rate curve vs. solar share |
| Q3 | Where should you build a battery? | Est. €/MW/year from daily arbitrage | Country ranking table |
| Q4 | When should EVs charge? | Avg price by hour × season × zone | Heatmap + "best window" |

## Scope
- **Bidding zones ([[ADR-002 Bidding Zones]]):** ES, PT, FR, DE_LU, NL, BE, PL, IT_NORD
- **Period:** 2019-01-01 → latest available (covers pre-crisis, 2022 crisis, renewables surge)
- **Data:** day-ahead prices, actual generation per type (solar, wind), total load

## Out of scope (on purpose)
- Intraday & balancing markets
- Price forecasting / ML models (maybe a v2)
- Grid-fee and tax effects on retail prices

## Definition of done
- [ ] Pipeline refreshes automatically (GitHub Actions)
- [ ] dbt models with tests and generated docs
- [ ] Notebooks answering Q1–Q4, each with a headline number
- [ ] Live dashboard on sbaiii.com
- [ ] One-page exec memo with 3 recommendations
- [ ] README a recruiter understands in 60 seconds
- [ ] LinkedIn post
