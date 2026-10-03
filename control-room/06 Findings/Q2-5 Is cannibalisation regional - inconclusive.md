# Is solar cannibalisation regional? Inconclusive with this data

**Question:** Q2 · **Date:** 2026-10-03

## Headline
France's and Belgium's solar capture rates correlate about as strongly with the coupled region's solar share (FR + DE_LU + ES + BE) as with their own (r ≈ −0.6 to −0.9 either way). The two shares rise almost in lockstep (r = 0.98 to 0.99), so this test cannot tell regional from local cannibalisation.

## Evidence
| Zone | Years | n | r, own share | r, regional share | Spearman own | Spearman regional | r between the two shares |
|---|---|---:|---:|---:|---:|---:|---:|
| FR | 2019 to 2025 | 7 | −0.64 | −0.76 | −0.75 | −0.79 | +0.98 |
| FR | 2019 to 2025 without 2022 | 6 | −0.88 | −0.93 | −0.94 | −1.00 | +0.99 |
| BE | 2019 to 2025 | 7 | −0.82 | −0.76 | −0.68 | −0.71 | +0.98 |
| BE | 2019 to 2025 without 2022 | 6 | −0.89 | −0.87 | −0.77 | −0.83 | +0.99 |

Regional share = Σ solar MWh / Σ total generation MWh over FR, DE_LU, ES, BE, as reported to ENTSO-E (5.1% in 2019, 12.9% in 2025).

2026 is left out: a partial year (to the as-of date) is not comparable with full years in a yearly correlation.

No chart: the result is not clear either way.

## What the data supports
- Both own and regional solar share are strongly negatively correlated with the capture rate in FR and BE.
- France's regional correlation is slightly stronger than its own; Belgium's is about the same. Differences this small, on 6 to 8 points, are not meaningful.

## What it does not support
- Any claim that French or Belgian solar loses value *because of* neighbours' solar. With two inputs this collinear (0.98 to 0.99), yearly data cannot separate them.
- One observation is suggestive but untested: France's capture rate fell to 58.9% in 2025 with only 5.7% solar of its own, a low rate for that share compared with other zones (Q2-2).

## What would settle it
Hourly data instead of yearly: e.g. whether French solar-hour prices fall more on days with high German or Spanish solar output, holding French solar constant. That is a separate analysis, not done here.

## Method
`fct_capture_prices`; correlations computed in `analysis/q2_capture_prices.ipynb` (section "Is cannibalisation regional?"). Pearson and Spearman (rank) correlations.

## Caveats
- 7 full years is far too few points for inference; these are descriptive correlations only.
- 2022 is unusual (Q2-4); results are shown with and without it.
