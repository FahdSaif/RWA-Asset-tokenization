import pytest

from arca.layer2_identity.did_registry import generate_did
from arca.layer3_runtime.audit_log import HashChainLedger
from arca.layer3_runtime.models import Rule
from arca.layer3_runtime.rule_registry import RuleRegistryModule
from arca.layer4_governance.governance import GovernanceModule


def _setup(quorum=2, n_members=3):
    audit = HashChainLedger()
    members = [generate_did() for _ in range(n_members)]
    gov = GovernanceModule(audit_log=audit, quorum_threshold=quorum)
    for m in members:
        gov.add_member(m.did)
    registry = RuleRegistryModule(audit_log=audit, registered_governance_members={m.did for m in members})
    return audit, members, gov, registry


def test_proposal_requires_registered_member():
    audit, members, gov, registry = _setup()
    outsider = generate_did()
    rule = Rule("R", "*", "*", "*", "max_transaction_amount", {"max_amount": 100})
    with pytest.raises(PermissionError):
        gov.propose_rule_change("add", rule, outsider.did)


def test_quorum_not_met_returns_none_and_registry_unchanged():
    audit, members, gov, registry = _setup(quorum=2)
    rule = Rule("R", "*", "*", "*", "max_transaction_amount", {"max_amount": 100})
    proposal = gov.propose_rule_change("add", rule, members[0].did)
    gov.cast_vote(proposal.proposal_id, members[0])
    auth = gov.finalize(proposal.proposal_id)
    assert auth is None
    assert registry.applicable_rules("*", "*", "*") == []


def test_quorum_met_applies_rule():
    audit, members, gov, registry = _setup(quorum=2)
    rule = Rule("R", "*", "*", "*", "max_transaction_amount", {"max_amount": 100})
    proposal = gov.propose_rule_change("add", rule, members[0].did)
    gov.cast_vote(proposal.proposal_id, members[0])
    gov.cast_vote(proposal.proposal_id, members[1])
    auth = gov.finalize(proposal.proposal_id)
    assert auth is not None
    assert registry.apply_update(auth) is True
    assert len(registry.applicable_rules("*", "*", "*")) == 1


def test_forged_vote_does_not_count_toward_quorum():
    audit, members, gov, registry = _setup(quorum=2)
    rule = Rule("R", "*", "*", "*", "max_transaction_amount", {"max_amount": 100})
    proposal = gov.propose_rule_change("add", rule, members[0].did)
    gov.cast_vote(proposal.proposal_id, members[0])

    # forge a "vote" from member[1] without their actual private key
    forged_sig = members[0].sign(b"not the real payload")
    proposal.votes[members[1].did] = forged_sig

    auth = gov.finalize(proposal.proposal_id)
    assert auth is None  # only 1 genuinely valid vote


def test_registry_independently_reverifies_authorization():
    """Even if a caller hands the registry a forged GovernanceAuthorization
    object (not obtained via the real GovernanceModule.finalize), the
    registry must reject it because it re-verifies signatures itself."""
    audit, members, gov, registry = _setup(quorum=2)
    from arca.layer4_governance.governance import GovernanceAuthorization

    rule = Rule("R", "*", "*", "*", "max_transaction_amount", {"max_amount": 100})
    fake_auth = GovernanceAuthorization(
        proposal_id="fake",
        action="add",
        rule=rule,
        signer_dids=[members[0].did, members[1].did],
        signatures=[b"not-a-real-signature", b"also-not-real"],
        quorum_required=2,
    )
    assert registry.apply_update(fake_auth) is False
    assert registry.applicable_rules("*", "*", "*") == []


def test_rule_modify_and_retire():
    audit, members, gov, registry = _setup(quorum=2)
    rule = Rule("R", "*", "*", "*", "max_transaction_amount", {"max_amount": 100})

    def propose_and_apply(action, r):
        p = gov.propose_rule_change(action, r, members[0].did)
        gov.cast_vote(p.proposal_id, members[0])
        gov.cast_vote(p.proposal_id, members[1])
        auth = gov.finalize(p.proposal_id)
        return registry.apply_update(auth)

    assert propose_and_apply("add", rule) is True
    assert registry.get_rule("R").params["max_amount"] == 100

    modified = Rule("R", "*", "*", "*", "max_transaction_amount", {"max_amount": 500})
    assert propose_and_apply("modify", modified) is True
    assert registry.get_rule("R").params["max_amount"] == 500
    assert registry.get_rule("R").version == 2

    assert propose_and_apply("retire", rule) is True
    assert registry.applicable_rules("*", "*", "*") == []
    assert registry.get_rule("R").active is False
