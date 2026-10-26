"""
Layer 3 — Compliance Rule Registry Module (paper Sec. V-E, "Compliance
Rule Registry Module").

Holds the currently active compliance rule set, indexed by
(asset_type, jurisdiction, transaction_class). Rule *updates* are
accepted only from a verified `GovernanceAuthorization` (Layer 4) — the
registry independently re-verifies the quorum signatures rather than
trusting the caller, which is what makes rule updates non-bypassable by
a compromised or careless governance client. Every accepted change is
written to the audit ledger with its authorizing decision reference.
"""
from __future__ import annotations

import dataclasses
from typing import Dict, List, Set

from arca.layer3_runtime.audit_log import HashChainLedger
from arca.layer3_runtime.models import Rule
from arca.layer4_governance.governance import GovernanceAuthorization, verify_authorization


class RuleRegistryModule:
    def __init__(self, audit_log: HashChainLedger, registered_governance_members: Set[str]):
        self.audit_log = audit_log
        self.registered_governance_members = registered_governance_members
        self._rules: Dict[str, Rule] = {}
        self._applied_proposals: Set[str] = set()

    def apply_update(self, auth: GovernanceAuthorization) -> bool:
        """Returns True iff the update was applied. A GovernanceAuthorization
        that fails independent signature/quorum re-verification is
        rejected outright and logged as such — it can never reach the
        active rule set."""
        if not verify_authorization(auth, self.registered_governance_members):
            self.audit_log.append(
                "rule_registry.update_rejected",
                {"proposal_id": auth.proposal_id, "reason": "governance authorization failed re-verification"},
            )
            return False

        if auth.proposal_id in self._applied_proposals:
            # Replay of an already-applied authorization (e.g. re-adding a
            # rule that was since retired) must not take effect again.
            self.audit_log.append(
                "rule_registry.update_rejected",
                {"proposal_id": auth.proposal_id, "reason": "authorization already applied (replay)"},
            )
            return False

        rule = auth.rule
        if auth.action == "add":
            self._rules[rule.rule_id] = rule
        elif auth.action == "modify":
            existing = self._rules.get(rule.rule_id)
            new_version = (existing.version + 1) if existing else rule.version
            self._rules[rule.rule_id] = dataclasses.replace(rule, version=new_version)
        elif auth.action == "retire":
            existing = self._rules.get(rule.rule_id)
            if existing:
                self._rules[rule.rule_id] = dataclasses.replace(existing, active=False)
        else:
            self.audit_log.append(
                "rule_registry.update_rejected",
                {"proposal_id": auth.proposal_id, "reason": f"unknown action '{auth.action}'"},
            )
            return False

        self._applied_proposals.add(auth.proposal_id)
        self.audit_log.append(
            "rule_registry.update_applied",
            {
                "proposal_id": auth.proposal_id,
                "action": auth.action,
                "rule_id": rule.rule_id,
                "authorizing_signers": auth.signer_dids,
            },
        )
        return True

    def applicable_rules(self, asset_type: str, jurisdiction: str, transaction_class: str) -> List[Rule]:
        """Rules match on exact value or wildcard '*' in each of the three
        index fields, mirroring the paper's "indexed by asset type,
        jurisdiction, and transaction class" description."""
        out = []
        for rule in self._rules.values():
            if not rule.active:
                continue
            if rule.asset_type not in (asset_type, "*"):
                continue
            if rule.jurisdiction not in (jurisdiction, "*"):
                continue
            if rule.transaction_class not in (transaction_class, "*"):
                continue
            out.append(rule)
        return out

    def get_rule(self, rule_id: str) -> Rule:
        return self._rules[rule_id]

    def all_rules(self) -> List[Rule]:
        return list(self._rules.values())

    def rule_set_version_snapshot(self) -> str:
        """A compact fingerprint of the currently active rule set, recorded
        in each Audit Log entry so a validation outcome can always be
        traced to the exact rules it was evaluated against."""
        import hashlib
        import json

        payload = json.dumps(
            sorted(
                [dataclasses.asdict(r) for r in self._rules.values() if r.active],
                key=lambda d: d["rule_id"],
            ),
            sort_keys=True,
            default=str,
        )
        return hashlib.sha256(payload.encode()).hexdigest()[:16]
