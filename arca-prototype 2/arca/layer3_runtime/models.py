"""
Shared data model for compliance rules, evaluated by the Transaction
Validation Module and updated only through the governance-authorized
path (see rule_registry.py, layer4_governance/governance.py).

Rules are deliberately data (JSON-serializable dicts), not code, so that
a governance-signed rule update is a signature over *data* — exactly
what the paper requires when it says the Rule Registry Module "enforces
this constraint cryptographically by verifying governance authorization
signatures before accepting any modification to the active rule set."
"""
from __future__ import annotations

import dataclasses
from typing import Any, Dict, List, Optional


@dataclasses.dataclass(frozen=True)
class Rule:
    rule_id: str
    asset_type: str            # e.g. "real_estate", "commodity", "security", "*" for any
    jurisdiction: str          # ISO alpha-2, or "*" for any
    transaction_class: str     # e.g. "transfer", "issuance", "redemption", "*"
    rule_type: str             # see PREDICATES below
    params: Dict[str, Any]
    version: int = 1
    active: bool = True

    def key(self) -> str:
        return f"{self.asset_type}|{self.jurisdiction}|{self.transaction_class}"


@dataclasses.dataclass
class RuleEvaluation:
    rule_id: str
    rule_type: str
    passed: bool
    detail: str


def evaluate_predicate(rule: Rule, evidence: Dict[str, Any]) -> RuleEvaluation:
    """
    evidence is a dict assembled by the Transaction Validation Module from
    verified ZKP attestations and verified CRRs — i.e. only data that has
    already passed cryptographic verification reaches this function.
    Supported evidence keys (populated as available):
      - "amount": float
      - "jurisdiction_membership_proof_valid": bool
      - "jurisdiction_binding_reason": Optional[str]
      - "eligibility_outcome": Optional[bool]
      - "risk_score": Optional[float]
      - "anomaly_flagged": Optional[bool]
      - "anomaly_severity": Optional[str]
    """
    rt = rule.rule_type
    p = rule.params

    if rt == "max_transaction_amount":
        amount = evidence.get("amount")
        if amount is None:
            return RuleEvaluation(rule.rule_id, rt, False, "no transaction amount supplied")
        ok = amount <= p["max_amount"]
        return RuleEvaluation(rule.rule_id, rt, ok, f"amount={amount} vs max={p['max_amount']}")

    if rt == "require_jurisdiction_allowlist_proof":
        ok = bool(evidence.get("jurisdiction_membership_proof_valid", False))
        reason = evidence.get("jurisdiction_binding_reason")
        detail = "ZK jurisdiction-allowlist proof " + ("valid" if ok else "missing/invalid")
        if reason:
            detail += f" ({reason})"
        return RuleEvaluation(rule.rule_id, rt, ok, detail)

    if rt == "require_eligibility_crr":
        outcome = evidence.get("eligibility_outcome")
        ok = outcome is True
        return RuleEvaluation(rule.rule_id, rt, ok, f"eligibility CRR outcome={outcome}")

    if rt == "max_risk_score":
        score = evidence.get("risk_score")
        if score is None:
            return RuleEvaluation(rule.rule_id, rt, False, "no risk-score CRR supplied")
        ok = score <= p["max_score"]
        return RuleEvaluation(rule.rule_id, rt, ok, f"risk_score={score} vs max={p['max_score']}")

    if rt == "block_if_anomaly_flagged":
        flagged = evidence.get("anomaly_flagged")
        if flagged is None:
            # Fail closed: a transaction cannot pass an anomaly screen simply
            # by omitting the anomaly CRR.
            return RuleEvaluation(rule.rule_id, rt, False, "no anomaly CRR supplied")
        ok = not bool(flagged)
        return RuleEvaluation(rule.rule_id, rt, ok, f"anomaly_flagged={bool(flagged)}")

    return RuleEvaluation(rule.rule_id, rt, False, f"unknown rule_type '{rt}'")


PREDICATES: List[str] = [
    "max_transaction_amount",
    "require_jurisdiction_allowlist_proof",
    "require_eligibility_crr",
    "max_risk_score",
    "block_if_anomaly_flagged",
]
