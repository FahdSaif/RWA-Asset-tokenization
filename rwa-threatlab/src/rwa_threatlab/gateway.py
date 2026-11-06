"""Compliance Gateway: the runtime enforcement point (reference monitor)."""
from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass
from typing import TYPE_CHECKING

from .credentials import Proof
from .crypto import digest
from .ledger import Approval, Transfer

if TYPE_CHECKING:  # pragma: no cover
    from .system import Instance


@dataclass(frozen=True)
class Decision:
    accepted: bool
    code: str            # internal reason (kept in the Trail)
    public_code: str     # what the caller sees (uniform if cfg.uniform_errors)
    rule_version: int
    matched: str
    trail_index: int


class ComplianceGateway:
    def __init__(self, inst: "Instance", generation: int = 0):
        self.inst = inst
        self._key = hashlib.sha256(f"gw/{inst.name}/{generation}".encode()).digest()
        self._used: set[int] = set()

    # ---- approval handling -------------------------------------------------
    def _mac(self, tx: Transfer, idx: int) -> str:
        return hmac.new(self._key, f"{tx.digest()}|{idx}".encode(), hashlib.sha256).hexdigest()

    def verify_approval(self, tx: Transfer, approval: Approval | None) -> bool:
        if approval is None or approval.trail_index in self._used:
            return False
        entries = self.inst.trail.entries
        if not (0 <= approval.trail_index < len(entries)):
            return False
        e = entries[approval.trail_index]
        if not (e.accepted and e.tx_ref == tx.digest()):
            return False
        if not hmac.compare_digest(self._mac(tx, approval.trail_index), approval.mac):
            return False
        self._used.add(approval.trail_index)
        return True

    def _commit(self, tx: Transfer, accepted: bool, code: str, matched: str, proof: Proof | None,
                now: int) -> tuple[Decision, Approval | None]:
        inst = self.inst
        rs = inst.store.active
        detail = matched if inst.cfg.log_granularity == "subrule" else self._class_of(tx.asset, rs)
        proof_ref = digest(proof.cred_id) if proof is not None else "-"
        entry = inst.trail.append(now, tx.digest(), accepted, rs.version, proof_ref, f"{code}:{detail}")
        pub = code if (accepted or not inst.cfg.uniform_errors) else "REJECTED"
        dec = Decision(accepted, code, pub, rs.version, matched, entry.index)
        return dec, (Approval(entry.index, self._mac(tx, entry.index)) if accepted else None)

    def _class_of(self, asset: str, rs) -> str:
        r = rs.rule_for(asset)
        return r.class_label if r else "unregulated"

    # ---- evaluation --------------------------------------------------------
    def evaluate(self, tx: Transfer, proof: Proof | None, now: int) -> tuple[Decision, Approval | None]:
        inst, cfg = self.inst, self.inst.cfg
        accepted, code, matched = False, "REJECT", "-"
        try:
            rs = inst.store.active
            rules = []
            local = rs.rule_for(tx.asset)
            if local is not None:
                rules.append(local)
            if cfg.profile_most_restrictive and tx.asset in inst.profiles:
                rules.append(inst.profiles[tx.asset])
            if cfg.defect_origin_spoof and tx.memo.startswith("SYS:"):
                accepted, code = True, "SYSTEM_ORIGIN"                         # A2 defect
            elif tx.dst in inst.infra:
                accepted, code = True, "INFRA"
            elif tx.dst in inst.held:
                code = "HELD_PENDING_CHANGE"                                   # M12
            elif tx.dst in rs.sanctioned:
                code = "SANCTIONED"
            elif not rules:
                accepted, code = True, "UNREGULATED"
            else:
                ids: list[str] = []
                ok = True
                for rule in rules:
                    m, last = None, "NOT_ELIGIBLE"
                    for sub in rule.subrules:
                        res = inst.verifier.verify(proof, sub.requires, tx.dst, now)
                        if res.ok:
                            m = sub.id
                            break
                        last = res.code
                    if m is None:
                        ok, code = False, last
                        break
                    ids.append(m)
                if ok:
                    accepted, code, matched = True, "OK", "+".join(ids)
        except Exception:  # fail closed
            accepted, code, matched = False, "ERROR", "-"
        return self._commit(tx, accepted, code, matched, proof, now)
