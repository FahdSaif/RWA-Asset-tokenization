"""Branch A: submit a transaction outside the validation path."""
from __future__ import annotations

import copy

from ..attacks import MAGIC_MEMO, BackdooredGateway, PermissiveGateway, conformance_failures
from ..config import Config
from ..ledger import Transfer
from ..rules import RuleSet
from ..system import PathClosed, UpgradeRejected
from .base import ASSET, Outcome, make_world

import dataclasses


def _cfg(variant: str) -> Config:
    return Config.baseline() if variant == "baseline" else Config.hardened()


def a1(variant: str) -> Outcome:
    w = make_world(_cfg(variant))
    try:
        w.o.raw_submit(Transfer(ASSET, "u", "mallory", 1, "raw", "user"))
        note = "raw path reached the balance primitive"
    except PathClosed as e:
        note = str(e)
    return Outcome(w.o.ledger.balance(ASSET, "mallory") > 0, note)


def a2(variant: str) -> Outcome:
    w = make_world(_cfg(variant))
    dec = w.o.transfer(ASSET, "u", "mallory", 1, None, memo="SYS:maintenance")
    fails = conformance_failures(copy.deepcopy(w.o))
    return Outcome(w.o.ledger.balance(ASSET, "mallory") > 0, f"gateway decision {dec.code}",
                   {"conformance_failures": len(fails), "found": fails[:2]})


def a3a(variant: str) -> Outcome:
    """P5: quorum-authorised forced transfer to a sanctioned party."""
    cfg = Config.baseline() if variant == "baseline" else Config.hardened()
    w = make_world(cfg)
    if variant == "residual":
        # reduces to governance: relax the sanction (B1) with contestation censored, then force the transfer
        w.o.governance.contest_censored = True
        relaxed = dataclasses.replace(w.o.store.active, sanctioned=frozenset())
        r = w.o.governance.propose("rules", relaxed, proposer="adversary")
        w.sign_with(w.o, r.pid, ["m1", "m2", "m3"])
        w.o.governance.watch()
        w.clock.advance(cfg.challenge_window)
    p = w.o.governance.propose("forced_transfer", [ASSET, "u", "z", 10], proposer="adversary")
    w.sign_with(w.o, p.pid, ["m1", "m2", "m3"])
    dec = w.o.forced_transfer(p.pid, ASSET, "u", "z", 10, w.proof("z"))
    return Outcome(w.o.ledger.balance(ASSET, "z") > 0, f"decision {dec.code if dec else 'unmediated'}")


def a3b(variant: str) -> Outcome:
    """P6: runtime upgrade that alters or removes the Gateway."""
    cfg = Config.baseline() if variant == "baseline" else Config.hardened()
    w = make_world(cfg)
    log: list[str] = []

    def attempt(factory, build: str) -> bool:
        p = w.o.governance.propose("upgrade", build, proposer="adversary")
        w.sign_with(w.o, p.pid, ["m1", "m2", "m3"])
        w.clock.advance(cfg.upgrade_timelock)
        try:
            w.o.upgrade_runtime(p.pid, factory, build)
            log.append(f"{factory.__name__}: installed")
            return True
        except UpgradeRejected as e:
            log.append(f"{factory.__name__}: {e}")
            return False

    if variant == "residual":
        w.o.attested_builds.add("build-evil")   # the quorum attests the malicious build as well
        if attempt(BackdooredGateway, "build-evil"):
            w.o.transfer(ASSET, "u", "mallory", 1, None, memo=MAGIC_MEMO)
    elif variant == "baseline":
        if attempt(PermissiveGateway, "build-evil"):
            w.o.transfer(ASSET, "u", "mallory", 1, None)
    else:
        attempt(PermissiveGateway, "build-evil")                    # unattested build
        w.o.attested_builds.add("build-evil2")
        if attempt(PermissiveGateway, "build-evil2"):               # attested, fails conformance
            w.o.transfer(ASSET, "u", "mallory", 1, None)
    return Outcome(w.o.ledger.balance(ASSET, "mallory") > 0, " | ".join(log))
