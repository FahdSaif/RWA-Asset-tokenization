"""Branch E: exploit cross-chain compliance inconsistency."""
from __future__ import annotations

import dataclasses

from ..config import Config
from ..credentials import present
from .base import ACCREDITED, ALL_CLAIMS, ASSET, KYC_ONLY, UNRESTRICTED, Outcome, make_world

CLAIMS = {"accredited": "yes", "jur": "AU", "kyc": "pass"}


def _cfg(variant: str) -> Config:
    return Config.baseline() if variant == "baseline" else Config.hardened()


def e1(variant: str) -> Outcome:
    """E1: transfer on the destination inside the window between origin activation and relay."""
    cfg = _cfg(variant)
    w = make_world(cfg, sanctioned=(), dest=True)
    assert w.bridge and w.d
    w.bridge.transfer(ASSET, "u", "u", 50, w.proof("u"))                 # asset now on the destination
    w.truth = frozenset({"z"})
    designated = dataclasses.replace(w.o.store.active, sanctioned=frozenset({"z"}))
    p = w.o.governance.propose("rules", designated, proposer="regulator-liaison")
    w.sign_with(w.o, p.pid, ["m1", "m2", "m3"])                           # active on the origin at t0
    w.clock.advance(0 if variant == "residual" else 3)
    dec = w.d.transfer(ASSET, "u", "z", 10, w.proof("z"))
    return Outcome(w.d.ledger.balance(ASSET, "z") > 0,
                   f"attack at +{0 if variant == 'residual' else 3} ticks after origin activation: {dec.public_code}")


def e2(variant: str) -> Outcome:
    """E2: the same asset is unrestricted on D but accredited-only on O."""
    cfg = _cfg(variant)
    w = make_world(cfg, dest=True, o_rule=ACCREDITED, d_rule=UNRESTRICTED)
    assert w.bridge and w.d
    declared = UNRESTRICTED if variant == "residual" else None           # issuer declares a weak profile
    w.bridge.transfer(ASSET, "u", "u", 50, w.proof("u"), declared_profile=declared)
    dec = w.d.transfer(ASSET, "u", "x", 10, w.proof("x"))                # x is not accredited
    return Outcome(w.d.ledger.balance(ASSET, "x") > 0, f"transfer to non-accredited x on D: {dec.public_code}")


def e3(variant: str) -> Outcome:
    """E3: bridge preserves asset state but not recipient eligibility under the destination's rules."""
    cfg = _cfg(variant)
    w = make_world(cfg, dest=True, o_rule=KYC_ONLY, d_rule=ACCREDITED)
    assert w.bridge and w.d
    res = w.bridge.transfer(ASSET, "u", "x", 10, w.proof("x"), sender_proof=w.proof("u"))
    return Outcome(w.d.ledger.balance(ASSET, "x") > 0, f"bridge status: {res.status} ({res.detail})")


def e4(variant: str) -> Outcome:
    """E4: revocation not reflected on the destination (the destination must check freshness itself)."""
    o_cfg = Config.hardened()
    d_cfg = Config.baseline().replace(dest_mediation=True) if variant == "baseline" else Config.hardened()
    w = make_world(o_cfg, dest=True, dest_cfg=d_cfg)
    assert w.bridge and w.d
    w.bridge.transfer(ASSET, "u", "u", 50, w.proof("u"))
    cred = w.issuer.issue("rev", CLAIMS, 0)
    s0 = w.issuer.status(0)
    w.clock.advance(9)
    s9 = w.issuer.status(9)
    w.clock.advance(1)
    w.issuer.revoke(cred.cred_id)
    if variant == "residual":
        w.clock.advance(1)
        proof = present(cred, ALL_CLAIMS, s9)
    else:
        proof = present(cred, ALL_CLAIMS, s0)
    dec = w.d.transfer(ASSET, "u", "rev", 5, proof)
    return Outcome(w.d.ledger.balance(ASSET, "rev") > 0,
                   f"destination status age {w.clock.now - proof.status.tick}: {dec.public_code}")
