"""Comparison policies. Each returns a Plan (start quarter per anchor) under the same capacity limit as QAMP, so
differences come from what each policy knows and when it decides, not from extra resources.

  none            no migration (reference for value captured)
  asap_fifo       start every migration as early as capacity allows, in census order
  deadline        schedule backwards from NIST's deprecation date (2030), latest start that completes in time
  annual_review   decisions only at yearly review gates (Q1), in census order: governance by review frequency
  mosca           priority by Mosca's x + y (record shelf life + migration time), then as early as possible
  greedy_risk     priority by value at risk x attack weight, then as early as possible
  kg_score        priority by an adapted readiness score in the spirit of knowledge-graph PQ-readiness frameworks:
                  vulnerability x (1 + log(1 + tokens controlled)) x (1 + compliance capabilities) x log10(value);
                  an adaptation of the scoring idea, not a re-implementation of any published system
  oracle          knows the CRQC arrival and every deviation of the evaluated scenario (upper bound)

None of the list policies looks at renewal boundaries: that is the difference QAMP's planner is designed to test.
"""
from __future__ import annotations

import math

from .loss import LossParams, attack_weight, effective_quarter
from .model import Deployment
from .planner import Plan, PlanParams, date_to_quarter, solve
from .scenarios import ScenarioSet


class _Capacity:
    def __init__(self, pp: PlanParams):
        self.pp = pp
        self.use: dict[tuple[str, int], int] = {}

    def fits(self, group: str, t: int, d: int) -> bool:
        return all(self.use.get((group, q), 0) < self.pp.capacity for q in range(t, t + d))

    def take(self, group: str, t: int, d: int) -> None:
        for q in range(t, t + d):
            self.use[(group, q)] = self.use.get((group, q), 0) + 1


def _list_schedule(dep: Deployment, order: list[int], pp: PlanParams, gates=None, latest=None, method="") -> Plan:
    cap = _Capacity(pp)
    starts: dict[str, int | None] = {a.anchor_id: None for a in dep.anchors}
    for i in order:
        a = dep.anchors[i]
        d = max(1, a.migration_quarters)
        cand = list(range(0, pp.last_start + 1))
        if gates is not None:
            cand = [t for t in cand if t in gates]
        if latest is not None:
            lt = latest(a)
            before = [t for t in cand if t <= lt]
            cand = list(reversed(before)) + [t for t in cand if t > lt]
        for t in cand:
            if cap.fits(a.issuer_group, t, d):
                cap.take(a.issuer_group, t, d)
                starts[a.anchor_id] = t
                break
        if starts[a.anchor_id] is None:      # no capacity left in the horizon: last start, reported as a miss
            starts[a.anchor_id] = pp.last_start
    return Plan(starts=starts, method=method, status="list-scheduled")


def none(dep: Deployment, **_) -> Plan:
    return Plan(starts={a.anchor_id: None for a in dep.anchors}, method="none", status="no migration")


def asap_fifo(dep, pp: PlanParams = PlanParams(), **_) -> Plan:
    return _list_schedule(dep, list(range(len(dep.anchors))), pp, method="asap_fifo")


def deadline(dep, pp: PlanParams = PlanParams(), deprecation_iso: str = "2030-12-31", **_) -> Plan:
    dq = date_to_quarter(deprecation_iso) + 1
    latest = lambda a: dq - max(1, a.migration_quarters) - a.timelock_quarters  # noqa: E731
    return _list_schedule(dep, list(range(len(dep.anchors))), pp, latest=latest, method="deadline")


def annual_review(dep, pp: PlanParams = PlanParams(), **_) -> Plan:
    gates = set(range(0, pp.last_start + 1, 4))
    return _list_schedule(dep, list(range(len(dep.anchors))), pp, gates=gates, method="annual_review")


def mosca(dep, ctx: dict, pp: PlanParams = PlanParams(), **_) -> Plan:
    key = lambda i: -(4 * ctx[dep.anchors[i].anchor_id]["retention_years"] + dep.anchors[i].migration_quarters)  # noqa: E731
    return _list_schedule(dep, sorted(range(len(dep.anchors)), key=key), pp, method="mosca")


def greedy_risk(dep, lp: LossParams = LossParams(), pp: PlanParams = PlanParams(), **_) -> Plan:
    key = lambda i: -(dep.anchors[i].value_usd * attack_weight(dep.anchors[i], lp))  # noqa: E731
    return _list_schedule(dep, sorted(range(len(dep.anchors)), key=key), pp, method="greedy_risk")


def kg_score(dep, pp: PlanParams = PlanParams(), **_) -> Plan:
    def score(a) -> float:
        comp = sum(c in a.capabilities for c in ("freeze_blacklist", "forced_transfer_recovery", "pause"))
        return (1.0 if a.quantum_vulnerable else 0.0) * (1 + math.log(1 + len(a.tokens))) * (1 + comp) * math.log10(max(a.value_usd, 10))
    return _list_schedule(dep, sorted(range(len(dep.anchors)), key=lambda i: -score(dep.anchors[i])), pp, method="kg_score")


def oracle(dep, ctx: dict, crqc_q: float, deltas, lp: LossParams, pp: PlanParams) -> Plan:
    """Deterministic MILP with the scenario's true arrival and deviations (an upper bound no policy can reach)."""
    import numpy as np
    from .loss import anchor_loss
    from .planner import spend
    n, T = len(dep.anchors), pp.last_start + 1
    C = np.zeros((n, T))
    F = np.ones((n, T), dtype=bool)
    for i, a in enumerate(dep.anchors):
        ret = ctx[a.anchor_id]["retention_years"]
        hard_q = ctx[a.anchor_id]["hard_q"]
        for t in range(T):
            E = effective_quarter(a, t, int(deltas[i]))
            if hard_q is not None and E > hard_q:
                F[i, t] = False
            C[i, t] = anchor_loss(a, E, crqc_q, ret, lp) + spend(a, t, pp)
    return solve(dep, C, F, pp, method="oracle")


LIST_BASELINES = dict(asap_fifo=asap_fifo, deadline=deadline, annual_review=annual_review, mosca=mosca,
                      greedy_risk=greedy_risk, kg_score=kg_score)
