"""Research hypotheses, kept separate from software tests.

Software tests (tests/) check that the code does what it says and must always pass.
Hypotheses (here) are the paper's *claims*. Each can come out CONFIRMED, REFUTED or INCONCLUSIVE and the
outcome is reported either way; none of them is a pass/fail gate for the build.

Seed discipline: seeds 0-399 were used *exploratorily* while building the fuzzer and fixing the three defects
documented in docs/FINDINGS.md. Every campaign below uses held-out seeds >= HELD_OUT_SEED0 that were never used
for debugging. Predictions are the paper's claims; they were fixed in the paper before these runs.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from . import fuzz, modelcheck, risk
from .config import Config
from .scenarios import ALL
from .scenarios.privacy import delay_sweep, epoch_sweep

HELD_OUT_SEED0 = 30_000     # ranges 10_000-10_599 and 20_000-20_599 were spent on instrument corrections; docs/FINDINGS.md
TRACES, STEPS = 600, 40


@dataclass
class Result:
    status: str                      # CONFIRMED | REFUTED | INCONCLUSIVE | DESCRIPTIVE
    evidence: str
    data: dict = field(default_factory=dict)


@dataclass
class Hypothesis:
    id: str
    statement: str
    prediction: str
    run: Callable[[], Result]


def _camp(cfg: Config, adv: str) -> dict:
    return fuzz.campaign(cfg, adv, traces=TRACES, steps=STEPS, seed0=HELD_OUT_SEED0)


def _scen(sid: str) -> dict:
    return next(s for s in ALL if s.id == sid).execute()


def h1() -> Result:
    cells = {a: _camp(Config.hardened(), a) for a in ("none", "minority", "feed", "feeds2")}
    unexpl = sum(c["violations"]["UNEXPLAINED"] for c in cells.values())
    adv = sum(c["violations"]["adversary"] for c in cells.values())
    lag = sum(c["violations"]["documented-lag"] for c in cells.values())
    crashes = sum(c["crashes"] + c["trail_integrity_failures"] for c in cells.values())
    ok = unexpl == 0 and adv == 0 and crashes == 0
    ex = [e for c in cells.values() for e in c["examples"]][:2]
    return Result("CONFIRMED" if ok else "REFUTED",
                  f"{4 * TRACES} traces x {STEPS} steps: {unexpl} unexplained, {adv} adversary-attributed, {lag} inside "
                  f"documented lag windows, {crashes} crashes/trail failures", dict(cells=cells, examples=ex))


def h1b() -> Result:
    c = _camp(Config.baseline(), "none")
    n = sum(c["violations"].values())
    return Result("CONFIRMED" if n > 0 else "INCONCLUSIVE",
                  f"instrument sensitivity: the baseline build shows {n} violations over {TRACES} traces with no "
                  f"adversary; a fuzzer that finds nothing there would be vacuous", dict(campaign=c))


def h2() -> Result:
    c = _camp(Config.hardened(), "quorum")
    caps = c["adversary_cap_sets"]
    relax = sum(v for k, v in caps.items() if "relax" in k)
    other = {k: v for k, v in caps.items() if set(k.split("+")) - {"upgrade"}}
    ok = relax == 0 and not other
    return Result("CONFIRMED" if ok else "REFUTED",
                  f"colluding quorum, no censorship: {c['traces_with_violation']}/{TRACES} traces violate; every "
                  f"violation goes through an installed backdoored upgrade; harmful relaxations: {relax}; "
                  f"attributed sets {caps or 'none'}", dict(campaign=c))


def h2b() -> Result:
    c = _camp(Config.hardened(), "quorum")
    ins = c["installs"]
    ok = ins.get("PermissiveGateway", 0) == 0 and ins.get("BackdooredGateway", 0) > 0
    return Result("CONFIRMED" if ok else "REFUTED",
                  f"guarded upgrades: permissive builds installed {ins.get('PermissiveGateway', 0)}, trigger-based "
                  f"backdoored builds installed {ins.get('BackdooredGateway', 0)} (bounded conformance tests catch "
                  f"blatant faults, not triggers)", dict(installs=ins))


def h3() -> Result:
    a, b = _camp(Config.hardened(), "quorum"), _camp(Config.hardened(), "quorum+censor")
    relax_a = sum(v for k, v in a["adversary_cap_sets"].items() if "relax" in k)
    relax_b = sum(v for k, v in b["adversary_cap_sets"].items() if "relax" in k)
    return Result("CONFIRMED" if relax_a == 0 and relax_b > 0 else "REFUTED",
                  f"rule-set corruption via relaxation: {relax_a} without censorship vs {relax_b} with censorship",
                  dict(quorum=a, quorum_censor=b))


def h4() -> Result:
    c = _camp(Config.hardened(), "issuer")
    caps = c["adversary_cap_sets"]
    ok = c["traces_with_violation"] > 0 and set(caps) <= {"issuer"} and c["violations"]["UNEXPLAINED"] == 0
    return Result("CONFIRMED" if ok else "REFUTED",
                  f"compromised listed issuer vs hardened build: {c['traces_with_violation']}/{TRACES} traces violate, "
                  f"all attributed to {sorted(caps) or 'none'} (trust-anchor floor)", dict(campaign=c))


def h5() -> Result:
    m = modelcheck.run(verbose=False)
    comp = {c["id"]: c["violation"] for c in m["composition"]}
    e3 = _scen("E3")
    ok = comp == {"I1": False, "I2": False, "I3": True, "I4": False} and e3["baseline"].attack_succeeded \
        and not e3["hardened"].attack_succeeded
    return Result("CONFIRMED" if ok else "REFUTED",
                  f"composition without adversary capabilities: model check {comp}; implementation E3 baseline attack "
                  f"{e3['baseline'].attack_succeeded}, hardened {e3['hardened'].attack_succeeded}")


def h6() -> Result:
    sw = epoch_sweep(runs=40)
    first_below = next((r["events_per_epoch"] for r in sw if r["hi"] < 0.25), None)
    ok = sw[0]["lo"] >= 0.25 and sw[-1]["hi"] < 0.25
    return Result("CONFIRMED" if ok else "REFUTED",
                  f"timing linkage falls from {sw[0]['mean']:.0%} (1 event/epoch) to {sw[-1]['mean']:.0%} "
                  f"({sw[-1]['events_per_epoch']}/epoch); drops below 25% (CI upper bound) from "
                  f"{first_below} events per epoch", dict(sweep=sw))


def h7() -> Result:
    d2 = _scen("D2")
    b, h = d2["baseline"].metrics, d2["hardened"].metrics
    ok = b["bits"] > 1.0 and h["bits"] == 0.0 and b["distinct_error_codes"] > h["distinct_error_codes"]
    return Result("CONFIRMED" if ok else "REFUTED",
                  f"sub-rule logging leaks {b['bits']:.2f} bits (worst-5% anonymity set {b['p5_anonymity_set']}); "
                  f"class-level logging leaks {h['bits']:.2f}; rejection codes {b['distinct_error_codes']} -> "
                  f"{h['distinct_error_codes']}", dict(baseline=b, hardened=h))


def h8() -> Result:
    sw = delay_sweep(runs=40)
    ok = sw[0]["lo"] >= 0.5 and next(r for r in sw if r["delay_mean"] == 60)["hi"] < 0.1
    return Result("CONFIRMED" if ok else "REFUTED",
                  f"blind issuance removes the credential-id join but timing remains: issuer links "
                  f"{sw[0]['mean']:.0%} at 1-tick delay and {next(r for r in sw if r['delay_mean'] == 60)['mean']:.0%} "
                  f"at 60-tick delay", dict(sweep=sw))


def h9() -> Result:
    b2 = _scen("B2")["residual"]
    ok = b2.attack_succeeded and b2.metrics.get("restored") is True
    return Result("CONFIRMED" if ok else "REFUTED",
                  f"false tightening freezes an honest holder (availability attack succeeds) for "
                  f"{b2.metrics.get('freeze_ticks')} ticks and is then undone: {b2.detail}", dict(metrics=b2.metrics))


def h10() -> Result:
    s = risk.sensitivity(trials=5000)
    return Result("DESCRIPTIVE",
                  f"rubric robustness (not a test): A1/A2 stays in the lowest band in {s['a1a2_lowest']:.0%} of "
                  f"perturbed assessments; >=3 of 4 trust-anchor rows stay >= Medium in {s['anchors_ge3']:.0%}; mean band "
                  f"shift {s['mean_shift']:.2f}", dict(sensitivity=s))


HYPOTHESES: list[Hypothesis] = [
    Hypothesis("H1", "Hardened build, no anchor capability: no violation outside the documented lag windows.",
               "0 unexplained and 0 adversary-attributed violations", h1),
    Hypothesis("H1b", "Instrument sensitivity: the same fuzzer finds violations in the baseline build.",
               "> 0 violations", h1b),
    Hypothesis("H2", "A colluding quorum without censorship cannot corrupt the rule set.",
               "no harmful relaxation; only the backdoored-upgrade route remains", h2),
    Hypothesis("H2b", "The bounded conformance suite stops blatant faulty upgrades but not trigger-based backdoors.",
               "permissive installs = 0; backdoored installs > 0", h2b),
    Hypothesis("H3", "Censorship of contestation is what opens branch B1.",
               "relax violations: 0 without, > 0 with censorship", h3),
    Hypothesis("H4", "A compromised listed issuer defeats every technical mitigation (trust-anchor floor).",
               "violations exist and are all attributed to the issuer", h4),
    Hypothesis("H5", "Cross-instance violations arise from composition with no adversary capability.",
               "I1, I2 safe; I3 unsafe; I4 safe; E3 baseline attack", h5),
    Hypothesis("H6", "Batching reduces timing linkage only when enough traffic shares an epoch.",
               "linkage >= 25% at 1 event/epoch and < 25% at 20", h6),
    Hypothesis("H7", "Logging the matched sub-rule leaks identity information that rule-class logging does not.",
               "> 1 bit vs 0 bits", h7),
    Hypothesis("H8", "Blind issuance defeats the credential-id join but not issuer timing correlation.",
               ">= 50% linked at 1-tick delay, < 10% at 60-tick delay", h8),
    Hypothesis("H9", "Immediate tightening trades an integrity attack for a bounded availability attack.",
               "freeze succeeds, then expires", h9),
    Hypothesis("H10", "Rubric ratings are stable under small perturbations.",
               "descriptive only", h10),
]


def run_all() -> list[tuple[Hypothesis, Result]]:
    return [(h, h.run()) for h in HYPOTHESES]


def markdown(results=None) -> str:
    results = results or run_all()
    out = [f"Held-out seeds from {HELD_OUT_SEED0}; {TRACES} traces x {STEPS} steps per fuzz cell.", "",
           "| ID | Hypothesis | Prediction | Outcome | Evidence |", "|---|---|---|---|---|"]
    for h, r in results:
        out.append(f"| {h.id} | {h.statement} | {h.prediction} | **{r.status}** | {r.evidence} |")
    return "\n".join(out)
