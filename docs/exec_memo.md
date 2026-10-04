# Free power, expensive evenings: what Europe's negative prices mean for solar, batteries and EVs

**Bottom line:** negative prices are now routine in Europe, but the money is not in the negative hours themselves; it is in the daily gap between cheap middays and expensive evenings, which takes value from solar and gives it to whoever can shift energy in time.

*Day-ahead prices and generation from ENTSO-E for 8 bidding zones (Belgium, France, Germany, the Netherlands, North Italy, Poland, Portugal, Spain). Full years 2019 to 2025; 2026 as of 2 Oct, compared only with the same dates of 2025. [Live dashboard](https://sbaiii.github.io/negative-hours/), updated daily.*

## What we found

- **Negative prices went from rare to routine.** 5 of 8 zones topped 500 negative hours in 2025; before 2023 no zone ever exceeded 298.
- **Solar earns about half the average price.** In 2025 solar earned 51% to 59% of the average price in 5 zones, down from 92% to 102% in 2019; wind kept 86% to 97%.
- **A battery's value depends on where it sits.** An optimised 2 h battery could have earned up to €85.6k per MW in 2025 in Poland, €76.1k in Germany and the Netherlands, and €36.6k in North Italy.
- **The cheapest time to charge moved to midday.** The cheapest hour moved from 03:00 or 04:00 in 2019 to 12:00 to 14:00 in 2025, and smart charging cut an EV's wholesale cost by 67% to 74% in 7 zones.

## What it means

Negative prices are a symptom. The value is in the daily spread between cheap middays and expensive evenings. Poland earned the most per MW of battery in 2025 (€85.6k) with 310 negative hours, against €76.1k in the Netherlands with 584. Being paid to charge was at most 11% of a battery's revenue in any zone and full year from 2019 to 2025.

## Three recommendations

- **Solar developer:** plan merchant revenue on about half the average price, not the full price, since solar captured only 51% to 59% of it in 5 zones in 2025.
- **Battery investor:** rank sites by the evening over midday price spread, not by the count of negative hours: Poland had 310 negative hours to the Netherlands' 584 in 2025 and still earned more (€85.6k vs €76.1k per MW).
- **EV fleet or charging operator:** move flexible charging from the night to the midday window, since in 2025 overnight charging delivered only 23% to 67% of the saving that charging in the cheapest hours achieved.

## How confident are we

- **Negative hours match official statistics:** Germany 2019 to 2024 and France 2023 to 2025 exactly, Spain 2025 within one hour (556 here, 555 reported by pv-magazine).
- **Solar value:** Germany's 2024 solar capture price (46.23 €/MWh) matches the published German solar market value to the cent.
- **Battery revenue:** Germany 2024 (€66k per MW) is the same order of magnitude as a published day-ahead-only estimate (about €70k, Gridcog).
- **Main caveats:** solar output is as reported to ENTSO-E (France 6% below the national figure; the Netherlands is indicative only). Only the day-ahead market is modelled, with perfect foresight, so battery figures are an upper bound. EV figures are wholesale prices only, without taxes, grid fees or retail margins. North Italy's market accepts no offers below 0 €/MWh, so its price can never go negative.

## Open question

Over the same window (1 Jan to 2 Oct), negative hours rose from 2025 to 2026 in Spain (535 to 747), Portugal (190 to 599) and France (493 to 563), and fell in Germany (525 to 471), the Netherlands (538 to 388) and Belgium (488 to 298); Poland was nearly flat (305 to 314). Over the same dates, the solar capture rate rose in Belgium (47.6% to 55.7%) and Germany (48.0% to 51.8%). The data do not show why; that is the next question to answer.

*Method, code and every number's source: [github.com/Sbaiii/negative-hours](https://github.com/Sbaiii/negative-hours). Every figure in this memo is checked automatically against a frozen data snapshot.*
