"""POST-REGISTRATION: does the plan follow the rules when the rules change?

Adds the scenario rule files in kb_scenarios/ to the frozen rules, or changes the jurisdictions,
and plans again with the frozen code. Plan written before the run: docs/KB_SCENARIOS_PLAN.md.
Changes no code in src/ and no frozen result. Not part of the pre-registration.

Run from rwa-quantumclock:  python tools/kb_scenarios.py
Quick test:                 python tools/kb_scenarios.py --quick
Writes results/exploratory/kb_scenarios.json and .md (or *_quick.* with --quick)."""
import argparse
import copy
import hashlib
import json
import re
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path
from types import SimpleNamespace

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from qamp import __main__ as cli, config, evaluate, explain, planner, scenarios  # noqa: E402
from qamp.kb import load_kb  # noqa: E402
from qamp.kb.engine import KnowledgeBase  # noqa: E402
from qamp.loss import effective_quarter  # noqa: E402
from qamp.planner import PlanParams  # noqa: E402

SCN = ROOT / "kb_scenarios"
RETENTION_RULES = ("RET-FATF-R11", "RET-EU-AMLD-40", "RET-US-SEC-17A4")
# id: (what changes, extra rule folder, rules left out, jurisdictions, capacity 1 for every issuer)
SCENARIOS = {
    "S0": ("Frozen knowledge base", None, (), ("US", "EU"), False),
    "S1": ("Hard deadline 2030 for compliance-critical keys", "S1", (), ("US", "EU"), False),
    "S2": ("Hard deadline 2032 for compliance-critical keys", "S2", (), ("US", "EU"), False),
    "S3": ("Hard deadline 2030 for all quantum-vulnerable keys", "S3", (), ("US", "EU"), False),
    "S4a": ("Jurisdictions: EU only", None, (), ("EU",), False),
    "S4b": ("Jurisdictions: US only", None, (), ("US",), False),
    "S4c": ("No retention rules", None, RETENTION_RULES, ("US", "EU"), False),
    "S5": ("EU retention 10 years", "S5", (), ("US", "EU"), False),
    "S6": ("S3 with capacity 1 per issuer", "S3", (), ("US", "EU"), True),
}


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


def make_kb(folder, exclude):
    rules = load_kb(exclude=exclude).rules
    if folder:
        rules = rules + load_kb(SCN / folder).rules
    return KnowledgeBase(rules)


def evidence_for(dep):
    # same evidence as the explanation check in qamp/__main__.py
    from qamp.discovery import RulesClassifier, scan_abi
    from qamp.discovery.abi import scan_controllers
    entries = RulesClassifier().classify([f for t in dep.tokens for f in scan_abi(t.address, t.abi_functions)]
                                         + scan_controllers(dep))
    ev_tok = {}
    for e in entries:
        ev_tok.setdefault(e.token, []).extend(e.evidence)
    return {a.anchor_id: [e for t in a.tokens for e in ev_tok.get(t, [])][:3] for a in dep.anchors}


def winning_rule(trace, key, value):
    # the first rule that gave the final value
    for r in trace:
        if key in r["then"] and str(r["then"][key]) == str(value):
            return r["rule"]
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true", help="small run to test the script")
    args = ap.parse_args()
    n_plan, n_eval = (2_000, 200) if args.quick else (20_000, 2_000)
    t0 = time.time()
    h_before = hashes()
    dep0 = cli._load(argparse.Namespace())  # same data as the held-out run
    evidence = evidence_for(dep0)
    rc = evaluate.RunConfig(n_plan=n_plan, n_eval=n_eval, seed_base=config.HELD_OUT_SEED_BASE, oracle=False)
    ss_eval = scenarios.sample(n_eval, len(dep0.anchors), seed=rc.seed_base + 2)  # same as run_policies
    groups = sorted({a.issuer_group for a in dep0.anchors})
    q2031 = config.year_end_quarter(2030) + 1

    res, costs0, starts0, ctx0 = {}, None, None, None
    for sid, (label, folder, exclude, juris, cap1) in SCENARIOS.items():
        kb = make_kb(folder, exclude)
        dep = dep0
        pp = rc.pp
        if cap1:
            dep = copy.deepcopy(dep0)
            dep.group_capacity = {g: 1 for g in groups}
            pp = PlanParams(**{**rc.pp.as_dict(), "capacity": 1})
        ctx = planner.kb_context(dep, kb, jurisdictions=juris)
        r = evaluate.run_policies(dep, kb, evaluate.RunConfig(n_plan=n_plan, n_eval=n_eval, seed_base=rc.seed_base,
                                                              oracle=False, pp=pp),
                                  ctx=ctx, include=("qamp_stochastic", "qamp_cost_first"))
        starts = r["plans"]["qamp_stochastic"]["starts"]
        cost = np.array(r["costs"]["qamp_stochastic"])
        cost_first = np.array(r["costs"]["qamp_cost_first"])
        if sid == "S0":
            costs0, starts0, ctx0 = cost, starts, ctx
        # the same plan scored with the frozen rules (same yardstick for every scenario)
        plan_ns = SimpleNamespace(starts=starts)
        cost_on_s0 = evaluate.realized_costs(dep, ctx0, plan_ns, ss_eval, rc.lp, pp)
        d_own, d_s0 = cost - costs0, cost_on_s0 - costs0
        # planned misses per issuer (no delay)
        miss_by_group = Counter()
        for a in dep.anchors:
            hq = ctx[a.anchor_id]["hard_q"]
            e = effective_quarter(a, starts[a.anchor_id])
            if hq is not None and a.quantum_vulnerable and e > hq:
                miss_by_group[a.issuer_group] += 1
        # which rule decided each deadline and retention value
        dl_rule, ret_rule, ret_vals, hard = Counter(), Counter(), Counter(), Counter()
        fired = Counter()
        for a in dep.anchors:
            inf = ctx[a.anchor_id]["inference"]
            c = inf.conclusions
            fired.update(inf.fired())
            hard[config.quarter_label(ctx[a.anchor_id]["hard_q"]) if ctx[a.anchor_id]["hard_q"] is not None else "none"] += 1
            dl_rule[winning_rule(inf.trace, "deadline_hard", c.get("deadline_hard")) or "none"] += 1
            ret_vals[ctx[a.anchor_id]["retention_years"]] += 1
            ret_rule[winning_rule(inf.trace, "retention_years", c.get("retention_years")) or "none"] += 1
        # explanations of this plan
        rats = [explain.write(a, starts[a.anchor_id], ctx[a.anchor_id]["inference"], evidence[a.anchor_id])
                for a in dep.anchors]
        sents = [s for x in rats for s in x.sentences]
        scn_sents = [s for s in sents if "[R:SCN-" in s]
        nist_named = [s for s in sents if "NIST IR 8547" in s]
        nist_wrong = [s for s in nist_named if not re.search(r"\[R:(NIST8547-|SCN-S1-|SCN-S3-)", s)]
        diag = planner.diagnose(dep, pp, q2031) if sid in ("S3", "S6") else None
        res[sid] = dict(
            label=label, extra_rules=folder, rules_left_out=list(exclude), jurisdictions=list(juris), capacity_1=cap1,
            M1_starts_changed_vs_S0=sum(starts[k] != starts0[k] for k in starts),
            M2_expected_deadline_misses=round(r["summary"]["qamp_stochastic"]["deadline_misses"], 2),
            M2_planned_misses_by_issuer=dict(sorted(miss_by_group.items())),
            M3_mean_cost_own_rules_usd_m=m(cost.mean()),
            M3_diff_vs_S0_own_rules_usd_m=m(d_own.mean()),
            M3_diff_vs_S0_own_rules_ci95=[m(x) for x in evaluate.bootstrap_ci(d_own)],
            M3_mean_cost_scored_with_S0_rules_usd_m=m(cost_on_s0.mean()),
            M3_diff_vs_S0_scored_with_S0_rules_usd_m=m(d_s0.mean()),
            M3_diff_vs_S0_scored_with_S0_rules_ci95=[m(x) for x in evaluate.bootstrap_ci(d_s0)],
            M4_price_of_compliance_usd_m=m((cost - cost_first).mean()),
            M4_cost_first_expected_misses=round(r["summary"]["qamp_cost_first"]["deadline_misses"], 2),
            M5_protected_by_2030=round(r["summary"]["qamp_stochastic"]["protected_by_2030"], 3),
            M5_protected_by_2032=round(r["summary"]["qamp_stochastic"]["protected_by_2032"], 3),
            M6_rules_fired=dict(sorted(fired.items())),
            M6_hard_deadline_quarter=dict(sorted(hard.items())),
            M6_deadline_decided_by=dict(sorted(dl_rule.items())),
            M6_retention_years=dict(sorted((str(k), v) for k, v in ret_vals.items())),
            M6_retention_decided_by=dict(sorted(ret_rule.items())),
            M8_explanations=explain.scores(rats),
            M8_sentences_citing_scenario_rules=len(scn_sents),
            M8_sentences_naming_nist_for_another_source=len(nist_wrong),
            M8_example_scenario_sentence=scn_sents[0] if scn_sents else None,
            diagnose_by_2031=diag,
            plan_status=r["plans"]["qamp_stochastic"]["status"],
        )
        print(sid, label, f"changed {res[sid]['M1_starts_changed_vs_S0']}", f"cost {m(cost.mean())}",
              f"misses {res[sid]['M2_expected_deadline_misses']}", flush=True)

    h_after = hashes()
    meta = dict(post_registration=True, plan="docs/KB_SCENARIOS_PLAN.md", seed_base=config.HELD_OUT_SEED_BASE,
                n_plan=n_plan, n_eval=n_eval, runtime_s=round(time.time() - t0, 1), env=evaluate.environment(),
                M7_src_kb_hash_before=h_before, M7_src_kb_hash_after=h_after, M7_unchanged=h_before == h_after,
                M7_git_lines_changed_src_kb=git_changed_lines())
    out = ROOT / "results" / "exploratory"
    out.mkdir(parents=True, exist_ok=True)
    tag = "kb_scenarios" + ("_quick" if args.quick else "")
    (out / f"{tag}.json").write_text(json.dumps(dict(meta=meta, scenarios=res), indent=1, default=str))

    md = ["# POST-REGISTRATION: knowledge-base scenarios", "",
          f"Plan committed before the run: docs/KB_SCENARIOS_PLAN.md. Held-out seeds from {config.HELD_OUT_SEED_BASE}; "
          f"{n_plan:,} planning and {n_eval:,} evaluation scenarios; frozen code. Costs in USD m. "
          "Not pre-registered.", "",
          f"Code and rules unchanged during the run: {meta['M7_unchanged']} "
          f"(git lines changed in src/ and kb/: {meta['M7_git_lines_changed_src_kb']}).", "",
          "| ID | Scenario | Starts changed | Expected misses | Cost (own rules) | Diff vs S0 (95% CI) | "
          "Diff vs S0, S0 rules (95% CI) | Price of compliance | Protected 2030 / 2032 |",
          "|---|---|---|---|---|---|---|---|---|"]
    for sid, x in res.items():
        a, b = x["M3_diff_vs_S0_own_rules_ci95"]
        c, d = x["M3_diff_vs_S0_scored_with_S0_rules_ci95"]
        md.append(f"| {sid} | {x['label']} | {x['M1_starts_changed_vs_S0']} | {x['M2_expected_deadline_misses']} | "
                  f"{x['M3_mean_cost_own_rules_usd_m']} | {x['M3_diff_vs_S0_own_rules_usd_m']:+.1f} ({a} to {b}) | "
                  f"{x['M3_diff_vs_S0_scored_with_S0_rules_usd_m']:+.1f} ({c} to {d}) | "
                  f"{x['M4_price_of_compliance_usd_m']:+.1f} | {x['M5_protected_by_2030']:.1%} / {x['M5_protected_by_2032']:.1%} |")
    md += ["", "## Rules and explanations", "",
           "| ID | Hard deadline (anchors) | Deadline set by | Retention years (anchors) | "
           "Validity | Faithfulness | Scenario-rule sentences | Names NIST for another source |",
           "|---|---|---|---|---|---|---|---|"]
    for sid, x in res.items():
        e = x["M8_explanations"]
        md.append(f"| {sid} | {x['M6_hard_deadline_quarter']} | {x['M6_deadline_decided_by']} | {x['M6_retention_years']} | "
                  f"{e['citation_validity']:.3f} | {e['faithfulness']:.3f} | {x['M8_sentences_citing_scenario_rules']} | "
                  f"{x['M8_sentences_naming_nist_for_another_source']} |")
    md += ["", "## Planned misses by issuer (no delay)", ""]
    for sid, x in res.items():
        if x["M2_planned_misses_by_issuer"]:
            md.append(f"- {sid}: {x['M2_planned_misses_by_issuer']}")
    for sid in ("S3", "S6"):
        if res[sid]["diagnose_by_2031"]:
            md.append(f"- {sid}, issuers that cannot fit by 2031 Q1 whatever the order: "
                      + ", ".join(f"{g['issuer_group']} ({g['slots_needed']} needed, {g['slots_available']} available)"
                                  for g in res[sid]["diagnose_by_2031"]))
    (out / f"{tag}.md").write_text("\n".join(md) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    main()
