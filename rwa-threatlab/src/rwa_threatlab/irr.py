"""Inter-rater reliability for the paper's rubric (Table 4 / Appendix A).

Independent assessors score each scenario on the six 1-3 factors WITHOUT seeing the authors' scores. This module
reports Krippendorff's alpha (ordinal metric), exact and within-one agreement per factor, and whether the assessors
arrive at the same residual band as the authors once their scores go through the rubric (`risk.rate`).

CSV columns: assessor,scenario,F1,F2,F3,G1,G2,G3     (one row per assessor per scenario; blanks allowed)
Run:  python -m rwa_threatlab.irr scores.csv
"""
from __future__ import annotations

import csv
import itertools
import sys
from collections import defaultdict
from pathlib import Path

from . import risk

FACTORS = ("F1", "F2", "F3", "G1", "G2", "G3")
CATS = (1, 2, 3)


def load_scores(path: str | Path) -> dict[str, dict[str, dict[str, int]]]:
    """scores[assessor][scenario][factor] -> 1..3"""
    out: dict = defaultdict(lambda: defaultdict(dict))
    with open(path, newline="") as f:
        for r in csv.DictReader(f):
            for fac in FACTORS:
                v = (r.get(fac) or "").strip()
                if v:
                    x = int(v)
                    if x not in CATS:
                        raise ValueError(f"{r['assessor']}/{r['scenario']}/{fac}: score {x} outside 1-3")
                    out[r["assessor"].strip()][r["scenario"].strip()][fac] = x
    return {a: dict(s) for a, s in out.items()}


def krippendorff_alpha_ordinal(units: list[list[int]]) -> float | None:
    """units: for each rated item, the list of scores given by the raters who rated it."""
    o = {(c, k): 0.0 for c in CATS for k in CATS}
    for u in units:
        m = len(u)
        if m < 2:
            continue
        for i, j in itertools.permutations(range(m), 2):
            o[(u[i], u[j])] += 1.0 / (m - 1)
    nc = {c: sum(o[(c, k)] for k in CATS) for c in CATS}
    n = sum(nc.values())
    if n <= 1:
        return None

    def d2(c: int, k: int) -> float:
        if c == k:
            return 0.0
        lo, hi = min(c, k), max(c, k)
        return (sum(nc[g] for g in CATS if lo <= g <= hi) - (nc[c] + nc[k]) / 2) ** 2

    num = sum(o[(c, k)] * d2(c, k) for c in CATS for k in CATS)
    den = sum(nc[c] * nc[k] * d2(c, k) for c in CATS for k in CATS)
    if den == 0:
        return None            # no variation in the data: alpha undefined (agreement is trivial)
    return 1 - (n - 1) * num / den


def _pair_agreement(units: list[list[int]]) -> tuple[float, float]:
    pairs = [(a, b) for u in units for a, b in itertools.combinations(u, 2)]
    if not pairs:
        return float("nan"), float("nan")
    return (sum(a == b for a, b in pairs) / len(pairs), sum(abs(a - b) <= 1 for a, b in pairs) / len(pairs))


def residual_band(sc: dict[str, int], scenario_id: str) -> int | None:
    row = next((s for s in risk.S if s[0] == scenario_id), None)
    if row is None or any(f not in sc for f in FACTORS):
        return None
    _, _, _, _, fadv, _, _, mit = row
    return risk.rate((sc["F1"], sc["F2"], sc["F3"]), (sc["G1"], sc["G2"], sc["G3"]), mit, fadv)["res"]


def report(scores: dict, authors: dict | None = None) -> dict:
    """`authors` (optional) is scores for the authors in the same shape, used to compare residual bands."""
    scen = sorted({s for a in scores.values() for s in a})
    per_factor = {}
    for fac in FACTORS:
        units = [[a[s][fac] for a in scores.values() if s in a and fac in a[s]] for s in scen]
        ex, w1 = _pair_agreement(units)
        per_factor[fac] = dict(alpha=krippendorff_alpha_ordinal(units), exact=ex, within_one=w1)
    bands = {s: {a: residual_band(v[s], s) for a, v in scores.items() if s in v} for s in scen}
    same_band = [len({b for b in d.values() if b is not None}) == 1 for d in bands.values() if len([b for b in d.values() if b]) >= 2]
    out = dict(assessors=sorted(scores), scenarios=scen, per_factor=per_factor, bands=bands,
               band_agreement=(sum(same_band) / len(same_band)) if same_band else None)
    if authors:
        ours = {s: residual_band(next(iter(authors.values()))[s], s) for s in scen if s in next(iter(authors.values()))}
        out["matches_authors"] = {a: sum(bands[s].get(a) == ours.get(s) for s in scen if bands[s].get(a) is not None) /
                                  max(1, sum(bands[s].get(a) is not None for s in scen)) for a in scores}
    return out


def markdown(rep: dict) -> str:
    f = lambda x: "n/a" if x is None or x != x else f"{x:.2f}"  # noqa: E731
    rows = ["| Factor | Krippendorff alpha (ordinal) | Exact agreement | Within one |", "|---|---|---|---|"]
    for fac, v in rep["per_factor"].items():
        rows.append(f"| {fac} | {f(v['alpha'])} | {f(v['exact'])} | {f(v['within_one'])} |")
    rows.append("")
    rows.append(f"Assessors: {', '.join(rep['assessors'])}. Scenarios scored: {len(rep['scenarios'])}. "
                f"Share of scenarios on which all assessors reach the same residual band: {f(rep['band_agreement'])}.")
    return "\n".join(rows)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    sc = load_scores(sys.argv[1])
    print(markdown(report(sc)))
