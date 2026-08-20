# Component → Paper Mapping

This is the table reviewers look for: every ARCA module in the paper, and the
code that implements it. Drop a version of this straight into the manuscript's
"Prototype Implementation" section.

| Paper layer | Paper component | This repo |
|---|---|---|
| L1 Compliance Intelligence | Investor Eligibility Evaluation Agent | `compliance-ai/src/arca_ai/agents/eligibility.py` |
| L1 Compliance Intelligence | Transaction Risk Scoring Agent | `compliance-ai/src/arca_ai/agents/risk_scoring.py` |
| L1 Compliance Intelligence | Compliance Recommendation Record (CRR) | `compliance-ai/src/arca_ai/crr.py` |
| L2 Verification & Identity | ZKP predicate (accreditation) | `circuits/src/accreditation.circom` |
| L2 Verification & Identity | On-chain ZKP verify + record | `pallets/verification/` |
| L3 Runtime Enforcement | Transaction Validation Module | `pallets/transaction-validation/` |
| L3 Runtime Enforcement | Compliance Rule Registry | `pallets/rule-registry/` |
| L3 Runtime Enforcement | Audit Log | `pallets/audit-log/` |
| L4 Asset & Governance | Governance gate (CRR admission) | `pallets/governance/` + `compliance-ai/src/arca_ai/governance_gate.py` |
| L4 Asset & Governance | Asset Registry / token standard | `pallets/asset-registry/` |

## Claims → evidence

| Paper claim | Where it's demonstrated |
|---|---|
| Enforcement is non-bypassable (§V-A, Threat I) | `pallets/transaction-validation/src/tests.rs::raw_bypass_is_still_rejected`, `experiments/bypass_experiment.py` |
| AI output cannot self-enforce (§V-A adaptive-intelligence principle) | `governance_gate.py`, `pallets/governance/`, `test_crr.py::test_tampered_crr_fails` |
| Privacy-preserving eligibility (Dim IV) | `circuits/src/accreditation.circom` (net_assets private) |
| ZK overhead is practical (§V-D) | `experiments/bench_zkp.py` → `results/raw/zkp.csv` |
| Validation latency | `pallets/.../benchmarking.rs`, `experiments/bench_latency.py` |
