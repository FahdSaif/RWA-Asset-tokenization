"""POST-REGISTRATION: stronger baselines and robustness to the renewal calendars.

Plan written before the run: docs/BASELINES_CALENDARS_PLAN.md. Uses the frozen code; the new baselines
are defined here, in tools/, and get the same information as QAMP. Changes no code in src/ and no frozen
result. Not part of the pre-registration.

Run from rwa-quantumclock:  python tools/baselines_calendars.py
Quick test:                 python tools/baselines_calendars.py --quick
Writes results/exploratory/baselines_calendars.json and .md (or *_quick.* with --quick)."""
import argparse
import copy
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from qamp import __main__ as cli, config, evaluate, planner, scenarios  # noqa: E402
from qamp.baselines import _Capacity  # noqa: E402
from qamp.kb import load_kb  # noqa: E402
from qamp.loss import attack_weight, effective_quarter  # noqa: E402
from qamp.model import Calendar  # noqa: E402
from qamp.planner import Plan, PlanParams  # noqa: E402

FRESH_SEED_BASE = 90_000          # never used before this run
DRAW_SEED = 90_100                # random phases in E2
FROZEN = ("qamp_stochastic", "qamp_no_windows", "qamp_expected", "asap_fifo", "greedy_risk", "mosca")
NEW = ("B1_cal_greedy_risk", "B2_earliest_last_start", "B3_greedy_cost_table", "B4_one_date_mean", "B5_one_date_median")
ORDER = FROZEN + NEW
SHORT = dict(qamp_stochastic="QAMP", qamp_no_windows="NoWin", qamp_expected="Exp", asap_fifo="ASAP", greedy_risk="Greedy",
             mosca="Mosca", B1_cal_greedy_risk="B1", B2_earliest_last_start="B2", B3_greedy_cost_table="B3",
             B4_one_date_mean="B4", B5_one_date_median="B5")


def m(x):
    # USD to USD millions, one decimal
    return round(float(x) / 1e6, 1)


def hashes():
    # fingerprint of the frozen code and rules, to show nothing changed
    files = sorted(list((ROOT / "src").rglob("*.py")) + list((ROOT / "kb").glob("*.yaml")))
    h = hashlib.sha256()
    for p in files:
        h.update(str(p.relative_to(ROOT)).encode())
        h.update(p.read_bytes())
    return h.hexdigest()


def git_changed_lines():
    # lines changed in src/ and kb/ against the last commit (None if git is not available)
    try:
        r = subprocess.run(["git", "-C", str(ROOT), "diff", "--numstat", "HEAD", "--", "src", "kb"],
                           capture_output=True, text=True, check=True)
    except (OSError, subprocess.CalledProcessError):
        return None
    return sum(int(a) + int(b) for a, b, *_ in (ln.split("\t") for ln in r.stdout.splitlines()) if a.isdigit())


# --- new baselines (same information as QAMP: calendars, delays, capacity, durations, rule deadlines)

def _risk(a, lp):
    return a.value_usd * attack_weight(a, lp)


def _calendar_schedule(dep, ctx, pp, order, method):
    """Give each anchor the latest start that still takes effect at its earliest reachable boundary,
    even with one quarter of delay, within capacity and the rule deadline."""
    cap = _Capacity(pp, dep.group_capacity)
    T = pp.last_start + 1
    starts = {}
    for i in order:
        a = dep.anchors[i]
        d = max(1, a.migration_quarters)
        hq = ctx[a.anchor_id]["hard_q"]
        fits = [t for t in range(T) if cap.fits(a.issuer_group, t, d)]
        ok = [t for t in fits if hq is None or effective_quarter(a, t) <= hq] or fits
        if not ok:                       # no room left: last start (counted as a miss), as the frozen baselines do
            starts[a.anchor_id] = pp.last_start
            continue
        e1 = {t: effective_quarter(a, t, 1) for t in ok}
        target = min(e1.values())
        t = max(t for t in ok if e1[t] == target)
        cap.take(a.issuer_group, t, d)
        starts[a.anchor_id] = t
    return Plan(starts=starts, method=method, status="list-scheduled")


def b1_cal_greedy_risk(dep, ctx, lp, pp):
    order = sorted(range(len(dep.anchors)), key=lambda i: -_risk(dep.anchors[i], lp))
    return _calendar_schedule(dep, ctx, pp, order, "B1_cal_greedy_risk")


def b2_earliest_last_start(dep, ctx, lp, pp):
    T = pp.last_start + 1

    def last_start(a):
        e = [effective_quarter(a, t, 1) for t in range(T)]
        return max(t for t in range(T) if e[t] == e[0])
    order = sorted(range(len(dep.anchors)), key=lambda i: (last_start(dep.anchors[i]), -_risk(dep.anchors[i], lp)))
    return _calendar_schedule(dep, ctx, pp, order, "B2_earliest_last_start")


def b3_greedy_cost_table(dep, ctx, lp, pp, C, F):
    """QAMP's own expected-cost table, filled anchor by anchor in risk order (no MILP)."""
    cap = _Capacity(pp, dep.group_capacity)
    T = C.shape[1]
    starts = {}
    for i in sorted(range(len(dep.anchors)), key=lambda i: -_risk(dep.anchors[i], lp)):
        a = dep.anchors[i]
        d = max(1, a.migration_quarters)
        fits = [t for t in range(T) if cap.fits(a.issuer_group, t, d)]
        if not fits:
            starts[a.anchor_id] = pp.last_start
            continue
        ok = [t for t in fits if F[i, t]] or fits
        t = min(ok, key=lambda t: C[i, t])
        cap.take(a.issuer_group, t, d)
        starts[a.anchor_id] = t
    return Plan(starts=starts, method="B3_greedy_cost_table", status="list-scheduled")


def b4_b5_one_date(dep, kb, ctx, lp, pp, ss_plan, stat, method):
    q = float(np.mean(ss_plan.crqc_quarter) if stat == "mean" else np.median(ss_plan.crqc_quarter))
    one = scenarios.ScenarioSet(np.array([q]), ss_plan.delta[:1], ss_plan.seed, params=dict(ss_plan.params))
    p = planner.plan(dep, kb, one, lp, pp, mode="stochastic", ctx=ctx)
    p.method = method
    p.info["arrival_quarter"] = q
    return p


# --- running and scoring

def score(dep, ctx, plans, ss_eval, rc):
    costs = {k: evaluate.realized_costs(dep, ctx, p, ss_eval, rc.lp, rc.pp) for k, p in plans.items()}
    tests = evaluate.paired_tests(costs["qamp_stochastic"], {k: v for k, v in costs.items() if k != "qamp_stochastic"})
    q2030, q2032 = config.year_end_quarter(2030), config.year_end_quarter(2032)
    rows = {}
    for k in ORDER:
        v = costs[k]
        t = tests.get(k)
        rows[k] = dict(mean=m(v.mean()), ci95=[m(x) for x in evaluate.bootstrap_ci(v)],
                       minus_qamp=m(t["mean_diff"]) if t else 0.0,
                       minus_qamp_ci95=[m(x) for x in t["mean_diff_ci95"]] if t else [0.0, 0.0],
                       deadline_misses=round(evaluate.deadline_misses(dep, ctx, plans[k], ss_eval), 2),
                       protected_2030=round(evaluate.protected_share(dep, plans[k], q2030 + 1, ss_eval), 3),
                       protected_2032=round(evaluate.protected_share(dep, plans[k], q2032 + 1, ss_eval), 3))
    return rows, costs


def make_plans(dep, kb, rc):
    """All policies on the same data, same information and same planning scenarios."""
    ctx = planner.kb_context(dep, kb)
    n = len(dep.anchors)
    r = evaluate.run_policies(dep, kb, evaluate.RunConfig(**{**rc.__dict__, "oracle": False}), ctx=ctx, include=FROZEN)
    plans = {k: Plan(starts=v["starts"], method=k, status=v["status"]) for k, v in r["plans"].items()}
    ss_plan = scenarios.sample(rc.n_plan, n, seed=rc.seed_base + 1, shift_years=rc.shift_years)   # as run_policies
    ss_eval = scenarios.sample(rc.n_eval, n, seed=rc.seed_base + 2, shift_years=rc.shift_years)
    C, F = planner.expected_cost_matrix(dep, ctx, ss_plan, rc.lp, rc.pp, "stochastic")
    plans["B1_cal_greedy_risk"] = b1_cal_greedy_risk(dep, ctx, rc.lp, rc.pp)
    plans["B2_earliest_last_start"] = b2_earliest_last_start(dep, ctx, rc.lp, rc.pp)
    plans["B3_greedy_cost_table"] = b3_greedy_cost_table(dep, ctx, rc.lp, rc.pp, C, F)
    plans["B4_one_date_mean"] = b4_b5_one_date(dep, kb, ctx, rc.lp, rc.pp, ss_plan, "mean", "B4_one_date_mean")
    plans["B5_one_date_median"] = b4_b5_one_date(dep, kb, ctx, rc.lp, rc.pp, ss_plan, "median", "B5_one_date_median")
    for k, p in plans.items():
        if any(v is None for v in p.starts.values()):
            raise RuntimeError(f"{k}: plan has anchors without a start")
    arrivals = dict(mean=plans["B4_one_date_mean"].info["arrival_quarter"], median=plans["B5_one_date_median"].info["arrival_quarter"])
    return plans, ctx, ss_eval, arrivals


def set_assumed(dep, period, phases=None):
    # change only the calendars that were assumed (observed calendars stay as they are)
    d = copy.deepcopy(dep)
    for a in d.anchors:
        if a.calendar.source == "assumed":
            ph = phases[a.anchor_id] if phases is not None else a.calendar.phase % max(period, 1)
            a.calendar = Calendar(period=period, phase=ph, source=f"assumed; period set to {period}")
    return d


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true", help="small run to test the script")
    args = ap.parse_args()
    n_plan, n_eval, draws = (2_000, 200, 2) if args.quick else (20_000, 2_000, 10)
    t0 = time.time()
    h_before = hashes()
    dep = cli._load(argparse.Namespace())  # same data as the held-out run
    kb = load_kb()
    assumed = [a.anchor_id for a in dep.anchors if a.calendar.source == "assumed"]
    res = dict(E1={}, E2={}, E3={})

    # E1: all policies, two seed bases, three settings (as the frozen main, period1 and tight runs)
    settings = dict(main=(dep, PlanParams()), period1=(evaluate.with_calendar_period(dep, 1), PlanParams()),
                    tight=(evaluate.with_calendar_period(dep, 8), PlanParams(capacity=1)))
    main_plans = None
    for base in (config.HELD_OUT_SEED_BASE, FRESH_SEED_BASE):
        for name, (d, pp) in settings.items():
            rc = evaluate.RunConfig(n_plan=n_plan, n_eval=n_eval, seed_base=base, oracle=False, pp=pp)
            plans, ctx, ss_eval, arr = make_plans(d, kb, rc)
            rows, _ = score(d, ctx, plans, ss_eval, rc)
            res["E1"][f"{name}_seed{base}"] = dict(rows=rows, one_date_arrival_quarter=arr)
            if name == "main" and base == config.HELD_OUT_SEED_BASE:
                main_plans, main_ctx, main_ss_eval, main_rc = plans, ctx, ss_eval, rc
            print("E1", name, base, f"QAMP {rows['qamp_stochastic']['mean']}",
                  " ".join(f"{SHORT[k]} {rows[k]['minus_qamp']:+.1f}" for k in NEW), flush=True)

    # E2: plan on the frozen calendars; score on different true calendars for the assumed anchors
    rng = np.random.default_rng(DRAW_SEED)
    for label, period in (("annual_random_phase", 4), ("every_2q", 2), ("every_quarter", 1), ("every_8q", 8)):
        per_draw = {k: [] for k in ORDER}
        means = {k: [] for k in ORDER}
        for _ in range(draws):
            phases = {aid: int(rng.integers(0, period)) for aid in assumed}
            true_dep = set_assumed(dep, period, phases)
            rows, _ = score(true_dep, main_ctx, main_plans, main_ss_eval, main_rc)
            for k in ORDER:
                per_draw[k].append(rows[k]["minus_qamp"])
                means[k].append(rows[k]["mean"])
        res["E2"][label] = {k: dict(mean=round(float(np.mean(means[k])), 1),
                                    minus_qamp=round(float(np.mean(per_draw[k])), 1),
                                    minus_qamp_range=[min(per_draw[k]), max(per_draw[k])]) for k in ORDER}
        print("E2", label, " ".join(f"{SHORT[k]} {res['E2'][label][k]['minus_qamp']:+.1f}" for k in ORDER[1:]), flush=True)

    # E3: assumed calendars set to another period for both planning and scoring
    for period in (1, 2, 4, 8):
        d = set_assumed(dep, period)
        rc = evaluate.RunConfig(n_plan=n_plan, n_eval=n_eval, seed_base=config.HELD_OUT_SEED_BASE, oracle=False)
        plans, ctx, ss_eval, _ = make_plans(d, kb, rc)
        rows, _ = score(d, ctx, plans, ss_eval, rc)
        res["E3"][f"assumed_period_{period}"] = dict(rows=rows)
        print("E3", period, f"QAMP {rows['qamp_stochastic']['mean']}",
              " ".join(f"{SHORT[k]} {rows[k]['minus_qamp']:+.1f}" for k in ORDER[1:]), flush=True)

    h_after = hashes()
    meta = dict(post_registration=True, plan="docs/BASELINES_CALENDARS_PLAN.md",
                seed_bases=[config.HELD_OUT_SEED_BASE, FRESH_SEED_BASE], draw_seed=DRAW_SEED, draws=draws,
                n_plan=n_plan, n_eval=n_eval, assumed_calendars=len(assumed),
                runtime_s=round(time.time() - t0, 1), env=evaluate.environment(),
                src_kb_hash_before=h_before, src_kb_hash_after=h_after, src_kb_unchanged=h_before == h_after,
                git_lines_changed_src_kb=git_changed_lines())
    out = ROOT / "results" / "exploratory"
    out.mkdir(parents=True, exist_ok=True)
    tag = "baselines_calendars" + ("_quick" if args.quick else "")
    (out / f"{tag}.json").write_text(json.dumps(dict(meta=meta, **res), indent=1, default=str))

    md = ["# POST-REGISTRATION: stronger baselines and calendar robustness", "",
          f"Plan committed before the run: docs/BASELINES_CALENDARS_PLAN.md. Seed bases {config.HELD_OUT_SEED_BASE} "
          f"(held-out) and {FRESH_SEED_BASE} (fresh); {n_plan:,} planning and {n_eval:,} evaluation scenarios; frozen code. "
          "Costs in USD m. Positive 'minus QAMP' means QAMP is cheaper. Not pre-registered.", "",
          f"Code and rules unchanged during the run: {meta['src_kb_unchanged']} "
          f"(git lines changed in src/ and kb/: {meta['git_lines_changed_src_kb']}).", "",
          "## E1. All policies (policy minus QAMP, 95% CI)", ""]
    for key, v in res["E1"].items():
        md += [f"### {key}", "", "| Policy | Mean cost | Minus QAMP (95% CI) | Expected misses | Protected 2030 |",
               "|---|---|---|---|---|"]
        for k in ORDER:
            r = v["rows"][k]
            lo, hi = r["minus_qamp_ci95"]
            md.append(f"| {k} | {r['mean']} | {r['minus_qamp']:+.1f} ({lo} to {hi}) | {r['deadline_misses']} | {r['protected_2030']:.1%} |")
        md += ["", f"One-date baselines planned for arrival quarter {v['one_date_arrival_quarter']['mean']:.1f} (mean) "
               f"and {v['one_date_arrival_quarter']['median']:.1f} (median).", ""]
    md += ["## E2. Wrong calendars (plan on frozen calendars, score on different ones for the 47 assumed anchors)", "",
           f"Mean over {draws} draws of random phases; range across draws in brackets.", "",
           "| True calendar | " + " | ".join(ORDER[1:]) + " |", "|---|" + "---|" * (len(ORDER) - 1)]
    for label, v in res["E2"].items():
        md.append(f"| {label} (QAMP {v['qamp_stochastic']['mean']}) | " + " | ".join(
            f"{v[k]['minus_qamp']:+.1f} ({v[k]['minus_qamp_range'][0]} to {v[k]['minus_qamp_range'][1]})" for k in ORDER[1:]) + " |")
    md += ["", "## E3. Assumed calendars set to another period (planning and scoring)", "",
           "| Assumed period | QAMP mean | " + " | ".join(ORDER[1:]) + " |", "|---|---|" + "---|" * (len(ORDER) - 1)]
    for label, v in res["E3"].items():
        r = v["rows"]
        md.append(f"| {label} | {r['qamp_stochastic']['mean']} | " + " | ".join(
            f"{r[k]['minus_qamp']:+.1f} ({r[k]['minus_qamp_ci95'][0]} to {r[k]['minus_qamp_ci95'][1]})" for k in ORDER[1:]) + " |")
    (out / f"{tag}.md").write_text("\n".join(md) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    main()
