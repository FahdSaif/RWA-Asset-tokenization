"""
Layer 4 — Governance Module (paper Sec. V-F, "Governance Module").

Implements the validation gateway between AI-generated rule
recommendations (Layer 1) and the active rule set (Layer 3): "no
AI-generated rule recommendation can become enforceable without
completing the governance validation process." Modelled as a
signature-quorum: a rule change becomes a `GovernanceAuthorization` only
once a governance-defined quorum of registered members has signed the
proposal, at which point the Rule Registry Module (Layer 3) will accept
it. Every proposal, vote, and finalization is written to the shared
audit ledger, giving "full provenance" per the paper's text.
"""
from __future__ import annotations

import dataclasses
import json
import time
import uuid
from typing import Dict, List, Optional, Set, Tuple, Union

from arca.layer2_identity.did_registry import DIDKeyPair, did_to_verify_key
from arca.layer3_runtime.audit_log import HashChainLedger
from arca.layer3_runtime.models import Rule
from cryptography.exceptions import InvalidSignature


def _canonical(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str).encode()


@dataclasses.dataclass
class RuleChangeProposal:
    proposal_id: str
    action: str          # "add" | "modify" | "retire"
    rule: Rule
    proposer_did: str
    created_at: float
    votes: Dict[str, bytes] = dataclasses.field(default_factory=dict)  # voter_did -> signature
    finalized: bool = False

    def payload(self) -> dict:
        return {
            "proposal_id": self.proposal_id,
            "action": self.action,
            "rule": dataclasses.asdict(self.rule),
        }


@dataclasses.dataclass
class GovernanceAuthorization:
    """The artifact the Rule Registry Module actually consumes. Carries
    enough signed material for the registry to independently re-verify
    quorum, rather than trusting the governance module's say-so."""
    proposal_id: str
    action: str
    rule: Rule
    signer_dids: List[str]
    signatures: List[bytes]
    quorum_required: int


ROLE_COMPLIANCE_AGENT = "compliance_agent"
ROLE_CREDENTIAL_ISSUER = "credential_issuer"
VALID_ROLES = (ROLE_COMPLIANCE_AGENT, ROLE_CREDENTIAL_ISSUER)


@dataclasses.dataclass
class RoleChangeProposal:
    """Proposal to register or revoke a Layer-1 compliance agent (with the
    CRR determination types it may issue) or a credential issuer. Uses the
    same quorum-signature machinery as rule changes, so the set of parties
    whose signatures the runtime layer trusts is itself governed."""
    proposal_id: str
    action: str                      # "register" | "revoke"
    role: str                        # one of VALID_ROLES
    subject_did: str
    allowed_types: Tuple[str, ...]   # CRR determination types (compliance_agent only)
    proposer_did: str
    created_at: float
    votes: Dict[str, bytes] = dataclasses.field(default_factory=dict)
    finalized: bool = False

    def payload(self) -> dict:
        return {
            "kind": "role_change",
            "proposal_id": self.proposal_id,
            "action": self.action,
            "role": self.role,
            "subject_did": self.subject_did,
            "allowed_types": sorted(self.allowed_types),
        }


@dataclasses.dataclass
class RoleAuthorization:
    """Artifact the runtime role registry consumes; carries enough signed
    material for the registry to independently re-verify quorum."""
    proposal_id: str
    action: str
    role: str
    subject_did: str
    allowed_types: Tuple[str, ...]
    signer_dids: List[str]
    signatures: List[bytes]
    quorum_required: int


class GovernanceModule:
    def __init__(self, audit_log: HashChainLedger, quorum_threshold: int):
        self.audit_log = audit_log
        self.quorum_threshold = quorum_threshold
        self.members: Set[str] = set()             # governance participant DIDs
        self.authorized_issuers: Set[str] = set()   # credential issuer DIDs
        self.authorized_oracle_providers: Set[str] = set()
        self._proposals: Dict[str, RuleChangeProposal] = {}

    # -- membership / role management -------------------------------------------------
    def add_member(self, did: str) -> None:
        self.members.add(did)
        self.audit_log.append("governance.member_added", {"did": did})

    def authorize_issuer(self, did: str) -> None:
        """Legacy bookkeeping only. Runtime enforcement consults the
        quorum-governed ComplianceRoleRegistry (layer3_runtime), populated
        via propose_role_change / finalize."""
        self.authorized_issuers.add(did)
        self.audit_log.append("governance.issuer_authorized", {"did": did})

    def authorize_oracle_provider(self, did: str) -> None:
        self.authorized_oracle_providers.add(did)
        self.audit_log.append("governance.oracle_provider_authorized", {"did": did})

    # -- rule-change proposal / vote / finalize ----------------------------------------
    def propose_rule_change(self, action: str, rule: Rule, proposer_did: str) -> RuleChangeProposal:
        if proposer_did not in self.members:
            raise PermissionError("proposer is not a registered governance member")
        proposal = RuleChangeProposal(
            proposal_id=str(uuid.uuid4()),
            action=action,
            rule=rule,
            proposer_did=proposer_did,
            created_at=time.time(),
        )
        self._proposals[proposal.proposal_id] = proposal
        self.audit_log.append(
            "governance.proposal_created",
            {"proposal_id": proposal.proposal_id, "action": action, "rule_id": rule.rule_id, "proposer": proposer_did},
        )
        return proposal

    def propose_role_change(
        self, action: str, role: str, subject_did: str, proposer_did: str, allowed_types=()
    ) -> RoleChangeProposal:
        if proposer_did not in self.members:
            raise PermissionError("proposer is not a registered governance member")
        if action not in ("register", "revoke"):
            raise ValueError(f"unknown role action '{action}'")
        if role not in VALID_ROLES:
            raise ValueError(f"unknown role '{role}'")
        if role == ROLE_COMPLIANCE_AGENT and action == "register" and not allowed_types:
            raise ValueError("registering a compliance agent requires at least one allowed determination type")
        proposal = RoleChangeProposal(
            proposal_id=str(uuid.uuid4()),
            action=action,
            role=role,
            subject_did=subject_did,
            allowed_types=tuple(sorted(allowed_types)),
            proposer_did=proposer_did,
            created_at=time.time(),
        )
        self._proposals[proposal.proposal_id] = proposal
        self.audit_log.append(
            "governance.role_proposal_created",
            {"proposal_id": proposal.proposal_id, "action": action, "role": role,
             "subject_did": subject_did, "allowed_types": list(proposal.allowed_types), "proposer": proposer_did},
        )
        return proposal

    def cast_vote(self, proposal_id: str, voter_keypair: DIDKeyPair) -> None:
        if voter_keypair.did not in self.members:
            raise PermissionError("voter is not a registered governance member")
        proposal = self._proposals[proposal_id]
        if proposal.finalized:
            raise RuntimeError("proposal already finalized")
        signature = voter_keypair.sign(_canonical(proposal.payload()))
        proposal.votes[voter_keypair.did] = signature
        self.audit_log.append(
            "governance.vote_cast",
            {"proposal_id": proposal_id, "voter": voter_keypair.did, "vote_count": len(proposal.votes)},
        )

    def finalize(self, proposal_id: str) -> Optional[Union[GovernanceAuthorization, RoleAuthorization]]:
        """Returns a GovernanceAuthorization once quorum is met, else None
        (the proposal remains pending — this is the governance-latency
        window discussed in Sec. VI-B, Threat Class II, and Sec. VIII-C)."""
        proposal = self._proposals[proposal_id]

        valid_votes = {}
        for voter_did, sig in proposal.votes.items():
            try:
                did_to_verify_key(voter_did).verify(sig, _canonical(proposal.payload()))
                valid_votes[voter_did] = sig
            except (InvalidSignature, ValueError):
                continue  # a forged/corrupted vote does not count toward quorum

        if len(valid_votes) < self.quorum_threshold:
            self.audit_log.append(
                "governance.finalize_pending",
                {"proposal_id": proposal_id, "valid_votes": len(valid_votes), "required": self.quorum_threshold},
            )
            return None

        proposal.finalized = True
        if isinstance(proposal, RoleChangeProposal):
            role_auth = RoleAuthorization(
                proposal_id=proposal.proposal_id,
                action=proposal.action,
                role=proposal.role,
                subject_did=proposal.subject_did,
                allowed_types=proposal.allowed_types,
                signer_dids=list(valid_votes.keys()),
                signatures=list(valid_votes.values()),
                quorum_required=self.quorum_threshold,
            )
            self.audit_log.append(
                "governance.finalized",
                {"proposal_id": proposal_id, "action": proposal.action, "role": proposal.role,
                 "subject_did": proposal.subject_did, "signers": role_auth.signer_dids},
            )
            return role_auth

        auth = GovernanceAuthorization(
            proposal_id=proposal.proposal_id,
            action=proposal.action,
            rule=proposal.rule,
            signer_dids=list(valid_votes.keys()),
            signatures=list(valid_votes.values()),
            quorum_required=self.quorum_threshold,
        )
        self.audit_log.append(
            "governance.finalized",
            {"proposal_id": proposal_id, "action": proposal.action, "rule_id": proposal.rule.rule_id, "signers": auth.signer_dids},
        )
        return auth

    def is_pending(self, proposal_id: str) -> bool:
        return not self._proposals[proposal_id].finalized


def verify_role_authorization(auth: RoleAuthorization, registered_members: Set[str]) -> bool:
    """Independent quorum re-verification for role changes (mirrors
    verify_authorization for rule changes)."""
    if len(auth.signer_dids) < auth.quorum_required:
        return False
    payload = _canonical({
        "kind": "role_change",
        "proposal_id": auth.proposal_id,
        "action": auth.action,
        "role": auth.role,
        "subject_did": auth.subject_did,
        "allowed_types": sorted(auth.allowed_types),
    })
    valid = 0
    seen = set()
    for did, sig in zip(auth.signer_dids, auth.signatures):
        if did not in registered_members or did in seen:
            continue
        try:
            did_to_verify_key(did).verify(sig, payload)
            valid += 1
            seen.add(did)
        except (InvalidSignature, ValueError):
            continue
    return valid >= auth.quorum_required


def verify_authorization(auth: GovernanceAuthorization, registered_members: Set[str]) -> bool:
    """Independent re-verification the Rule Registry Module performs on
    a GovernanceAuthorization before applying it — it does not simply
    trust the GovernanceModule object, matching the paper's requirement
    that the registry itself "enforces this constraint cryptographically."""
    if len(auth.signer_dids) < auth.quorum_required:
        return False
    payload = _canonical({
        "proposal_id": auth.proposal_id,
        "action": auth.action,
        "rule": dataclasses.asdict(auth.rule),
    })
    valid = 0
    seen = set()  # a member's signature counts once, however often it is repeated
    for did, sig in zip(auth.signer_dids, auth.signatures):
        if did not in registered_members or did in seen:
            continue
        try:
            did_to_verify_key(did).verify(sig, payload)
            valid += 1
            seen.add(did)
        except (InvalidSignature, ValueError):
            continue
    return valid >= auth.quorum_required
