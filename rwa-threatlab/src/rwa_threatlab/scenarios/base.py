"""Shared scenario scaffolding: outcomes, reports and a standard simulated world."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from ..bridge import Bridge
from ..config import Config
from ..credentials import Credential, Issuer, Proof, present
from ..crypto import Pki, Signer
from ..rules import Rule, RuleSet, SubRule
from ..system import Clock, Instance

ASSET = "RWA-1"
ACCREDITED = Rule(ASSET, "accredited-investor", (SubRule("acc-AU", (("accredited", "yes"), ("jur", "AU"))),))
KYC_ONLY = Rule(ASSET, "kyc-only", (SubRule("kyc-AU", (("kyc", "pass"), ("jur", "AU"))),))
UNRESTRICTED = Rule(ASSET, "unrestricted", (SubRule("any", ()),))
ALL_CLAIMS = ["accredited", "jur", "kyc"]


@dataclass
class Outcome:
    attack_succeeded: bool
    detail: str
    metrics: dict = field(default_factory=dict)


@dataclass
class Scenario:
    id: str
    node: str
    name: str
    adversary: str
    run: Callable[[str], Outcome]
    variants: tuple[str, ...] = ("baseline", "hardened")
    residual_note: str = ""

    def execute(self) -> dict[str, Outcome]:
        return {v: self.run(v) for v in self.variants}


@dataclass
class World:
    clock: Clock
    pki: Pki
    issuer: Issuer
    signers: dict[str, Signer]
    creds: dict[str, Credential]
    o: Instance
    d: Instance | None = None
    bridge: Bridge | None = None
    truth: frozenset[str] = frozenset()

    def proof(self, name: str, reveal: list[str] | None = None, status_tick: int | None = None,
              issuer: Issuer | None = None) -> Proof:
        iss = issuer or self.issuer
        cred = self.creds[name]
        st = iss.status(self.clock.now if status_tick is None else status_tick)
        return present(cred, [k for k in (reveal or ALL_CLAIMS) if k in cred.claims], st)

    def sign_with(self, inst: Instance, pid: int, who: list[str]) -> None:
        for m in who:
            inst.governance.sign(pid, self.signers[m])


def make_world(cfg: Config, *, sanctioned=("z",), threshold: int = 3, blind_issuer: bool = False,
               dest: bool = False, dest_cfg: Config | None = None, o_rule: Rule = ACCREDITED,
               d_rule: Rule = ACCREDITED, relay_latency: int = 6) -> World:
    pki, clock = Pki(), Clock()
    issuer = Issuer("kyc-gov", pki, blind=blind_issuer)
    members = [f"m{i}" for i in range(1, 6)]
    signers = {m: pki.register(m) for m in members}
    registry = {"kyc-gov": frozenset({"kyc", "accredited", "jur"}), "bank-kyc": frozenset({"kyc"})}
    creds = {
        "u": issuer.issue("u", {"accredited": "yes", "jur": "AU", "kyc": "pass"}, 0),
        "x": issuer.issue("x", {"kyc": "pass", "jur": "AU"}, 0),
        "z": issuer.issue("z", {"accredited": "yes", "jur": "AU", "kyc": "pass"}, 0),
    }
    w = World(clock, pki, issuer, signers, creds, None, truth=frozenset(sanctioned))  # type: ignore[arg-type]

    def build(name: str, c: Config, rule: Rule) -> Instance:
        inst = Instance(name, c, pki, clock, RuleSet(1, (rule,), frozenset(sanctioned)),
                        dict(registry), members, threshold, ["w1", "w2"])
        inst.ledger.credit_genesis(ASSET, "treasury", 1000)
        inst.ledger.credit_genesis(ASSET, "u", 100)
        # honest ground truth: a rules proposal is judged by its delta against the regulator's sanction list
        inst.governance.truth_provider = lambda _w=w: _w.truth
        return inst

    w.o = build("O", cfg, o_rule)
    if dest:
        w.d = build("D", dest_cfg or cfg, d_rule)
        w.d.ledger.credit_genesis(ASSET, "u", 0)
        w.bridge = Bridge(w.o, w.d, relay_latency=relay_latency)
    return w
