"""Adversarial stateful fuzzer: random action sequences against a full two-chain deployment.

An *oracle of truth* tracks who is legally eligible at every tick. After every action, any participant
whose balance increased while ineligible is a violation. Each violation is classified as:
  * documented-lag : the ineligibility began no more than L_DOC ticks ago (the paper's stated windows);
  * adversary      : an adversary capability had a recorded effect earlier in the trace;
  * UNEXPLAINED    : neither. These are genuine findings (a hole the paper did not predict).
Counterexample traces are kept so they can be replayed and inspected.
"""
from __future__ import annotations

import dataclasses
import random
from dataclasses import dataclass, field

from .attacks import MAGIC_MEMO, BackdooredGateway, PermissiveGateway
from .config import Config
from .credentials import present
from .governance import PState
from .oracle import OracleAggregator, OracleFeed
from .scenarios.base import ALL_CLAIMS, ASSET, make_world
from .system import UpgradeRejected

NAMES = ["u", "x", "z", "a1", "a2", "k1"]
ACCREDITED = {"u": True, "x": False, "z": True, "a1": True, "a2": True, "k1": False}
L_DOC = 6          # documented windows: freshness bound 3, notice 1, relay latency 6

ADVERSARIES: dict[str, frozenset[str]] = {
    "none": frozenset(),
    "minority": frozenset({"minority"}),
    "quorum": frozenset({"quorum"}),
    "quorum+censor": frozenset({"quorum", "censor"}),
    "issuer": frozenset({"issuer"}),
    "feed": frozenset({"feed"}),
    "feeds2": frozenset({"feed", "feed2"}),
    "feeds2+quorum": frozenset({"feed", "feed2", "quorum"}),
}


@dataclass
class Violation:
    step: int
    tick: int
    chain: str
    name: str
    kind: str                      # documented-lag | adversary | UNEXPLAINED
    caps: tuple[str, ...]
    lag: int | None


@dataclass
class TraceResult:
    seed: int
    violations: list[Violation] = field(default_factory=list)
    actions: list[str] = field(default_factory=list)
    crashed: str | None = None
    installs: list[str] = field(default_factory=list)
    trail_ok: bool = True


class _Run:
    def __init__(self, cfg: Config, adv: frozenset[str], seed: int):
        self.rnd = random.Random(seed)
        self.adv = adv
        self.w = make_world(cfg, dest=True, sanctioned=("z",))
        self.cfg = cfg
        w = self.w
        for n in ("a1", "a2", "k1"):
            claims = {"jur": "AU", "kyc": "pass"}
            if ACCREDITED[n]:
                claims["accredited"] = "yes"
            w.creds[n] = w.issuer.issue(n, claims, 0)
        for inst in (w.o, w.d):
            for n in ("a1", "a2"):
                inst.ledger.credit_genesis(ASSET, n, 20)
        self.sanctioned_since = {"z": -1000}
        self.revoked_since: dict[str, int] = {}
        self.feeds = [OracleFeed(f"feed{i}", w.pki) for i in (1, 2, 3)]
        self.agg = OracleAggregator(w.o)
        self.statuses = [w.issuer.status(0)]
        self.forged: dict[str, object] = {}
        self.caps_effective: set[str] = set()
        self.adv_props: list[tuple[object, int]] = []
        self.backdoor_inst = None
        self.installs: list[str] = []
        self.adv_pids: set[tuple[str, int]] = set()
        for inst in (self.w.o, self.w.d):
            inst.governance.listeners.append(lambda p, _i=inst: self._on_activation(_i, p))
        self.result = TraceResult(seed)

    def _on_activation(self, inst, p) -> None:
        """Harm is judged at the moment an adversary proposal takes effect: did it remove a name that the
        regulator sanctions *at that moment*? (Judging against later truth was an instrument error.)"""
        if (inst.name, p.pid) in self.adv_pids and p.state == PState.ACTIVE \
                and (p.applied_remove & set(self.sanctioned_since)):
            self.caps_effective.add("relax")

    # ---- truth oracle --------------------------------------------------------
    def eligible(self, n: str) -> bool:
        return ACCREDITED[n] and n not in self.sanctioned_since and n not in self.revoked_since

    def inelig_since(self, n: str) -> int | None:
        if self.eligible(n):
            return None
        ts = [-1000] if not ACCREDITED[n] else []
        ts += [t for t in (self.sanctioned_since.get(n), self.revoked_since.get(n)) if t is not None]
        return min(ts)

    def holdings(self) -> dict[tuple[str, str], int]:
        return {(c.name, n): c.ledger.balance(ASSET, n) for c in (self.w.o, self.w.d) for n in NAMES}

    # ---- helpers -------------------------------------------------------------
    def proof_for(self, n: str, kind: str):
        w = self.w
        if kind == "none":
            return None
        if kind == "foreign":
            n2 = self.rnd.choice([m for m in NAMES if m != n])
            return w.proof(n2)
        if kind == "forged" and n in self.forged:
            cred = self.forged[n]
            return present(cred, ALL_CLAIMS, w.issuer.status(w.clock.now))
        if kind == "stale":
            st = self.rnd.choice(self.statuses)
            cred = w.creds[n]
            return present(cred, [k for k in ALL_CLAIMS if k in cred.claims], st)
        return w.proof(n)

    def watch(self) -> None:
        for inst in (self.w.o, self.w.d):
            inst.governance.watch()

    def honest_sign(self, inst, pid):
        for m in ("m1", "m2", "m3"):
            inst.governance.sign(pid, self.w.signers[m])

    # ---- actions ---------------------------------------------------------------
    def a_transfer(self):
        inst = self.rnd.choice([self.w.o, self.w.d])
        holders = [h for h in NAMES + ["treasury"] if inst.ledger.balance(ASSET, h) > 0]
        if not holders:
            return "transfer(skip)"
        src, dst = self.rnd.choice(holders), self.rnd.choice(NAMES)
        kinds = ["fresh", "fresh", "stale", "foreign", "none"] + (["forged"] if self.forged else [])
        kind = self.rnd.choice(kinds)
        if kind == "forged" and dst in self.forged:
            self.caps_effective.add("issuer")
        inst.transfer(ASSET, src, dst, 1, self.proof_for(dst, kind))
        return f"transfer({inst.name}:{src}->{dst},{kind})"

    def a_bridge(self):
        o = self.w.o
        holders = [h for h in NAMES + ["treasury"] if o.ledger.balance(ASSET, h) > 0]
        if not holders:
            return "bridge(skip)"
        src, dst = self.rnd.choice(holders), self.rnd.choice(NAMES)
        kind = self.rnd.choice(["fresh", "fresh", "stale", "none"] + (["forged"] if self.forged else []))
        if kind == "forged" and dst in self.forged:
            self.caps_effective.add("issuer")
        p = self.proof_for(dst, kind)
        self.w.bridge.transfer(ASSET, src, dst, 1, p, p, sender_proof=self.proof_for(src, "fresh") if src in NAMES else None)
        return f"bridge({src}->{dst},{kind})"

    def a_sanction(self):
        cands = [n for n in NAMES if n not in self.sanctioned_since]
        if not cands:
            return "sanction(skip)"
        n = self.rnd.choice(cands)
        t = self.w.clock.now
        self.sanctioned_since[n] = t
        self.w.truth = frozenset(self.sanctioned_since)
        o = self.w.o
        p = o.governance.propose("rules", dataclasses.replace(o.store.active, sanctioned=o.store.active.sanctioned | {n}),
                                 proposer="regulator-liaison")
        self.honest_sign(o, p.pid)
        return f"sanction({n})"

    def a_delist(self):
        cands = [n for n in self.sanctioned_since if n != "z"]
        if not cands:
            return "delist(skip)"
        n = self.rnd.choice(cands)
        del self.sanctioned_since[n]
        self.w.truth = frozenset(self.sanctioned_since)
        o = self.w.o
        p = o.governance.propose("rules", dataclasses.replace(o.store.active, sanctioned=o.store.active.sanctioned - {n}),
                                 proposer="regulator-liaison")
        self.honest_sign(o, p.pid)
        return f"delist({n})"

    def a_revoke(self):
        cands = [n for n in NAMES if n not in self.revoked_since]
        if not cands:
            return "revoke(skip)"
        n = self.rnd.choice(cands)
        self.revoked_since[n] = self.w.clock.now
        self.w.issuer.revoke(self.w.creds[n].cred_id)
        return f"revoke({n})"

    # ---- adversary actions ----------------------------------------------------
    def colluders(self) -> list[str]:
        return ["m1", "m2", "m3"] if "quorum" in self.adv else ["m1", "m2"]

    def a_collude_relax(self):
        inst = self.rnd.choice([self.w.o, self.w.d])
        cands = sorted(inst.store.active.sanctioned)
        if not cands:
            return "collude_relax(skip)"
        n = self.rnd.choice(cands)
        p = inst.governance.propose("rules", dataclasses.replace(inst.store.active, sanctioned=inst.store.active.sanctioned - {n}),
                                    proposer="adversary")
        self.adv_pids.add((inst.name, p.pid))
        for m in self.colluders():
            inst.governance.sign(p.pid, self.w.signers[m])
        self.adv_props.append((inst, p.pid))
        return f"collude_relax({inst.name}:{n})"

    def a_collude_forced(self):
        inst = self.rnd.choice([self.w.o, self.w.d])
        holders = [h for h in NAMES if inst.ledger.balance(ASSET, h) > 0]
        if not holders:
            return "collude_forced(skip)"
        src, dst = self.rnd.choice(holders), self.rnd.choice([n for n in NAMES if not self.eligible(n)] or NAMES)
        p = inst.governance.propose("forced_transfer", [ASSET, src, dst, 1], proposer="adversary")
        for m in self.colluders():
            inst.governance.sign(p.pid, self.w.signers[m])
        try:
            b = inst.ledger.balance(ASSET, dst)
            inst.forced_transfer(p.pid, ASSET, src, dst, 1, self.proof_for(dst, "fresh"))
            if inst.ledger.balance(ASSET, dst) > b:
                self.caps_effective.add("forced")
        except (PermissionError, ValueError):
            pass
        return f"collude_forced({inst.name}:{src}->{dst})"

    def a_collude_upgrade(self):
        inst = self.rnd.choice([self.w.o, self.w.d])
        factory = self.rnd.choice([PermissiveGateway, BackdooredGateway])
        build = f"build-{self.rnd.randint(0, 99)}"
        inst.attested_builds.add(build)                       # a quorum can also attest builds
        p = inst.governance.propose("upgrade", build, proposer="adversary")
        for m in self.colluders():
            inst.governance.sign(p.pid, self.w.signers[m])
        self.w.clock.advance(inst.cfg.upgrade_timelock)
        try:
            inst.upgrade_runtime(p.pid, factory, build)
            self.caps_effective.add("upgrade")
            self.installs.append(factory.__name__)
            if factory is BackdooredGateway:
                self.backdoor_inst = inst
            return f"collude_upgrade({inst.name},{factory.__name__}):installed"
        except (UpgradeRejected, PermissionError):
            return f"collude_upgrade({inst.name},{factory.__name__}):rejected"

    def a_backdoor(self):
        inst = self.backdoor_inst
        holders = [h for h in NAMES if inst.ledger.balance(ASSET, h) > 0]
        if not holders:
            return "backdoor(skip)"
        dst = self.rnd.choice([n for n in NAMES if not self.eligible(n)] or NAMES)
        inst.transfer(ASSET, self.rnd.choice(holders), dst, 1, None, memo=MAGIC_MEMO)
        return f"backdoor({inst.name}->{dst})"

    def a_censor(self):
        for inst in (self.w.o, self.w.d):
            inst.governance.contest_censored = True
        return "censor"

    def a_forge(self):
        cands = [n for n in NAMES if not ACCREDITED[n]]
        n = self.rnd.choice(cands)
        self.forged[n] = self.w.issuer.issue(n, {"accredited": "yes", "jur": "AU", "kyc": "pass"}, self.w.clock.now)
        return f"forge({n})"

    def a_poison(self):
        o = self.w.o
        cands = sorted(o.store.active.sanctioned)
        if not cands:
            return "poison(skip)"
        target = self.rnd.choice(cands)
        t = self.w.clock.now
        truth = set(o.store.active.sanctioned)
        bad = truth - {target}
        n_bad = 2 if "feed2" in self.adv else 1
        listings = [self.feeds[i].publish(bad if i < n_bad else truth, t) for i in range(3)]
        p = self.agg.ingest(listings)
        if p is None:
            return "poison(no-consensus)"
        self.adv_pids.add((o.name, p.pid))
        if p.state == PState.PROPOSED:
            if "quorum" in self.adv:
                for m in self.colluders():
                    o.governance.sign(p.pid, self.w.signers[m])
            else:
                for m in ("m1", "m2", "m3", "m4", "m5"):
                    o.governance.review_and_sign(p.pid, self.w.signers[m])
        self.adv_props.append((o, p.pid))
        return f"poison({target},feeds={n_bad})"

    # ---- driver ------------------------------------------------------------------
    def menu(self) -> list:
        base = [(self.a_transfer, 8), (self.a_bridge, 3), (self.a_sanction, 1), (self.a_delist, 1), (self.a_revoke, 1)]
        if self.adv & {"quorum", "minority"}:
            base += [(self.a_collude_relax, 2), (self.a_collude_forced, 2), (self.a_collude_upgrade, 1)]
        if self.backdoor_inst is not None:
            base += [(self.a_backdoor, 3)]
        if "censor" in self.adv:
            base += [(self.a_censor, 1)]
        if "issuer" in self.adv:
            base += [(self.a_forge, 1)]
        if "feed" in self.adv:
            base += [(self.a_poison, 2)]
        return base

    def step(self, i: int) -> None:
        menu = self.menu()
        fn = self.rnd.choices([m[0] for m in menu], [m[1] for m in menu])[0]
        before = self.holdings()
        try:
            desc = fn()
        except Exception as e:                                   # noqa: BLE001 - a crash is itself a finding
            self.result.crashed = f"{fn.__name__}: {type(e).__name__}: {e}"
            desc = f"{fn.__name__}:CRASH"
        self.result.actions.append(desc)
        self.watch()                                              # watchers monitor continuously,
        for _ in range(self.rnd.randint(1, 3)):                   # i.e. before every tick, not once per step
            self.w.clock.advance(1)
            self.statuses.append(self.w.issuer.status(self.w.clock.now))
            self.watch()
        if "censor" in self.adv and any(i2.governance.contest_censored for i2 in (self.w.o, self.w.d)):
            self.caps_effective.add("censor")
        after = self.holdings()
        for (chain, n), amt in after.items():
            if amt > before[(chain, n)] and not self.eligible(n):
                since = self.inelig_since(n)
                lag = None if since is None else self.w.clock.now - since
                if self.caps_effective:
                    kind = "adversary"
                elif lag is not None and 0 <= lag <= L_DOC:
                    kind = "documented-lag"
                else:
                    kind = "UNEXPLAINED"
                self.result.violations.append(Violation(i, self.w.clock.now, chain, n, kind,
                                                        tuple(sorted(self.caps_effective)), lag))


def run_trace(cfg: Config, adv_name: str, seed: int, steps: int = 40) -> TraceResult:
    r = _Run(cfg, ADVERSARIES[adv_name], seed)
    for i in range(steps):
        r.step(i)
    r.result.installs = list(r.installs)
    r.result.trail_ok = r.w.o.trail.verify()[0] and r.w.d.trail.verify()[0]
    return r.result


def campaign(cfg: Config, adv_name: str, traces: int = 150, steps: int = 40, seed0: int = 0) -> dict:
    kinds = {"documented-lag": 0, "adversary": 0, "UNEXPLAINED": 0}
    with_v = crashes = bad_trails = 0
    cap_sets: dict[tuple[str, ...], int] = {}
    installs: dict[str, int] = {}
    examples: list[dict] = []
    for s in range(seed0, seed0 + traces):
        res = run_trace(cfg, adv_name, s, steps)
        crashes += res.crashed is not None
        for name in res.installs:
            installs[name] = installs.get(name, 0) + 1
        bad_trails += not res.trail_ok
        if res.violations:
            with_v += 1
        for v in res.violations:
            kinds[v.kind] += 1
            if v.kind == "adversary":
                cap_sets[v.caps] = cap_sets.get(v.caps, 0) + 1
            if v.kind == "UNEXPLAINED" and len(examples) < 3:
                examples.append(dict(seed=s, violation=dataclasses.asdict(v), actions=res.actions[: v.step + 1]))
        if res.crashed and len(examples) < 3:
            examples.append(dict(seed=s, crash=res.crashed, actions=res.actions))
    return dict(adversary=adv_name, traces=traces, steps=steps, traces_with_violation=with_v, violations=kinds,
                adversary_cap_sets={"+".join(k): v for k, v in sorted(cap_sets.items())},
                installs=installs, crashes=crashes, trail_integrity_failures=bad_trails, examples=examples)
