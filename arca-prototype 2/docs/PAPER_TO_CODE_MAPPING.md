# Paper-to-code mapping

Every architectural component named in the paper is implemented somewhere
in this repository. This table is the index — use it to find the code
behind any specific paragraph, table, or figure.

| Paper section | Component | Code |
|---|---|---|
| Sec. II, statement of contribution | CRR interface (AI recommendation → deterministic rule) | `arca/layer1_intelligence/crr.py` |
| Sec. V-C | Jurisdictional Regulatory Analysis Agent | `arca/layer1_intelligence/jurisdiction_agent.py` |
| Sec. V-C | Investor Eligibility Evaluation Agent | `arca/layer1_intelligence/eligibility_agent.py` |
| Sec. V-C | Transaction Risk Scoring Agent (SHAP-explained) | `arca/layer1_intelligence/risk_scoring_agent.py` |
| Sec. V-C | Behavioural Anomaly Detection Agent | `arca/layer1_intelligence/anomaly_detection_agent.py` |
| Sec. V-C | Compliance Recommendation Record | `arca/layer1_intelligence/crr.py` |
| Sec. V-D | Decentralized Identity Registry | `arca/layer2_identity/did_registry.py` |
| Sec. V-D | Verifiable Credentials Management | `arca/layer2_identity/verifiable_credentials.py` |
| Sec. V-D | Zero-Knowledge Proof Verification Module | `arca/layer2_identity/zkp_module.py` |
| Sec. V-E | Compliance Rule Registry Module | `arca/layer3_runtime/rule_registry.py`, `arca/layer3_runtime/models.py` |
| Sec. V-E | Transaction Validation Module | `arca/layer3_runtime/transaction_validator.py` |
| Sec. V-E / V-F | Registry of approved compliance agents and credential issuers (quorum-governed) | `arca/layer3_runtime/role_registry.py`, `arca/layer4_governance/governance.py` |
| Sec. V-D, Threat Class III | Jurisdiction proof bound to an issuer-certified credential | `arca/layer2_identity/jurisdiction_binding.py`, `arca/layer2_identity/verifiable_credentials.py` |
| Sec. V-E | Audit Log Module | `arca/layer3_runtime/audit_log.py` |
| Sec. V-F | Token Standards and Asset Registry | `arca/layer4_governance/asset_registry.py`, `arca/layer3_runtime/contracts/ComplianceToken.sol` |
| Sec. V-F | Regulatory Oracle Network | `arca/layer4_governance/oracle_network.py` |
| Sec. V-F | Governance Module | `arca/layer4_governance/governance.py` |
| Sec. V-G | Cross-Layer Data Flow / Compliance Lifecycle | `arca/pipeline/end_to_end_demo.py` |
| Table 2 (Sec. VI-A comparative analysis) | — | Qualitative/literature-based; not re-derived from this codebase (see README "What this repo does *not* claim") |
| Table 3 (Sec. VI-C property mapping) | Property → component | `docs/property_mapping_check.py` (regenerates the mapping from the same objects the rest of the code uses, as a consistency check) |
| Sec. VI-B, Threat Class I | Direct Protocol Bypass Attempt | `tests/test_threat_model.py::TestThreatClassI_DirectProtocolBypass` |
| Sec. VI-B, Threat Class II | Stale Compliance Rule Exploitation | `tests/test_threat_model.py::TestThreatClassII_StaleRuleExploitation` |
| Sec. VI-B, Threat Class III | Fraudulent Credential Presentation | `tests/test_threat_model.py::TestThreatClassIII_FraudulentCredentialPresentation` |
| Sec. VI-B, Threat Class III (extended) | Unauthorized recommendations; false jurisdiction claims; governance hardening | `tests/test_trust_checks.py` |
| Sec. VII-B..D (cost) | Validation latency, governance cost, EVM gas | `scripts/benchmark_costs.py`, `docs/BENCHMARKS.md` |
| Sec. VI-B, Threat Class IV | Oracle Data Manipulation | `tests/test_threat_model.py::TestThreatClassIV_OracleDataManipulation` |
| Sec. VIII-B (asset-class applicability) | Real estate / commodity / security examples | `notebooks/03_end_to_end_pipeline.ipynb` (real estate walkthrough); other asset types are configuration (`asset_type` field), not separate code paths |
| Sec. VIII-C (governance latency) | Acknowledged residual vulnerability | Directly exercised in `TestThreatClassII_StaleRuleExploitation` |

## What this repo does *not* claim

- **Table 2's comparative analysis** (application-layer / smart-contract /
  AI-only / static-runtime approaches vs. ARCA) is a qualitative literature
  comparison in the paper. This repo does not include working
  implementations of those four alternative architectures to benchmark
  against — that would be a much larger empirical study in its own right,
  and isn't what Table 2 claims to be (it cites which properties each
  *category* of prior work does or doesn't address, not measured results).
  What this repo *does* provide is a working ARCA implementation you can
  point any future comparative benchmark at.
- **Empirical validation on real transaction/regulatory data** is explicitly
  future work per the paper's own Sec. VII-F and VIII-E — see `data/README.md` for why
  the training data here is synthetic, and the Threat Class II test for the
  one place this prototype makes an *empirical* claim (the latency window
  exists and closes on quorum) rather than just an architectural one.
- The zero-knowledge proofs in `layer2_identity/zkp_module.py` are a real,
  working Sigma-protocol construction, not a mock — but they are not the
  "succinct non-interactive argument of knowledge constructions" (i.e.
  zk-SNARKs) the paper's Sec. V-D describes for production use. See the
  limitation noted in that module's docstring.
