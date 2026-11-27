| Policy | Mean realized cost (USD m) | 95% CI | Protected by 2030 | Protected by 2032 | Diff vs QAMP (USD m) | p (Holm) |
|---|---|---|---|---|---|---|
| oracle | 277.6 | 127.4–457.3 | nan | nan | -50.15 | 5e-05 |
| qamp_stochastic | 379.3 | 317.4–447.8 | 1.000 | 1.000 | +0.00 | nan |
| qamp_no_kb | 379.3 | 317.4–447.8 | 1.000 | 1.000 | +0.00 | 1 |
| qamp_cost_first | 379.3 | 317.4–447.8 | 1.000 | 1.000 | +0.00 | 0.88 |
| qamp_no_windows | 385.0 | 322.4–453.8 | 1.000 | 1.000 | +5.75 | 0.0006 |
| qamp_pessimistic | 395.9 | 332.5–465.4 | 1.000 | 1.000 | +16.62 | 0.0006 |
| greedy_risk | 419.4 | 353.1–492.7 | 1.000 | 1.000 | +40.14 | 0.0006 |
| mosca | 422.3 | 355.6–496.4 | 1.000 | 1.000 | +43.03 | 0.0006 |
| qamp_expected | 427.8 | 359.8–502.6 | 1.000 | 1.000 | +48.51 | 0.0006 |
| asap_fifo | 431.8 | 363.4–506.9 | 1.000 | 1.000 | +52.55 | 0.0006 |
| kg_score | 522.3 | 434.5–616.6 | 1.000 | 1.000 | +143.06 | 0.0006 |
| annual_review | 577.7 | 498.4–660.9 | 1.000 | 1.000 | +198.41 | 0.0006 |
| deadline | 3,331.5 | 3,018.8–3,646.3 | 0.575 | 1.000 | +2952.26 | 0.0006 |
| none | 15,649.1 | 15,136.6–16,159.7 | 0.000 | 0.000 | +15269.87 | 0.0006 |

The oracle row is computed on the oracle subset of evaluation scenarios only.


Price of compliance (QAMP compliance-first vs cost-first): extra expected cost USD 0.0m for 0.00 fewer deadline misses.
