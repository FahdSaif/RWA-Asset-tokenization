"""Runs the experiments.

Plans are made on one set of scenarios and scored on a different set.
Development seeds are for trying out; held-out seeds are only for the pre-registered run.

Cost of a plan in a scenario = losses + migration spending.
Reported: mean cost with 95% interval, share of the best possible saving, share protected by 2030 and 2032,
missed deadlines, and paired tests against QAMP (sign-flip test on the mean, Holm correction)."""
from __future__ import annotations

import copy
import json
import platform
import time
from dataclasses import dataclass, field

import numpy as np
import scipy
from scipy import stats

from . import baselines, config, guard, planner, scenarios
from .kb.engine import KnowledgeBase
from .loss import LossParams, anchor_loss, effective_quarter
from .model import Calendar, Deployment
from .planner import Plan, PlanParams


# --- scoring

def realized_costs(dep: Deployment, ctx: dict, plan: Plan, ss: scenarios.ScenarioSet, lp: LossParams,
                   pp: PlanParams, bridge_policy: str = "open") -> np.ndarray:
    out = np.zeros(len(ss))
    spend_total = sum(planner.spend(a, plan.starts[a.anchor_id], pp) for a in dep.anchors if plan.starts[a.anchor_id] is not None)
    for s in range(len(ss)):
        eff = {a.anchor_id: effective_quarter(a, plan.starts[a.anchor_id], int(ss.delta[s, i])) for i, a in enumerate(dep.anchors)}
        if dep.bridges:
            eff = guard.true_effective(dep, eff, bridge_policy)
        tot = spend_total
        for a in dep.anchors:
            tot += anchor_loss(a, eff[a.anchor_id], float(ss.crqc_quarter[s]), ctx[a.anchor_id]["retention_years"], lp)
        out[s] = tot
    return out


def protected_share(dep: Deployment, plan: Plan, by_quarter: int, ss: scenarios.ScenarioSet | None = None) -> float:
    """Share of value whose migration takes effect by a given quarter."""
    tot = sum(a.value_usd for a in dep.anchors if a.quantum_vulnerable)
    if tot == 0:
        return 1.0
    if ss is None:
        ok = sum(a.value_usd for a in dep.anchors
                 if (e := effective_quarter(a, plan.starts[a.anchor_id])) is not None and e <= by_quarter)
        return ok / tot
    vals = []
    for s in range(len(ss)):
        ok = sum(a.value_usd for i, a in enumerate(dep.anchors)
                 if (e := effective_quarter(a, plan.starts[a.anchor_id], int(ss.delta[s, i]))) is not None and e <= by_quarter)
        vals.append(ok / tot)
    return float(np.mean(vals))


def deadline_misses(dep: Deployment, ctx: dict, plan: Plan, ss: scenarios.ScenarioSet) -> float:
    m = []
    for s in range(len(ss)):
        k = 0
        for i, a in enumerate(dep.anchors):
            hq = ctx[a.anchor_id]["hard_q"]
            e = effective_quarter(a, plan.starts[a.anchor_id], int(ss.delta[s, i]))
            if hq is not None and a.quantum_vulnerable and (e is None or e > hq):
                k += 1
        m.append(k)
    return float(np.mean(m))


def bootstrap_ci(x: np.ndarray, n: int = 2000, seed: int = 0) -> tuple[float, float]:
    rng = np.random.default_rng(seed)
    means = rng.choice(x, size=(n, len(x)), replace=True).mean(axis=1)
    return float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))


def sign_flip_test(d: np.ndarray, n_perm: int = 20_000, seed: int = 0) -> float:
    """Paired test that the mean difference is zero. Uses the mean because losses have rare large values."""
    d = np.asarray(d, dtype=float)
    if np.allclose(d, 0):
        return 1.0
    rng = np.random.default_rng(seed)
    obs = abs(d.mean())
    hits = 0
    for chunk in range(0, n_perm, 2_000):
        b = min(2_000, n_perm - chunk)
        signs = rng.choice((-1.0, 1.0), size=(b, len(d)))
        hits += int(np.sum(np.abs(signs @ d) / len(d) >= obs - 1e-12))
    return (hits + 1) / (n_perm + 1)


def paired_tests(ref: np.ndarray, others: dict[str, np.ndarray]) -> dict[str, dict]:
    """Mean difference, 95% interval and p-values for each policy against the reference."""
    raw = {}
    for k, v in others.items():
        d = np.asarray(v) - np.asarray(ref)
        if np.allclose(d, 0):
            raw[k] = dict(p=1.0, p_wilcoxon=1.0, median_diff=0.0, mean_diff=0.0, mean_diff_ci95=(0.0, 0.0), n_nonzero=0)
            continue
        w = stats.wilcoxon(v, ref, zero_method="wilcox", alternative="two-sided")
        raw[k] = dict(p=sign_flip_test(d), p_wilcoxon=float(w.pvalue), median_diff=float(np.median(d)),
                      mean_diff=float(np.mean(d)), mean_diff_ci95=bootstrap_ci(d), n_nonzero=int(np.sum(~np.isclose(d, 0))))
    order = sorted(raw, key=lambda k: raw[k]["p"])
    m, running = len(order), 0.0
    for j, k in enumerate(order):
        running = max(running, min(1.0, (m - j) * raw[k]["p"]))
        raw[k]["p_holm"] = running
    return raw


# --- variants for ablations

def with_calendar_period(dep: Deployment, period: int) -> Deployment:
    d = copy.deepcopy(dep)
    for a in d.anchors:
        a.calendar = Calendar(period=period, phase=a.calendar.phase % max(period, 1), source=f"{a.calendar.source}; period set to {period}")
    return d


def ctx_without_kb(ctx: dict) -> dict:
    return {k: dict(v, hard_q=None, retention_years=0.0) for k, v in ctx.items()}


# --- main experiment

@dataclass
class RunConfig:
    n_plan: int = 20_000
    n_eval: int = 2_000
    n_oracle: int = 200          # oracle is slow: score it on the first n_oracle scenarios
    seed_base: int = config.DEV_SEED_BASE
    shift_years: float = 0.0
    oracle: bool = True
    lp: LossParams = field(default_factory=LossParams)
    pp: PlanParams = field(default_factory=PlanParams)

    def as_dict(self) -> dict:
        return dict(n_plan=self.n_plan, n_eval=self.n_eval, n_oracle=self.n_oracle, seed_base=self.seed_base, shift_years=self.shift_years,
                    oracle=self.oracle, loss=self.lp.as_dict(), plan=self.pp.as_dict())


def run_policies(dep: Deployment, kb: KnowledgeBase, rc: RunConfig, ctx: dict | None = None,
                 include=("qamp_stochastic", "qamp_expected", "qamp_pessimistic", "qamp_no_windows", "qamp_no_kb",
                          "asap_fifo", "deadline", "annual_review", "mosca", "greedy_risk", "kg_score", "none")) -> dict:
    ctx = ctx or planner.kb_context(dep, kb)
    n = len(dep.anchors)
    ss_plan = scenarios.sample(rc.n_plan, n, seed=rc.seed_base + 1, shift_years=rc.shift_years)
    ss_eval = scenarios.sample(rc.n_eval, n, seed=rc.seed_base + 2, shift_years=rc.shift_years)
    plans: dict[str, Plan] = {}
    t0 = time.time()
    for name in include:
        if name.startswith("qamp_") and name not in ("qamp_no_windows", "qamp_no_kb"):
            plans[name] = planner.plan(dep, kb, ss_plan, rc.lp, rc.pp, mode=name.split("_", 1)[1], ctx=ctx)
        elif name == "qamp_no_windows":
            d1 = with_calendar_period(dep, 1)            # plan as if every quarter were a renewal date
            p = planner.plan(d1, kb, ss_plan, rc.lp, rc.pp, mode="stochastic", ctx=ctx)
            p.method = name
            plans[name] = p
        elif name == "qamp_no_kb":
            p = planner.plan(dep, kb, ss_plan, rc.lp, rc.pp, mode="stochastic", ctx=ctx_without_kb(ctx))
            p.method = name
            plans[name] = p
        elif name == "none":
            plans[name] = baselines.none(dep)
        else:
            plans[name] = baselines.LIST_BASELINES[name](dep, ctx=ctx, lp=rc.lp, pp=rc.pp)
    costs = {k: realized_costs(dep, ctx, p, ss_eval, rc.lp, rc.pp) for k, p in plans.items()}
    if rc.oracle:
        no = min(rc.n_oracle, len(ss_eval))
        oc = np.zeros(no)
        for s in range(no):
            op = baselines.oracle(dep, ctx, float(ss_eval.crqc_quarter[s]), ss_eval.delta[s], rc.lp, rc.pp)
            one = scenarios.ScenarioSet(ss_eval.crqc_quarter[s:s + 1], ss_eval.delta[s:s + 1], ss_eval.seed)
            oc[s] = realized_costs(dep, ctx, op, one, rc.lp, rc.pp)[0]
        costs["oracle"] = oc
    q2030, q2032 = config.year_end_quarter(2030), config.year_end_quarter(2032)
    summary = {}
    no = len(costs["oracle"]) if "oracle" in costs else 0
    L_none = costs["none"][:no].mean() if ("none" in costs and no) else None
    L_or = costs["oracle"].mean() if no else None
    for k, v in costs.items():
        row = dict(mean=float(v.mean()), ci95=bootstrap_ci(v), median=float(np.median(v)), n=len(v))
        if no:
            row["mean_oracle_subset"] = float(v[:no].mean())
        if L_none is not None and L_or is not None and L_none > L_or:
            # same scenarios for every policy
            row["value_captured"] = float((L_none - v[:no].mean()) / (L_none - L_or))
        if k in plans:
            row["protected_by_2030"] = protected_share(dep, plans[k], q2030 + 1, ss_eval)
            row["protected_by_2032"] = protected_share(dep, plans[k], q2032 + 1, ss_eval)
            row["deadline_misses"] = deadline_misses(dep, ctx, plans[k], ss_eval)
        summary[k] = row
    ref = "qamp_stochastic"
    tests = paired_tests(costs[ref], {k: v for k, v in costs.items() if k not in (ref, "oracle")}) if ref in costs else {}
    if no:
        tests["oracle_subset"] = paired_tests(costs[ref][:no], {"oracle": costs["oracle"]})["oracle"]
    return dict(summary=summary, tests=tests, costs={k: v.tolist() for k, v in costs.items()},
                plans={k: dict(starts=p.starts, status=p.status, info=_jsonable(p.info)) for k, p in plans.items()},
                crqc_by_year=scenarios.cumulative_probability_by_year(ss_eval),
                scenario_params=ss_eval.params, runtime_s=time.time() - t0, run_config=rc.as_dict(), env=environment())


def run_guard(dep: Deployment, kb: KnowledgeBase, rc: RunConfig, top_k: int = 6,
              instances=("ethereum", "l2"), split=(0.7, 0.3), topology: str = "auto") -> dict:
    """RQ3: bridged chains during a migration.

    Uses the observed chain copies if there are any, otherwise a labelled made-up example.
    Compares planning each chain alone, planning with the guard, and pausing bridges."""
    use_obs = (topology == "observed") or (topology == "auto" and bool(dep.observed_topology))
    if use_obs:
        topo = dict(dep.observed_topology)
        d2 = guard.expand_instances(dep, topo, label="observed multi-chain topology (bridges assumed)")
    else:
        top = sorted(dep.anchors, key=lambda a: -a.value_usd)[:top_k]
        topo = {a.anchor_id: list(instances) for a in top}
        d2 = guard.expand_instances(dep, topo, value_split=dict(zip(instances, split)), label="synthetic topology")
    ctx = planner.kb_context(d2, kb)
    n = len(d2.anchors)
    ss_plan = scenarios.sample(rc.n_plan, n, seed=rc.seed_base + 11, shift_years=rc.shift_years)
    ss_eval = scenarios.sample(rc.n_eval, n, seed=rc.seed_base + 12, shift_years=rc.shift_years)
    C, F = planner.expected_cost_matrix(d2, ctx, ss_plan, rc.lp, rc.pp, "stochastic")
    indep = planner.solve(d2, C, F, rc.pp, method="qamp_independent")
    guarded, rounds, final, hist = guard.guarded_plan(d2, lambda cp: planner.solve(d2, C, F, rc.pp, coupling=cp, method="qamp_guarded"))
    res_indep = guard.check_plan(d2, indep.starts)
    res_pause = guard.check_plan(d2, indep.starts, bridge_policy="pause_revalidate")
    out = dict(topology_kind="observed" if use_obs else "synthetic", topology={k: v for k, v in topo.items()},
               rounds=rounds, history=hist,
               violations=dict(independent=sum(g.violation for g in res_indep),
                               guarded=sum(g.violation for g in final),
                               independent_pause_revalidate=sum(g.violation for g in res_pause)),
               components=len(res_indep),
               example_trace=next((g.trace for g in res_indep if g.violation), None),
               states_max=max((g.states for g in res_indep), default=0))
    costs = dict(independent=realized_costs(d2, ctx, indep, ss_eval, rc.lp, rc.pp),
                 guarded=realized_costs(d2, ctx, guarded, ss_eval, rc.lp, rc.pp),
                 independent_pause_revalidate=realized_costs(d2, ctx, indep, ss_eval, rc.lp, rc.pp, bridge_policy="pause_revalidate"))
    # what the plan expected, ignoring bridges
    believed = float(np.mean([sum(anchor_loss(a, effective_quarter(a, indep.starts[a.anchor_id], int(ss_eval.delta[s, i])),
                                               float(ss_eval.crqc_quarter[s]), ctx[a.anchor_id]["retention_years"], rc.lp)
                                   for i, a in enumerate(d2.anchors)) for s in range(len(ss_eval))]))
    out["mean_cost"] = {k: float(v.mean()) for k, v in costs.items()}
    eff0 = {a.anchor_id: effective_quarter(a, indep.starts[a.anchor_id]) for a in d2.anchors}
    effg = {a.anchor_id: effective_quarter(a, guarded.starts[a.anchor_id]) for a in d2.anchors}
    out["bridge_downtime_quarters"] = dict(independent_pause_revalidate=guard.bridge_downtime(d2, eff0),
                                           guarded=guard.bridge_downtime(d2, effg))
    out["independent_believed_loss"] = believed
    out["tests"] = paired_tests(costs["guarded"], {k: v for k, v in costs.items() if k != "guarded"})
    return out


def environment() -> dict:
    return dict(python=platform.python_version(), numpy=np.__version__, scipy=scipy.__version__,
                platform=platform.platform(), utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))


def _jsonable(o):
    return json.loads(json.dumps(o, default=str))


def run_sensitivity(dep: Deployment, kb: KnowledgeBase, seed_base: int = config.DEV_SEED_BASE,
                    capacities=(1, 2, 3), periods=(2, 4, 8), hazards=(0.25, 1.0, 4.0),
                    n_plan: int = 5_000, n_eval: int = 1_000) -> list[dict]:
    """Exploratory: where does timing pay? QAMP vs ASAP across capacity, renewal period and hazard."""
    rows = []
    for period in periods:
        dp = with_calendar_period(dep, period) if period != 4 else dep
        for cap in capacities:
            for h in hazards:
                rc = RunConfig(n_plan=n_plan, n_eval=n_eval, seed_base=seed_base, oracle=False,
                               lp=LossParams(hazard_per_year=h), pp=PlanParams(capacity=cap))
                r = run_policies(dp, kb, rc, include=("qamp_stochastic", "asap_fifo", "annual_review"))
                t = r["tests"]["asap_fifo"]
                ta = r["tests"]["annual_review"]
                q = r["summary"]["qamp_stochastic"]["mean"]
                rows.append(dict(period=period, capacity=cap, hazard=h, qamp_mean=q,
                                 asap_minus_qamp=t["mean_diff"], asap_rel=t["mean_diff"] / q, p_asap=t["p"],
                                 annual_minus_qamp=ta["mean_diff"], p_annual=ta["p"]))
    return rows
