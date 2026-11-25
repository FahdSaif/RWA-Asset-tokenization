"""Model-checked guard: mixed-cryptography states across bridged instances.

Setting. One anchor (an admin or issuer key) is accepted on several instances of a token (chains or rollups)
joined by bridges that accept the source instance's state as valid. Each instance migrates at its own effective
quarter E_c: before E_c it accepts the quantum-vulnerable signature, from E_c only the post-quantum one.

Claim of a plan. "Instance d is protected from E_d on."
Counterexample. After a CRQC arrives, an adversary forges the legacy signature on an instance c that still accepts it
(q < E_c), creates a forged position there (mint, unfreeze, forced transfer) and bridges it to d at a quarter
q >= E_d. Instance d then holds a forged-origin position although its own migration is complete. This extends the
authors' earlier finding (two individually correct instances joined by a bridge can violate compliance with no
adversary) to a migration in progress.

Bounded explicit-state search (breadth-first, like rwa_threatlab.modelcheck):
  state      (q, crqc_arrived, loc, f)   loc: instance holding a forged position (or None); f: quarter it was forged
  actions    tick (q + 1, up to the horizon); crqc (once); forge on c if crqc, q < E_c and no position yet;
             bridge loc -> d along an open bridge
  violation  a position forged at f >= E_d arrives at d through a bridge (d was already protected when it was
             forged: the plan's claim fails). Positions forged before E_d are ordinary pre-migration exposure,
             counted by the loss model, not a violation.
  bridge policy  "open"; or "pause_revalidate": a bridge is closed while exactly one end has migrated, and on
             reopening rejects positions forged after the destination migrated (costs bridge downtime)
This is a consistency check of plans in a stated abstraction, not a verification of any deployed system.
"""
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


def expand_instances(dep: Deployment, topology: dict[str, list[str]], value_split: dict[str, float] | None = None) -> Deployment:
    """Copy each anchor listed in ``topology`` into one anchor per instance ("<id>@<instance>"), split its value
    (equally unless ``value_split`` gives shares per instance) and connect the copies with bridges to the first
    (canonical) instance. Instances of one anchor share its issuer group and calendar."""
    anchors, bridges = [], []
    for a in dep.anchors:
        insts = topology.get(a.anchor_id)
        if not insts:
            anchors.append(a)
            continue
        shares = value_split or {c: 1 / len(insts) for c in insts}
        for c in insts:
            b = copy.deepcopy(a)
            b.anchor_id = f"{a.anchor_id}@{c}"
            b.instances = [c]
            b.value_usd = a.value_usd * shares[c]
            b.provenance = dict(a.provenance, instance=f"{c} (synthetic topology)", base_anchor=a.anchor_id)
            anchors.append(b)
        for c in insts[1:]:
            bridges.append(Bridge(anchor_id=a.anchor_id, a=f"{a.anchor_id}@{insts[0]}", b=f"{a.anchor_id}@{c}"))
    return Deployment(tokens=dep.tokens, anchors=anchors, bridges=bridges, source=dep.source + " + synthetic instance topology")


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
    """Plan, model-check every bridged component, couple the violating components (start together) and re-plan
    until no violation remains. Returns (plan, rounds, results of the final check, history)."""
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
    """Effective protection with bridges: an instance is protected only once every instance it is bridged to has
    migrated (forged positions can cross an open bridge). With ``pause_revalidate`` bridges its own quarter counts."""
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
    """Quarters during which some bridge is closed under ``pause_revalidate`` (mixed state)."""
    tot = 0
    for comp in components(dep).values():
        for a, b in comp["edges"]:
            ea = horizon if eff[a] is None else eff[a]
            eb = horizon if eff[b] is None else eff[b]
            tot += abs(ea - eb)
    return tot
