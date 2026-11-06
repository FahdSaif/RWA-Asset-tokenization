"""Narrated walkthrough of attack-tree branch B1 (quorum collusion) against three builds.

    python examples/walkthrough_quorum_collusion.py
"""
import dataclasses
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from rwa_threatlab.config import Config                      # noqa: E402
from rwa_threatlab.scenarios.base import ASSET, make_world   # noqa: E402


def run(label: str, cfg: Config, censor: bool = False) -> None:
    w = make_world(cfg)
    print(f"\n=== {label} ===")
    print("z is sanctioned, so a transfer to z is rejected:",
          w.o.transfer(ASSET, "u", "z", 10, w.proof("z")).public_code)
    w.o.governance.contest_censored = censor
    relaxed = dataclasses.replace(w.o.store.active, sanctioned=frozenset())
    p = w.o.governance.propose("rules", relaxed, proposer="colluding-members")
    w.sign_with(w.o, p.pid, ["m1", "m2", "m3"])               # B1a: threshold-sufficient coalition
    print(f"3 of 5 members approve removing z from the sanction list -> proposal is '{p.state.value}'")
    print(f"honest watchers contest: {w.o.governance.watch()} (contestation censored: {censor})")
    w.clock.advance(cfg.challenge_window)
    dec = w.o.transfer(ASSET, "u", "z", 10, w.proof("z"))
    print(f"proposal is now '{p.state.value}'; transfer to z -> {dec.public_code}; z holds {w.o.ledger.balance(ASSET, 'z')}")
    ok, bad = w.o.trail.verify()
    print(f"Compliance Trail: {len(w.o.trail.entries)} entries, hash chain intact: {ok}")


run("baseline build (no challenge window)", Config.baseline())
run("hardened build (challenge window + honest watchers)", Config.hardened())
run("hardened build, contestation suppressed (B1a AND B1b: residual risk)", Config.hardened(), censor=True)
