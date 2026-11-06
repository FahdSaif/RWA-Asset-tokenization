"""Branch D: deanonymise a participant via metadata correlation (realistic synthetic generators)."""
from __future__ import annotations

import math
import random

from ..config import Config
from ..credentials import present
from ..crypto import digest
from ..ledger import Transfer
from ..rules import Rule, SubRule
from .base import ASSET, Outcome, make_world
from .privacy import issuer_timing_linkage, linkage_stats, zipf_weights


def d1(variant: str) -> Outcome:
    params = {"baseline": dict(mean_gap=10.0, epoch=None),
              "hardened": dict(mean_gap=10.0, epoch=100),          # ~10 events per batch
              "residual": dict(mean_gap=50.0, epoch=100)}[variant]  # batching with little traffic (~2 per batch)
    m, lo, hi = linkage_stats(runs=40, **params)
    return Outcome(m >= 0.25, f"observer links {m:.0%} (95% CI {lo:.0%}-{hi:.0%}) of submissions; {params}",
                   {"linkage": m, "ci": (lo, hi)})


def d2(variant: str) -> Outcome:
    """D2: Trail entries that log the matched sub-rule narrow the anonymity set; Gateway error codes act as an
    eligibility oracle. Real Gateway and Trail; jurisdictions are Zipf-concentrated, as in real investor bases."""
    k, n = 8, 400
    cfg = Config.baseline() if variant == "baseline" else Config.hardened()
    rule = Rule(ASSET, "jurisdiction-accredited", tuple(SubRule(f"J{i}", (("jur", f"J{i}"),)) for i in range(k)))
    w = make_world(cfg, o_rule=rule)
    rnd = random.Random(3)
    weights = zipf_weights(k, 1.0)
    for i in range(n):
        j = rnd.choices(range(k), weights)[0]
        name = f"p{i}"
        cred = w.issuer.issue(name, {"jur": f"J{j}"}, 0)
        w.o.transfer(ASSET, "treasury", name, 1, present(cred, ["jur"], w.issuer.status(0)))
    details = [e.detail.split(":", 1)[1] for e in w.o.trail.entries if e.accepted]
    counts = {d: details.count(d) for d in set(details)}
    anon = sorted(counts[d] for d in details)                       # anonymity set of every observed entry
    mean_anon = sum(anon) / len(anon)
    p5 = anon[int(0.05 * len(anon))]
    bits = sum(math.log2(n / a) for a in anon) / len(anon)
    probes = [w.o.transfer(ASSET, "u", "q1", 1, None).public_code,
              w.o.transfer(ASSET, "u", "z", 1, w.proof("z")).public_code,
              w.o.transfer(ASSET, "u", "q2", 1, present(w.issuer.issue("q2", {"jur": "J99"}, 0), ["jur"],
                                                          w.issuer.status(0))).public_code]
    return Outcome(bits >= 1.0, f"mean anonymity set {mean_anon:.0f}/{n}, worst-5% {p5} ({bits:.2f} bits leaked); "
                   f"{len(set(probes))} distinct rejection codes",
                   {"bits": bits, "anonymity_set": mean_anon, "p5_anonymity_set": p5,
                    "distinct_error_codes": len(set(probes))})


def d3(variant: str) -> Outcome:
    """D3: a colluding issuer joins its issuance log with on-chain presentations (credential id, then timing)."""
    n = 40
    blind = variant != "baseline"
    delay_mean = 60.0 if variant == "hardened" else 1.0
    w = make_world(Config.hardened(), blind_issuer=blind)
    rnd = random.Random(5)
    t, plan = 0.0, []
    for i in range(n):
        t += rnd.expovariate(1 / 3.0)
        plan.append((round(t), round(t + rnd.expovariate(1 / delay_mean)), f"h{i}"))
    creds = {}
    for t_issue, _, name in plan:
        w.clock.now = t_issue
        creds[name] = w.issuer.issue(name, {"accredited": "yes", "jur": "AU", "kyc": "pass"}, t_issue)
    w.clock.now = 0
    truth: dict[str, str] = {}
    for t_issue, t_pres, name in sorted(plan, key=lambda p: p[1]):
        if t_pres > w.clock.now:
            w.clock.advance(t_pres - w.clock.now)
        pr = present(creds[name], ["accredited", "jur"], w.issuer.status(w.clock.now))
        w.o.transfer(ASSET, "treasury", name, 1, pr)
        truth[Transfer(ASSET, "treasury", name, 1).digest()] = name
    log = w.issuer.issuance_log
    by_hash = {digest(e["cred_id"]): e["identity"] for e in log if "cred_id" in e}
    linked = 0
    for e in w.o.trail.entries:
        if e.tx_ref not in truth:
            continue
        guess = by_hash.get(e.proof_ref)
        if guess is None:                                           # fall back to timing correlation
            prev = [x for x in log if x["tick"] <= e.tick]
            guess = prev[-1]["identity"] if prev else None
        linked += guess == truth[e.tx_ref]
    acc = linked / n
    return Outcome(acc >= 0.5, f"issuer links {acc:.0%} of presentations (blind issuance={blind}, mean "
                   f"presentation delay {delay_mean:g} ticks)", {"linkage": acc})
