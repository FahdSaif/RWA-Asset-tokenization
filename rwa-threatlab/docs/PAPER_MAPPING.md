# Paper to code to test

Each attack-tree leaf of the paper is an executable scenario with three variants: **baseline** (naive build),
**hardened** (all mitigations) and, where the paper predicts one, **residual** (the capability that survives).
The expected outcome of every cell is asserted in `tests/test_scenarios.py`.

| Tree node | Scenario | Code | Baseline | Hardened | Residual |
|---|---|---|---|---|---|
| A1 raw path | `A1` | `scenarios/branch_a.py::a1` | attack | blocked | n/a (fault assumed absent) |
| A2 gateway defect | `A2` | `branch_a.py::a2` | attack | blocked | n/a |
| A3 privileged forced transfer | `A3a` | `branch_a.py::a3a` | attack | blocked | attack, **after the rule set is corrupted (reduces to B1)** |
| A3 runtime upgrade | `A3b` | `branch_a.py::a3b` | attack | blocked | attack: attested, backdoored build passes bounded tests |
| B1a AND B1b | `B1` | `branch_b.py::b1` | attack | blocked | attack: contestation suppressed |
| B2 latency window | `B2` | `branch_b.py::b2` | attack | blocked | availability attack (false tightening), expires |
| B3a AND B3b | `B3` | `branch_b.py::b3` | attack | blocked | attack: two feeds + colluding quorum, provenance-dependent contestation |
| C1a unlisted / out-of-scope issuer | `C1a` | `branch_c.py::c1a` | attack | blocked | n/a |
| C1 compromised listed issuer | `C1` | `branch_c.py::c1` | attack | **attack** | trust-anchor floor |
| C2 revoked credential | `C2` | `branch_c.py::c2` | attack | blocked | attack inside the freshness bound |
| D1 timing correlation | `D1` | `branch_d.py::d1` | ~69 % linked | ~10 % | ~40 % with little traffic |
| D2 trail granularity | `D2` | `branch_d.py::d2` | ~2.6 bits leaked (worst-5 % anonymity set 19 of 400) | 0 bits | n/a |
| D3a AND D3b issuer linkage | `D3` | `branch_d.py::d3` | 100 % linked | ~8 % | ~57 % (blind issuance, immediate presentation) |
| E1 rule-propagation lag | `E1` | `branch_e.py::e1` | attack | blocked | attack before the pending notice arrives |
| E2 misclassification | `E2` | `branch_e.py::e2` | attack | blocked | attack: issuer declares a weak profile |
| E3a AND E3b bridge identity | `E3` | `branch_e.py::e3` | attack | blocked | n/a |
| E4 cross-chain revocation | `E4` | `branch_e.py::e4` | attack | blocked | attack inside the freshness bound |

Other artefacts of the paper:

| Paper artefact | Code | Test |
|---|---|---|
| Table 1 mediation surface (P1-P8) | `Instance.mediation_report()` | `test_mediation_surface_matches_table_1` |
| Tables 3-4 rubric, floor rule, residual ratings | `risk.py` | `test_rubric_reproduces_residual_ratings` |
| Section 4.4 sensitivity analysis | `risk.sensitivity()` | `test_sensitivity_claims` |
| Section 4.5 / Table 5 mechanised check | `modelcheck.py` | `test_model_check_*` |
| Table 2 threats T16/T17 (trail tampering) | `trail.py` | `test_trail_detects_*` |

The D rows use synthetic generators (heavy-tailed gaps, Zipf jurisdictions); figures are means over fixed seeds and the tests assert bounds, not exact values. See `DATA.md`.

| Section 4.6 adversarial fuzzer and hypotheses | `fuzz.py`, `hypotheses.py` | `tests/test_instruments.py`, `FINDINGS.md` |
