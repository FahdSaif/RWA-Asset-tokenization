| ID | Tree node | Scenario | Adversary | Baseline | Hardened | Residual |
|---|---|---|---|---|---|---|
| A1 | A1 | Raw / node-level transaction with no validation hook | Adv1 | attack succeeds | blocked | n/a |
| A2 | A2 | Gateway software defect (origin spoofing) | Adv1/2 | attack succeeds | blocked | n/a |
| A3a | A3 | Privileged forced transfer / recovery operation | Adv5 | attack succeeds | blocked | **attack succeeds** |
| A3b | A3 | Runtime upgrade that alters the Gateway | Adv5/6 | attack succeeds | blocked | **attack succeeds** |
| B1 | B1a+B1b | Quorum collusion defeating the challenge window | Adv5 | attack succeeds | blocked | **attack succeeds** |
| B2 | B2 | Rule-activation latency window | Adv2 | attack succeeds | blocked | **attack succeeds** |
| B3 | B3a+B3b | Poisoned regulatory-data feed | Adv4 | attack succeeds | blocked | **attack succeeds** |
| C1a | C1a | Unlisted or out-of-scope issuer | Adv2/3 | attack succeeds | blocked | n/a |
| C1 | C1 | Compromised, listed, in-scope issuer | Adv3 | attack succeeds | attack succeeds | n/a |
| C2 | C2 | Revoked credential inside the status lag | Adv2 | attack succeeds | blocked | **attack succeeds** |
| D1 | D1 | Timing / value correlation | Adv1 | attack succeeds | blocked | **attack succeeds** |
| D2 | D2 | Trail-granularity leakage and error oracle | Adv1 | attack succeeds | blocked | n/a |
| D3 | D3a+D3b | Issuer-linkage deanonymisation | Adv3 | attack succeeds | blocked | **attack succeeds** |
| E1 | E1 | Cross-chain rule-propagation lag | Adv2 | attack succeeds | blocked | **attack succeeds** |
| E2 | E2 | Jurisdictional misclassification | Adv2 | attack succeeds | blocked | **attack succeeds** |
| E3 | E3a+E3b | Bridge identity discontinuity | Adv2 | attack succeeds | blocked | n/a |
| E4 | E4 | Cross-chain revocation lag | Adv2 | attack succeeds | blocked | **attack succeeds** |
