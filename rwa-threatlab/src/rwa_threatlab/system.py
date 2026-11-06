"""A runtime-enforced compliance instance: wires the five modules together and exposes the
state-transition entry points P1-P7 of the paper's mediation surface (Table 1)."""
from __future__ import annotations

import copy
from typing import Callable

from .attacks import conformance_failures
from .config import Config
from .credentials import Proof
from .crypto import Pki, Signer
from .gateway import ComplianceGateway, Decision
from .governance import Governance
from .ledger import Ledger, Transfer
from .rules import ParameterStore, Rule, RuleSet
from .trail import Trail
from .verifier import VerificationModule


class PathClosed(Exception):
    pass


class UpgradeRejected(Exception):
    pass


class Clock:
    def __init__(self) -> None:
        self.now = 0
        self._listeners: list[Callable[[int], None]] = []

    def on_tick(self, f: Callable[[int], None]) -> None:
        self._listeners.append(f)

    def advance(self, n: int = 1) -> None:
        for _ in range(n):
            self.now += 1
            for f in list(self._listeners):
                f(self.now)


class Instance:
    def __init__(self, name: str, cfg: Config, pki: Pki, clock: Clock, ruleset: RuleSet,
                 issuer_registry: dict[str, frozenset[str] | None], members: list[str],
                 threshold: int, watchers: list[str], infra: tuple[str, ...] = ()):
        self.name, self.cfg, self.pki, self.clock = name, cfg, pki, clock
        self.trail = Trail()
        self.store = ParameterStore()
        self.store.activate(ruleset, clock.now, "genesis")
        self.ledger = Ledger()
        self.verifier = VerificationModule(pki, cfg, issuer_registry)
        self.infra: set[str] = set(infra)
        self.profiles: dict[str, Rule] = {}      # asset-bound compliance profiles (M13)
        self.held: set[str] = set()              # subjects with a pending rule change (M12)
        self.attested_builds: set[str] = {"build-A"}
        self.gateway = ComplianceGateway(self)
        self.ledger.set_verifier(self.gateway.verify_approval)
        self.governance = Governance(self, members, threshold, watchers)
        clock.on_tick(self.governance.tick)

    # ---- P1: user transactions ------------------------------------------------
    def transfer(self, asset: str, src: str, dst: str, amount: int, proof: Proof | None = None,
                 memo: str = "") -> Decision:
        tx = Transfer(asset, src, dst, amount, memo)
        dec, appr = self.gateway.evaluate(tx, proof, self.clock.now)
        if dec.accepted:
            self.ledger.apply(tx, appr)
        return dec

    # ---- A1: a raw / node-level path (only exists in a faulty build) ------------
    def raw_submit(self, tx: Transfer) -> None:
        if not self.cfg.legacy_raw_path:
            raise PathClosed("no raw path to the balance primitive")
        self.ledger.raw_move(tx)

    # ---- P2: VM / contract calls and precompiles -------------------------------
    def contract_transfer(self, asset: str, src: str, dst: str, amount: int,
                          proof: Proof | None = None) -> Decision | None:
        if self.cfg.p2_mediated:
            return self.transfer(asset, src, dst, amount, proof, memo="vm-call")
        self.ledger.raw_move(Transfer(asset, src, dst, amount, "vm-call", "vm"))
        return None

    # ---- P3: system operations (rewards, fees, hooks) --------------------------
    def system_reward(self, asset: str, dst: str, amount: int, proof: Proof | None = None) -> Decision | None:
        if self.cfg.p3_mediated:
            return self.transfer(asset, "treasury", dst, amount, proof, memo="reward")
        self.ledger.raw_move(Transfer(asset, "treasury", dst, amount, "reward", "system"))
        return None

    # ---- P4: bridge-inbound mints ------------------------------------------------
    def inbound_mint(self, asset: str, dst: str, amount: int, proof: Proof | None,
                     origin: str) -> Decision | None:
        esc = "bridge:escrow"
        if self.ledger.balance(asset, esc) < amount:
            self.ledger.credit_genesis(asset, esc, amount)
        tx = Transfer(asset, esc, dst, amount, f"inbound:{origin}", "bridge")
        if self.cfg.dest_mediation:
            dec, appr = self.gateway.evaluate(tx, proof, self.clock.now)
            if dec.accepted:
                self.ledger.apply(tx, appr)
            return dec
        self.ledger.raw_move(tx)          # E3: bridge preserves asset state, not eligibility
        return None

    # ---- P5: privileged administrative / recovery operation ---------------------
    def forced_transfer(self, pid: int, asset: str, src: str, dst: str, amount: int,
                        proof: Proof | None = None) -> Decision | None:
        p = self.governance.authorised(pid, "forced_transfer")
        if p.payload != [asset, src, dst, amount]:
            raise PermissionError("payload does not match the authorised proposal")
        self.governance.mark_executed(pid)
        tx = Transfer(asset, src, dst, amount, "RECOVERY", "recovery")
        if self.cfg.priv_via_gateway:     # M3: re-expressed as a Gateway-evaluated transaction
            dec, appr = self.gateway.evaluate(tx, proof, self.clock.now)
            if dec.accepted:
                self.ledger.apply(tx, appr)
            return dec
        self.ledger.raw_move(tx)
        return None

    # ---- P6: runtime upgrade (replaces the Gateway itself) ----------------------
    def upgrade_runtime(self, pid: int, factory: Callable[["Instance"], ComplianceGateway],
                        build_hash: str) -> None:
        p = self.governance.authorised(pid, "upgrade")
        if p.payload != build_hash:
            raise PermissionError("build hash does not match the authorised proposal")
        if self.cfg.guarded_upgrade:      # M3: time-lock, attested build, conformance suite
            if self.clock.now < (p.authorised_at or 0) + self.cfg.upgrade_timelock:
                raise UpgradeRejected("time-lock has not elapsed")
            if build_hash not in self.attested_builds:
                raise UpgradeRejected("build is not attested")
            sb = copy.deepcopy(self)
            sb.gateway = factory(sb)
            sb.ledger.set_verifier(sb.gateway.verify_approval)
            fails = conformance_failures(sb)
            if fails:
                raise UpgradeRejected("conformance failures: " + "; ".join(fails))
        self.governance.mark_executed(pid)
        self.gateway = factory(self)
        self.ledger.set_verifier(self.gateway.verify_approval)

    # ---- P7: state migration / restore -----------------------------------------
    def restore_snapshot(self, pid: int, snapshot: dict) -> None:
        p = self.governance.authorised(pid, "snapshot")
        if p.payload != sorted([list(k) + [v] for k, v in snapshot.items()]):
            raise PermissionError("snapshot does not match the authorised proposal")
        self.governance.mark_executed(pid)
        self.ledger.restore(snapshot)     # governance only: outside the runtime's mediation

    # ---- executable version of Table 1 -----------------------------------------
    def mediation_report(self, asset: str, holder: str, signers: dict[str, Signer],
                         victim: str = "mallory") -> list[dict]:
        """Probe every entry point with an ineligible recipient (no proof) on a sandbox copy and
        report whether the victim ended up holding the asset. P5-P7 are probed with a quorum
        that has authorised the operation (the strongest adversary that can reach them)."""
        out: list[dict] = []

        def authorise(sb: "Instance", kind: str, payload) -> int:
            p = sb.governance.propose(kind, payload, proposer="probe")
            for s in list(signers.values())[: sb.governance.threshold]:
                sb.governance.sign(p.pid, s)
            return p.pid

        def probe(path: str, desc: str, fn: Callable[["Instance"], None]) -> None:
            sb = copy.deepcopy(self)
            sb.ledger.credit_genesis(asset, "treasury", 10)
            before = sb.ledger.balance(asset, victim)
            note = "ok"
            try:
                fn(sb)
            except Exception as e:      # noqa: BLE001 - the exception type is the evidence
                note = type(e).__name__
            out.append({"path": path, "entry point": desc,
                        "mediated": sb.ledger.balance(asset, victim) <= before, "note": note})

        from .attacks import PermissiveGateway

        probe("P1", "user transaction", lambda sb: sb.transfer(asset, holder, victim, 1, None))
        probe("P2", "VM / contract call", lambda sb: sb.contract_transfer(asset, holder, victim, 1, None))
        probe("P3", "system reward hook", lambda sb: sb.system_reward(asset, victim, 1, None))
        probe("P4", "bridge-inbound mint", lambda sb: sb.inbound_mint(asset, victim, 1, None, "other"))
        probe("P5", "forced transfer (quorum-authorised)", lambda sb: sb.forced_transfer(
            authorise(sb, "forced_transfer", [asset, holder, victim, 1]), asset, holder, victim, 1, None))

        def p6(sb: "Instance") -> None:
            pid = authorise(sb, "upgrade", "build-A")
            sb.clock.advance(sb.cfg.upgrade_timelock)
            sb.upgrade_runtime(pid, PermissiveGateway, "build-A")
            sb.transfer(asset, holder, victim, 1, None)
        probe("P6", "runtime upgrade to a permissive gateway", p6)

        def p7(sb: "Instance") -> None:
            snap = sb.ledger.snapshot()
            snap[(asset, victim)] = snap.get((asset, victim), 0) + 1
            pid = authorise(sb, "snapshot", sorted([list(k) + [v] for k, v in snap.items()]))
            sb.restore_snapshot(pid, snap)
        probe("P7", "state restore / migration", p7)
        return out
