| Policy | Mean realized cost (USD m) | 95% CI | Protected by 2030 | Protected by 2032 | Diff vs QAMP (USD m) | p (Holm) |
|---|---|---|---|---|---|---|
| qamp_no_kb | 495.4 | 431.8–565.2 | 0.989 | 0.997 | -298.57 | 0.0006 |
| qamp_cost_first | 495.4 | 431.9–565.3 | 0.989 | 0.997 | -298.56 | 0.0006 |
| qamp_no_windows | 521.6 | 455.1–593.5 | 0.989 | 0.997 | -272.41 | 0.0006 |
| greedy_risk | 522.2 | 455.6–595.2 | 0.989 | 0.997 | -271.83 | 0.0006 |
| mosca | 527.7 | 460.0–601.0 | 0.989 | 0.997 | -266.35 | 0.0006 |
| asap_fifo | 531.9 | 464.0–606.0 | 0.989 | 0.997 | -262.06 | 0.0006 |
| oracle | 618.1 | 441.8–826.4 | nan | nan | -143.29 | 5e-05 |
| kg_score | 619.7 | 532.7–713.1 | 0.989 | 0.997 | -174.28 | 0.0006 |
| annual_review | 749.2 | 671.8–832.3 | 0.980 | 0.986 | -44.76 | 0.0006 |
| qamp_pessimistic | 787.2 | 715.9–863.7 | 0.959 | 0.965 | -6.81 | 0.00085 |
| qamp_stochastic | 794.0 | 725.9–868.6 | 0.959 | 0.965 | +0.00 | nan |
| qamp_expected | 834.1 | 759.5–914.0 | 0.959 | 0.965 | +40.09 | 0.0006 |
| deadline | 3,340.5 | 3,031.3–3,653.4 | 0.586 | 0.997 | +2546.53 | 0.0006 |
| none | 15,649.1 | 15,136.6–16,159.7 | 0.000 | 0.000 | +14855.11 | 0.0006 |

The oracle row is computed on the oracle subset of evaluation scenarios only.


Price of compliance (QAMP compliance-first vs cost-first): extra expected cost USD 298.6m for 0.70 fewer deadline misses.
