"""Post-hoc revision of three scope (G1) scores after the inter-rater study.

The original ratings in `risk.S` are frozen and unchanged. This module re-expresses the same table with one clarified rule
for the scope factor and recomputes everything with the unchanged rubric code in `risk.rate`.

Rule (G1, scope): the number of participants, transactions or assets that ONE attacker holding the scenario's capability
can affect (the reach of the attack path, not the number of victims of a single execution).
  3 = every participant or asset; 2 = the participants or assets served by one component, issuer or chain; 1 = one.

Why: the assessors' largest difference from the authors was the scope of the privacy scenarios D1-D3. In the original table
the compliance scenarios (A1/A2, A3, B1, B3) were scored by reach, and D1-D3 per affected participant. Applying one rule
changes exactly three scores. No other factor of any scenario is changed. This is a post-hoc revision and is reported as such.
"""
from __future__ import annotations

from . import risk

REVISED_G1 = {"D1": 3, "D2": 3, "D3": 2}
REASON = {
    "D1": "a passive observer can correlate timing and value for every participant (reach: all)",
    "D2": "the Compliance Trail is readable by anyone and every entry carries the matched sub-rule (reach: all)",
    "D3": "a colluding issuer can link only the credentials it issued (reach: that issuer's holders, as for C1)",
}


def revised_scenarios() -> list[tuple]:
    out = []
    for sid, name, node, adv, fadv, F, G, mit in risk.S:
        if sid in REVISED_G1:
            G = (REVISED_G1[sid],) + tuple(G[1:])
        out.append((sid, name, node, adv, fadv, F, G, mit))
    return out


def _rate(row: tuple, floor: bool = True) -> dict:
    sid, name, node, adv, fadv, F, G, mit = row
    return risk.rate(tuple(F), tuple(G), mit, fadv, floor=floor)


def table(revised: bool = True, floor: bool = True) -> list[dict]:
    rows = revised_scenarios() if revised else list(risk.S)
    out = []
    for row in rows:
        r = _rate(row, floor)
        out.append(dict(id=row[0], name=row[1], F=list(row[5]), G=list(row[6]), L=r["L"], I=r["I"], P=r["P"], res=r["res"]))
    return out


def comparison() -> list[dict]:
    before, after = {r["id"]: r for r in table(False)}, {r["id"]: r for r in table(True)}
    return [dict(id=k, name=before[k]["name"], before=before[k], after=after[k], changed=before[k]["G"] != after[k]["G"])
            for k in before]


def ranking(revised: bool = True, floor: bool = True) -> list[tuple[str, int, int]]:
    t = table(revised, floor)
    return sorted(((r["id"], r["res"], r["P"]) for r in t), key=lambda x: (-x[1], -x[2], x[0]))


def headline(revised: bool = True) -> dict:
    t = {r["id"]: r for r in table(revised)}
    return dict(
        low=sorted(k for k, v in t.items() if v["res"] == 1),
        medium_or_above=sorted(k for k, v in t.items() if v["res"] >= 3),
        top=[(k, risk.LV[b], p) for k, b, p in ranking(revised)[:4]],
        floor_changes=sorted(k for k in t if table(revised, floor=False)[[r["id"] for r in table(revised)].index(k)]["res"] != t[k]["res"]),
    )
