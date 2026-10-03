# ADR-008: EV charging strategies and the hourly price profile (Q4)

**Date:** 2026-10-03 · **Status:** accepted

## Context
Q4 asks when EVs and fleets should charge. Two marts answer it: `fct_hourly_profile` (the shape of a day's prices) and `fct_ev_charging` (what one EV pays under three charging habits). Both need choices on seasons, the charging block and what "cost" includes.

## Options
1. Rank hours by average price only (no vehicle)
2. A simple vehicle with a daily energy need, priced day by day under explicit strategies, next to the hourly profile

## Decision
Option 2.

**Hourly profile** (`fct_hourly_profile`, zone × local year × season × local hour):
- Seasons are meteorological, kept **inside the local calendar year**: winter = Jan, Feb and Dec of the same year, spring = Mar to May, summer = Jun to Aug, autumn = Sep to Nov. The four seasons then add up to the year.
- Mean price and share of time ≤ 0 are duration-weighted over native periods; the median is over hourly values (15-min periods averaged to the hour first), so every hour counts once in 2025 and 2026.

**EV charging** (`fct_ev_charging`, zone × local year × season, plus season `year`):

| | Value |
|---|---|
| Need | 10 kWh per day, every day |
| Charger | 7 kW → 1 h 25 m 43 s of charging per day |
| Charging block | one **continuous** block at full power; it can start at any price period (hourly, or 15-min since 1 Oct 2025); the last period is charged partly |
| (a) immediate | block starting at **18:00** local on day D |
| (b) overnight | cheapest block inside **22:00 on D to 07:00 on D+1** |
| (c) smart | cheapest block inside day **D (00:00 to 24:00)** |
| Price | wholesale **day-ahead** price only |
| Excluded | retail margin, taxes, levies, grid fees, charging losses, dynamic-tariff fees |
| Foresight | perfect, on day-ahead prices: they are published around noon on D for D+1, before any window opens, so a smart charger can really know them |
| Annualising | € per year = average daily cost in the year (or season) × 365 |

Days are kept only if all three strategies have prices (drops the last day, whose night needs tomorrow's prices).

## Why
- **Continuous block, not the cheapest separate periods:** it is what a simple timer or "charge by 07:00" setting does, and it keeps (b) and (c) comparable with (a). Splitting into the cheapest separate quarter-hours would save a little more; this is a conservative choice.
- **18:00 as "typical":** plugging in on arrival from work is the usual uncontrolled pattern and coincides with the evening peak.
- **Wholesale only:** taxes and grid fees differ by country and tariff and would swamp the comparison; the wholesale part is what timing can change (on a dynamic tariff). The € figures are **not** a household bill.
- **Checked by hand:** DE_LU 15 Jun 2024 (hourly prices): immediate = 7 kWh × (−0.01) + 3 kWh × 40.00 €/MWh = 0.11993 €, the mart's value; smart = −0.72876 €, equal to the cheapest hourly start of the day computed separately. On all 22,340 zone-days smart ≤ immediate (tested).

## Consequences
- Savings are per car and small in absolute terms (hundreds of € per year at most); the relative saving (share) is the more transferable number.
- Prices are taken as given: a large fleet charging in the same hours would raise them.
- Overnight (b) can cost more than immediate (a) where evenings are cheap (e.g. ES 2026); the mart keeps negative savings rather than clipping them.
