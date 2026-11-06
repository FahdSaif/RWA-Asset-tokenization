"""Branch B: corrupt the active rule set (quorum collusion, latency window, oracle poisoning)."""
from __future__ import annotations

import dataclasses

from ..config import Config
from ..oracle import OracleAggregator, OracleFeed
from ..governance import PState
from .base import ASSET, Outcome, make_world


def b1(variant: str) -> Outcome:
    """B1a AND B1b: colluding quorum relaxes the sanction list; contestation must also be defeated."""
    cfg = Config.baseline() if variant == "baseline" else Config.hardened()
    w = make_world(cfg)
    if variant == "residual":
        w.o.governance.contest_censored = True        # B1b: suppress honest contestation
    relaxed = dataclasses.replace(w.o.store.active, sanctioned=frozenset())
    p = w.o.governance.propose("rules", relaxed, proposer="adversary")
    w.sign_with(w.o, p.pid, ["m1", "m2", "m3"])       # B1a: threshold-sufficient coalition
    contested = w.o.governance.watch()
    w.clock.advance(cfg.challenge_window)
    dec = w.o.transfer(ASSET, "u", "z", 10, w.proof("z"))
    return Outcome(w.o.ledger.balance(ASSET, "z") > 0,
                   f"proposal {p.state.value}, contested={contested}, transfer {dec.public_code}")


def b2(variant: str) -> Outcome:
    """Latency window between a legitimate sanction designation and activation."""
    if variant == "baseline":       # a challenge window that delays tightenings too (symmetric)
        cfg = Config.hardened().replace(asymmetric_activation=False)
    else:
        cfg = Config.hardened()
    w = make_world(cfg, sanctioned=())
    if variant == "residual":
        # availability attack enabled by immediate tightening: a colluding quorum freezes honest holder u
        frozen = dataclasses.replace(w.o.store.active, sanctioned=frozenset({"u"}))
        p = w.o.governance.propose("rules", frozen, proposer="adversary")
        w.sign_with(w.o, p.pid, ["m1", "m2", "m3"])
        dec = w.o.transfer(ASSET, "treasury", "u", 5, w.proof("u"))
        during = dec.public_code
        w.clock.advance(cfg.tighten_expiry)           # unratified emergency tightening lapses
        dec2 = w.o.transfer(ASSET, "treasury", "u", 5, w.proof("u"))
        return Outcome(not dec.accepted, f"honest holder u: {during} during freeze, {dec2.public_code} after expiry",
                       {"freeze_ticks": cfg.tighten_expiry, "restored": dec2.accepted})
    w.truth = frozenset({"z"})                        # regulator designates z at t=0
    designated = dataclasses.replace(w.o.store.active, sanctioned=frozenset({"z"}))
    p = w.o.governance.propose("rules", designated, proposer="regulator-liaison")
    w.sign_with(w.o, p.pid, ["m1", "m2", "m3"])       # honest quorum authorises promptly
    w.clock.advance(2)                                # attacker acts two ticks later, inside the window
    dec = w.o.transfer(ASSET, "u", "z", 10, w.proof("z"))
    return Outcome(w.o.ledger.balance(ASSET, "z") > 0,
                   f"proposal {p.state.value}, transfer to designated z: {dec.public_code}")


def b3(variant: str) -> Outcome:
    """B3a AND B3b: poisoned regulatory feed ingested without independent validation."""
    if variant == "baseline":
        cfg = Config.baseline()
    elif variant == "residual":
        # the documented hazard: contestation keyed to provenance lets collusion hide behind two feeds
        cfg = Config.hardened().replace(provenance_independent_contestation=False)
    else:
        cfg = Config.hardened()
    w = make_world(cfg)
    feeds = [OracleFeed(f"feed{i}", w.pki) for i in (1, 2, 3)]
    agg = OracleAggregator(w.o)
    t = w.clock.now
    truth = {"z"}
    if variant == "residual":
        listings = [feeds[0].publish(set(), t), feeds[1].publish(set(), t), feeds[2].publish(truth, t)]
    else:
        listings = [feeds[0].publish(set(), t), feeds[1].publish(truth, t), feeds[2].publish(truth, t)]
        if variant == "baseline":
            listings = [feeds[0].publish(set(), t)]        # single feed, compromised
    p = agg.ingest(listings)
    notes = [f"flags={agg.flags}"]
    if p is not None and p.state == PState.PROPOSED:
        if variant == "residual":
            w.sign_with(w.o, p.pid, ["m1", "m2", "m3"])    # colluding quorum "reviews" it through
        else:
            for m in ("m1", "m2", "m3"):                   # honest members check independent sources
                w.o.governance.review_and_sign(p.pid, w.signers[m])
    if p is not None:
        w.o.governance.watch()
        w.clock.advance(cfg.challenge_window)
        notes.append(f"proposal {p.state.value}")
    else:
        notes.append("no proposal: feed consensus equals the active list")
    dec = w.o.transfer(ASSET, "u", "z", 10, w.proof("z"))
    return Outcome(w.o.ledger.balance(ASSET, "z") > 0, "; ".join(notes) + f"; transfer {dec.public_code}")
