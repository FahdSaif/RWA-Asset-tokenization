"""Chooses a start quarter for each anchor's migration (MILP, HiGHS solver).

A migration only counts from the anchor's next renewal date, so a late start can cost a full period.
Goal: lowest expected loss plus migration cost.
Limits: one start each; NIST deadline; migrations at once per issuer; some anchors start together.
Modes: stochastic (uses the delay odds), expected (no delay), pessimistic (adds a margin)."""
from __future__ import annotations

import datetime as dt
from dataclasses import asdict, dataclass, field

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp
from scipy.sparse import lil_matrix

from . import config
from .kb.engine import KnowledgeBase, anchor_facts
from .loss import LossParams, anchor_loss, effective_quarter
from .model import Deployment
from .scenarios import ScenarioSet


@dataclass(frozen=True)
class PlanParams:
    capacity: int = 2
    cost_unit_usd: float = 1.0e6
    cost_decline_per_year: float = 0.10
    margin: int = 1
    last_start: int = config.PLAN_LAST_QUARTER
    time_limit_s: float = 60.0

    def as_dict(self) -> dict:
        return asdict(self)


@dataclass
class Plan:
    starts: dict[str, int | None]
    method: str
    objective: float | None = None
    status: str = ""
    info: dict = field(default_factory=dict)


def date_to_quarter(iso: str) -> int:
    d = dt.date.fromisoformat(iso)
    return (d.year - config.START_YEAR) * 4 + (d.month - 1) // 3


def kb_context(dep: Deployment, kb: KnowledgeBase, jurisdictions=("US", "EU")) -> dict[str, dict]:
    """Rule results, hard deadline and retention years for each anchor."""
    out = {}
    for a in dep.anchors:
        inf = kb.infer(anchor_facts(a, jurisdictions))
        c = inf.conclusions
        hard = c.get("deadline_hard")
        # must take effect by 2036 Q1
        hard_q = date_to_quarter(hard) + 1 if hard else None
        out[a.anchor_id] = dict(inference=inf, hard_q=hard_q, retention_years=float(c.get("retention_years", 0)))
    return out


def spend(anchor, t: int, pp: PlanParams) -> float:
    return pp.cost_unit_usd * anchor.migration_cost * (1 - pp.cost_decline_per_year) ** (t / 4)


def expected_cost_matrix(dep: Deployment, ctx: dict, ss: ScenarioSet, lp: LossParams, pp: PlanParams,
                         mode: str = "stochastic") -> tuple[np.ndarray, np.ndarray]:
    """Expected cost of each start quarter for each anchor, and which starts meet the deadline."""
    """Expectations: the deviation is independent of the CRQC arrival, so the expected loss is
    sum_delta P(delta) * mean over the planning sample of arrivals (mode "stochastic"); "expected" and
    "pessimistic" use a single deviation (0 or +margin). The sample of arrivals should be large (default 20,000):
    losses are dominated by rare early arrivals."""
    from .loss import anchor_loss_vec
    from .scenarios import DELTA_PROBS, DELTA_VALUES
    n, T = len(dep.anchors), pp.last_start + 1
    C = np.zeros((n, T))
    F = np.ones((n, T), dtype=bool)
    crqc = ss.crqc_quarter
    probs = ss.params.get("delta_probs", DELTA_PROBS)
    if mode == "stochastic":
        dist = list(zip(DELTA_VALUES.tolist(), probs))
    else:
        dist = [(pp.margin if mode == "pessimistic" else 0, 1.0)]
    for i, a in enumerate(dep.anchors):
        ret = ctx[a.anchor_id]["retention_years"]
        hard_q = ctx[a.anchor_id]["hard_q"]
        memo: dict[int | None, float] = {}
        for t in range(T):
            planned_E = effective_quarter(a, t, 0, pp.margin if mode == "pessimistic" else 0)
            if hard_q is not None and planned_E > hard_q:
                F[i, t] = False
            exp_loss = 0.0
            for d, pr in dist:
                E = effective_quarter(a, t, int(d))
                if E not in memo:
                    memo[E] = float(np.mean(anchor_loss_vec(a, E, crqc, ret, lp)))
                exp_loss += pr * memo[E]
            C[i, t] = exp_loss + spend(a, t, pp)
    return C, F


def solve(dep: Deployment, C: np.ndarray, F: np.ndarray, pp: PlanParams, coupling: list[list[str]] | None = None,
          method: str = "qamp", priority: str = "compliance") -> Plan:
    """Chooses one start quarter per anchor.

    priority "compliance" (default): first the fewest deadline misses, then the lowest expected cost.
    priority "cost": first the lowest expected cost, then the fewest misses at that cost.
    An anchor that does not fit within its issuer's capacity can take an "overflow" start: the last quarter,
    outside the capacity limit, counted as a miss. The list baselines do the same, so the comparison is fair.
    The deadline is therefore soft: the plan always exists, and misses are reported."""
    n, T = C.shape
    idx = lambda i, t: i * T + t  # noqa: E731
    ov = lambda i: n * T + i      # noqa: E731  overflow variable of anchor i
    nv = n * T + n
    miss = np.concatenate([(~F).astype(float).flatten(), np.ones(n)])
    cost = np.concatenate([C.flatten(), C[:, T - 1]])
    rows, lo, hi = [], [], []

    def add(row: dict[int, float], l: float, h: float):
        rows.append(row)
        lo.append(l)
        hi.append(h)

    for i in range(n):
        row = {idx(i, t): 1.0 for t in range(T)}
        row[ov(i)] = 1.0
        add(row, 1, 1)
    groups: dict[str, list[int]] = {}
    for i, a in enumerate(dep.anchors):
        groups.setdefault(a.issuer_group, []).append(i)
    for g, members in groups.items():
        cap = int(dep.group_capacity.get(g, pp.capacity))
        for tau in range(T + 4):
            row = {}
            for i in members:
                d = max(1, dep.anchors[i].migration_quarters)
                for t in range(max(0, tau - d + 1), min(T, tau + 1)):
                    row[idx(i, t)] = 1.0
            if len(row) > cap:
                add(row, 0, cap)
    pos = {a.anchor_id: i for i, a in enumerate(dep.anchors)}
    for grp in coupling or []:
        ids = [pos[x] for x in grp if x in pos]
        for j in ids[1:]:
            for t in range(T):
                add({idx(ids[0], t): 1.0, idx(j, t): -1.0}, 0, 0)
            add({ov(ids[0]): 1.0, ov(j): -1.0}, 0, 0)

    def run(obj: np.ndarray, extra: tuple | None):
        rr, ll, hh = list(rows), list(lo), list(hi)
        if extra is not None:
            rr.append({k: v for k, v in enumerate(extra[0]) if v}), ll.append(-np.inf), hh.append(extra[1])
        A = lil_matrix((len(rr), nv))
        for r, row in enumerate(rr):
            for k, v in row.items():
                A[r, k] = v
        return milp(c=obj, constraints=LinearConstraint(A.tocsr(), ll, hh), integrality=np.ones(nv),
                    bounds=Bounds(np.zeros(nv), np.ones(nv)), options=dict(time_limit=pp.time_limit_s, disp=False))

    first, second = (miss, cost) if priority == "compliance" else (cost, miss)
    r1 = run(first, None)
    if r1.x is None:
        raise RuntimeError(f"{method}: planning failed in step 1: {r1.message}")
    bound = r1.fun + 0.5 if priority == "compliance" else r1.fun + max(1.0, 1e-9 * abs(r1.fun))
    res = run(second, (first, bound))                     # step 2: best second goal without losing the first
    if res.x is None:
        raise RuntimeError(f"{method}: planning failed in step 2: {res.message}")
    x = np.round(res.x)
    m_star = int(round(float(miss @ x)))
    starts, overflow = {}, []
    for i, a in enumerate(dep.anchors):
        if x[ov(i)] > 0.5:
            starts[a.anchor_id] = T - 1
            overflow.append(a.anchor_id)
        else:
            starts[a.anchor_id] = int(np.argmax(x[i * T:(i + 1) * T]))
    info = dict(n_vars=nv, n_constraints=len(rows), mip_gap=getattr(res, "mip_gap", None), priority=priority,
                planned_misses=m_star, planned_cost=float(cost @ x),
                overflow=overflow, diagnosis=diagnose(dep, pp, T))
    return Plan(starts=starts, method=method, objective=float(res.fun), status=res.message, info=info)


def diagnose(dep: Deployment, pp: PlanParams, T: int) -> list[dict]:
    """Issuer groups that cannot finish all migrations in time, even with perfect scheduling.

    Needed: sum of migration times. Available: capacity x quarters in the planning window."""
    need: dict[str, int] = {}
    for a in dep.anchors:
        need[a.issuer_group] = need.get(a.issuer_group, 0) + max(1, a.migration_quarters)
    out = []
    for g, k in sorted(need.items()):
        cap = int(dep.group_capacity.get(g, pp.capacity))
        avail = cap * T
        if k > avail:
            out.append(dict(issuer_group=g, slots_needed=k, slots_available=avail, capacity=cap, quarters=T))
    return out


def plan(dep: Deployment, kb: KnowledgeBase, ss: ScenarioSet, lp: LossParams = LossParams(),
         pp: PlanParams = PlanParams(), mode: str = "stochastic", coupling=None, ctx=None,
         priority: str = "compliance") -> Plan:
    ctx = ctx or kb_context(dep, kb)
    C, F = expected_cost_matrix(dep, ctx, ss, lp, pp, mode)
    p = solve(dep, C, F, pp, coupling, method=f"qamp_{mode}", priority=priority)
    p.info.update(mode=mode, planning_scenarios=len(ss), planning_seed=ss.seed)
    return p
