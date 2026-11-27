"""Command line.

  census          list the anchors
  facts           interpret the notebook data
  labels          merge bytecode and manual labels
  discover        build the CBOM and score it
  plan            make a plan with explanations
  explain-check   check the explanations (RQ4)
  sensitivity     exploratory grid
  experiments     development run; --held-out for the pre-registered run (once)"""
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
    """Uses the census until the notebook data exists, then the full sample."""
    facts = Path(args.facts) if getattr(args, "facts", None) else config.DATA_DIR / "anchor_facts.json"
    cals = Path(args.calendars) if getattr(args, "calendars", None) else config.DATA_DIR / "calendars.csv"
    q1 = config.DATA_DIR / "q1_raw.json"
    tokens = config.DATA_DIR / "sample_tokens.txt" if q1.exists() else config.CENSUS_TOKENS
    dep = load_census(tokens_path=tokens, facts_path=facts if facts.exists() else None,
                      calendars_path=cals if cals.exists() else None, q1_raw_path=q1 if q1.exists() else None,
                      calendar_policy=getattr(args, "calendar_policy", "observed_only"),
                      unobserved_roles=getattr(args, "unobserved_roles", "per_token"),
                      q1b_raw_path=config.DATA_DIR / "q1b_raw.json")
    if q1.exists() and not dep.source.startswith("extraction notebook"):
        print("WARNING: data/q1_raw.json does not cover every token of data/sample_tokens.txt; using the census records")
    return dep


def cmd_facts(args) -> None:
    """Interprets the notebook data: key exposure, bytecode labels, observed summary."""
    from .extraction import digest, facts_from_raw
    raw_p = config.DATA_DIR / "q1_raw.json"
    if not raw_p.exists():
        raise SystemExit("data/q1_raw.json not found: run notebooks/Q1_fetch_anchor_facts.ipynb and unzip into rwa-quantumclock/data/")
    raw = json.loads(raw_p.read_text())
    summ_p = config.DATA_DIR / "q1_summary.json"
    if summ_p.exists() and json.loads(summ_p.read_text()).get("sha256_raw") != digest(raw):
        raise SystemExit("q1_raw.json does not match the digest in q1_summary.json")
    import csv
    from collections import Counter
    from .observed import bytecode_labels
    q1b_p = config.DATA_DIR / "q1b_raw.json"
    if q1b_p.exists():                       # Q1b role getters, added to the checked Q1 records
        from .data import load_q1b
        from .extraction import merge_role_getters
        raw = merge_role_getters(raw, load_q1b(q1b_p))
    facts = facts_from_raw(raw)
    (config.DATA_DIR / "anchor_facts.json").write_text(json.dumps(facts, indent=1, sort_keys=True))
    rows = bytecode_labels(raw)
    with open(config.DATA_DIR / "labels_bytecode.csv", "w", newline="") as fh:
        wr = csv.DictWriter(fh, fieldnames=["token", "surface", "present", "annotator", "evidence", "notes"])
        wr.writeheader()
        wr.writerows(rows)
    dep = _load(args)
    obs_cal = Counter(a.calendar.source.split(":")[0] for a in dep.anchors)
    summary_obs = dict(
        tokens=len(raw["tokens"]), with_errors=sum(bool(t.get("errors")) for t in raw["tokens"]),
        q1b_used=q1b_p.exists(),
        controllers=len(facts), key_exposed=Counter(str(f["key_exposed"]) for f in facts.values()),
        bytecode_labels=len(rows), events=sum(len(t.get("events", [])) for t in raw["tokens"]),
        anchors=len(dep.anchors), calendars_by_source=dict(obs_cal), group_capacity=dep.group_capacity,
        multi_chain_anchors=len(dep.observed_topology),
        instances=Counter(c for v in dep.observed_topology.values() for c in v))
    out = _out("observed")
    (out / "observed_summary.json").write_text(json.dumps(summary_obs, indent=1, default=str))
    print(json.dumps(summary_obs, indent=1, default=str))


def cmd_label_sheet(args) -> None:
    """Writes the blank hand-label sheet: one row per distinct source code and surface."""
    import csv
    from .observed import MANUAL_SURFACES, code_groups
    toks = [ln.split()[0].lower() for ln in (config.DATA_DIR / "sample_tokens.txt").read_text().splitlines()
            if ln.strip() and not ln.startswith("#")]
    groups = code_groups(toks, config.DATA_DIR / "sources")
    with open(config.DATA_DIR / "code_groups.csv", "w", newline="") as fh:
        wr = csv.writer(fh)
        wr.writerow(["token", "code_group"])
        for rep, members in groups.items():
            for m in members:
                wr.writerow([m, rep])
    out = config.DATA_DIR / "labels_sheet_blank.csv"
    with open(out, "w", newline="") as fh:
        wr = csv.writer(fh)
        wr.writerow(["token", "tokens_with_same_code", "source_file", "surface", "present", "annotator", "evidence", "notes"])
        for rep, members in groups.items():
            src = f"sources/{rep}.impl.sol.txt" if (config.DATA_DIR / "sources" / f"{rep}.impl.sol.txt").exists() \
                else f"sources/{rep}.sol.txt"
            for surf in MANUAL_SURFACES:
                wr.writerow([rep, len(members), src, surf, "", "", "", ""])
    print(f"wrote {out.name}: {len(groups)} distinct codes x {len(MANUAL_SURFACES)} surfaces = "
          f"{len(groups) * len(MANUAL_SURFACES)} rows; data/code_groups.csv maps each token to its code")


def cmd_labels(args) -> None:
    """Merges bytecode labels with your manual labels. Bytecode wins where it can decide.

    A manual label on one token is copied to every token with identical code (data/code_groups.csv)."""
    import csv
    from .observed import BYTECODE_SURFACES
    bc_p, man_p = config.DATA_DIR / "labels_bytecode.csv", config.DATA_DIR / "labels_manual.csv"
    grp_p = config.DATA_DIR / "code_groups.csv"
    members: dict[str, list[str]] = {}
    if grp_p.exists():
        for r in csv.DictReader(open(grp_p, newline="")):
            members.setdefault(r["code_group"], []).append(r["token"])
    rows, ignored = [], []
    if bc_p.exists():
        rows += list(csv.DictReader(open(bc_p, newline="")))
    if man_p.exists():
        for r in csv.DictReader(open(man_p, newline="")):
            if r["surface"] in BYTECODE_SURFACES:
                ignored.append(r)
                continue
            for m in members.get(r["token"].lower(), [r["token"].lower()]):
                note = (r.get("notes") or "") + ("" if m == r["token"].lower() else f" (copied from identical code {r['token'][:10]})")
                rows.append(dict(r, token=m, notes=note.strip()))
    if not rows:
        raise SystemExit("no labels: run `python -m qamp facts` (bytecode labels) and/or write data/labels_manual.csv")
    with open(config.DATA_DIR / "labels.csv", "w", newline="") as fh:
        wr = csv.DictWriter(fh, fieldnames=["token", "surface", "present", "annotator", "evidence", "notes"])
        wr.writeheader()
        wr.writerows({k: r.get(k, "") for k in wr.fieldnames} for r in rows)
    print(f"wrote data/labels.csv: {len(rows)} rows; ignored {len(ignored)} manual rows for bytecode-decided surfaces")


def cmd_explain_check(args) -> None:
    """Runs the explanation checks; with --llm also tests LLM rewording."""
    res = _explain_results(_load(args), load_kb(), llm=args.llm)
    out = _out("explain")
    (out / "checks.json").write_text(json.dumps(res, indent=1))
    print(json.dumps(res, indent=1))


def _explain_results(dep, kb, llm: bool = False) -> dict:
    from .discovery import RulesClassifier, scan_abi
    from .discovery.abi import scan_controllers
    ctx = planner.kb_context(dep, kb)
    ss = scenarios.sample(5_000, len(dep.anchors), seed=config.DEV_SEED_BASE + 21)
    p = planner.plan(dep, kb, ss, ctx=ctx)
    entries = RulesClassifier().classify([f for t in dep.tokens for f in scan_abi(t.address, t.abi_functions)] + scan_controllers(dep))
    ev_tok: dict[str, list[str]] = {}
    for e in entries:
        ev_tok.setdefault(e.token, []).extend(e.evidence)
    evidence = {a.anchor_id: [e for t in a.tokens for e in ev_tok.get(t, [])][:3] for a in dep.anchors}
    rats = [explain.write(a, p.starts[a.anchor_id], ctx[a.anchor_id]["inference"], evidence[a.anchor_id]) for a in dep.anchors]
    res = dict(deterministic=explain.scores(rats), counterfactual=explain.counterfactual_consistency(dep, ctx, p.starts, kb, evidence))
    if llm:
        from .discovery.classify import LLMClassifier
        clf = LLMClassifier(log_path=config.RESULTS_DIR / "explain" / "llm_log.jsonl")
        tot = kept = 0
        for r in rats:
            def logged(prompt: str, _id: str = r.anchor_id) -> str:
                text = clf.transport(prompt)
                clf._log(_id, prompt, text)
                return text
            k, d = explain.rephrase_with_llm(r, logged)
            kept += len(k)
            tot += len(k) + d
        res["llm"] = dict(model=clf.model, sentences=tot, retained=kept / tot if tot else None)
    return res


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
        import csv
        from .observed import OBSERVED_ONLY_SURFACES
        labels = {k: v for k, v in read_labels(Path(args.labels)).items() if k[1] not in OBSERVED_ONLY_SURFACES}
        scored = [e for e in entries if e.surface not in OBSERVED_ONLY_SURFACES]
        res["score"] = score(scored, labels)                      # every token
        grp_p = config.DATA_DIR / "code_groups.csv"
        if grp_p.exists():                                         # each distinct code once
            firsts = {r["code_group"] for r in csv.DictReader(open(grp_p, newline=""))}
            res["score_per_distinct_code"] = score([e for e in scored if e.token.lower() in firsts],
                                                   {k: v for k, v in labels.items() if k[0] in firsts})
    (out / f"discovery_{clf.name}.json").write_text(json.dumps(res, indent=1))
    print(json.dumps(res, indent=1))


def _h9_from_discovery():
    """H9 from the saved rules-based discovery score (python -m qamp discover --labels data/labels.csv)."""
    f = config.RESULTS_DIR / "discovery" / "discovery_rules.json"
    if not f.exists():
        return None
    d = json.loads(f.read_text())
    if "score" not in d:
        return None
    o = d["score"]["overall"]
    per = d.get("score_per_distinct_code", {}).get("overall", {})
    ok = (o.get("recall") or 0) >= 0.90
    ev = (f"recall {o['recall']:.3f} (precision {o['precision']:.3f}, F1 {o['f1']:.3f}) over {o['tp'] + o['fn']} labelled positives"
          + (f"; per distinct code recall {per['recall']:.3f}" if per.get("recall") is not None else ""))
    return ("CONFIRMED" if ok else "REFUTED"), ev


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
    for d in p.info.get("diagnosis", []):
        lines.append(f"**Deadline cannot be met for {d['issuer_group']}:** its migrations need {d['slots_needed']} quarter-slots, "
                     f"but capacity {d['capacity']} over {d['quarters']} quarters gives {d['slots_available']}.\n")
    if p.info.get("overflow"):
        lines.append(f"Anchors that miss the deadline (scheduled in the last quarter, beyond capacity): "
                     f"{len(p.info['overflow'])}.\n")
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
    if getattr(args, "unobserved_roles", "per_token") != "per_token":
        tag += "_roles_" + args.unobserved_roles
    out = _out(tag)
    results = {}
    print("main …")
    results["main"] = evaluate.run_policies(dep, kb, rc)
    sm = results["main"]["summary"]
    dc = sm["qamp_stochastic"]["mean"] - sm["qamp_cost_first"]["mean"]
    dm = sm["qamp_cost_first"]["deadline_misses"] - sm["qamp_stochastic"]["deadline_misses"]
    results["price_of_compliance"] = dict(extra_cost_usd=dc, misses_avoided=dm,
                                          usd_per_miss_avoided=(dc / dm if dm > 0 else None),
                                          diagnosis=results["main"]["plans"]["qamp_stochastic"].get("info", {}).get("diagnosis"))
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
    print("explanations …")
    results["explanations"] = _explain_results(dep, kb)
    h9 = _h9_from_discovery()
    if h9:
        results["H9"] = h9
    rows = hypotheses.evaluate_all(results)
    from . import __version__
    meta = dict(seed_base=base, held_out=args.held_out, frozen_commit=args.frozen_commit, git_commit=_git_commit(),
                qamp_version=__version__, unobserved_roles=getattr(args, "unobserved_roles", "per_token"),
                run_config=rc.as_dict(), env=evaluate.environment(), kb_unverified_rules=kb.unverified())
    (out / "results.json").write_text(json.dumps(dict(meta=meta, results=results, hypotheses=rows), indent=1, default=str))
    note = (f"Seeds from {base} ({'HELD-OUT, pre-registered run' if args.held_out else 'development seeds, not evidence'}); "
            f"QAMP {__version__}; unseen role holders {meta['unobserved_roles']}; commit {meta['git_commit'][:10] or 'n/a'}; n_eval {rc.n_eval}, n_plan {rc.n_plan}, oracle on {rc.n_oracle}.")
    (out / "hypotheses.md").write_text(hypotheses.markdown(rows, note))
    poc = results["price_of_compliance"]
    if poc["misses_avoided"] > 0:
        poc_line = (f"Price of compliance (QAMP compliance-first vs cost-first): extra expected cost USD "
                    f"{poc['extra_cost_usd'] / 1e6:,.1f}m for {poc['misses_avoided']:.2f} fewer deadline misses.")
    else:   # both modes meet the deadline equally: any cost gap is solver rounding
        poc_line = ("Price of compliance: none. Both QAMP modes miss the deadline equally often "
                    f"(cost gap USD {poc['extra_cost_usd'] / 1e6:,.1f}m, within solver tolerance).")
    (out / "main_table.md").write_text(_main_table(results["main"]) + "\n\n" + poc_line + "\n")
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
    ap.add_argument("--calendar-policy", default="observed_only", choices=["observed_only", "lower_bound"],
                    help="how observed key changes become calendars (qamp.observed.calendars_from_events)")
    ap.add_argument("--unobserved-roles", default="per_token", choices=["per_token", "per_issuer"],
                    help="role holders that could not be listed: one key per token (default) or one per issuer")
    sub.add_parser("census")
    sub.add_parser("facts")
    sub.add_parser("label-sheet")
    sub.add_parser("labels")
    x = sub.add_parser("explain-check")
    x.add_argument("--llm", action="store_true")
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
    dict(census=cmd_census, facts=cmd_facts, labels=cmd_labels, **{"label-sheet": cmd_label_sheet, "explain-check": cmd_explain_check}, discover=cmd_discover, plan=cmd_plan, sensitivity=cmd_sensitivity, experiments=cmd_experiments)[args.cmd](args)


if __name__ == "__main__":
    main()
