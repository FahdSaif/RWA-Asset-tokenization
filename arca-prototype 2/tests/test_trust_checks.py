"""
Trust-check tests added in response to peer review.

Two gaps were closed, and each is exercised here from the attacker's side:

  1. UNAUTHORIZED RECOMMENDATIONS -- a Compliance Recommendation Record is
     now evidence only if its signer is a governance-registered, currently
     active compliance agent approved for that determination type. A valid
     signature from an unknown key no longer counts.

  2. FALSE JURISDICTION CLAIMS -- a jurisdiction zero-knowledge proof is now
     accepted only if it is about the commitment that an authorized issuer
     signed for THIS sender, so a prover cannot choose their own value.

Related hardening covered below: governance quorum cannot be inflated by
repeating one signature, authorizations cannot be replayed, a missing
anomaly CRR no longer counts as "clean", and conflicting authorized CRRs
are rejected rather than resolved arbitrarily.
"""
from __future__ import annotations

import dataclasses

import pytest

from arca.layer1_intelligence.anomaly_detection_agent import (
    BehaviouralAnomalyDetectionAgent,
    TransactionGraph,
)
from arca.layer1_intelligence.crr import issue_crr
from arca.layer2_identity.did_registry import generate_did
from arca.layer2_identity.verifiable_credentials import CredentialIssuer
from arca.layer2_identity.zkp_module import commit, prove_membership
from arca.layer3_runtime.models import Rule
from arca.layer3_runtime.transaction_validator import Transaction
from arca.layer4_governance.governance import (
    ROLE_COMPLIANCE_AGENT,
    ROLE_CREDENTIAL_ISSUER,
    GovernanceAuthorization,
    RoleAuthorization,
    verify_authorization,
)
from arca.pipeline.end_to_end_demo import (
    _finalize_role_change,
    _finalize_rule_proposal,
    build_arca_environment,
)

ALLOWED = [1, 2, 3]       # encoded allow-listed jurisdictions
DISALLOWED_CODE = 99      # a jurisdiction outside the allow-list


def _tx(env, tx_id, *, crrs=(), proof=None, credential=None, sender="alice", receiver="bob", sender_did=None):
    ids = env["identities"]
    return Transaction(
        tx_id=tx_id, sender_did=sender_did or ids[sender].did, receiver_did=ids[receiver].did,
        asset_type="real_estate", asset_jurisdiction="AU", transaction_class="transfer",
        amount=1, jurisdiction_proof=proof, jurisdiction_credential=credential, crrs=list(crrs),
    )


def _add_rules(env, *rule_types):
    for rt in rule_types:
        params = {}
        if rt == "require_jurisdiction_allowlist_proof":
            params = {"allowed_jurisdictions_encoded": ALLOWED}
        elif rt == "max_risk_score":
            params = {"max_score": 0.5}
        assert _finalize_rule_proposal(env, "add", Rule(f"R-{rt}", "*", "*", "*", rt, params)) is True


def _certified(env, subject="alice", code=1):
    bundle = env["issuer"].issue_jurisdiction_credential(env["identities"][subject].did, code)
    return bundle


# ===========================================================================
# 1. Unauthorized recommendations (CRR signer must be an approved agent)
# ===========================================================================
class TestUnauthorizedRecommendations:
    def _crrs(self, signer, tx_id):
        return [
            issue_crr(signer, "eligibility", tx_id, True, ["trust me"], {}),
            issue_crr(signer, "risk_score", tx_id, 0.01, ["trust me"], {}),
            issue_crr(signer, "anomaly", tx_id, False, ["trust me"], {}),
        ]

    def test_crrs_signed_by_unregistered_key_are_rejected(self):
        env = build_arca_environment()
        _add_rules(env, "require_eligibility_crr", "max_risk_score", "block_if_anomaly_flagged")
        mallory = generate_did()  # fresh self-generated key, never registered
        result = env["validator"].validate(_tx(env, "TX-U1", crrs=self._crrs(mallory, "TX-U1")))
        assert result.accepted is False
        assert len(result.ignored_crrs) == 3
        assert all("not an authorized agent" in r for r in result.ignored_crrs)

    def test_registered_identity_without_agent_role_is_rejected(self):
        """`mallory` exists in the DID registry but was never approved as an agent."""
        env = build_arca_environment()
        _add_rules(env, "require_eligibility_crr")
        mallory = env["identities"]["mallory"]
        crr = issue_crr(mallory, "eligibility", "TX-U2", True, ["x"], {})
        assert env["validator"].validate(_tx(env, "TX-U2", crrs=[crr])).accepted is False

    def test_authorized_agent_cannot_issue_outside_its_role(self):
        env = build_arca_environment()
        _add_rules(env, "require_eligibility_crr")
        risk_agent = env["identities"]["risk_agent"]  # approved for "risk_score" only
        crr = issue_crr(risk_agent, "eligibility", "TX-U3", True, ["x"], {})
        result = env["validator"].validate(_tx(env, "TX-U3", crrs=[crr]))
        assert result.accepted is False
        assert "not an authorized agent for 'eligibility'" in result.ignored_crrs[0]

    def test_control_authorized_agents_are_accepted(self):
        env = build_arca_environment()
        _add_rules(env, "require_eligibility_crr", "max_risk_score")
        ids = env["identities"]
        crrs = [
            issue_crr(ids["eligibility_agent"], "eligibility", "TX-U4", True, ["ok"], {}, subject_did=ids["alice"].did),
            issue_crr(ids["risk_agent"], "risk_score", "TX-U4", 0.1, ["ok"], {}),
        ]
        result = env["validator"].validate(_tx(env, "TX-U4", crrs=crrs))
        assert result.accepted is True and result.ignored_crrs == []

    def test_revoked_agent_is_no_longer_trusted(self):
        env = build_arca_environment()
        _add_rules(env, "require_eligibility_crr")
        agent = env["identities"]["eligibility_agent"]
        alice = env["identities"]["alice"].did
        before = issue_crr(agent, "eligibility", "TX-U5a", True, ["ok"], {}, subject_did=alice)
        assert env["validator"].validate(_tx(env, "TX-U5a", crrs=[before])).accepted is True

        assert _finalize_role_change(env, "revoke", ROLE_COMPLIANCE_AGENT, agent.did) is True
        after = issue_crr(agent, "eligibility", "TX-U5b", True, ["ok"], {}, subject_did=alice)
        assert env["validator"].validate(_tx(env, "TX-U5b", crrs=[after])).accepted is False

    def test_agent_registration_requires_governance_quorum(self):
        env = build_arca_environment(quorum_threshold=2)
        gov, ids = env["governance"], env["identities"]
        new_agent = generate_did()
        proposal = gov.propose_role_change(
            "register", ROLE_COMPLIANCE_AGENT, new_agent.did, ids["gov_1"].did, ("eligibility",)
        )
        gov.cast_vote(proposal.proposal_id, ids["gov_1"])      # 1 of 2 required votes
        assert gov.finalize(proposal.proposal_id) is None       # not enough -> no authorization
        assert env["role_registry"].is_authorized_agent(new_agent.did, "eligibility") is False

    def test_forged_role_authorization_with_repeated_signature_is_rejected(self):
        """One governance member repeating their own signature must not reach quorum."""
        env = build_arca_environment(quorum_threshold=2)
        gov, ids = env["governance"], env["identities"]
        new_agent = generate_did()
        proposal = gov.propose_role_change(
            "register", ROLE_COMPLIANCE_AGENT, new_agent.did, ids["gov_1"].did, ("eligibility",)
        )
        gov.cast_vote(proposal.proposal_id, ids["gov_1"])
        sig = proposal.votes[ids["gov_1"].did]
        forged = RoleAuthorization(
            proposal_id=proposal.proposal_id, action="register", role=ROLE_COMPLIANCE_AGENT,
            subject_did=new_agent.did, allowed_types=("eligibility",),
            signer_dids=[ids["gov_1"].did, ids["gov_1"].did], signatures=[sig, sig], quorum_required=2,
        )
        assert env["role_registry"].apply(forged) is False
        assert env["role_registry"].is_authorized_agent(new_agent.did, "eligibility") is False

    def test_forged_rule_authorization_with_repeated_signature_is_rejected(self):
        env = build_arca_environment(quorum_threshold=2)
        gov, ids = env["governance"], env["identities"]
        rule = Rule("R-forge", "*", "*", "*", "max_transaction_amount", {"max_amount": 10**12})
        proposal = gov.propose_rule_change("add", rule, ids["gov_1"].did)
        gov.cast_vote(proposal.proposal_id, ids["gov_1"])
        sig = proposal.votes[ids["gov_1"].did]
        forged = GovernanceAuthorization(
            proposal_id=proposal.proposal_id, action="add", rule=rule,
            signer_dids=[ids["gov_1"].did] * 2, signatures=[sig, sig], quorum_required=2,
        )
        members = {ids[k].did for k in ("gov_1", "gov_2", "gov_3")}
        assert verify_authorization(forged, members) is False
        assert env["rule_registry"].apply_update(forged) is False

    def test_replayed_register_cannot_undo_a_revocation(self):
        env = build_arca_environment()
        gov, ids, reg = env["governance"], env["identities"], env["role_registry"]
        agent = generate_did()
        p = gov.propose_role_change("register", ROLE_COMPLIANCE_AGENT, agent.did, ids["gov_1"].did, ("risk_score",))
        for k in ("gov_1", "gov_2"):
            gov.cast_vote(p.proposal_id, ids[k])
        register_auth = gov.finalize(p.proposal_id)
        assert reg.apply(register_auth) is True
        assert _finalize_role_change(env, "revoke", ROLE_COMPLIANCE_AGENT, agent.did) is True
        assert reg.is_authorized_agent(agent.did, "risk_score") is False

        assert reg.apply(register_auth) is False                       # replay refused
        assert reg.is_authorized_agent(agent.did, "risk_score") is False

    def test_replayed_rule_authorization_cannot_resurrect_a_retired_rule(self):
        env = build_arca_environment()
        gov, ids, reg = env["governance"], env["identities"], env["rule_registry"]
        rule = Rule("R-replay", "*", "*", "*", "max_transaction_amount", {"max_amount": 5})
        p = gov.propose_rule_change("add", rule, ids["gov_1"].did)
        for k in ("gov_1", "gov_2"):
            gov.cast_vote(p.proposal_id, ids[k])
        add_auth = gov.finalize(p.proposal_id)
        assert reg.apply_update(add_auth) is True
        assert _finalize_rule_proposal(env, "retire", rule) is True
        assert reg.apply_update(add_auth) is False                     # replay refused
        assert reg.applicable_rules("real_estate", "AU", "transfer") == []

    def test_conflicting_authorized_crrs_are_rejected(self):
        env = build_arca_environment()
        _add_rules(env, "require_eligibility_crr")
        agent = env["identities"]["eligibility_agent"]
        crrs = [
            issue_crr(agent, "eligibility", "TX-U6", True, ["a"], {}, subject_did=env["identities"]["alice"].did),
            issue_crr(agent, "eligibility", "TX-U6", False, ["b"], {}, subject_did=env["identities"]["alice"].did),
        ]
        result = env["validator"].validate(_tx(env, "TX-U6", crrs=crrs))
        assert result.accepted is False
        assert any("conflicting authorized CRRs" in r for r in result.rejection_reasons)

    def test_every_rejection_is_recorded_in_the_audit_log(self):
        env = build_arca_environment()
        _add_rules(env, "require_eligibility_crr")
        mallory = generate_did()
        env["validator"].validate(_tx(env, "TX-U7", crrs=[issue_crr(mallory, "eligibility", "TX-U7", True, ["x"], {})]))
        entry = [e for e in env["audit_log"]._entries if e.payload.get("tx_id") == "TX-U7"][-1]
        assert entry.payload["accepted"] is False
        assert entry.payload["crrs_ignored"]
        assert env["audit_log"].verify_integrity() is True


# ===========================================================================
# 2. False jurisdiction claims (proof must be about an issuer-certified value)
# ===========================================================================
class TestFalseJurisdictionClaims:
    def test_self_chosen_commitment_without_credential_is_rejected(self):
        env = build_arca_environment()
        _add_rules(env, "require_jurisdiction_allowlist_proof")
        c, r = commit(1)  # prover simply commits to an allowed value
        proof = prove_membership(1, r, c, ALLOWED)
        result = env["validator"].validate(_tx(env, "TX-J1", proof=proof))
        assert result.accepted is False
        assert "no issuer-certified jurisdiction credential" in " ".join(result.rejection_reasons)

    def test_lying_about_a_disallowed_jurisdiction_is_rejected(self):
        """Attacker's certified jurisdiction is outside the allow-list. They
        mint a fresh commitment to an allowed value and attach their real
        credential. The proof is valid in isolation but not about what the
        issuer certified."""
        env = build_arca_environment()
        _add_rules(env, "require_jurisdiction_allowlist_proof")
        honest = _certified(env, code=DISALLOWED_CODE)
        c, r = commit(1)
        fake_proof = prove_membership(1, r, c, ALLOWED)
        result = env["validator"].validate(_tx(env, "TX-J2", proof=fake_proof, credential=honest.credential))
        assert result.accepted is False
        assert "not about the issuer-certified" in " ".join(result.rejection_reasons)

    def test_holder_cannot_prove_a_disallowed_certified_jurisdiction(self):
        env = build_arca_environment()
        bundle = _certified(env, code=DISALLOWED_CODE)
        with pytest.raises(ValueError):
            bundle.prove_in(ALLOWED)

    def test_credential_from_unauthorized_issuer_is_rejected(self):
        env = build_arca_environment()
        _add_rules(env, "require_jurisdiction_allowlist_proof")
        rogue = CredentialIssuer(env["identities"]["mallory"])  # signs well, but is not an approved issuer
        bundle = rogue.issue_jurisdiction_credential(env["identities"]["alice"].did, 1)
        result = env["validator"].validate(
            _tx(env, "TX-J3", proof=bundle.prove_in(ALLOWED), credential=bundle.credential)
        )
        assert result.accepted is False
        assert "not an authorized issuer" in " ".join(result.rejection_reasons)

    def test_revoked_jurisdiction_credential_is_rejected(self):
        env = build_arca_environment()
        _add_rules(env, "require_jurisdiction_allowlist_proof")
        bundle = _certified(env)
        env["revocation_registry"].revoke(bundle.credential.id)
        result = env["validator"].validate(
            _tx(env, "TX-J4", proof=bundle.prove_in(ALLOWED), credential=bundle.credential)
        )
        assert result.accepted is False
        assert "invalid, expired or revoked" in " ".join(result.rejection_reasons)

    def test_credential_issued_to_someone_else_is_rejected(self):
        env = build_arca_environment()
        _add_rules(env, "require_jurisdiction_allowlist_proof")
        bobs = _certified(env, subject="bob")          # Bob's valid credential...
        result = env["validator"].validate(            # ...presented by Alice
            _tx(env, "TX-J5", sender="alice", proof=bobs.prove_in(ALLOWED), credential=bobs.credential)
        )
        assert result.accepted is False
        assert "not issued to the transaction sender" in " ".join(result.rejection_reasons)

    def test_tampered_credential_commitment_is_rejected(self):
        env = build_arca_environment()
        _add_rules(env, "require_jurisdiction_allowlist_proof")
        bundle = _certified(env, code=DISALLOWED_CODE)
        c, r = commit(1)
        forged_claims = dict(bundle.credential.claims, jurisdictionCommitment=__import__(
            "arca.layer2_identity.zkp_module", fromlist=["point_to_hex"]).point_to_hex(c.point))
        forged_vc = dataclasses.replace(bundle.credential, claims=forged_claims)  # issuer signature now stale
        result = env["validator"].validate(
            _tx(env, "TX-J6", proof=prove_membership(1, r, c, ALLOWED), credential=forged_vc)
        )
        assert result.accepted is False
        assert "invalid, expired or revoked" in " ".join(result.rejection_reasons)

    def test_control_honest_holder_is_accepted(self):
        env = build_arca_environment()
        _add_rules(env, "require_jurisdiction_allowlist_proof")
        bundle = _certified(env, code=2)
        result = env["validator"].validate(
            _tx(env, "TX-J7", proof=bundle.prove_in(ALLOWED), credential=bundle.credential)
        )
        assert result.accepted is True

    # -- the Eligibility agent applies the same binding, so its CRR cannot
    # -- vouch for an unbound proof or an unapproved accreditation issuer
    def test_eligibility_agent_refuses_unbound_proof(self):
        env = build_arca_environment()
        ids = env["identities"]
        c, r = commit(1)
        proof = prove_membership(1, r, c, ALLOWED)
        crr = env["eligibility_agent"].evaluate(
            "TX-J8", proof, ALLOWED, None, require_accreditation=False,
            sender_did=ids["alice"].did, jurisdiction_credential=None,
        )
        assert crr.outcome is False

    def test_eligibility_agent_refuses_accreditation_from_unapproved_issuer(self):
        env = build_arca_environment()
        ids = env["identities"]
        bundle = _certified(env)
        rogue_vc = CredentialIssuer(ids["mallory"]).issue(
            ids["alice"].did, "AccreditedInvestorCredential", {"accredited": True}
        )
        crr = env["eligibility_agent"].evaluate(
            "TX-J9", bundle.prove_in(ALLOWED), ALLOWED, rogue_vc, require_accreditation=True,
            sender_did=ids["alice"].did, jurisdiction_credential=bundle.credential,
        )
        assert crr.outcome is False

    def test_eligibility_agent_refuses_accreditation_issued_to_someone_else(self):
        env = build_arca_environment()
        ids = env["identities"]
        bundle = _certified(env)
        bobs_vc = env["issuer"].issue(ids["bob"].did, "AccreditedInvestorCredential", {"accredited": True})
        crr = env["eligibility_agent"].evaluate(
            "TX-J10", bundle.prove_in(ALLOWED), ALLOWED, bobs_vc, require_accreditation=True,
            sender_did=ids["alice"].did, jurisdiction_credential=bundle.credential,
        )
        assert crr.outcome is False

    def test_eligibility_agent_control_accepts_fully_certified_sender(self):
        env = build_arca_environment()
        ids = env["identities"]
        bundle = _certified(env)
        vc = env["issuer"].issue(ids["alice"].did, "AccreditedInvestorCredential", {"accredited": True})
        crr = env["eligibility_agent"].evaluate(
            "TX-J11", bundle.prove_in(ALLOWED), ALLOWED, vc, require_accreditation=True,
            sender_did=ids["alice"].did, jurisdiction_credential=bundle.credential,
        )
        assert crr.outcome is True


# ===========================================================================
# 3. Anomaly screening actually blocks (previously a dead rule)
# ===========================================================================
def _layering_graph():
    parties = [generate_did() for _ in range(15)]
    g = TransactionGraph()
    for i in range(10):
        g.add_transaction(parties[i % 15].did, parties[(i + 1) % 15].did, amount=500 + i * 10, timestamp=i)
    hub = parties[0].did
    for j in range(2, 12):
        g.add_transaction(hub, parties[j].did, amount=2000, timestamp=100 + j)
    g.add_transaction(parties[3].did, parties[4].did, amount=1900, timestamp=150)
    g.add_transaction(parties[4].did, hub, amount=1850, timestamp=160)
    return parties, g


class TestAnomalyScreening:
    def test_flagged_participant_blocks_the_transaction_end_to_end(self):
        env = build_arca_environment()
        _add_rules(env, "block_if_anomaly_flagged")
        parties, graph = _layering_graph()
        agent = env["anomaly_agent"]
        agent.fit(graph)
        crr = agent.evaluate("TX-A1", parties[0].did, graph)   # the layering hub
        assert crr.outcome is True
        result = env["validator"].validate(_tx(env, "TX-A1", crrs=[crr], sender_did=parties[0].did))
        assert result.accepted is False
        assert "anomaly_flagged=True" in " ".join(result.rejection_reasons)

    def test_clean_participant_is_accepted(self):
        env = build_arca_environment()
        _add_rules(env, "block_if_anomaly_flagged")
        parties, graph = _layering_graph()
        agent = env["anomaly_agent"]
        agent.fit(graph)
        crr = agent.evaluate("TX-A2", parties[7].did, graph)
        assert crr.outcome is False
        assert env["validator"].validate(_tx(env, "TX-A2", crrs=[crr], sender_did=parties[7].did)).accepted is True

    def test_omitting_the_anomaly_crr_cannot_pass_the_screen(self):
        env = build_arca_environment()
        _add_rules(env, "block_if_anomaly_flagged")
        result = env["validator"].validate(_tx(env, "TX-A3", crrs=[]))
        assert result.accepted is False
        assert "no anomaly CRR supplied" in " ".join(result.rejection_reasons)

    def test_anomaly_crr_signed_by_unregistered_key_is_ignored(self):
        env = build_arca_environment()
        _add_rules(env, "block_if_anomaly_flagged")
        forged_clean = issue_crr(generate_did(), "anomaly", "TX-A4", False, ["x"], {})
        assert env["validator"].validate(_tx(env, "TX-A4", crrs=[forged_clean])).accepted is False


# ===========================================================================
# 4. A CRR must be about the participant it is used for (subject binding)
# ===========================================================================
class TestCRRSubjectBinding:
    def test_eligibility_crr_for_another_participant_is_ignored(self):
        """Bob is eligible; Alice tries to use Bob's eligibility CRR on her own transaction."""
        env = build_arca_environment()
        _add_rules(env, "require_eligibility_crr")
        ids = env["identities"]
        crr = issue_crr(ids["eligibility_agent"], "eligibility", "TX-S1", True, ["bob is fine"], {},
                        subject_did=ids["bob"].did)
        result = env["validator"].validate(_tx(env, "TX-S1", crrs=[crr], sender="alice"))
        assert result.accepted is False
        assert "does not evaluate the transaction sender" in result.ignored_crrs[0]

    def test_clean_anomaly_crr_of_another_participant_cannot_clear_a_flagged_sender(self):
        """The layering hub borrows a clean anomaly CRR issued for an ordinary participant."""
        env = build_arca_environment()
        _add_rules(env, "block_if_anomaly_flagged")
        parties, graph = _layering_graph()
        agent = env["anomaly_agent"]
        agent.fit(graph)
        borrowed = agent.evaluate("TX-S2", parties[7].did, graph)       # clean, about someone else
        assert borrowed.outcome is False
        result = env["validator"].validate(_tx(env, "TX-S2", crrs=[borrowed], sender_did=parties[0].did))
        assert result.accepted is False                                 # hub is the sender
        assert "no anomaly CRR supplied" in " ".join(result.rejection_reasons)

    def test_crr_naming_no_subject_is_ignored_for_participant_specific_types(self):
        env = build_arca_environment()
        _add_rules(env, "require_eligibility_crr")
        crr = issue_crr(env["identities"]["eligibility_agent"], "eligibility", "TX-S3", True, ["x"], {})
        assert env["validator"].validate(_tx(env, "TX-S3", crrs=[crr])).accepted is False

    def test_subject_cannot_be_rewritten_after_issuance(self):
        env = build_arca_environment()
        ids = env["identities"]
        crr = issue_crr(ids["eligibility_agent"], "eligibility", "TX-S4", True, ["x"], {}, subject_did=ids["bob"].did)
        crr.subject_did = ids["alice"].did          # attacker retargets Bob's CRR at Alice
        from arca.layer1_intelligence.crr import verify_crr
        assert verify_crr(crr) is False

    def test_control_matching_subject_is_accepted(self):
        env = build_arca_environment()
        _add_rules(env, "require_eligibility_crr")
        ids = env["identities"]
        crr = issue_crr(ids["eligibility_agent"], "eligibility", "TX-S5", True, ["ok"], {}, subject_did=ids["alice"].did)
        assert env["validator"].validate(_tx(env, "TX-S5", crrs=[crr], sender="alice")).accepted is True

    def test_risk_score_crr_is_not_subject_bound(self):
        """Risk score describes the transaction, not one participant, so it carries no subject."""
        env = build_arca_environment()
        _add_rules(env, "max_risk_score")
        crr = issue_crr(env["identities"]["risk_agent"], "risk_score", "TX-S6", 0.1, ["ok"], {})
        assert env["validator"].validate(_tx(env, "TX-S6", crrs=[crr])).accepted is True
