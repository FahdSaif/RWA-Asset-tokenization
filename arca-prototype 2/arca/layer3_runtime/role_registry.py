"""
Layer 3 -- Compliance Role Registry (supports paper Sec. V-E "Transaction
Validation Module" and Sec. V-F "Governance Module").

Records WHICH signing identities the runtime layer will treat as
authoritative:

  * compliance agents -- the Layer-1 agents whose Compliance Recommendation
    Records (CRRs) may be cited as evidence, each limited to the CRR
    determination types it is approved to issue; and
  * credential issuers -- the parties whose signatures on Verifiable
    Credentials are accepted.

Like the Rule Registry Module, this registry accepts changes only from a
quorum-signed authorization produced by the governance module, which it
re-verifies independently (it does not trust the caller). Each
authorization can be applied at most once, so an old "register" cannot be
replayed to undo a later "revoke". Every accepted or rejected change is
written to the audit log.

Before this registry existed, the validator checked only that a CRR's
signature matched the agent_did *claimed inside the record*, so a record
signed by any self-generated key was accepted.
"""
from __future__ import annotations

import dataclasses
from typing import Dict, FrozenSet, Set

from arca.layer3_runtime.audit_log import HashChainLedger
from arca.layer4_governance.governance import (
    ROLE_COMPLIANCE_AGENT,
    ROLE_CREDENTIAL_ISSUER,
    RoleAuthorization,
    verify_role_authorization,
)


@dataclasses.dataclass
class _AgentRecord:
    allowed_types: FrozenSet[str]
    active: bool


class ComplianceRoleRegistry:
    def __init__(self, audit_log: HashChainLedger, registered_governance_members: Set[str]):
        self.audit_log = audit_log
        self.registered_governance_members = registered_governance_members
        self._agents: Dict[str, _AgentRecord] = {}
        self._issuers: Dict[str, bool] = {}
        self._applied_proposals: Set[str] = set()

    def apply(self, auth: RoleAuthorization) -> bool:
        """True iff applied. Fails closed on any verification problem."""
        def reject(reason: str) -> bool:
            self.audit_log.append(
                "role_registry.update_rejected", {"proposal_id": auth.proposal_id, "reason": reason}
            )
            return False

        if not verify_role_authorization(auth, self.registered_governance_members):
            return reject("governance authorization failed re-verification")
        if auth.proposal_id in self._applied_proposals:
            return reject("authorization already applied (replay)")

        if auth.role == ROLE_COMPLIANCE_AGENT:
            if auth.action == "register":
                if not auth.allowed_types:
                    return reject("agent registration without allowed determination types")
                self._agents[auth.subject_did] = _AgentRecord(frozenset(auth.allowed_types), True)
            elif auth.action == "revoke":
                existing = self._agents.get(auth.subject_did)
                if existing is None:
                    return reject("cannot revoke an unregistered agent")
                self._agents[auth.subject_did] = _AgentRecord(existing.allowed_types, False)
            else:
                return reject(f"unknown action '{auth.action}'")
        elif auth.role == ROLE_CREDENTIAL_ISSUER:
            if auth.action == "register":
                self._issuers[auth.subject_did] = True
            elif auth.action == "revoke":
                if auth.subject_did not in self._issuers:
                    return reject("cannot revoke an unregistered issuer")
                self._issuers[auth.subject_did] = False
            else:
                return reject(f"unknown action '{auth.action}'")
        else:
            return reject(f"unknown role '{auth.role}'")

        self._applied_proposals.add(auth.proposal_id)
        self.audit_log.append(
            "role_registry.update_applied",
            {
                "proposal_id": auth.proposal_id,
                "action": auth.action,
                "role": auth.role,
                "subject_did": auth.subject_did,
                "allowed_types": list(auth.allowed_types),
                "authorizing_signers": auth.signer_dids,
            },
        )
        return True

    def is_authorized_agent(self, did: str, determination_type: str) -> bool:
        rec = self._agents.get(did)
        return bool(rec and rec.active and determination_type in rec.allowed_types)

    def is_authorized_issuer(self, did: str) -> bool:
        return self._issuers.get(did, False)
