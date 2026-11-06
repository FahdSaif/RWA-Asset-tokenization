"""Executable attack scenarios: one per attack-tree leaf of the paper."""
from __future__ import annotations

from . import branch_a, branch_b, branch_c, branch_d, branch_e
from .base import Outcome, Scenario

BR = ("baseline", "hardened", "residual")
ALL: list[Scenario] = [
    Scenario("A1", "A1", "Raw / node-level transaction with no validation hook", "Adv1", branch_a.a1),
    Scenario("A2", "A2", "Gateway software defect (origin spoofing)", "Adv1/2", branch_a.a2),
    Scenario("A3a", "A3", "Privileged forced transfer / recovery operation", "Adv5", branch_a.a3a, BR,
             "residual reduces to governance: rules relaxed first (B1) with contestation censored"),
    Scenario("A3b", "A3", "Runtime upgrade that alters the Gateway", "Adv5/6", branch_a.a3b, BR,
             "residual: attested, backdoored build passes bounded conformance tests"),
    Scenario("B1", "B1a+B1b", "Quorum collusion defeating the challenge window", "Adv5", branch_b.b1, BR,
             "residual: contestation suppressed (B1b)"),
    Scenario("B2", "B2", "Rule-activation latency window", "Adv2", branch_b.b2, BR,
             "residual is an availability attack: false tightening freezes an honest holder"),
    Scenario("B3", "B3a+B3b", "Poisoned regulatory-data feed", "Adv4", branch_b.b3, BR,
             "residual: two feeds + colluding quorum with provenance-dependent contestation"),
    Scenario("C1a", "C1a", "Unlisted or out-of-scope issuer", "Adv2/3", branch_c.c1a),
    Scenario("C1", "C1", "Compromised, listed, in-scope issuer", "Adv3", branch_c.c1, ("baseline", "hardened"),
             "trust-anchor floor: no technical mitigation removes this"),
    Scenario("C2", "C2", "Revoked credential inside the status lag", "Adv2", branch_c.c2, BR,
             "residual: inside the freshness bound"),
    Scenario("D1", "D1", "Timing / value correlation", "Adv1", branch_d.d1, BR,
             "residual: batching with little traffic"),
    Scenario("D2", "D2", "Trail-granularity leakage and error oracle", "Adv1", branch_d.d2),
    Scenario("D3", "D3a+D3b", "Issuer-linkage deanonymisation", "Adv3", branch_d.d3, BR,
             "residual: blind issuance but immediate presentation leaves a timing link"),
    Scenario("E1", "E1", "Cross-chain rule-propagation lag", "Adv2", branch_e.e1, BR,
             "residual: before the pending-change notice arrives"),
    Scenario("E2", "E2", "Jurisdictional misclassification", "Adv2", branch_e.e2, BR,
             "residual: issuer declares a weak compliance profile"),
    Scenario("E3", "E3a+E3b", "Bridge identity discontinuity", "Adv2", branch_e.e3),
    Scenario("E4", "E4", "Cross-chain revocation lag", "Adv2", branch_e.e4, BR,
             "residual: inside the freshness bound"),
]

__all__ = ["ALL", "Outcome", "Scenario"]
