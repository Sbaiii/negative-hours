# Wind does not suffer the same: it kept 86 to 96% of the average price in 2025

**Question:** Q2 · **Date:** 2026-10-03

## Headline
In 2025, wind earned 86 to 96% of the average day-ahead price (7 zones), while solar earned 51 to 82% (8 zones).

## Evidence
![Solar vs wind capture rate, 2025](../../docs/figures/q2_solar_vs_wind_2025.png)

| Zone | Solar rate | Wind rate | Gap (points) | Solar capture (€/MWh) | Wind capture (€/MWh) | Wind share |
|---|---:|---:|---:|---:|---:|---:|
| BE | 51.4% | 86.3% | 34.9 | 42.46 | 71.24 | 17.7% |
| DE_LU | 51.6% | 88.4% | 36.8 | 46.06 | 78.95 | 30.4% |
| PT | 53.4% | 91.7% | 38.3 | 35.34 | 60.67 | 27.5% |
| ES | 55.2% | 96.5% | 41.2 | 36.18 | 63.19 | 21.5% |
| FR | 59.1% | 89.7% | 30.6 | 36.06 | 54.74 | 9.1% |
| NL* | 61.5% | 91.6% | 30.1 | 53.42 | 79.52 | 19.3% |
| PL | 64.5% | 94.3% | 29.8 | 67.27 | 98.35 | 13.8% |
| IT_NORD** | 81.9% | 102.4% | 20.5 | 94.92 | 118.68 | 0.3% |

\*NL solar indicative only. \*\*IT_NORD wind is 0.3% of reported generation, too small to compare; left out of the wind range.

- The gap is widest in Spain: wind 96.5% vs solar 55.2%.
- In Germany, a MWh of wind earned 78.95 €/MWh in 2025 and a MWh of solar 46.06.

## Method
`fct_capture_prices`: wind = Wind Onshore + Wind Offshore, same capture-rate formula as solar ([[04 Decisions/ADR-006 Hourly Grid and Capture Prices|ADR-006]]). Notebook chart 3.

## Caveats
- One year (2025). Wind capture rates in earlier years ranged from 73.7% (DE_LU 2022) upward; check the full series before generalising.
- No claim is made here about why wind holds its value better.

## So what?
The value erosion is mostly a solar problem so far, which suggests that adding storage or wind to a solar portfolio could limit exposure to it (not tested here). Q3 will check whether the cheapest hours a battery can buy are the solar hours.
