"""Adversarial / faulty runtime components and the bounded conformance suite used to vet upgrades."""
from __future__ import annotations

from typing import TYPE_CHECKING

from .credentials import Issuer, present
from .gateway import ComplianceGateway
from .ledger import Transfer
from .rules import Rule, RuleSet, SubRule

if TYPE_CHECKING:  # pragma: no cover
    from .system import Instance

MAGIC_MEMO = "MAINT-7f3a"


class PermissiveGateway(ComplianceGateway):
    """A malicious upgrade: accepts everything (A3b, naive)."""
    def evaluate(self, tx, proof, now):
        return self._commit(tx, True, "PERMISSIVE", "-", proof, now)


class BackdooredGateway(ComplianceGateway):
    """Behaves correctly except for one trigger value an input-sampling test is unlikely to hit."""
    def evaluate(self, tx, proof, now):
        if tx.memo == MAGIC_MEMO:
            return self._commit(tx, True, "MAINTENANCE", "-", proof, now)
        return super().evaluate(tx, proof, now)


def conformance_failures(sb: "Instance") -> list[str]:
    """Bounded complete-mediation tests run on a sandbox copy that has the candidate gateway installed.
    This is bounded testing, NOT formal verification: it catches blatant and prefix-style faults only."""
    fails: list[str] = []
    asset = "CONF-ASSET"
    issuer = Issuer("conf-issuer", sb.pki)
    sb.verifier.registry["conf-issuer"] = None
    rule = Rule(asset, "conf", (SubRule("kyc", (("kyc", "pass"),)),))
    sb.store.activate(RuleSet(0, sb.store.active.rules + (rule,), sb.store.active.sanctioned | {"conf-bad"}),
                      sb.clock.now, "conformance")
    sb.ledger.credit_genesis(asset, "conf-src", 1000)
    now = sb.clock.now

    def proof_for(subject: str, claims: dict[str, str]):
        c = issuer.issue(subject, claims, now)
        return present(c, list(claims), issuer.status(now))

    def attempt(dst: str, proof, memo: str = "") -> bool:
        before = sb.ledger.balance(asset, dst)
        try:
            sb.transfer(asset, "conf-src", dst, 1, proof, memo)
        except Exception:
            pass
        return sb.ledger.balance(asset, dst) > before

    n0 = len(sb.trail.entries)
    if attempt("conf-nokyc", None):
        fails.append("accepts transfer with no proof")
    if attempt("conf-wrong", proof_for("conf-wrong", {"kyc": "fail"})):
        fails.append("accepts proof with wrong claim")
    if attempt("conf-bad", proof_for("conf-bad", {"kyc": "pass"})):
        fails.append("accepts sanctioned recipient")
    for memo in ("SYS:maintenance", "SYS:", "SYSTEM", "sys:x"):
        if attempt("conf-spoof-" + memo, None, memo):
            fails.append(f"origin spoofing accepted for memo {memo!r}")
    if not attempt("conf-ok", proof_for("conf-ok", {"kyc": "pass"})):
        fails.append("rejects an eligible recipient")
    if len(sb.trail.entries) <= n0:
        fails.append("decisions are not logged to the Trail")
    return fails
