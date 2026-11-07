#!/usr/bin/env python3
"""Write docs/results/ratings_revised.json and docs/results/irr.json (+ irr.md) from the revised-ratings module and the
anonymised assessor scores, so every number in the paper's rating and inter-rater sections comes from code.

    python scripts/make_revision_outputs.py
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from rwa_threatlab import irr, risk, risk_revised as rr  # noqa: E402

FAC = ["F1", "F2", "F3", "G1", "G2", "G3"]


def main() -> int:
    res = ROOT / "docs" / "results"
    res.mkdir(parents=True, exist_ok=True)
    out = dict(status="post-hoc revision of three scope (G1) scores after the inter-rater study; original ratings unchanged in risk.py",
               rule=rr.__doc__.split("Rule (G1, scope):")[1].split("Why:")[0].strip(), reasons=rr.REASON,
               comparison=rr.comparison(), headline_original=rr.headline(False), headline_revised=rr.headline(True))
    (res / "ratings_revised.json").write_text(json.dumps(out, indent=1, default=str) + "\n")

    scores = irr.load_scores(ROOT / "docs" / "irr" / "scores_R1-R4.csv")
    rep = irr.report(scores)
    authors = {s[0]: dict(zip(FAC, list(s[5]) + list(s[6]))) for s in risk.S}
    per_assessor = {}
    band_eq = band_w1 = n = 0
    base = {r["id"]: r["res"] for r in risk.table()}
    for a, sc in scores.items():
        ex = w1 = m = 0
        for sid, row in authors.items():
            for k in FAC:
                ex += sc[sid][k] == row[k]
                w1 += abs(sc[sid][k] - row[k]) <= 1
                m += 1
        per_assessor[a] = dict(exact=ex / m, within_one=w1 / m, cells=m)
        for sid in authors:
            b = irr.residual_band(sc[sid], sid)
            n += 1
            band_eq += b == base[sid]
            band_w1 += abs(b - base[sid]) <= 1
    all_same = sum(len({v for v in d.values()}) == 1 for d in rep["bands"].values())
    summary = dict(assessors=rep["assessors"], scenarios=len(rep["scenarios"]), per_factor=rep["per_factor"],
                   per_assessor_vs_authors=per_assessor, residual_band_equal_to_authors=f"{band_eq}/{n}",
                   residual_band_within_one=f"{band_w1}/{n}", scenarios_all_assessors_same_band=f"{all_same}/{len(rep['scenarios'])}")
    (res / "irr.json").write_text(json.dumps(summary, indent=1, default=str) + "\n")
    (res / "irr.md").write_text(irr.markdown(rep) + "\n")
    print("wrote docs/results/ratings_revised.json, irr.json, irr.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
