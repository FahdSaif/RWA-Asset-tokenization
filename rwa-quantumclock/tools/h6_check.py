"""POST HOC CHECK of the guard result (H6). Read only: changes no code and no frozen result.

It reruns the frozen held-out guard experiment and reports:
1. the frozen numbers again (to show nothing changed);
2. the 'underestimate' measured like for like (the frozen code compared loss only with loss plus spend);
3. how the guarded plan behaves when each bridged copy can run late or early on its own,
   with the frozen bridge rule and with the pause-and-revalidate rule.

Run from rwa-quantumclock:  python tools/h6_check.py
Writes results/exploratory/h6_check.json and .md. Not part of the pre-registration."""
import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from qamp import __main__ as cli, config, evaluate, guard, planner, scenarios  # noqa: E402
from qamp.kb import load_kb  # noqa: E402
from qamp.loss import effective_quarter  # noqa: E402


def m(x):
    # USD to USD millions, one decimal
    return round(float(x) / 1e6, 1)


def main():
    t0 = time.time()
    dep = cli._load(argparse.Namespace())  # same data as the held-out run
    kb = load_kb()
    rc = evaluate.RunConfig(seed_base=config.HELD_OUT_SEED_BASE)

    # 1. Frozen guard experiment, unchanged.
    out = evaluate.run_guard(dep, kb, rc)

    # Rebuild the same plans (same seeds, same code) to split spend from loss.
    d2 = guard.expand_instances(dep, dict(dep.observed_topology), label="observed multi-chain topology (bridges assumed)")
    ctx = planner.kb_context(d2, kb)
    n = len(d2.anchors)
    ss_plan = scenarios.sample(rc.n_plan, n, seed=rc.seed_base + 11, shift_years=rc.shift_years)
    ss_eval = scenarios.sample(rc.n_eval, n, seed=rc.seed_base + 12, shift_years=rc.shift_years)
    C, F = planner.expected_cost_matrix(d2, ctx, ss_plan, rc.lp, rc.pp, "stochastic")
    indep = planner.solve(d2, C, F, rc.pp, method="qamp_independent")
    guarded, _, _, _ = guard.guarded_plan(d2, lambda cp: planner.solve(d2, C, F, rc.pp, coupling=cp, method="qamp_guarded"))

    def spend(plan):
        return sum(planner.spend(a, plan.starts[a.anchor_id], rc.pp) for a in d2.anchors if plan.starts[a.anchor_id] is not None)

    believed = out["independent_believed_loss"]
    cost_indep = out["mean_cost"]["independent"]
    spend_indep = spend(indep)
    loss_indep = cost_indep - spend_indep

    # 2. Like-for-like underestimate (H6 asks for at least 10%).
    under = dict(
        frozen_loss_vs_cost=1 - believed / cost_indep,
        loss_vs_loss=1 - believed / loss_indep,
        loss_plus_spend_vs_cost=1 - (believed + spend_indep) / cost_indep,
    )

    # 3. Guarded plan when each copy draws its own delay (as in the cost evaluation).
    comps = guard.components(d2)
    idx = {a.anchor_id: i for i, a in enumerate(d2.anchors)}
    same_start = all(len({guarded.starts[x] for x in c["members"]}) == 1 for c in comps.values())
    diverge, viol_open, viol_pause = [], [], []
    for s in range(len(ss_eval)):
        eff = {a.anchor_id: effective_quarter(a, guarded.starts[a.anchor_id], int(ss_eval.delta[s, idx[a.anchor_id]]))
               for a in d2.anchors}
        d = vo = vp = 0
        for base, c in comps.items():
            e = {x: eff[x] for x in c["members"]}
            d += len(set(e.values())) > 1
            vo += guard.check_component(base, e, c["edges"]).violation
            vp += guard.check_component(base, e, c["edges"], bridge_policy="pause_revalidate").violation
        diverge.append(d)
        viol_open.append(vo)
        viol_pause.append(vp)
    diverge, viol_open, viol_pause = map(np.array, (diverge, viol_open, viol_pause))

    res = dict(
        meta=dict(post_hoc=True, seed_base=config.HELD_OUT_SEED_BASE, n_plan=rc.n_plan, n_eval=rc.n_eval,
                  runtime_s=time.time() - t0, env=evaluate.environment()),
        frozen_reproduced=dict(mean_cost_usd_m={k: m(v) for k, v in out["mean_cost"].items()},
                               independent_believed_loss_usd_m=m(believed),
                               violations=out["violations"], components=out["components"]),
        spend_usd_m=dict(independent=m(spend_indep), guarded=m(spend(guarded))),
        independent_realised_loss_usd_m=m(loss_indep),
        underestimate=dict((k, round(v, 3)) for k, v in under.items()),
        guarded_under_sampled_delays=dict(
            starts_identical_within_every_component=same_start,
            mean_components_with_different_effect_quarters=round(float(diverge.mean()), 2),
            share_of_scenarios_with_a_violation_open_bridges=round(float((viol_open > 0).mean()), 3),
            mean_violations_open_bridges=round(float(viol_open.mean()), 2),
            share_of_scenarios_with_a_violation_pause_revalidate=round(float((viol_pause > 0).mean()), 3),
        ),
    )
    outdir = ROOT / "results" / "exploratory"
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / "h6_check.json").write_text(json.dumps(res, indent=1))
    g = res["guarded_under_sampled_delays"]
    md = [
        "# POST HOC: check of the guard result (H6)", "",
        f"Held-out seeds from {config.HELD_OUT_SEED_BASE}; frozen code; not pre-registered.", "",
        "## Frozen numbers, reproduced", "",
        f"- Mean realised cost (USD m): {res['frozen_reproduced']['mean_cost_usd_m']}",
        f"- Independent plan, expected loss ignoring bridges (USD m): {m(believed)}",
        f"- Violations: {out['violations']} of {out['components']} components", "",
        "## Underestimate, like for like (H6 threshold: at least 10%)", "",
        "| Comparison | Underestimate |", "|---|---|",
        f"| Frozen code: expected loss vs realised loss plus spend | {under['frozen_loss_vs_cost']:.1%} |",
        f"| Expected loss vs realised loss | {under['loss_vs_loss']:.1%} |",
        f"| Expected loss plus spend vs realised loss plus spend | {under['loss_plus_spend_vs_cost']:.1%} |", "",
        f"Spend of the independent plan: USD {m(spend_indep)}m; its realised loss: USD {m(loss_indep)}m.", "",
        "## Guarded plan when each bridged copy runs late or early on its own", "",
        f"- Start quarters identical within every component: {same_start}",
        f"- Components whose copies take effect in different quarters (mean per scenario): {g['mean_components_with_different_effect_quarters']} of {len(comps)}",
        f"- Scenarios with at least one violation, bridges open: {g['share_of_scenarios_with_a_violation_open_bridges']:.1%} (mean {g['mean_violations_open_bridges']} per scenario)",
        f"- Scenarios with at least one violation, pause-and-revalidate: {g['share_of_scenarios_with_a_violation_pause_revalidate']:.1%}",
    ]
    (outdir / "h6_check.md").write_text("\n".join(md) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    main()
