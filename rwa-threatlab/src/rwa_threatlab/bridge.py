"""Two-phase bridge between two compliance instances, with relay of rule changes."""
from __future__ import annotations

import dataclasses
from dataclasses import dataclass
from typing import Callable

from .credentials import Proof
from .governance import PState, Proposal
from .ledger import Transfer
from .rules import Rule
from .system import Instance


@dataclass
class BridgeResult:
    status: str     # completed | rejected_origin | rejected_destination_refunded | quarantined
    detail: str = ""


class Bridge:
    ESCROW = "bridge:escrow"

    def __init__(self, origin: Instance, dest: Instance, relay_latency: int = 6, notice_delay: int = 1):
        assert origin.clock is dest.clock, "instances must share a clock"
        self.origin, self.dest = origin, dest
        self.relay_latency, self.notice_delay = relay_latency, notice_delay
        self.quarantine: list[tuple[str, str, int]] = []
        self._due: list[tuple[int, Callable[[], None]]] = []
        for inst in (origin, dest):
            inst.infra.add(self.ESCROW)
        origin.governance.listeners.append(self._on_origin_change)
        origin.clock.on_tick(self._tick)

    # ---- asset transfer (lock, evaluate at destination, mint or refund) ----------
    def transfer(self, asset: str, sender: str, recipient: str, amount: int, proof_origin: Proof | None,
                 proof_dest: Proof | None = None, sender_proof: Proof | None = None,
                 declared_profile: Rule | None = None) -> BridgeResult:
        o, d = self.origin, self.dest
        pre = o.gateway.evaluate(Transfer(asset, sender, recipient, amount, "bridge-precheck", "bridge"),
                                 proof_origin, o.clock.now)[0]
        if not pre.accepted:                                    # E3a: origin eligibility
            return BridgeResult("rejected_origin", pre.code)
        o.transfer(asset, sender, self.ESCROW, amount, None)    # phase 1: lock
        if d.cfg.profile_most_restrictive:                      # M13: the asset carries its profile
            prof = declared_profile or o.store.active.rule_for(asset)
            if prof is not None:
                d.profiles[asset] = prof
        dec = d.inbound_mint(asset, recipient, amount, proof_dest or proof_origin, o.name)  # phase 2
        if dec is None or dec.accepted:
            return BridgeResult("completed", "unmediated" if dec is None else dec.code)
        back = o.transfer(asset, self.ESCROW, sender, amount, sender_proof)                 # refund
        if back.accepted:
            return BridgeResult("rejected_destination_refunded", dec.code)
        self.quarantine.append((asset, sender, amount))
        return BridgeResult("quarantined", dec.code)

    # ---- relay of rule changes (E1) -----------------------------------------------
    def _on_origin_change(self, p: Proposal) -> None:
        if p.kind != "rules" or p.state != PState.ACTIVE or p.prior is None:
            return
        affected = frozenset(p.payload.sanctioned - p.prior.sanctioned)
        if not affected:
            return
        now = self.origin.clock.now
        if self.dest.cfg.pending_flag:                          # M12: fast pending-change notice
            self._due.append((now + self.notice_delay, lambda: self.dest.held.update(affected)))
        self._due.append((now + self.relay_latency, lambda: self._apply_to_dest(affected)))

    def _apply_to_dest(self, affected: frozenset[str]) -> None:
        d = self.dest
        rs = d.store.active
        d.store.activate(dataclasses.replace(rs, sanctioned=rs.sanctioned | affected), d.clock.now, "relay")
        d.held.difference_update(affected)

    def _tick(self, now: int) -> None:
        due = [x for x in self._due if x[0] <= now]
        self._due = [x for x in self._due if x[0] > now]
        for _, fn in due:
            fn()
