"""Scaled version of the composition / lag checks of ``modelcheck.py``: k chains and n participants.

Why: the original model has two chains and four participants (at most 34 reachable states), so "exhaustive"
holds only inside a very small abstraction. This module re-expresses the *same* transition relation for any
number of chains k >= 2 and participants n >= 4, so the composition and lag claims (paper Table 6a) can be
checked on larger instances and over many eligibility assignments. At k = 2, n = 4 it reproduces the original
verdicts (see tests/test_modelcheck_scaled.py).

Semantics (identical to modelcheck.py, generalised)
  state      (loc, holder, truth, store, law_done, activated, bad)
  truth[c][p] legally correct eligibility of p on chain c;  store[c][p] what chain c's Gateway consults.
  user xfer  on the current chain to r != holder when store[loc][r] == 1
  bridge     loc -> any other chain d, to r, when store[loc][r] == 1 and, if dest_mediation, store[d][r] == 1
  law        participant 0 ("u") loses eligibility on every chain (sanction or revocation), once
  activate   the change reaches chain c's store, one chain per step
             immediate_at_origin: chain 0 is activated in the law step itself (tightening is immediate there)
             atomic: every chain is activated in the law step (an assumption, not a mitigation)
  violation  the asset is placed with a holder whose truth on that chain is 0
This is a consistency check of the analysis in a stated abstraction, not a verification of any system.
"""
from __future__ import annotations

import random
from collections import deque

U = 0  # participant 0 is the one who loses eligibility


def paper_eligibility(k: int, n: int) -> list[list[int]]:
    """elig[c][p]. Participants 0..3 are the paper's u, x, w, z; extras use a fixed deterministic pattern."""
    def e(c: int, p: int) -> int:
        if p == 0 or p == 2:
            return 1                      # u, w: eligible everywhere
        if p == 1:
            return 1 if c == 0 else 0      # x: eligible only on the origin chain
        if p == 3:
            return 0                      # z: eligible nowhere
        return 1 if (p * 7 + c * 3) % 5 < 3 else 0
    return [[e(c, p) for p in range(n)] for c in range(k)]


def random_eligibility(k: int, n: int, rnd: random.Random) -> list[list[int]]:
    el = [[rnd.randint(0, 1) for _ in range(n)] for _ in range(k)]
    for c in range(k):
        el[c][U] = 1                       # participant 0 starts eligible everywhere and holds the asset
    return el


def search(elig, *, dest_mediation=False, law=False, immediate_at_origin=False, atomic=False,
           bridge=True, start=0):
    k, n = len(elig), len(elig[0])
    truth = tuple(tuple(r) for r in elig)
    s0 = (start, U, truth, truth, 0, (0,) * k, 0)
    seen = {s0: None}
    q = deque([s0])
    while q:
        s = q.popleft()
        loc, h, tr, st, law_done, act, bad = s
        if bad:
            trace = []
            while seen[s] is not None:
                s, a = seen[s]
                trace.append(a)
            return list(reversed(trace)), len(seen)
        nxt = []
        for r in range(n):
            if r != h and st[loc][r]:
                nxt.append((f"xfer(c{loc},p{r})", (loc, r, tr, st, law_done, act, int(tr[loc][r] == 0))))
            if bridge:
                for d in range(k):
                    if d == loc or not st[loc][r]:
                        continue
                    if dest_mediation and not st[d][r]:
                        continue
                    nxt.append((f"bridge(c{loc}->c{d},p{r})", (d, r, tr, st, law_done, act, int(tr[d][r] == 0))))
        if law and not law_done:
            ntr = tuple(tuple(0 if p == U else v for p, v in enumerate(row)) for row in tr)
            nst, nact = st, act
            if atomic:
                nst, nact = ntr, (1,) * k
            elif immediate_at_origin:
                nst = tuple(tuple(0 if (c == 0 and p == U) else v for p, v in enumerate(row)) for c, row in enumerate(st))
                nact = (1,) + act[1:]
            nxt.append(("law_change", (loc, h, ntr, nst, 1, nact, 0)))
        if law and law_done:
            for c in range(k):
                if not act[c]:
                    nst = tuple(tuple(0 if (cc == c and p == U) else v for p, v in enumerate(row)) for cc, row in enumerate(st))
                    nact = act[:c] + (1,) + act[c + 1:]
                    nxt.append((f"activate(c{c})", (loc, h, tr, nst, law_done, nact, 0)))
        for a, ns in nxt:
            if ns not in seen:
                seen[ns] = (s, a)
                q.append(ns)
    return None, len(seen)


CHECKS = {
    "alone": lambda el, c: search(el, bridge=False, start=c),
    "bridge_baseline": lambda el, c: search(el),
    "bridge_dest_mediated": lambda el, c: search(el, dest_mediation=True),
    "lag_single_instance": lambda el, c: search(el, bridge=False, law=True),
    "lag_origin_only": lambda el, c: search(el, dest_mediation=True, law=True, immediate_at_origin=True),
    "lag_atomic": lambda el, c: search(el, dest_mediation=True, law=True, atomic=True),
}


def run_on(elig) -> dict:
    out = {}
    for name, f in CHECKS.items():
        if name == "alone":
            res = [f(elig, c) for c in range(len(elig))]
            out[name] = dict(violation=any(t for t, _ in res), states=max(n for _, n in res))
        else:
            t, n = f(elig, 0)
            out[name] = dict(violation=t is not None, states=n, trace_len=len(t) if t else None)
    return out


def sweep(ks=(2, 3, 4, 5), ns=(4, 6, 8), random_instances: int = 25, seed: int = 7) -> dict:
    """Paper-pattern instance plus random eligibility assignments for each (k, n)."""
    rows, rnd = [], random.Random(seed)
    for k in ks:
        for n in ns:
            insts = [("paper", paper_eligibility(k, n))] + [("random", random_eligibility(k, n, rnd)) for _ in range(random_instances)]
            agg = {name: dict(violating=0, max_states=0) for name in CHECKS}
            for _, el in insts:
                r = run_on(el)
                for name, v in r.items():
                    agg[name]["violating"] += bool(v["violation"])
                    agg[name]["max_states"] = max(agg[name]["max_states"], v["states"])
            rows.append(dict(chains=k, participants=n, instances=len(insts), checks=agg,
                             paper_pattern=run_on(paper_eligibility(k, n))))
    return dict(rows=rows, seed=seed)


SAFE_CLAIMS = ("alone", "bridge_dest_mediated", "lag_atomic", "lag_single_instance_with_tightening_note")


def markdown(res: dict) -> str:
    hdr = "| k chains | n participants | instances | max states | alone | bridge baseline | bridge + dest mediation | lag, origin-only tightening | lag, atomic |"
    out = [hdr, "|---|---|---|---|---|---|---|---|---|"]
    for r in res["rows"]:
        c = r["checks"]
        ms = max(v["max_states"] for v in c.values())
        f = lambda n: f"{c[n]['violating']}/{r['instances']}"  # noqa: E731
        out.append(f"| {r['chains']} | {r['participants']} | {r['instances']} | {ms} | {f('alone')} | {f('bridge_baseline')} | "
                   f"{f('bridge_dest_mediated')} | {f('lag_origin_only')} | {f('lag_atomic')} |")
    return "\n".join(out)
