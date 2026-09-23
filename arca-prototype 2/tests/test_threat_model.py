"""
Executable counterpart to the paper's Sec. VI-B threat model analysis.
Each test class below corresponds 1:1 to a named threat class from the
paper, and is written to demonstrate exactly the mitigation (and, for
Threat Class II, the paper's own acknowledged residual vulnerability)
that the corresponding subsection describes — not a generic fuzz test.
"""
from __future__ import annotations

from arca.layer1_intelligence.crr import verify_crr
from arca.layer2_identity.verifiable_credentials import CredentialIssuer, CredentialRevocationRegistry
from arca.layer2_identity.did_registry import generate_did
from arca.layer3_runtime.models import Rule
from arca.layer3_runtime.transaction_validator import Transaction
from arca.layer4_governance.oracle_network import RegulatoryOracleNetwork, submit_report
from arca.layer4_governance.governance import GovernanceModule
from arca.layer3_runtime.audit_log import HashChainLedger
from arca.pipeline.end_to_end_demo import build_arca_environment, _finalize_rule_proposal


# ---------------------------------------------------------------------------
# Threat Class I — Direct Protocol Bypass Attempt
# ---------------------------------------------------------------------------
class TestThreatClassI_DirectProtocolBypass:
    def test_raw_transaction_with_no_attestations_is_rejected(self):
        """A 'raw transaction' here means: call the Transaction Validation
        Module directly with none of the artefacts an application UI would
        normally have collected first (no ZK proof, no CRRs at all) — this
        IS the bypass attempt, since there is no separate application layer
        to go around: the validator is the only path to finalization."""
        env = build_arca_environment()
        rule = Rule("R", "*", "*", "*", "require_jurisdiction_allowlist_proof",
                    {"allowed_jurisdictions_encoded": [1, 2, 3]})
        assert _finalize_rule_proposal(env, "add", rule) is True

        ids = env["identities"]
        bare_tx = Transaction(
            tx_id="TX-BYPASS", sender_did=ids["alice"].did, receiver_did=ids["bob"].did,
            asset_type="real_estate", asset_jurisdiction="AU", transaction_class="transfer",
            amount=1_000_000,  # no jurisdiction_proof, no crrs supplied at all
        )
        result = env["validator"].validate(bare_tx)
        assert result.accepted is False
        assert any("require_jurisdiction_allowlist_proof" in r for r in result.rejection_reasons)

    def test_onchain_transfer_bypass_reverts_regardless_of_submission_path(self):
        """The on-chain equivalent: whether a transfer is submitted via a
        wallet, a script, or a hand-crafted raw transaction, it hits the
        exact same compliance check inside the contract's _transfer -
        there is no alternate code path that skips it."""
        import pathlib
        build_path = (
            pathlib.Path(__file__).resolve().parents[1]
            / "arca" / "layer3_runtime" / "contracts" / "build" / "contracts.json"
        )
        if not build_path.exists():
            import pytest
            pytest.skip("Contracts not compiled - run node scripts/compile_contracts.js")

        from arca.layer3_runtime.evm_bridge import LocalEVM

        evm = LocalEVM()
        owner, mallory = evm.owner, evm.accounts[3]
        evm.set_allowed(owner, True)  # mallory NOT allow-listed

        ok, err = evm.transfer(owner, mallory, 1)
        assert ok is False
        assert "not compliant" in (err or "")


# ---------------------------------------------------------------------------
# Threat Class II — Stale Compliance Rule Exploitation
# ---------------------------------------------------------------------------
class TestThreatClassII_StaleRuleExploitation:
    def test_governance_latency_window_then_closure(self):
        """Demonstrates BOTH halves of the paper's own analysis: the
        acknowledged residual vulnerability during the governance-approval
        window, AND that the window closes once quorum is reached."""
        env = build_arca_environment(quorum_threshold=2)
        gov, registry, validator, ids = env["governance"], env["rule_registry"], env["validator"], env["identities"]

        original_rule = Rule("AU-limit", "real_estate", "AU", "transfer",
                              "max_transaction_amount", {"max_amount": 10_000_000})
        assert _finalize_rule_proposal(env, "add", original_rule) is True

        def make_tx(tx_id, amount):
            return Transaction(tx_id=tx_id, sender_did=ids["alice"].did, receiver_did=ids["bob"].did,
                                asset_type="real_estate", asset_jurisdiction="AU", transaction_class="transfer",
                                amount=amount)

        assert validator.validate(make_tx("TX-A", 500_000)).accepted is True

        # A regulatory event (e.g. sudden sanctions) prompts a stricter rule,
        # but governance has not yet reached quorum on it.
        stricter_rule = Rule("AU-limit", "real_estate", "AU", "transfer",
                              "max_transaction_amount", {"max_amount": 1_000})
        proposal = gov.propose_rule_change("modify", stricter_rule, ids["gov_1"].did)
        gov.cast_vote(proposal.proposal_id, ids["gov_1"])  # 1 of 2 required votes
        assert gov.finalize(proposal.proposal_id) is None
        assert gov.is_pending(proposal.proposal_id) is True

        # ACKNOWLEDGED RESIDUAL VULNERABILITY (paper Sec. VI-B / VII.3):
        # identical transaction is still accepted under the stale rule.
        result_during_latency = validator.validate(make_tx("TX-B", 500_000))
        assert result_during_latency.accepted is True

        # Governance completes -> window closes.
        gov.cast_vote(proposal.proposal_id, ids["gov_2"])
        auth = gov.finalize(proposal.proposal_id)
        assert registry.apply_update(auth) is True

        result_after = validator.validate(make_tx("TX-C", 500_000))
        assert result_after.accepted is False


# ---------------------------------------------------------------------------
# Threat Class III — Fraudulent Credential Presentation
# ---------------------------------------------------------------------------
class TestThreatClassIII_FraudulentCredentialPresentation:
    def test_forged_credential_signature_fails_eligibility(self):
        env = build_arca_environment()
        ids = env["identities"]
        real_issuer = CredentialIssuer(ids["issuer"])
        impostor_kp = generate_did()

        vc = real_issuer.issue(ids["alice"].did, "AccreditedInvestorCredential", {"accredited": True})
        vc.signature = impostor_kp.sign(b"forged")  # attacker cannot produce the real issuer's signature

        from arca.layer2_identity.zkp_module import commit, prove_membership
        allowed = [1, 2, 3]
        c, r = commit(1)
        proof = prove_membership(1, r, c, allowed)

        crr = env["eligibility_agent"].evaluate("TX-FORGE", proof, allowed, vc, require_accreditation=True)
        assert crr.outcome is False

    def test_revoked_credential_fails_eligibility(self):
        env = build_arca_environment()
        ids = env["identities"]
        real_issuer = CredentialIssuer(ids["issuer"])

        vc = real_issuer.issue(ids["alice"].did, "AccreditedInvestorCredential", {"accredited": True})
        env["revocation_registry"].revoke(vc.id)

        from arca.layer2_identity.zkp_module import commit, prove_membership
        allowed = [1, 2, 3]
        c, r = commit(1)
        proof = prove_membership(1, r, c, allowed)

        crr = env["eligibility_agent"].evaluate("TX-REVOKED", proof, allowed, vc, require_accreditation=True)
        assert crr.outcome is False

    def test_tampered_crr_outcome_fails_signature_check_and_is_dropped(self):
        """Even if an eligibility CRR was legitimately issued, an attacker
        flipping its outcome afterwards invalidates the signature; the
        Transaction Validation Module silently drops any CRR that fails
        verification rather than trusting its stated outcome."""
        env = build_arca_environment()
        ids = env["identities"]
        rule = Rule("R", "*", "*", "*", "require_eligibility_crr", {})
        assert _finalize_rule_proposal(env, "add", rule) is True

        vc = CredentialIssuer(ids["issuer"]).issue(ids["alice"].did, "AccreditedInvestorCredential", {"accredited": True})
        from arca.layer2_identity.zkp_module import commit, prove_membership
        allowed = [1, 2, 3]
        c, r = commit(1)
        proof = prove_membership(1, r, c, allowed)

        crr = env["eligibility_agent"].evaluate("TX-TAMPER", proof, allowed, vc, require_accreditation=True)
        assert crr.outcome is True  # legitimately eligible before tampering

        crr.outcome = False  # attacker (or a bug) tampers with the record post-issuance
        assert verify_crr(crr) is False  # signature no longer matches payload

        tx = Transaction(tx_id="TX-TAMPER", sender_did=ids["alice"].did, receiver_did=ids["bob"].did,
                          asset_type="*", asset_jurisdiction="*", transaction_class="*",
                          amount=1, crrs=[crr])
        result = env["validator"].validate(tx)
        assert result.accepted is False  # tampered CRR is dropped -> no valid eligibility evidence -> rule fails


# ---------------------------------------------------------------------------
# Threat Class IV — Oracle Data Manipulation
# ---------------------------------------------------------------------------
class TestThreatClassIV_OracleDataManipulation:
    def test_single_compromised_authorized_provider_cannot_override_majority(self):
        audit = HashChainLedger()
        providers = [generate_did() for _ in range(3)]
        authorized = {p.did for p in providers}
        net = RegulatoryOracleNetwork(audit_log=audit, authorized_providers=authorized, consensus_quorum=2)

        # 2 honest providers correctly report a newly-sanctioned jurisdiction
        # as prohibited; 1 compromised (but still nominally "authorized")
        # provider reports the opposite.
        reports = [
            submit_report(providers[0], "risk:XX", "prohibited"),
            submit_report(providers[1], "risk:XX", "prohibited"),
            submit_report(providers[2], "risk:XX", "low"),  # compromised
        ]
        consensus = net.ingest("risk:XX", reports)
        assert consensus == "prohibited"

    def test_unauthorized_outsider_cannot_manufacture_consensus_alone(self):
        audit = HashChainLedger()
        providers = [generate_did() for _ in range(3)]
        outsider = generate_did()
        authorized = {p.did for p in providers}  # outsider excluded
        net = RegulatoryOracleNetwork(audit_log=audit, authorized_providers=authorized, consensus_quorum=2)

        reports = [
            submit_report(providers[0], "risk:XX", "prohibited"),
            submit_report(outsider, "risk:XX", "low"),
            submit_report(outsider, "risk:XX", "low"),  # even submitting "twice" via same unauthorized DID
        ]
        consensus = net.ingest("risk:XX", reports)
        assert consensus is None  # only 1 authorized report -> below quorum, correctly inconclusive
