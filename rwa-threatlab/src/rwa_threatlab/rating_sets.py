"""Residual bands of the 14 rated scenarios under three rating sets (robustness check for the post-hoc scope revision).

Sets
  original  the authors' ratings as first made (`risk.S`, frozen); the paper's primary table
  revised   the post-hoc scope revision of D1 to D3 (`risk_revised`, see docs/RATINGS_REVISION.md)
  median    per factor, the median of the four assessors' scores (`docs/irr/scores_R1-R4.csv`)

All three go through the unchanged rubric code (`risk.rate`, including the trust-anchor floor). With four assessors a median
can fall half-way between two levels. The rule for such cells was chosen AFTER the scores were seen, so both roundings are
reported ("median_down", "median_up") and any scenario whose band depends on the rounding is flagged. Status: post-hoc,
not part of the pre-registration. No rating is changed here.

Run:  python scripts/make_rating_sets.py      (writes docs/results/rating_sets.json and rating_sets.md)
"""
from __future__ import annotations

import math
import statistics
from pathlib import Path

from . import irr, risk, risk_revised

SETS = ("original", "revised", "median_down", "median_up")
DEFAULT_SCORES = Path(__file__).resolve().parents[2] / "docs" / "irr" / "scores_R1-R4.csv"


def _band(row: tuple, F: tuple, G: tuple) -> int:
    sid, name, node, adv, fadv, _, _, mit = row
    return risk.rate(tuple(F), tuple(G), mit, fadv)["res"]


def median_scores(scores: dict) -> dict[str, dict[str, float]]:
    """scenario -> factor -> median over assessors (may be x.5 with an even number of assessors)."""
    out = {}
    for row in risk.S:
        sid = row[0]
        out[sid] = {f: statistics.median(scores[a][sid][f] for a in scores if f in scores[a].get(sid, {}))
                    for f in irr.FACTORS}
    return out


def compute(scores_path: str | Path = DEFAULT_SCORES) -> dict:
    scores = irr.load_scores(scores_path)
    med = median_scores(scores)
    revised = {r[0]: r for r in risk_revised.revised_scenarios()}
    rows = []
    for row in risk.S:
        sid = row[0]
        m = med[sid]
        down = {f: math.floor(v) for f, v in m.items()}
        up = {f: math.ceil(v) for f, v in m.items()}
        rv = revised[sid]
        b = dict(original=_band(row, row[5], row[6]),
                 revised=_band(rv, rv[5], rv[6]),
                 median_down=_band(row, [down[f] for f in ("F1", "F2", "F3")], [down[f] for f in ("G1", "G2", "G3")]),
                 median_up=_band(row, [up[f] for f in ("F1", "F2", "F3")], [up[f] for f in ("G1", "G2", "G3")]))
        rows.append(dict(id=sid, name=row[1], bands={k: risk.LV[v] for k, v in b.items()}, levels=b,
                         half_median_factors=[f for f, v in m.items() if v != int(v)],
                         same_in_all_sets=len(set(b.values())) == 1,
                         depends_on_rounding=b["median_down"] != b["median_up"],
                         lowest=risk.LV[min(b.values())], highest=risk.LV[max(b.values())]))
    g1 = {sid: [scores[a][sid]["G1"] for a in sorted(scores)] for sid in risk_revised.REVISED_G1}
    original_g1 = {r[0]: r[6][0] for r in risk.S}
    scope_check = {sid: dict(original=original_g1[sid], revised=risk_revised.REVISED_G1[sid], assessors=v,
                             assessors_support_revision=sum(x == risk_revised.REVISED_G1[sid] for x in v) > len(v) / 2)
                   for sid, v in g1.items()}
    return dict(
        status="post-hoc robustness check; original ratings (risk.py) remain the primary table; no rating changed",
        assessors=sorted(scores), rounding_rule_note="median rounding rule chosen after the scores were seen; both roundings reported",
        rows=rows,
        same_in_all_sets=[(r["id"], r["bands"]["original"]) for r in rows if r["same_in_all_sets"]],
        depends_on_rating_set=[r["id"] for r in rows if not r["same_in_all_sets"] and not r["depends_on_rounding"]],
        depends_on_rounding=[r["id"] for r in rows if r["depends_on_rounding"]],
        scope_revision_check=scope_check,
    )


def markdown(res: dict) -> str:
    out = ["# Residual bands under three rating sets (post-hoc robustness check)", "",
           "Original = the authors' ratings (primary table). Revised = post-hoc scope revision of D1 to D3. Median = per-factor "
           "median of the four assessors, rounded down or up where it falls half-way (rounding rule chosen after the data were "
           "seen, so both are shown). All sets use the same rubric code (`risk.rate`).", "",
           "| Scenario | Original | Revised | Median (down) | Median (up) | Half-way factors | Same in all sets |",
           "|---|---|---|---|---|---|---|"]
    for r in res["rows"]:
        b = r["bands"]
        out.append(f"| {r['id']} | {b['original']} | {b['revised']} | {b['median_down']} | {b['median_up']} | "
                   f"{', '.join(r['half_median_factors']) or '-'} | {'yes' if r['same_in_all_sets'] else 'no'} |")
    out += ["", "**Same band in all sets:** " + "; ".join(f"{i} {b}" for i, b in res["same_in_all_sets"]),
            "", "**Band depends on the rating set:** " + ", ".join(res["depends_on_rating_set"]),
            "", "**Band depends only on how the median is rounded:** " + ", ".join(res["depends_on_rounding"]),
            "", "## Scope (G1) of D1 to D3: does the assessors' scoring support the revision?", "",
            "| Scenario | Original G1 | Revised G1 | Assessors' G1 | Majority supports revision |", "|---|---|---|---|---|"]
    for sid, c in res["scope_revision_check"].items():
        out.append(f"| {sid} | {c['original']} | {c['revised']} | {', '.join(map(str, c['assessors']))} | "
                   f"{'yes' if c['assessors_support_revision'] else 'no'} |")
    out += ["", "The assessors scored with the original scope wording, not the clarified rule, so their scores neither confirm nor "
                "refute the clarified rule itself."]
    return "\n".join(out)
