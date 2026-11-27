| Policy | Mean realized cost (USD m) | 95% CI | Protected by 2030 | Protected by 2032 | Diff vs QAMP (USD m) | p (Holm) |
|---|---|---|---|---|---|---|
| oracle | 304.3 | 161.2–477.9 | nan | nan | -57.35 | 5e-05 |
| qamp_stochastic | 344.8 | 290.4–400.1 | 1.000 | 1.000 | +0.00 | nan |
| qamp_no_kb | 344.8 | 290.4–400.1 | 1.000 | 1.000 | -0.00 | 1 |
| qamp_cost_first | 344.8 | 290.4–400.1 | 1.000 | 1.000 | -0.00 | 1 |
| qamp_pessimistic | 358.0 | 302.1–414.6 | 1.000 | 1.000 | +13.24 | 0.0006 |
| qamp_no_windows | 374.1 | 316.7–431.7 | 1.000 | 1.000 | +29.32 | 0.0006 |
| greedy_risk | 378.6 | 320.5–437.9 | 1.000 | 1.000 | +33.80 | 0.0006 |
| mosca | 379.0 | 320.0–439.5 | 1.000 | 1.000 | +34.25 | 0.0006 |
| qamp_expected | 390.5 | 329.6–451.7 | 1.000 | 1.000 | +45.68 | 0.0006 |
| asap_fifo | 391.1 | 331.2–451.8 | 1.000 | 1.000 | +46.29 | 0.0006 |
| kg_score | 477.8 | 399.2–555.4 | 1.000 | 1.000 | +133.00 | 0.0006 |
| annual_review | 509.7 | 438.2–580.8 | 1.000 | 1.000 | +164.86 | 0.0006 |
| deadline | 3,216.6 | 2,901.0–3,554.1 | 0.583 | 1.000 | +2871.82 | 0.0006 |
| none | 15,862.9 | 15,298.9–16,419.0 | 0.000 | 0.000 | +15518.10 | 0.0006 |

The oracle row is computed on the oracle subset of evaluation scenarios only.


Price of compliance: none. Both QAMP modes miss the deadline equally often (cost gap USD 0.0m, within solver tolerance).
