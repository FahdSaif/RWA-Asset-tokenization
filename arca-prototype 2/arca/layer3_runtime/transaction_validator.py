"""
Layer 3 — Transaction Validation Module (paper Sec. V-E, "Transaction
Validation Module").

Multi-stage validation sequence, matching the paper's description
exactly: retrieve applicable rules -> verify ZKP attestations -> verify
referenced CRRs -> evaluate the combined determination against the
active rule set -> accept/reject with a structured reason. This is the
component the paper calls non-bypassable: it is the *only* path by which
a transaction involving a tokenized RWA can be finalized, and it is
invoked directly here rather than through any application-layer
wrapper — which is exactly what lets `tests/test_threat_model.py`
demonstrate Threat Class I (a "raw" transaction submitted with no
attestations at all is still intercepted and rejected).
"""
from __future__ import annotations

import dataclasses
import time
from typing import Any, Dict, List, Optional

from arca.layer1_intelligence.crr import ComplianceRecommendationRecord, verify_crr
from arca.layer2_identity.zkp_module import ORMembershipProof, verify_membership
from arca.layer3_runtime.audit_log import HashChainLedger
from arca.layer3_runtime.models import Rule, evaluate_predicate
from arca.layer3_runtime.rule_registry import RuleRegistryModule


@dataclasses.dataclass
class Transaction:
    tx_id: str
    sender_did: str
    receiver_did: str
    asset_type: str
    asset_jurisdiction: str
    transaction_class: str
    amount: float
    jurisdiction_proof: Optional[ORMembershipProof] = None
    crrs: List[ComplianceRecommendationRecord] = dataclasses.field(default_factory=list)


@dataclasses.dataclass
class ValidationResult:
    tx_id: str
    accepted: bool
    rule_set_version: str
    rule_details: List[str]
    rejection_reasons: List[str]


class TransactionValidationModule:
    def __init__(self, rule_registry: RuleRegistryModule, audit_log: HashChainLedger):
        self.rule_registry = rule_registry
        self.audit_log = audit_log

    def validate(self, tx: Transaction) -> ValidationResult:
        rules = self.rule_registry.applicable_rules(
            tx.asset_type, tx.asset_jurisdiction, tx.transaction_class
        )
        rule_set_version = self.rule_registry.rule_set_version_snapshot()

        # Stage: verify every CRR's signature up front. Only CRRs that pass
        # signature verification AND are bound (context_id) to this exact
        # transaction are trusted as evidence — anything else is dropped
        # silently rather than trusted, which is what stops a stale or
        # forged CRR from a different transaction being replayed here.
        verified_outcomes: Dict[str, Any] = {}
        crr_ids_cited: List[str] = []
        for crr in tx.crrs:
            if crr.context_id != tx.tx_id:
                continue
            if not verify_crr(crr):
                continue
            verified_outcomes[crr.determination_type] = crr.outcome
            crr_ids_cited.append(crr.record_id)

        rule_details: List[str] = []
        rejection_reasons: List[str] = []

        if not rules:
            rejection_reasons.append(
                "no applicable compliance rules found for "
                f"(asset_type={tx.asset_type}, jurisdiction={tx.asset_jurisdiction}, class={tx.transaction_class})"
            )

        for rule in rules:
            evidence: Dict[str, Any] = {}

            if rule.rule_type == "max_transaction_amount":
                evidence["amount"] = tx.amount

            elif rule.rule_type == "require_jurisdiction_allowlist_proof":
                proof_valid = False
                if tx.jurisdiction_proof is not None:
                    try:
                        proof_valid = verify_membership(
                            tx.jurisdiction_proof, rule.params["allowed_jurisdictions_encoded"]
                        )
                    except Exception:
                        proof_valid = False
                evidence["jurisdiction_membership_proof_valid"] = proof_valid

            elif rule.rule_type == "require_eligibility_crr":
                evidence["eligibility_outcome"] = verified_outcomes.get("eligibility")

            elif rule.rule_type == "max_risk_score":
                evidence["risk_score"] = verified_outcomes.get("risk_score")

            elif rule.rule_type == "block_if_anomaly_flagged":
                evidence["anomaly_flagged"] = verified_outcomes.get("anomaly_flagged")

            result = evaluate_predicate(rule, evidence)
            rule_details.append(f"[{rule.rule_id}:{rule.rule_type}] {result.detail} -> {'PASS' if result.passed else 'FAIL'}")
            if not result.passed:
                rejection_reasons.append(f"rule '{rule.rule_id}' ({rule.rule_type}) failed: {result.detail}")

        accepted = len(rejection_reasons) == 0

        self.audit_log.append(
            "transaction.validated",
            {
                "tx_id": tx.tx_id,
                "sender_did": tx.sender_did,
                "receiver_did": tx.receiver_did,
                "asset_type": tx.asset_type,
                "asset_jurisdiction": tx.asset_jurisdiction,
                "transaction_class": tx.transaction_class,
                "amount": tx.amount,
                "rule_set_version": rule_set_version,
                "crr_ids_cited": crr_ids_cited,
                "accepted": accepted,
                "rejection_reasons": rejection_reasons,
                "validated_at": time.time(),
            },
        )

        return ValidationResult(
            tx_id=tx.tx_id,
            accepted=accepted,
            rule_set_version=rule_set_version,
            rule_details=rule_details,
            rejection_reasons=rejection_reasons,
        )
