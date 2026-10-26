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
from arca.layer2_identity.jurisdiction_binding import verify_jurisdiction_binding
from arca.layer2_identity.verifiable_credentials import (
    CredentialRevocationRegistry,
    VerifiableCredential,
)
from arca.layer2_identity.zkp_module import ORMembershipProof
from arca.layer3_runtime.audit_log import HashChainLedger
from arca.layer3_runtime.models import Rule, evaluate_predicate
from arca.layer3_runtime.role_registry import ComplianceRoleRegistry
from arca.layer3_runtime.rule_registry import RuleRegistryModule


# Determination types that are statements about ONE participant. For these the
# CRR must name the transaction's sender as its subject; a CRR about anyone else
# (or naming no one) is ignored. Other types (risk score, jurisdiction analysis)
# are not about a single participant and carry no subject.
SENDER_BOUND_DETERMINATION_TYPES = frozenset({"eligibility", "anomaly"})


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
    jurisdiction_credential: Optional[VerifiableCredential] = None
    crrs: List[ComplianceRecommendationRecord] = dataclasses.field(default_factory=list)


@dataclasses.dataclass
class ValidationResult:
    tx_id: str
    accepted: bool
    rule_set_version: str
    rule_details: List[str]
    rejection_reasons: List[str]
    ignored_crrs: List[str] = dataclasses.field(default_factory=list)


class TransactionValidationModule:
    def __init__(
        self,
        rule_registry: RuleRegistryModule,
        audit_log: HashChainLedger,
        role_registry: ComplianceRoleRegistry,
        revocation_registry: CredentialRevocationRegistry,
    ):
        self.rule_registry = rule_registry
        self.audit_log = audit_log
        self.role_registry = role_registry
        self.revocation_registry = revocation_registry

    def validate(self, tx: Transaction) -> ValidationResult:
        rules = self.rule_registry.applicable_rules(
            tx.asset_type, tx.asset_jurisdiction, tx.transaction_class
        )
        rule_set_version = self.rule_registry.rule_set_version_snapshot()

        # Stage: decide which CRRs may be treated as evidence. A CRR is trusted
        # only if (1) it is bound (context_id) to this exact transaction, (2) its
        # signature verifies, (3) its signer is a governance-registered
        # compliance agent that is currently active and approved to issue this
        # determination type, and (4) for participant-specific determinations,
        # it is about the transaction's sender. Anything else is ignored (and logged), never
        # trusted -- a valid signature from an unknown key proves nothing.
        verified_outcomes: Dict[str, Any] = {}
        crr_ids_cited: List[str] = []
        ignored_crrs: List[str] = []
        conflicting_types: List[str] = []
        for crr in tx.crrs:
            if crr.context_id != tx.tx_id:
                ignored_crrs.append(f"{crr.record_id}: not bound to this transaction")
                continue
            if not verify_crr(crr):
                ignored_crrs.append(f"{crr.record_id}: invalid signature")
                continue
            if not self.role_registry.is_authorized_agent(crr.agent_did, crr.determination_type):
                ignored_crrs.append(
                    f"{crr.record_id}: signer is not an authorized agent for '{crr.determination_type}'"
                )
                continue
            if crr.determination_type in SENDER_BOUND_DETERMINATION_TYPES and crr.subject_did != tx.sender_did:
                ignored_crrs.append(
                    f"{crr.record_id}: '{crr.determination_type}' CRR does not evaluate the transaction sender"
                )
                continue
            if crr.determination_type in verified_outcomes and verified_outcomes[crr.determination_type] != crr.outcome:
                conflicting_types.append(crr.determination_type)
                continue
            verified_outcomes[crr.determination_type] = crr.outcome
            crr_ids_cited.append(crr.record_id)

        rule_details: List[str] = []
        rejection_reasons: List[str] = []

        for ctype in sorted(set(conflicting_types)):
            rejection_reasons.append(f"conflicting authorized CRRs for determination type '{ctype}'")

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
                proof_valid, reason = verify_jurisdiction_binding(
                    tx.jurisdiction_proof,
                    tx.jurisdiction_credential,
                    tx.sender_did,
                    rule.params["allowed_jurisdictions_encoded"],
                    self.revocation_registry,
                    self.role_registry.is_authorized_issuer,
                )
                evidence["jurisdiction_membership_proof_valid"] = proof_valid
                evidence["jurisdiction_binding_reason"] = reason

            elif rule.rule_type == "require_eligibility_crr":
                evidence["eligibility_outcome"] = verified_outcomes.get("eligibility")

            elif rule.rule_type == "max_risk_score":
                evidence["risk_score"] = verified_outcomes.get("risk_score")

            elif rule.rule_type == "block_if_anomaly_flagged":
                evidence["anomaly_flagged"] = verified_outcomes.get("anomaly")

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
                "crrs_ignored": ignored_crrs,
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
            ignored_crrs=ignored_crrs,
        )
