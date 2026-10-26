"""
Regenerates the paper's Table 3 (Sec. VI-C, "Mapping of Recognized
Compliance System Properties to ARCA Components") as a consistency
check: for each property, it imports the exact class/function the paper
claims provides it and confirms it actually exists and is importable.
This is not a proof the property genuinely holds (that's what the
threat-model tests are for) — it's a much weaker but still useful check
that Table 3 in the paper and the code in this repo have not drifted
apart from each other.

Run: python docs/property_mapping_check.py
"""
from __future__ import annotations

import importlib
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))


def _check(module_path: str, attr: str) -> str:
    try:
        mod = importlib.import_module(module_path)
        getattr(mod, attr)
        return "OK"
    except (ImportError, AttributeError) as exc:
        return f"MISSING ({exc})"


PROPERTY_TABLE = [
    ("Enforceability", "arca.layer3_runtime.transaction_validator", "TransactionValidationModule"),
    ("Auditability", "arca.layer3_runtime.audit_log", "HashChainLedger"),
    ("Auditability", "arca.layer1_intelligence.crr", "ComplianceRecommendationRecord"),
    ("Adaptability", "arca.layer1_intelligence.jurisdiction_agent", "JurisdictionalRegulatoryAnalysisAgent"),
    ("Adaptability", "arca.layer4_governance.oracle_network", "RegulatoryOracleNetwork"),
    ("Adaptability", "arca.layer4_governance.governance", "GovernanceModule"),
    ("Privacy", "arca.layer2_identity.zkp_module", "verify_membership"),
    ("Privacy", "arca.layer2_identity.did_registry", "DIDRegistry"),
    ("Interoperability", "arca.layer2_identity.did_registry", "generate_did"),
    ("Interoperability", "arca.layer2_identity.verifiable_credentials", "VerifiableCredential"),
    ("Accountability", "arca.layer1_intelligence.risk_scoring_agent", "TransactionRiskScoringAgent"),
]


if __name__ == "__main__":
    print(f"{'Property':<18} {'Component':<45} {'Status'}")
    print("-" * 80)
    all_ok = True
    for prop, module_path, attr in PROPERTY_TABLE:
        status = _check(module_path, attr)
        all_ok = all_ok and status == "OK"
        print(f"{prop:<18} {module_path + '.' + attr:<45} {status}")
    print("-" * 80)
    print("All properties map to an existing component:" , all_ok)
