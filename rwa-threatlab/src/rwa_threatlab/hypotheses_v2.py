"""Pre-registered hypotheses of the journal extension (see docs/PREREGISTRATION.md). New file: the frozen
hypotheses.py is untouched. H11 = independent oracle (addendum A2). Seeds 40,000-40,599, run once."""
from __future__ import annotations

from . import oracle_independent as oi
from .config import Config
from .fuzz_observed import observe
from .hypotheses import Result

H11_SEED0, TRACES, STEPS = 40_000, 600, 40
# every (build, adversary) cell used by H1-H4 and H1b
CELLS = [("baseline", Config.baseline, "none")] + [("hardened", Config.hardened, a) for a in
         ("none", "minority", "feed", "feeds2", "quorum", "quorum+censor", "issuer")]
H1_CELLS = {("hardened", a) for a in ("none", "minority", "feed", "feeds2")}


def run_h11(seed0: int = H11_SEED0, traces: int = TRACES, steps: int = STEPS) -> dict:
    cells, tot = {}, dict(violations=0, disagreements=0)
    conv_names = list(oi.ALL_CONVENTIONS)
    # per convention: within-lag count, flips (beyond->within, within->beyond), would-be unexplained in H1 cells
    sens = {c: dict(violations=0, within=0, to_within=0, to_beyond=0, h1_unexplained=0) for c in conv_names}
    examples = []
    for build, mk, adv in CELLS:
        cfg, n_v, dis, per_kind = mk(), 0, 0, {}
        for s in range(seed0, seed0 + traces):
            res, log = observe(cfg, adv, s, steps)
            cmp_ = oi.compare(res.violations, oi.evaluate(log, oi.FUZZER_CONVENTIONS))
            n_v += cmp_["n_fuzzer"]
            dis += cmp_["disagreements"]
            if cmp_["disagreements"] and len(examples) < 5:
                examples.append(dict(build=build, adversary=adv, seed=s, **{k: v for k, v in cmp_.items() if k != "n_oracle"}))
            for c in conv_names:
                o = {(v["step"], v["chain"], v["name"]): v for v in oi.evaluate(log, oi.ALL_CONVENTIONS[c])}
                for v in res.violations:
                    w = o[(v.step, v.chain, v.name)]["within_lag"] if (v.step, v.chain, v.name) in o else None
                    if w is None:
                        continue
                    was = v.lag is not None and 0 <= v.lag <= oi.L_DOC
                    d = sens[c]
                    d["violations"] += 1
                    d["within"] += w
                    d["to_within"] += (w and not was)
                    d["to_beyond"] += ((not w) and was)
                    if (build, adv) in H1_CELLS and v.kind != "adversary" and not w:
                        d["h1_unexplained"] += 1
        cells[f"{build}/{adv}"] = dict(traces=traces, violations=n_v, disagreements=dis)
        tot["violations"] += n_v
        tot["disagreements"] += dis
    return dict(cells=cells, totals=tot, sensitivity=sens, examples=examples, seeds=f"{seed0}-{seed0 + traces - 1}")


def h11a(data: dict) -> Result:
    base_v = data["cells"]["baseline/none"]["violations"]
    t = data["totals"]
    if t["violations"] == 0 or base_v == 0:
        return Result("INCONCLUSIVE", "no violations were compared in the baseline cell, so the comparison is vacuous", data)
    ok = t["disagreements"] == 0
    return Result("CONFIRMED" if ok else "REFUTED",
                  f"independent oracle vs fuzzer oracle, {len(data['cells'])} cells x {TRACES} traces (seeds {data['seeds']}): "
                  f"{t['violations']} violations compared, {t['disagreements']} disagreements", dict(data=data))


def h11b(data: dict) -> Result:
    s = data["sensitivity"]
    mono = all(v["to_beyond"] == 0 for k, v in s.items() if k.startswith("action/"))
    robust = all(v["h1_unexplained"] == 0 for v in s.values())
    parts = "; ".join(f"{k}: {v['within']}/{v['violations']} within lag, {v['to_within']} flip to within, {v['to_beyond']} to beyond"
                      for k, v in s.items())
    ok = mono and robust
    return Result("CONFIRMED" if ok else "REFUTED",
                  f"measuring the lag at the action tick never turns a within-lag violation into a beyond-lag one: {mono}; "
                  f"H1 cells show 0 unexplained under all four conventions: {robust}. {parts}", dict(sensitivity=s))
