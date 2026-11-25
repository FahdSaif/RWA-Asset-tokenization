"""Command-line interface.

  python -m qamp census                      anchors derived from the real census (results/census_anchors.md)
  python -m qamp facts                       classify notebook observations (data/q1_raw.json -> data/anchor_facts.json)
  python -m qamp discover [--source-dir D] [--labels F] [--llm]
                                             CBOM from ABIs + controllers (+ verified source); score against labels
  python -m qamp plan                        QAMP plan with grounded rationales (results/plan.md)
  python -m qamp sensitivity                 EXPLORATORY grid: capacity x renewal period x hazard (dev seeds)
  python -m qamp experiments [--quick]       development run: main, period-1, accelerated, guard + hypotheses
  python -m qamp experiments --held-out --frozen-commit <sha>
                                             the pre-registered run (held-out seeds; run once, after freezing)
"""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

from . import config, evaluate, explain, guard, hypotheses, planner, scenarios
from .data import load_census, summary
from .kb import load_kb
from .kb.engine import anchor_facts


def _out(sub: str) -> Path:
    p = config.RESULTS_DIR / sub
    p.mkdir(parents=True, exist_ok=True)
    return p


def _git_commit() -> str:
    try:
        return subprocess.run(["git", "-C", str(config.REPO_ROOT), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    except OSError:
        return "unknown"


def _load(args):
    facts = Path(args.facts) if getattr(args, "facts", None) else config.DATA_DIR / "anchor_facts.json"
    cals = Path(args.calendars) if getattr(args, "calendars", None) else config.DATA_DIR / "calendars.csv"
    q1 = config.DATA_DIR / "q1_raw.json"
    return load_census(facts_path=facts if facts.exists() else None, calendars_path=cals if cals.exists() else None,
                       q1_raw_path=q1 if q1.exists() else None)


def cmd_facts(args) -> None:
    """Classify the extraction notebook's observations (data/q1_raw.json) into data/anchor_facts.json."""
    from .extraction import digest, facts_from_raw
    raw_p = config.DATA_DIR / "q1_raw.json"
    if not raw_p.exists():
        raise SystemExit("data/q1_raw.json not found: run notebooks/Q1_fetch_anchor_facts.ipynb and unzip into qamp/data/")
    raw = json.loads(raw_p.read_text())
    summ_p = config.DATA_DIR / "q1_summary.json"
    if summ_p.exists() and json.loads(summ_p.read_text()).get("sha256_raw") != digest(raw):
        raise SystemExit("q1_raw.json does not match the digest in q1_summary.json")
    facts = facts_from_raw(raw)
    (config.DATA_DIR / "anchor_facts.json").write_text(json.dumps(facts, indent=1, sort_keys=True))
    n = len(facts)
    print(f"{n} controller addresses; exposed {sum(f['key_exposed'] is True for f in facts.values())}, "
          f"not exposed {sum(f['key_exposed'] is False for f in facts.values())}, unknown {sum(f['key_exposed'] is None for f in facts.values())}")


def cmd_census(args) -> None:
    dep = _load(args)
    s = summary(dep)
    out = _out("census")
    rows = ["| Anchor | Role | Controller | Keys | Tokens | Value at risk (USD m) | Group | Exposure | Calendar |",
            "|---|---|---|---|---|---|---|---|---|"]
    for a in sorted(dep.anchors, key=lambda a: -a.value_usd):
        rows.append(f"| {a.anchor_id[:22]}… | {a.role} | {a.controller_type} | {a.n_keys} | {len(a.tokens)} | {a.value_usd / 1e6:,.0f} | "
                    f"{a.issuer_group} | {a.provenance.get('key_exposed')} | {a.calendar.period}q/{a.calendar.source} |")
    (out / "census_anchors.md").write_text(f"Source: {dep.source}\n\n```json\n{json.dumps(s, indent=1)}\n```\n\n" + "\n".join(rows) + "\n")
    (out / "census_anchors.json").write_text(json.dumps(dict(summary=s, anchors=[a.__dict__ | dict(calendar=a.calendar.__dict__) for a in dep.anchors]), indent=1, default=str))
    print(json.dumps(s, indent=1))
    print(f"wrote {out}")


def cmd_discover(args) -> None:
    from .discovery import LLMClassifier, RulesClassifier, scan_abi, scan_source
    from .discovery.abi import scan_controllers
    from .discovery.cbom import read_labels, score, to_cbom
    from .discovery.classify import entries_to_json
    dep = _load(args)
    findings = [f for t in dep.tokens for f in scan_abi(t.address, t.abi_functions)] + scan_controllers(dep)
    if args.source_dir:
        for p in sorted(Path(args.source_dir).glob("0x*.sol*")):
            findings += scan_source(p.name.split(".")[0].lower(), p.read_text())
    out = _out("discovery")
    clf = LLMClassifier(log_path=out / "llm_log.jsonl") if args.llm else RulesClassifier()
    entries = clf.classify(findings)
    (out / f"inventory_{clf.name}.json").write_text(json.dumps(entries_to_json(entries), indent=1))
    (out / f"cbom_{clf.name}.json").write_text(json.dumps(to_cbom(entries, "rwa-census-25"), indent=1))
    res = dict(findings=len(findings), entries=len(entries), classifier=clf.name)
    if args.llm:
        res.update(hallucinated_citations=clf.hallucinated, dropped_entries=clf.dropped)
    if args.labels:
        res["score"] = score(entries, read_labels(Path(args.labels)))
    (out / f"discovery_{clf.name}.json").write_text(json.dumps(res, indent=1))
    print(json.dumps(res, indent=1))


def cmd_plan(args) -> None:
    from .discovery import RulesClassifier, scan_abi
    from .discovery.abi import scan_controllers
    dep = _load(args)
    kb = load_kb()
    ctx = planner.kb_context(dep, kb)
    ss = scenarios.sample(20_000, len(dep.anchors), seed=config.DEV_SEED_BASE + 1)
    p = planner.plan(dep, kb, ss, ctx=ctx)
    entries = RulesClassifier().classify([f for t in dep.tokens for f in scan_abi(t.address, t.abi_functions)] + scan_controllers(dep))
    ev_by_token: dict[str, list[str]] = {}
    for e in entries:
        ev_by_token.setdefault(e.token, []).extend(e.evidence)
    lines = [f"# QAMP plan (development scenarios)\n\nSource: {dep.source}. Solver: {p.status}. "
             f"Objective (expected loss + spend): USD {p.objective / 1e6:,.1f}m.\n"]
    for a in sorted(dep.anchors, key=lambda a: (p.starts[a.anchor_id], -a.value_usd)):
        inf = ctx[a.anchor_id]["inference"]
        ev = [e for t in a.tokens for e in ev_by_token.get(t, [])][:3]
        r = explain.write(a, p.starts[a.anchor_id], inf, ev)
        kept, dropped = explain.validate(r.sentences, r.allowed)
        lines.append(f"## {a.anchor_id}\n\nValue at risk USD {a.value_usd / 1e6:,.0f}m · {a.role} · {a.controller_type} · group {a.issuer_group}\n")
        lines += [f"- {s}" for s in kept]
        if dropped:
            lines.append(f"- ({dropped} sentence(s) dropped by the citation check)")
        lines.append("")
    out = _out("plan")
    (out / "plan.md").write_text("\n".join(lines))
    (out / "plan.json").write_text(json.dumps(dict(starts=p.starts, status=p.status, objective=p.objective, info=p.info), indent=1, default=str))
    print(f"wrote {out / 'plan.md'}")


def cmd_experiments(args) -> None:
    if args.held_out and not args.frozen_commit:
        raise SystemExit("--held-out needs --frozen-commit <sha> of the frozen instrument (docs/PREREGISTRATION.md)")
    base = config.HELD_OUT_SEED_BASE if args.held_out else config.DEV_SEED_BASE
    quick = args.quick
    rc = evaluate.RunConfig(seed_base=base, n_plan=5_000 if quick else 20_000, n_eval=500 if quick else 2_000,
                            n_oracle=50 if quick else 200)
    dep = _load(args)
    kb = load_kb()
    tag = ("held_out" if args.held_out else "dev") + ("_quick" if quick else "")
    out = _out(tag)
    results = {}
    print("main …")
    results["main"] = evaluate.run_policies(dep, kb, rc)
    print("period-1 calendars …")
    rc1 = evaluate.RunConfig(**{**rc.__dict__, "oracle": False})
    results["period1"] = evaluate.run_policies(evaluate.with_calendar_period(dep, 1), kb, rc1,
                                               include=("qamp_stochastic", "asap_fifo", "none"))
    print("accelerated timeline …")
    rca = evaluate.RunConfig(**{**rc.__dict__, "oracle": False, "shift_years": 2.0})
    results["accelerated"] = evaluate.run_policies(dep, kb, rca, include=("qamp_stochastic",) + hypotheses.LIST_BASELINES + ("none",))
    print("tight condition (8-quarter renewals, capacity 1) …")
    from .planner import PlanParams
    rct = evaluate.RunConfig(**{**rc.__dict__, "oracle": False, "pp": PlanParams(capacity=1)})
    results["tight"] = evaluate.run_policies(evaluate.with_calendar_period(dep, 8), kb, rct,
                                             include=("qamp_stochastic", "asap_fifo", "none"))
    print("guard …")
    results["guard"] = evaluate.run_guard(dep, kb, rc)
    rows = hypotheses.evaluate_all(results)
    meta = dict(seed_base=base, held_out=args.held_out, frozen_commit=args.frozen_commit, git_commit=_git_commit(),
                run_config=rc.as_dict(), env=evaluate.environment(), kb_unverified_rules=kb.unverified())
    (out / "results.json").write_text(json.dumps(dict(meta=meta, results=results, hypotheses=rows), indent=1, default=str))
    note = (f"Seeds from {base} ({'HELD-OUT, pre-registered run' if args.held_out else 'development seeds, not evidence'}); "
            f"commit {meta['git_commit'][:10] or 'n/a'}; n_eval {rc.n_eval}, n_plan {rc.n_plan}, oracle on {rc.n_oracle}.")
    (out / "hypotheses.md").write_text(hypotheses.markdown(rows, note))
    (out / "main_table.md").write_text(_main_table(results["main"]))
    print(hypotheses.markdown(rows, note))
    print(f"wrote {out}")


def cmd_sensitivity(args) -> None:
    dep = _load(args)
    rows = evaluate.run_sensitivity(dep, load_kb())
    out = _out("dev_sensitivity")
    md = ["EXPLORATORY, development seeds. QAMP-stochastic vs ASAP and annual review; differences in USD m (positive: QAMP cheaper).",
          "", "| Renewal period (q) | Capacity | Hazard /y | QAMP mean | ASAP - QAMP | rel. | p | Annual - QAMP | p |",
          "|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        md.append(f"| {r['period']} | {r['capacity']} | {r['hazard']} | {r['qamp_mean'] / 1e6:,.1f} | {r['asap_minus_qamp'] / 1e6:+.2f} | "
                  f"{r['asap_rel']:+.2%} | {r['p_asap']:.2g} | {r['annual_minus_qamp'] / 1e6:+.2f} | {r['p_annual']:.2g} |")
    (out / "sensitivity.md").write_text("\n".join(md) + "\n")
    (out / "sensitivity.json").write_text(json.dumps(rows, indent=1))
    print("\n".join(md))


def _main_table(r: dict) -> str:
    s = "| Policy | Mean realized cost (USD m) | 95% CI | Protected by 2030 | Protected by 2032 | Diff vs QAMP (USD m) | p (Holm) |\n|---|---|---|---|---|---|---|\n"
    for k, v in sorted(r["summary"].items(), key=lambda kv: kv[1]["mean"]):
        t = r["tests"].get("oracle_subset" if k == "oracle" else k, {})
        s += (f"| {k} | {v['mean'] / 1e6:,.1f} | {v['ci95'][0] / 1e6:,.1f}–{v['ci95'][1] / 1e6:,.1f} | "
              f"{v.get('protected_by_2030', float('nan')):.3f} | {v.get('protected_by_2032', float('nan')):.3f} | "
              f"{t.get('mean_diff', 0) / 1e6:+.2f} | {t.get('p_holm', float('nan')):.2g} |\n")
    return s + "\nThe oracle row is computed on the oracle subset of evaluation scenarios only.\n"


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(prog="qamp")
    ap.add_argument("--facts", help="anchor_facts.json from the extraction notebook")
    ap.add_argument("--calendars", help="observed or documented calendars CSV")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("census")
    sub.add_parser("facts")
    d = sub.add_parser("discover")
    d.add_argument("--source-dir")
    d.add_argument("--labels")
    d.add_argument("--llm", action="store_true")
    sub.add_parser("plan")
    sub.add_parser("sensitivity")
    e = sub.add_parser("experiments")
    e.add_argument("--quick", action="store_true")
    e.add_argument("--held-out", action="store_true")
    e.add_argument("--frozen-commit")
    args = ap.parse_args(argv)
    dict(census=cmd_census, facts=cmd_facts, discover=cmd_discover, plan=cmd_plan, sensitivity=cmd_sensitivity, experiments=cmd_experiments)[args.cmd](args)


if __name__ == "__main__":
    main()
