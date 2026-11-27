| Policy | Mean realized cost (USD m) | 95% CI | Protected by 2030 | Protected by 2032 | Diff vs QAMP (USD m) | p (Holm) |
|---|---|---|---|---|---|---|
| oracle | 299.7 | 138.4–491.6 | nan | nan | -58.55 | 5e-05 |
| qamp_stochastic | 391.7 | 332.2–459.3 | 1.000 | 1.000 | +0.00 | nan |
| qamp_no_kb | 391.9 | 332.4–459.5 | 1.000 | 1.000 | +0.22 | 0.048 |
| qamp_cost_first | 391.9 | 332.4–459.5 | 1.000 | 1.000 | +0.22 | 0.048 |
| qamp_pessimistic | 405.5 | 343.6–474.5 | 1.000 | 1.000 | +13.77 | 0.0006 |
| qamp_no_windows | 423.3 | 360.1–492.5 | 1.000 | 1.000 | +31.56 | 0.0006 |
| greedy_risk | 425.1 | 360.7–497.6 | 1.000 | 1.000 | +33.41 | 0.0006 |
| mosca | 428.2 | 365.0–499.7 | 1.000 | 1.000 | +36.46 | 0.0006 |
| asap_fifo | 434.4 | 368.8–507.6 | 1.000 | 1.000 | +42.64 | 0.0006 |
| qamp_expected | 436.8 | 371.6–508.8 | 1.000 | 1.000 | +45.09 | 0.0006 |
| kg_score | 523.6 | 438.3–615.5 | 1.000 | 1.000 | +131.86 | 0.0006 |
| annual_review | 573.3 | 499.0–652.7 | 1.000 | 1.000 | +181.54 | 0.0006 |
| deadline | 3,550.2 | 3,218.8–3,887.3 | 0.593 | 1.000 | +3158.43 | 0.0006 |
| none | 16,666.7 | 16,120.9–17,210.5 | 0.000 | 0.000 | +16274.99 | 0.0006 |

The oracle row is computed on the oracle subset of evaluation scenarios only.


Price of compliance: none. Both QAMP modes miss the deadline equally often (cost gap USD -0.2m, within solver tolerance).
