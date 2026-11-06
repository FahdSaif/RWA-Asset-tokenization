"""Governance / Quorum Authority: t-of-n approvals, challenge window (M4), asymmetric activation (M5),
privileged-operation authorisation (M3). Quorum approvals are distinct valid signatures; real
deployments would use threshold signatures such as FROST (which also hide *who* approved, see T23)."""
from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, TYPE_CHECKING

from .crypto import Signer, digest
from .rules import RuleSet, classify_change

if TYPE_CHECKING:  # pragma: no cover
    from .system import Instance


class PState(str, Enum):
    PROPOSED = "proposed"
    AUTHORISED = "authorised"
    PENDING = "pending"        # waiting out the challenge window
    ACTIVE = "active"
    REJECTED = "rejected"
    EXPIRED = "expired"        # emergency tightening lapsed without ratification
    EXECUTED = "executed"      # privileged operation consumed


@dataclass
class Proposal:
    pid: int
    kind: str                  # rules | forced_transfer | upgrade | snapshot
    payload: Any
    source: str                # manual | oracle
    created: int
    proposer: str
    approvals: dict[str, str] = field(default_factory=dict)
    state: PState = PState.PROPOSED
    authorised_at: int | None = None
    activates_at: int | None = None
    expires_at: int | None = None
    direction: str = "none"
    contested_by: set[str] = field(default_factory=set)
    ratified: bool = False
    prior: RuleSet | None = None
    base: RuleSet | None = None                      # rule set the proposer started from
    applied_add: frozenset = frozenset()              # sanctions this proposal actually added
    applied_remove: frozenset = frozenset()           # sanctions this proposal actually removed

    def msg(self) -> str:
        return f"proposal|{self.pid}|{self.kind}|{digest(self.payload)}"


class Governance:
    def __init__(self, inst: "Instance", members: list[str], threshold: int, watchers: list[str]):
        self.inst = inst
        self.members = set(members)
        self.threshold = threshold
        self.watchers = list(watchers)
        self.proposals: dict[int, Proposal] = {}
        self._next = 1
        self.contest_censored = False          # adversary capability: suppress contestation (B1b)
        # Honest ground truth. `truth_provider` returns the regulator's current sanction list; a rules proposal is
        # judged by its own *delta*: every name it adds must be truly sanctioned and no name it removes may be.
        self.truth_provider: Callable[[], frozenset[str]] | None = None
        self.independent_check: Callable[[Proposal], bool] = self.consistent
        self.listeners: list[Callable[[Proposal], None]] = []

    # ---- lifecycle ---------------------------------------------------------
    def propose(self, kind: str, payload: Any, source: str = "manual", proposer: str = "n/a") -> Proposal:
        p = Proposal(self._next, kind, payload, source, self.inst.clock.now, proposer)
        if kind == "rules":
            p.base = self.inst.store.active
        self.proposals[p.pid] = p
        self._next += 1
        return p

    def sign(self, pid: int, signer: Signer) -> bool:
        p = self.proposals[pid]
        if p.state != PState.PROPOSED or signer.key_id not in self.members:
            return False
        sig = signer.sign(p.msg())
        if not self.inst.pki.verify(signer.key_id, p.msg(), sig):
            return False
        p.approvals[signer.key_id] = sig
        if len(p.approvals) >= self.threshold:
            self._authorise(p)
        return True

    def consistent(self, p: Proposal) -> bool:
        if p.kind != "rules" or self.truth_provider is None or p.base is None:
            return True
        truth = self.truth_provider()
        add = p.payload.sanctioned - p.base.sanctioned
        rem = p.base.sanctioned - p.payload.sanctioned
        return add <= truth and not (rem & truth)

    def review_and_sign(self, pid: int, signer: Signer) -> bool:
        """An honest member signs only if the proposal matches independent ground truth."""
        if not self.independent_check(self.proposals[pid]):
            return False
        return self.sign(pid, signer)

    def auto_authorise(self, pid: int) -> None:
        """Unreviewed ingestion (B3b): automation approves without human review."""
        p = self.proposals[pid]
        p.approvals["automation"] = "auto"
        self._authorise(p)

    def _authorise(self, p: Proposal) -> None:
        now = self.inst.clock.now
        p.state, p.authorised_at = PState.AUTHORISED, now
        if p.kind != "rules":
            return
        cfg = self.inst.cfg
        p.direction = classify_change(self.inst.store.active, p.payload)
        if p.direction == "tighten" and cfg.asymmetric_activation:
            self._activate(p, expiry=cfg.tighten_expiry or None)
        elif cfg.challenge_window > 0 and p.direction != "none":
            p.state, p.activates_at = PState.PENDING, now + cfg.challenge_window
        else:
            self._activate(p)

    def _rebase(self, p: Proposal) -> RuleSet | None:
        """Apply the proposal as a *delta* on the current rule set. A whole-snapshot overwrite would silently
        undo any change activated since the proposal was written (lost update). Found by the fuzzer."""
        cur, base, new = self.inst.store.active, p.base, p.payload
        if base is None or cur.version == base.version:
            p.applied_add = frozenset(new.sanctioned - cur.sanctioned)
            p.applied_remove = frozenset(cur.sanctioned - new.sanctioned)
            return new
        add, rem = new.sanctioned - base.sanctioned, base.sanctioned - new.sanctioned
        if new.rules != base.rules and cur.rules != base.rules:
            return None                                   # concurrent rule-content change: fail closed
        rules = new.rules if new.rules != base.rules else cur.rules
        p.applied_add = frozenset(add - cur.sanctioned)
        p.applied_remove = frozenset(rem & cur.sanctioned)
        return dataclasses.replace(cur, rules=rules, sanctioned=(cur.sanctioned - rem) | add)

    def _activate(self, p: Proposal, expiry: int | None = None) -> None:
        now = self.inst.clock.now
        merged = self._rebase(p)
        if merged is None:
            p.state = PState.REJECTED
            return
        p.prior = self.inst.store.active
        self.inst.store.activate(merged, now, f"proposal:{p.pid}")
        p.state = PState.ACTIVE
        if expiry:
            p.expires_at = now + expiry
        for f in self.listeners:
            f(p)

    def contest(self, pid: int, watcher: str) -> bool:
        p = self.proposals[pid]
        if self.contest_censored or p.state != PState.PENDING:
            return False
        if p.source == "oracle" and not self.inst.cfg.provenance_independent_contestation:
            return False       # provenance laundering: oracle-sourced updates look authoritative
        p.contested_by.add(watcher)
        p.state = PState.REJECTED
        return True

    def watch(self) -> int:
        """Honest watchers contest pending proposals that fail the independent check."""
        n = 0
        for p in list(self.proposals.values()):
            if p.state == PState.PENDING and not self.independent_check(p):
                for w in self.watchers:
                    if self.contest(p.pid, w):
                        n += 1
                        break
        return n

    def ratify(self, pid: int, signers: list[Signer]) -> bool:
        p = self.proposals[pid]
        good = {s.key_id for s in signers if s.key_id in self.members
                and self.inst.pki.verify(s.key_id, f"ratify|{pid}", s.sign(f"ratify|{pid}"))}
        if len(good) >= self.threshold:
            p.ratified = True
        return p.ratified

    def tick(self, now: int) -> None:
        for p in list(self.proposals.values()):
            if p.state == PState.PENDING and p.activates_at is not None and now >= p.activates_at:
                self._activate(p)
            elif (p.state == PState.ACTIVE and p.expires_at is not None and not p.ratified
                  and now >= p.expires_at):
                if self.independent_check(p):
                    p.ratified = True            # review deadline passed and the change matches ground truth
                    continue
                cur = self.inst.store.active
                truth = self.truth_provider() if self.truth_provider else frozenset()
                bad_add = frozenset(n for n in p.applied_add if n not in truth)      # false sanctions only
                bad_rem = frozenset(n for n in p.applied_remove if n in truth)       # wrongful delistings only
                undone = dataclasses.replace(cur, sanctioned=(cur.sanctioned - bad_add) | bad_rem)
                p.prior = cur
                self.inst.store.activate(undone, now, f"expiry:{p.pid}")
                p.state = PState.EXPIRED
                for f in self.listeners:
                    f(p)

    # ---- privileged operations -------------------------------------------------
    def authorised(self, pid: int, kind: str) -> Proposal:
        p = self.proposals[pid]
        if p.kind != kind or p.state != PState.AUTHORISED:
            raise PermissionError(f"proposal {pid} is not an authorised {kind}")
        return p

    def mark_executed(self, pid: int) -> None:
        self.proposals[pid].state = PState.EXECUTED
