# POST-REGISTRATION: knowledge-base scenarios

Plan committed before the run: docs/KB_SCENARIOS_PLAN.md. Held-out seeds from 50000; 20,000 planning and 2,000 evaluation scenarios; frozen code. Costs in USD m. Not pre-registered.

Code and rules unchanged during the run: True (git lines changed in src/ and kb/: 0).

| ID | Scenario | Starts changed | Expected misses | Cost (own rules) | Diff vs S0 (95% CI) | Diff vs S0, S0 rules (95% CI) | Price of compliance | Protected 2030 / 2032 |
|---|---|---|---|---|---|---|---|---|
| S0 | Frozen knowledge base | 0 | 0.0 | 369.6 | +0.0 (0.0 to 0.0) | +0.0 (0.0 to 0.0) | +0.0 | 100.0% / 100.0% |
| S1 | Hard deadline 2030 for compliance-critical keys | 5 | 0.0 | 369.7 | +0.0 (-0.2 to 0.2) | +0.0 (-0.2 to 0.2) | +0.0 | 100.0% / 100.0% |
| S2 | Hard deadline 2032 for compliance-critical keys | 4 | 0.0 | 369.6 | -0.0 (-0.2 to 0.2) | -0.0 (-0.2 to 0.2) | -0.0 | 100.0% / 100.0% |
| S3 | Hard deadline 2030 for all quantum-vulnerable keys | 6 | 0.29 | 369.7 | +0.1 (-0.1 to 0.3) | +0.1 (-0.1 to 0.3) | +0.1 | 100.0% / 100.0% |
| S4a | Jurisdictions: EU only | 0 | 0.0 | 367.6 | -2.0 (-2.3 to -1.7) | +0.0 (0.0 to 0.0) | +0.0 | 100.0% / 100.0% |
| S4b | Jurisdictions: US only | 0 | 0.0 | 369.6 | +0.0 (0.0 to 0.0) | +0.0 (0.0 to 0.0) | +0.0 | 100.0% / 100.0% |
| S4c | No retention rules | 0 | 0.0 | 358.8 | -10.8 (-11.5 to -10.1) | +0.0 (0.0 to 0.0) | +0.0 | 100.0% / 100.0% |
| S5 | EU retention 10 years | 2 | 0.0 | 377.0 | +7.3 (6.8 to 8.0) | +0.0 (-0.0 to 0.0) | +0.0 | 100.0% / 100.0% |
| S6 | S3 with capacity 1 per issuer | 31 | 3.9 | 727.3 | +357.6 (307.7 to 408.2) | +357.6 (307.7 to 408.2) | -1.5 | 98.6% / 100.0% |

## Rules and explanations

| ID | Hard deadline (anchors) | Deadline set by | Retention years (anchors) | Validity | Faithfulness | Scenario-rule sentences | Names NIST for another source |
|---|---|---|---|---|---|---|---|
| S0 | {'2036 Q1': 75} | {'NIST8547-DISALLOW': 75} | {'0.0': 18, '6.0': 57} | 1.000 | 1.000 | 0 | 0 |
| S1 | {'2031 Q1': 43, '2036 Q1': 32} | {'NIST8547-DISALLOW': 32, 'SCN-S1-CRITICAL-2030': 43} | {'0.0': 18, '6.0': 57} | 1.000 | 1.000 | 43 | 0 |
| S2 | {'2033 Q1': 43, '2036 Q1': 32} | {'NIST8547-DISALLOW': 32, 'SCN-S2-CRITICAL-2032': 43} | {'0.0': 18, '6.0': 57} | 1.000 | 1.000 | 43 | 43 |
| S3 | {'2031 Q1': 75} | {'SCN-S3-ALL-2030': 75} | {'0.0': 18, '6.0': 57} | 1.000 | 1.000 | 75 | 0 |
| S4a | {'2036 Q1': 75} | {'NIST8547-DISALLOW': 75} | {'0.0': 18, '5.0': 57} | 1.000 | 1.000 | 0 | 0 |
| S4b | {'2036 Q1': 75} | {'NIST8547-DISALLOW': 75} | {'0.0': 18, '6.0': 57} | 1.000 | 1.000 | 0 | 0 |
| S4c | {'2036 Q1': 75} | {'NIST8547-DISALLOW': 75} | {'0.0': 75} | 1.000 | 1.000 | 0 | 0 |
| S5 | {'2036 Q1': 75} | {'NIST8547-DISALLOW': 75} | {'0.0': 18, '10.0': 57} | 1.000 | 1.000 | 57 | 0 |
| S6 | {'2031 Q1': 75} | {'SCN-S3-ALL-2030': 75} | {'0.0': 18, '6.0': 57} | 1.000 | 1.000 | 75 | 0 |

## Planned misses by issuer (no delay)

- S6: {'Ondo': 3}
- S6, issuers that cannot fit by 2031 Q1 whatever the order: Ondo (22 needed, 16 available)
