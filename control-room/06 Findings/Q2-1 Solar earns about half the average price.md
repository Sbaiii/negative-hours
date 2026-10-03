# Solar now earns about half the average power price in most zones

**Question:** Q2 · **Date:** 2026-10-03

## Headline
In 2025, a MWh of solar earned only 51 to 59% of the average day-ahead price in 5 of 8 zones (BE, DE_LU, PT, ES, FR); in 2019 the same zones were at 92 to 102%.

## Evidence
![Solar capture rate per zone and year](../../docs/figures/q2_solar_capture_rate_by_zone.png)

| Zone | Capture rate 2019 | Capture rate 2025 | Solar capture price 2025 (€/MWh) | Baseload 2025 (€/MWh) | 2026 YTD |
|---|---:|---:|---:|---:|---:|
| BE | 92.1% | 51.4% | 42.46 | 82.57 | 55.6% |
| DE_LU | 92.7% | 51.6% | 46.06 | 89.32 | 52.8% |
| PT | 101.9% | 53.4% | 35.34 | 66.18 | 50.1% |
| ES | 101.9% | 55.4% | 36.18 | 65.29 | 51.4% |
| FR | 95.7% | 59.1% | 36.06 | 61.07 | 54.9% |
| NL* | 94.2% | 61.5% | 53.42 | 86.81 | 60.0% |
| PL | 94.2% (2021) | 64.5% | 67.27 | 104.29 | 59.5% |
| IT_NORD | 98.6% | 81.9% | 94.92 | 115.86 | 84.9% |

\*NL: ENTSO-E's solar series covers ~2% of Dutch output; indicative only. PL: solar reported from April 2020, first full year 2021.

- The decline is not a straight line: in 2022 the rate rose again in DE_LU (77.9% → 94.4%), BE, NL, FR and IT_NORD, but not in ES, PT or PL. This note does not try to explain why.
- North Italy is the outlier: 81.9% in 2025, the only zone above 65%.

## Method
`fct_capture_prices` (dbt): capture price = Σ(hourly price × solar MWh) / Σ(solar MWh) on an hourly grid; rate = capture / time-weighted baseload over all price hours (= Q1 `avg_price`) ([[04 Decisions/ADR-006 Hourly Grid and Capture Prices|ADR-006]]). Notebook `analysis/q2_capture_prices.ipynb`, chart 1.
**Check:** DE_LU 2024 solar capture price 46.23 €/MWh vs the published German solar market value of 4.624 ct/kWh (Netztransparenz).

## Caveats
- Solar output is as reported to ENTSO-E (see Data Dictionary). NL is unreliable; other zones were not all checked against national statistics.
- Day-ahead prices only: intraday, balancing and support schemes are not included.
- 2026 is year to date.

## So what?
A solar business case that assumes the average power price overstates revenue by roughly 2× in most of these zones. Developers and lenders should model a capture rate, not the baseload price.
