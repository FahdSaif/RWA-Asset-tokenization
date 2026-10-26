"""
Cross-Layer Data Flow demo (paper Sec. V-G, "Cross-Layer Data Flow and
Compliance Lifecycle").

Wires all four ARCA layers together for one full transaction lifecycle,
exactly as narrated in the paper:

  1. The Compliance Intelligence Layer (Layer 1) processes oracle data
     (Layer 4) to maintain up-to-date rule recommendations.
  2. Rule updates that complete governance validation (Layer 4) are
     activated in the Rule Registry Module (Layer 3).
  3. At submission time, the participant generates a ZKP (Layer 2) and
     submits it with the transaction.
  4. The Transaction Validation Module (Layer 3) verifies the ZKP,
     retrieves rules and CRRs, and produces an enforcement decision.
  5. The outcome is written to the Audit Log Module (Layer 3).

Run: python -m arca.pipeline.end_to_end_demo
"""
from __future__ import annotations

from arca.layer1_intelligence.anomaly_detection_agent import (
    BehaviouralAnomalyDetectionAgent,
    TransactionGraph,
)
from arca.layer1_intelligence.eligibility_agent import InvestorEligibilityEvaluationAgent
from arca.layer1_intelligence.jurisdiction_agent import (
    JurisdictionalRegulatoryAnalysisAgent,
    _encode_iso2,
)
from arca.layer1_intelligence.risk_scoring_agent import TransactionRiskScoringAgent
from arca.layer2_identity.did_registry import DIDRegistry, generate_did
from arca.layer2_identity.verifiable_credentials import (
    CredentialIssuer,
    CredentialRevocationRegistry,
)
from arca.layer3_runtime.audit_log import HashChainLedger
from arca.layer3_runtime.models import Rule
from arca.layer3_runtime.role_registry import ComplianceRoleRegistry
from arca.layer3_runtime.rule_registry import RuleRegistryModule
from arca.layer3_runtime.transaction_validator import Transaction, TransactionValidationModule
from arca.layer4_governance.asset_registry import AssetRegistry
from arca.layer4_governance.governance import (
    ROLE_COMPLIANCE_AGENT,
    ROLE_CREDENTIAL_ISSUER,
    GovernanceModule,
)


def build_arca_environment(quorum_threshold: int = 2):
    """Stands up one shared instance of every layer, with a set of
    identities and initial authorizations — the fixture the demo (and
    the pytest integration tests) both build on."""
    audit_log = HashChainLedger()
    did_registry = DIDRegistry()

    identities = {
        "gov_1": generate_did(), "gov_2": generate_did(), "gov_3": generate_did(),
        "oracle_1": generate_did(), "oracle_2": generate_did(), "oracle_3": generate_did(),
        "issuer": generate_did(),
        "jurisdiction_agent": generate_did(),
        "eligibility_agent": generate_did(),
        "risk_agent": generate_did(),
        "anomaly_agent": generate_did(),
        "alice": generate_did(),   # sender / investor
        "bob": generate_did(),     # receiver / investor
        "mallory": generate_did(), # will remain unauthorized in threat-model tests
    }
    for kp in identities.values():
        did_registry.register(kp)

    gov = GovernanceModule(audit_log=audit_log, quorum_threshold=quorum_threshold)
    for key in ("gov_1", "gov_2", "gov_3"):
        gov.add_member(identities[key].did)
    for key in ("oracle_1", "oracle_2", "oracle_3"):
        gov.authorize_oracle_provider(identities[key].did)

    governance_member_dids = {identities[k].did for k in ("gov_1", "gov_2", "gov_3")}
    rule_registry = RuleRegistryModule(audit_log=audit_log, registered_governance_members=governance_member_dids)
    role_registry = ComplianceRoleRegistry(audit_log=audit_log, registered_governance_members=governance_member_dids)
    revocation_registry = CredentialRevocationRegistry()
    validator = TransactionValidationModule(
        rule_registry=rule_registry, audit_log=audit_log,
        role_registry=role_registry, revocation_registry=revocation_registry,
    )
    asset_registry = AssetRegistry(audit_log=audit_log)

    issuer = CredentialIssuer(identities["issuer"])

    jurisdiction_agent = JurisdictionalRegulatoryAnalysisAgent(identities["jurisdiction_agent"])
    eligibility_agent = InvestorEligibilityEvaluationAgent(identities["eligibility_agent"], revocation_registry, role_registry)
    risk_agent = TransactionRiskScoringAgent(identities["risk_agent"])
    anomaly_agent = BehaviouralAnomalyDetectionAgent(identities["anomaly_agent"])

    env = {
        "audit_log": audit_log,
        "did_registry": did_registry,
        "identities": identities,
        "governance": gov,
        "rule_registry": rule_registry,
        "validator": validator,
        "asset_registry": asset_registry,
        "revocation_registry": revocation_registry,
        "issuer": issuer,
        "jurisdiction_agent": jurisdiction_agent,
        "eligibility_agent": eligibility_agent,
        "risk_agent": risk_agent,
        "anomaly_agent": anomaly_agent,
        "role_registry": role_registry,
    }

    # Which identities the runtime layer will trust is itself decided by
    # governance quorum -- nothing is trusted by default. `mallory` is
    # deliberately never registered.
    for key, types in (
        ("jurisdiction_agent", ("jurisdiction_risk", "rule_update")),
        ("eligibility_agent", ("eligibility",)),
        ("risk_agent", ("risk_score",)),
        ("anomaly_agent", ("anomaly",)),
    ):
        _finalize_role_change(env, "register", ROLE_COMPLIANCE_AGENT, identities[key].did, types)
    _finalize_role_change(env, "register", ROLE_CREDENTIAL_ISSUER, identities["issuer"].did)
    return env


def _finalize_role_change(env: dict, action: str, role: str, subject_did: str, allowed_types=()) -> bool:
    """Helper: proposes a role change, collects full governance consensus,
    and applies it to the role registry (happy path; tests exercise
    partial-quorum and forged-authorization scenarios separately)."""
    gov = env["governance"]
    proposer = env["identities"]["gov_1"]
    proposal = gov.propose_role_change(action, role, subject_did, proposer.did, allowed_types)
    for key in ("gov_1", "gov_2", "gov_3"):
        gov.cast_vote(proposal.proposal_id, env["identities"][key])
    auth = gov.finalize(proposal.proposal_id)
    return env["role_registry"].apply(auth)


def _finalize_rule_proposal(env: dict, action: str, rule: Rule) -> bool:
    """Helper: proposes a rule change and has all 3 governance members vote
    (full consensus) — used for the demo's happy path. Tests exercise
    partial-quorum scenarios separately (Threat Class II)."""
    gov = env["governance"]
    proposer = env["identities"]["gov_1"]
    proposal = gov.propose_rule_change(action, rule, proposer.did)
    for key in ("gov_1", "gov_2", "gov_3"):
        gov.cast_vote(proposal.proposal_id, env["identities"][key])
    auth = gov.finalize(proposal.proposal_id)
    return env["rule_registry"].apply_update(auth)


def run_demo(verbose: bool = True) -> dict:
    env = build_arca_environment()
    ids = env["identities"]

    def log(*args):
        if verbose:
            print(*args)

    log("=" * 78)
    log("STEP 1 — Layer 4: Regulatory Oracle Network -> Layer 1: Jurisdiction Agent")
    log("=" * 78)
    ja = env["jurisdiction_agent"]
    tier_au = ja.classify("AU")
    tier_sy = ja.classify("SY")
    log(f"Jurisdiction risk classification — AU: {tier_au}, SY (FATF grey list): {tier_sy}")

    log()
    log("=" * 78)
    log("STEP 2 — Layer 1 proposes rule updates -> Layer 4 governance validates -> Layer 3 activates")
    log("=" * 78)
    amount_rule = ja.propose_rule_update("AU", asset_type="real_estate", transaction_class="transfer")
    applied = _finalize_rule_proposal(env, "add", amount_rule)
    log(f"Rule '{amount_rule.rule_id}' (max_amount={amount_rule.params['max_amount']}) applied: {applied}")

    allowed_jurisdictions = ja.allowed_jurisdiction_set(exclude_tiers=["prohibited"])
    allowed_encoded = [_encode_iso2(c) for c in allowed_jurisdictions]
    jurisdiction_rule = Rule(
        rule_id="jurisdiction-allowlist-real_estate-transfer",
        asset_type="real_estate", jurisdiction="*", transaction_class="transfer",
        rule_type="require_jurisdiction_allowlist_proof",
        params={"allowed_jurisdictions_encoded": allowed_encoded},
    )
    applied2 = _finalize_rule_proposal(env, "add", jurisdiction_rule)
    log(f"Rule '{jurisdiction_rule.rule_id}' applied: {applied2} ({len(allowed_encoded)} allowed jurisdictions)")

    eligibility_rule = Rule(
        rule_id="require-eligibility-real_estate-transfer",
        asset_type="real_estate", jurisdiction="*", transaction_class="transfer",
        rule_type="require_eligibility_crr", params={},
    )
    risk_rule = Rule(
        rule_id="max-risk-score-real_estate-transfer",
        asset_type="real_estate", jurisdiction="*", transaction_class="transfer",
        rule_type="max_risk_score", params={"max_score": 0.6},
    )
    anomaly_rule = Rule(
        rule_id="block-anomaly-real_estate-transfer",
        asset_type="real_estate", jurisdiction="*", transaction_class="transfer",
        rule_type="block_if_anomaly_flagged", params={},
    )
    _finalize_rule_proposal(env, "add", eligibility_rule)
    _finalize_rule_proposal(env, "add", risk_rule)
    _finalize_rule_proposal(env, "add", anomaly_rule)
    log(f"Rules '{eligibility_rule.rule_id}', '{risk_rule.rule_id}' and '{anomaly_rule.rule_id}' also applied.")

    log()
    log("=" * 78)
    log("STEP 3 — Layer 4: Asset Registry")
    log("=" * 78)
    asset = env["asset_registry"].register_asset(
        "ASSET-AU-001", "real_estate", "AU", "unclassified", ids["alice"].did
    )
    log(f"Registered asset {asset.asset_id} ({asset.asset_type}, jurisdiction={asset.issuing_jurisdiction})")

    log()
    log("=" * 78)
    log("STEP 4 — Layer 2: participant obtains a credential and generates a ZK proof")
    log("=" * 78)
    accreditation_vc = env["issuer"].issue(
        subject_did=ids["alice"].did,
        credential_type="AccreditedInvestorCredential",
        claims={"accredited": True, "jurisdictionOfResidence": "AU"},
    )
    log(f"Issued VC {accreditation_vc.id} to Alice, signed by issuer {accreditation_vc.issuer_did[:24]}...")

    jurisdiction_bundle = env["issuer"].issue_jurisdiction_credential(ids["alice"].did, _encode_iso2("AU"))
    jurisdiction_proof = jurisdiction_bundle.prove_in(allowed_encoded)
    log("Generated ZK proof that the issuer-certified jurisdiction is in the allowed set, without revealing which one.")

    log()
    log("=" * 78)
    log("STEP 5 — Layer 1: AI agents evaluate the transaction, each issuing a signed CRR")
    log("=" * 78)
    tx_id = "TX-DEMO-001"

    eligibility_crr = env["eligibility_agent"].evaluate(
        tx_id, jurisdiction_proof, allowed_encoded, accreditation_vc, require_accreditation=True,
        sender_did=ids["alice"].did, jurisdiction_credential=jurisdiction_bundle.credential,
    )
    log(f"Eligibility CRR: outcome={eligibility_crr.outcome}")
    for line in eligibility_crr.reasoning_trace:
        log("   -", line)

    tx_features = {
        "amount": 250_000.0, "jurisdiction_tier": 0, "tx_velocity_24h": 1,
        "unique_counterparties_7d": 2, "account_age_days": 800, "cross_border": 0,
        "is_new_counterparty": 0, "hour_of_day": 11, "structuring_proximity": 0.0, "is_round_number": 0.0,
    }
    risk_crr = env["risk_agent"].score(tx_id, tx_features)
    log(f"Risk-scoring CRR: outcome={risk_crr.outcome:.3f}")
    for line in risk_crr.reasoning_trace:
        log("   -", line)

    graph = TransactionGraph()
    graph.add_transaction(ids["bob"].did, ids["alice"].did, amount=100_000, timestamp=0)
    graph.add_transaction(ids["alice"].did, ids["bob"].did, amount=50_000, timestamp=1)
    env["anomaly_agent"].fit(graph)
    anomaly_crr = env["anomaly_agent"].evaluate(tx_id, ids["alice"].did, graph)
    log(f"Anomaly-detection CRR: outcome (flagged)={anomaly_crr.outcome}")
    for line in anomaly_crr.reasoning_trace:
        log("   -", line)

    log()
    log("=" * 78)
    log("STEP 6 — Layer 3: Transaction Validation Module — final enforcement decision")
    log("=" * 78)
    tx = Transaction(
        tx_id=tx_id,
        sender_did=ids["alice"].did,
        receiver_did=ids["bob"].did,
        asset_type="real_estate",
        asset_jurisdiction="AU",
        transaction_class="transfer",
        amount=tx_features["amount"],
        jurisdiction_proof=jurisdiction_proof,
        jurisdiction_credential=jurisdiction_bundle.credential,
        crrs=[eligibility_crr, risk_crr, anomaly_crr],
    )
    result = env["validator"].validate(tx)
    log(f"Transaction {tx.tx_id} ACCEPTED: {result.accepted}")
    for line in result.rule_details:
        log("   -", line)
    if result.rejection_reasons:
        for reason in result.rejection_reasons:
            log("   REJECTED because:", reason)

    log()
    log("=" * 78)
    log("STEP 7 — Layer 3: Audit Log integrity check")
    log("=" * 78)
    log(f"Audit log length: {len(env['audit_log'])} entries")
    log(f"Audit log integrity intact: {env['audit_log'].verify_integrity()}")

    return {"env": env, "result": result, "tx": tx}


if __name__ == "__main__":
    run_demo(verbose=True)
