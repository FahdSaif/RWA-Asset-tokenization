| Policy | Mean realized cost (USD m) | 95% CI | Protected by 2030 | Protected by 2032 | Diff vs QAMP (USD m) | p (Holm) |
|---|---|---|---|---|---|---|
| oracle | 320.6 | 176.8–495.2 | nan | nan | -74.21 | 5e-05 |
| qamp_no_kb | 369.6 | 312.7–426.2 | 1.000 | 1.000 | -0.01 | 1 |
| qamp_stochastic | 369.6 | 312.8–426.1 | 1.000 | 1.000 | +0.00 | nan |
| qamp_cost_first | 369.6 | 312.8–426.1 | 1.000 | 1.000 | +0.00 | 1 |
| qamp_pessimistic | 383.2 | 325.1–441.9 | 1.000 | 1.000 | +13.60 | 0.0006 |
| qamp_no_windows | 399.2 | 338.5–458.6 | 1.000 | 1.000 | +29.54 | 0.0006 |
| greedy_risk | 399.6 | 339.2–460.4 | 1.000 | 1.000 | +29.98 | 0.0006 |
| mosca | 401.4 | 341.5–461.6 | 1.000 | 1.000 | +31.74 | 0.0006 |
| qamp_expected | 406.5 | 344.8–467.5 | 0.999 | 1.000 | +36.91 | 0.0006 |
| asap_fifo | 409.2 | 347.5–471.5 | 1.000 | 1.000 | +39.54 | 0.0006 |
| kg_score | 501.4 | 420.9–580.7 | 1.000 | 1.000 | +131.76 | 0.0006 |
| annual_review | 531.0 | 459.6–601.7 | 1.000 | 1.000 | +161.40 | 0.0006 |
| deadline | 3,217.6 | 2,899.8–3,559.4 | 0.594 | 1.000 | +2847.96 | 0.0006 |
| none | 15,862.9 | 15,298.9–16,419.0 | 0.000 | 0.000 | +15493.27 | 0.0006 |

The oracle row is computed on the oracle subset of evaluation scenarios only.


Price of compliance: none. Both QAMP modes miss the deadline equally often (cost gap USD 0.0m, within solver tolerance).
