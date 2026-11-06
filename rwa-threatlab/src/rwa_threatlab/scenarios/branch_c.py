"""Branch C: forge a valid-looking compliance proof."""
from __future__ import annotations

from ..config import Config
from ..credentials import Issuer, present
from .base import ALL_CLAIMS, ASSET, Outcome, make_world

CLAIMS = {"accredited": "yes", "jur": "AU", "kyc": "pass"}


def c1a(variant: str) -> Outcome:
    """C1a: impersonate a low-assurance issuer: unlisted issuer, or a listed issuer outside its scope."""
    cfg = Config.baseline() if variant == "baseline" else Config.hardened()
    w = make_world(cfg)
    log = []
    for who, issuer in (("x1", Issuer("shady-kyc", w.pki)), ("x2", Issuer("bank-kyc", w.pki))):
        cred = issuer.issue(who, CLAIMS, w.clock.now)
        proof = present(cred, ALL_CLAIMS, issuer.status(w.clock.now))
        dec = w.o.transfer(ASSET, "u", who, 1, proof)
        log.append(f"{issuer.name}: {dec.public_code}")
    got = w.o.ledger.balance(ASSET, "x1") + w.o.ledger.balance(ASSET, "x2") > 0
    return Outcome(got, "; ".join(log))


def c1(variant: str) -> Outcome:
    """C1: a legitimately listed, in-scope issuer is itself compromised (trust-anchor floor)."""
    cfg = Config.baseline() if variant == "baseline" else Config.hardened()
    w = make_world(cfg)
    forged = w.issuer.issue("x", CLAIMS, w.clock.now)          # adversary holds the issuer's key
    dec = w.o.transfer(ASSET, "u", "x", 1, present(forged, ALL_CLAIMS, w.issuer.status(w.clock.now)))
    return Outcome(w.o.ledger.balance(ASSET, "x") > 0, f"forged credential from listed issuer: {dec.public_code}")


def c2(variant: str) -> Outcome:
    """C2: present a credential after revocation, inside the status-propagation lag."""
    cfg = Config.baseline() if variant == "baseline" else Config.hardened()
    w = make_world(cfg)
    cred = w.issuer.issue("rev", CLAIMS, 0)
    s0 = w.issuer.status(0)
    w.clock.advance(9)
    s9 = w.issuer.status(9)
    w.clock.advance(1)
    w.issuer.revoke(cred.cred_id)                               # revoked at t=10
    if variant == "residual":
        w.clock.advance(1)
        proof = present(cred, ALL_CLAIMS, s9)                   # status taken just before revocation
    else:
        proof = present(cred, ALL_CLAIMS, s0)                   # replay of an old status proof
    dec = w.o.transfer(ASSET, "u", "rev", 1, proof)
    return Outcome(w.o.ledger.balance(ASSET, "rev") > 0,
                   f"status age {w.clock.now - proof.status.tick} ticks, bound {cfg.freshness_bound}: {dec.public_code}")
