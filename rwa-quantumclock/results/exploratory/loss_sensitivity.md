# EXPLORATORY: sensitivity of costs to the loss settings

Held-out seeds from 50000; 20,000 planning and 2,000 evaluation scenarios; one setting changed at a time; base: hazard 1.0, hidden weight 0.25, rho 0.002. Differences in USD m; positive means QAMP is cheaper. Not pre-registered.

| Setting | Value | QAMP mean | ASAP - QAMP (95% CI) | Greedy - QAMP | Mosca - QAMP |
|---|---|---|---|---|---|
| hazard_per_year | 0.25 | 212.3 | +19.8 (17.0 to 22.7) | +15.8 | +17.1 |
| hazard_per_year | 0.5 | 274.3 | +28.3 (23.2 to 33.9) | +21.7 | +23.6 |
| hazard_per_year | 1.0 | 369.6 | +39.5 (31.5 to 48.2) | +30.0 | +31.7 |
| hazard_per_year | 2.0 | 492.7 | +48.1 (37.4 to 59.6) | +36.7 | +36.9 |
| hazard_per_year | 4.0 | 615.6 | +51.6 (38.7 to 65.3) | +40.0 | +37.9 |
| hidden_weight | 0.0 | 369.3 | +39.9 (31.8 to 48.5) | +30.3 | +32.1 |
| hidden_weight | 0.1 | 369.4 | +39.7 (31.7 to 48.4) | +30.2 | +31.9 |
| hidden_weight | 0.25 | 369.6 | +39.5 (31.5 to 48.2) | +30.0 | +31.7 |
| hidden_weight | 0.5 | 369.8 | +39.4 (31.4 to 48.0) | +29.8 | +31.6 |
| hidden_weight | 1.0 | 369.9 | +39.3 (31.3 to 48.0) | +29.8 | +31.5 |
| rho_records | 0.0 | 358.8 | +38.5 (30.5 to 47.1) | +29.2 | +30.9 |
| rho_records | 0.002 | 369.6 | +39.5 (31.5 to 48.2) | +30.0 | +31.7 |
| rho_records | 0.01 | 412.8 | +43.6 (35.4 to 52.4) | +33.1 | +35.1 |
| rho_records | 0.05 | 628.2 | +64.7 (56.0 to 74.4) | +49.4 | +52.5 |
