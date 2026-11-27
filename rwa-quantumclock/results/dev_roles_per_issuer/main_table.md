| Policy | Mean realized cost (USD m) | 95% CI | Protected by 2030 | Protected by 2032 | Diff vs QAMP (USD m) | p (Holm) |
|---|---|---|---|---|---|---|
| oracle | 277.9 | 117.1–462.2 | nan | nan | -53.23 | 5e-05 |
| qamp_stochastic | 371.8 | 313.2–437.6 | 1.000 | 1.000 | +0.00 | nan |
| qamp_no_kb | 371.8 | 313.2–437.6 | 1.000 | 1.000 | +0.00 | 1 |
| qamp_cost_first | 371.9 | 313.3–437.8 | 1.000 | 1.000 | +0.11 | 0.57 |
| qamp_pessimistic | 383.7 | 324.2–451.1 | 1.000 | 1.000 | +11.89 | 0.0006 |
| qamp_no_windows | 401.2 | 341.0–468.8 | 1.000 | 1.000 | +29.37 | 0.0006 |
| greedy_risk | 407.7 | 345.0–477.1 | 1.000 | 1.000 | +35.89 | 0.0006 |
| mosca | 411.7 | 349.7–481.7 | 1.000 | 1.000 | +39.90 | 0.0006 |
| qamp_expected | 416.5 | 353.3–486.4 | 1.000 | 1.000 | +44.69 | 0.0006 |
| asap_fifo | 418.6 | 354.6–489.5 | 1.000 | 1.000 | +46.84 | 0.0006 |
| kg_score | 505.4 | 421.3–594.8 | 1.000 | 1.000 | +133.56 | 0.0006 |
| annual_review | 557.0 | 484.0–636.0 | 1.000 | 1.000 | +185.23 | 0.0006 |
| deadline | 3,548.1 | 3,217.3–3,885.5 | 0.587 | 1.000 | +3176.34 | 0.0006 |
| none | 16,666.7 | 16,120.9–17,210.5 | 0.000 | 0.000 | +16294.92 | 0.0006 |

The oracle row is computed on the oracle subset of evaluation scenarios only.


Price of compliance: none. Both QAMP modes miss the deadline equally often (cost gap USD -0.1m, within solver tolerance).
