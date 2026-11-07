#!/usr/bin/env python3
"""Rubric-based likelihood / impact / residual-risk scoring (Table 3-4 and Appendix A of the paper)."""
from __future__ import annotations

import random
LV = {1: "Low", 2: "Low-Med", 3: "Medium", 4: "Med-High", 5: "High"}
def band_sum(s):  return 1 if s<=4 else 2 if s==5 else 3 if s==6 else 4 if s==7 else 5   # 3..9 -> 1..5
def band_prod(p): return 1 if p<=5 else 2 if p<=9 else 3 if p<=14 else 4 if p<=19 else 5  # 1..25 -> 1..5
REDUCE = {"T":2, "P":1, "X":0}          # mitigation class -> likelihood levels removed
ANCHORS = {"Adv3","Adv4","Adv5"}         # trust-anchor adversaries (floor rule)

# id, scenario, tree nodes, adversary shown, adversary used for floor rule, (F1,F2,F3), (G1,G2,G3), mitigation class
S = [
 ("A1/A2","Unmediated path or Gateway defect","A1, A2","Adv1/2","Adv1",(3,1,2),(3,2,3),"T"),
 ("A3","Privileged path (upgrade, admin, recovery)","A3","Adv5/6","Adv5",(2,2,2),(3,3,3),"P"),
 ("B1","Quorum collusion","B1a, B1b","Adv5","Adv5",(1,2,2),(3,3,3),"P"),
 ("B2","Rule-activation latency window","B2","Adv2","Adv2",(3,2,2),(1,2,3),"P"),
 ("B3","Regulatory-oracle poisoning","B3a, B3b","Adv4","Adv4",(2,2,2),(3,2,3),"P"),
 ("C1","Compromised or forged issuer","C1a","Adv3","Adv3",(2,2,2),(2,3,3),"P"),
 ("C2","Revoked credential in lag window","C2","Adv2","Adv2",(3,2,2),(1,2,3),"P"),
 ("D1","Timing and value correlation","D1","Adv1","Adv1",(3,2,3),(1,3,2),"P"),
 ("D2","Trail-granularity leakage","D2","Adv1","Adv1",(3,2,2),(1,3,2),"P"),
 ("D3","Issuer-linkage deanonymisation","D3a, D3b","Adv3","Adv3",(2,2,2),(1,3,2),"P"),
 ("E1","Cross-chain rule-propagation lag","E1","Adv2","Adv2",(3,2,2),(2,2,3),"P"),
 ("E2","Jurisdictional misclassification","E2","Adv2","Adv2",(3,3,2),(2,2,2),"P"),
 ("E3","Bridge identity discontinuity","E3a, E3b","Adv2","Adv2",(3,2,2),(2,2,2),"T"),
 ("E4","Cross-chain revocation lag","E4","Adv2","Adv2",(3,2,2),(1,2,3),"P"),
]
def rate(F,G,mit,floor_adv,floor=True,mitmap=None):
    L=band_sum(sum(F)); I=band_sum(sum(G)); pre=band_prod(L*I)
    Lr=max(1,L-REDUCE[mit])
    if floor and floor_adv in ANCHORS: Lr=max(Lr,2)
    return dict(L=L,I=I,pre=pre,Lr=Lr,res=band_prod(Lr*I),P=Lr*I)
def table():
    out=[]
    for sid,name,node,adv,fadv,F,G,mit in S:
        r=rate(F,G,mit,fadv); r.update(id=sid,name=name,node=node,adv=adv,F=F,G=G,mit=mit); out.append(r)
    return out

def sensitivity(rows=None, trials: int = 20000, seed: int = 2026) -> dict:
    rows = rows or table()
    base = {r["id"]: r["res"] for r in rows}
    no_floor = {s[0]: rate(s[5], s[6], s[7], s[4], floor=False)["res"] for s in S}
    floor_changes = [(k, LV[base[k]], LV[no_floor[k]]) for k in base if base[k] != no_floor[k]]
    e2 = next(x for x in S if x[0] == "E2")
    e2_x = rate(e2[5], e2[6], "X", e2[4])["res"]
    tot = chg = big = 0
    for sid, name, node, adv, fadv, F, G, mit in S:
        for k in range(6):
            for d in (-1, 1):
                f, g = list(F), list(G)
                arr, i = (f, k) if k < 3 else (g, k - 3)
                if not 1 <= arr[i] + d <= 3:
                    continue
                arr[i] += d
                res = rate(tuple(f), tuple(g), mit, fadv)["res"]
                tot += 1
                chg += res != base[sid]
                big += abs(res - base[sid]) >= 2
    rnd = random.Random(seed)
    low = le2 = anch = dsum = n = ge2 = 0
    for _ in range(trials):
        res = {}
        for sid, name, node, adv, fadv, F, G, mit in S:
            F2 = tuple(min(3, max(1, x + rnd.choice([-1, 0, 0, 1]))) for x in F)
            G2 = tuple(min(3, max(1, x + rnd.choice([-1, 0, 0, 1]))) for x in G)
            res[sid] = rate(F2, G2, mit, fadv)["res"]
            dd = abs(res[sid] - base[sid]); dsum += dd; n += 1; ge2 += dd >= 2
        low += res["A1/A2"] <= min(v for k, v in res.items() if k != "A1/A2")
        le2 += res["A1/A2"] <= 2
        anch += sum(res[k] >= 3 for k in ("A3", "B1", "B3", "C1")) >= 3
    return dict(floor_changes=floor_changes, e2_if_class_X=LV[e2_x], perturb_total=tot, perturb_changed=chg,
                perturb_two_bands=big, trials=trials, a1a2_lowest=low / trials, a1a2_le2=le2 / trials,
                anchors_ge3=anch / trials, mean_shift=dsum / n, share_ge2=ge2 / n)


def markdown_table(rows=None) -> str:
    rows = rows or table()
    out = ["| ID | Scenario | Node | Adv | L | I | Inherent | Mit. | L_res | Residual |",
           "|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        out.append(f"| {r['id']} | {r['name']} | {r['node']} | {r['adv']} | {r['L']} | {r['I']} | "
                   f"{LV[r['pre']]} | {r['mit']} | {r['Lr']} | **{LV[r['res']]}** |")
    return "\n".join(out)


def ranking(floor: bool = True) -> list[tuple[str, int, int]]:
    """Scenarios ordered by residual risk: (id, residual band 1-5, residual score L_res x I), highest first.
    Used to show how much of the paper's ranking depends on the trust-anchor floor (floor=False removes it)."""
    rows = []
    for sid, name, node, adv, fadv, F, G, mit in S:
        r = rate(F, G, mit, fadv, floor=floor)
        rows.append((sid, r["res"], r["P"]))
    return sorted(rows, key=lambda x: (-x[1], -x[2], x[0]))


def floor_dependence() -> dict:
    """Which conclusions survive without the trust-anchor floor? Compares both rankings."""
    with_f, without = ranking(True), ranking(False)
    pos = lambda rk: {sid: i for i, (sid, _, _) in enumerate(rk)}  # noqa: E731
    pw, po = pos(with_f), pos(without)
    return dict(with_floor=with_f, without_floor=without,
                band_changes=[(a[0], LV[a[1]], LV[b[1]]) for a, b in
                              zip(sorted(with_f), sorted(without)) if a[1] != b[1]],
                rank_shift={k: po[k] - pw[k] for k in pw if po[k] != pw[k]})
