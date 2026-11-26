"""Checks bridged chains during a migration.

If one chain has migrated but a bridged chain has not, an attacker with a quantum computer can
forge on the old chain and bridge the result to the new one. The check searches all steps for
this case and returns the path if it finds one.

Bridge options: open, or pause_revalidate (close the bridge until both sides have migrated).
It checks a simple model of a plan, not real systems."""
from __future__ import annotations

import copy
from collections import deque
from dataclasses import dataclass

from . import config
from .loss import effective_quarter
from .model import Anchor, Bridge, Deployment


@dataclass
class GuardResult:
    anchor_id: str
    violation: bool
    trace: list[str] | None
    states: int
    effective: dict[str, int | None]


def check_component(anchor_id: str, effective: dict[str, int | None], bridges: list[tuple[str, str]],
                    horizon: int = config.HORIZON_QUARTERS, bridge_policy: str = "open") -> GuardResult:
    inst = sorted(effective)
    E = {c: (horizon + 1 if effective[c] is None else effective[c]) for c in inst}
    adj = {c: set() for c in inst}
    for a, b in bridges:
        adj[a].add(b)
        adj[b].add(a)

    def can_bridge(c: str, d: str, q: int, f: int) -> bool:
        if bridge_policy == "pause_revalidate":
            return (q >= E[c]) == (q >= E[d]) and f < E[d]
        return True

    s0 = (0, False, None, -1)
    seen = {s0: None}
    dq = deque([s0])
    while dq:
        s = dq.popleft()
        q, crqc, loc, f = s
        if loc is not None and loc.startswith("!"):
            trace = []
            while seen[s] is not None:
                s, act = seen[s]
                trace.append(act)
            return GuardResult(anchor_id, True, list(reversed(trace)), len(seen), dict(effective))
        nxt = []
        if q < horizon:
            nxt.append((f"tick->{config.quarter_label(q + 1)}", (q + 1, crqc, loc, f)))
        if not crqc:
            nxt.append((f"crqc@{config.quarter_label(q)}", (q, True, loc, f)))
        if crqc and loc is None:
            for c in inst:
                if q < E[c]:
                    nxt.append((f"forge@{c}@{config.quarter_label(q)}", (q, crqc, c, q)))
        if loc is not None:
            for d in adj[loc]:
                if can_bridge(loc, d, q, f):
                    bad = f >= E[d]
                    nxt.append((f"bridge {loc}->{d}@{config.quarter_label(q)}", (q, crqc, ("!" + d) if bad else d, f)))
        for act, ns in nxt:
            if ns not in seen:
                seen[ns] = (s, act)
                dq.append(ns)
    return GuardResult(anchor_id, False, None, len(seen), dict(effective))


def expand_instances(dep: Deployment, topology: dict, value_split: dict[str, float] | None = None,
                     label: str = "synthetic topology") -> Deployment:
    """Makes one anchor per chain and joins them with bridges."""
    anchors, bridges = [], []
    for a in dep.anchors:
        insts = topology.get(a.anchor_id)
        if not insts:
            anchors.append(a)
            continue
        if isinstance(insts, dict):
            shares = dict(insts)
            insts = sorted(insts, key=lambda c: (c != "ethereum", c))
        else:
            shares = value_split or {c: 1 / len(insts) for c in insts}
        for c in insts:
            b = copy.deepcopy(a)
            b.anchor_id = f"{a.anchor_id}@{c}"
            b.instances = [c]
            b.value_usd = a.value_usd * shares[c]
            b.provenance = dict(a.provenance, instance=f"{c} ({label})", base_anchor=a.anchor_id)
            anchors.append(b)
        for c in insts[1:]:
            bridges.append(Bridge(anchor_id=a.anchor_id, a=f"{a.anchor_id}@{insts[0]}", b=f"{a.anchor_id}@{c}"))
    return Deployment(tokens=dep.tokens, anchors=anchors, bridges=bridges, source=dep.source + f" + {label}",
                      group_capacity=dict(dep.group_capacity))


def components(dep: Deployment) -> dict[str, dict]:
    comps: dict[str, dict] = {}
    for br in dep.bridges:
        c = comps.setdefault(br.anchor_id, dict(members=set(), edges=[]))
        c["members"].update([br.a, br.b])
        c["edges"].append((br.a, br.b))
    return comps


def check_plan(dep: Deployment, starts: dict[str, int | None], bridge_policy: str = "open", delta: int = 0) -> list[GuardResult]:
    out = []
    for base, comp in components(dep).items():
        eff = {m: effective_quarter(dep.anchor(m), starts.get(m), delta) for m in comp["members"]}
        out.append(check_component(base, eff, comp["edges"], bridge_policy=bridge_policy))
    return out


def guarded_plan(dep: Deployment, plan_fn, max_rounds: int = 5, bridge_policy: str = "open"):
    """Plans, checks, makes bridged copies start together if needed, and plans again."""
    coupling: list[list[str]] = []
    history = []
    for r in range(max_rounds):
        p = plan_fn(coupling)
        res = check_plan(dep, p.starts, bridge_policy)
        bad = [g for g in res if g.violation]
        history.append(dict(round=r, violations=len(bad), coupled=len(coupling)))
        if not bad:
            p.info.update(guard_rounds=r + 1, coupling=coupling)
            return p, r + 1, res, history
        comps = components(dep)
        for g in bad:
            grp = sorted(comps[g.anchor_id]["members"])
            if grp not in coupling:
                coupling.append(grp)
    p.info.update(guard_rounds=max_rounds, coupling=coupling, guard_unresolved=True)
    return p, max_rounds, res, history


def true_effective(dep: Deployment, eff: dict[str, int | None], bridge_policy: str = "open") -> dict[str, int | None]:
    """When each copy is really protected: only once every bridged copy has migrated."""
    if bridge_policy == "pause_revalidate":
        return dict(eff)
    out = dict(eff)
    for comp in components(dep).values():
        vals = [eff[m] for m in comp["members"]]
        worst = None if any(v is None for v in vals) else max(vals)
        for m in comp["members"]:
            out[m] = worst
    return out


def bridge_downtime(dep: Deployment, eff: dict[str, int | None], horizon: int = config.HORIZON_QUARTERS) -> int:
    """Quarters a bridge is closed under pause_revalidate."""
    tot = 0
    for comp in components(dep).values():
        for a, b in comp["edges"]:
            ea = horizon if eff[a] is None else eff[a]
            eb = horizon if eff[b] is None else eff[b]
            tot += abs(ea - eb)
    return tot
