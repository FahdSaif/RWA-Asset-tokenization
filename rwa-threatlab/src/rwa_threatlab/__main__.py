"""Command line: python -m rwa_threatlab {scenarios,risk,modelcheck,mediation,all} [--out DIR]"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import modelcheck, risk
from .config import Config
from .scenarios import ALL
from .scenarios.base import make_world, ASSET


def scenarios_md(results=None) -> str:
    results = results or {s.id: s.execute() for s in ALL}
    sym = lambda o: "attack succeeds" if o.attack_succeeded else "blocked"  # noqa: E731
    lines = ["| ID | Tree node | Scenario | Adversary | Baseline | Hardened | Residual |", "|---|---|---|---|---|---|---|"]
    for s in ALL:
        r = results[s.id]
        res = f"**{sym(r['residual'])}**" if "residual" in r else "n/a"
        lines.append(f"| {s.id} | {s.node} | {s.name} | {s.adversary} | {sym(r['baseline'])} | {sym(r['hardened'])} | {res} |")
    return "\n".join(lines)


def mediation_md() -> str:
    out = []
    for label, cfg in (("baseline (faulty) build", Config.baseline()), ("hardened build", Config.hardened())):
        w = make_world(cfg)
        rep = w.o.mediation_report(ASSET, "u", w.signers)
        out += [f"**{label}**", "", "| Path | Entry point | Mediated by the Gateway | Evidence |", "|---|---|---|---|"]
        for r in rep:
            out.append(f"| {r['path']} | {r['entry point']} | {'yes' if r['mediated'] else '**NO**'} | {r['note']} |")
        out.append("")
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="rwa_threatlab", description=__doc__)
    ap.add_argument("command", choices=["scenarios", "risk", "modelcheck", "scaled", "mediation", "hypotheses", "h11", "ofac-parse", "real", "all"], nargs="?", default="all")
    ap.add_argument("--out", type=Path, help="write reports (markdown/json) to this directory")
    ap.add_argument("--inputs", nargs="*", default=[], help="ofac-parse: sdnnewYY.txt files")
    ap.add_argument("--only", nargs="*", default=["ofac", "timing", "bridge"], choices=["ofac", "timing", "bridge"], help="real: sections to run")
    ap.add_argument("--force", action="store_true", help="real: run although the tree is not committed (logged in the output)")
    ap.add_argument("--details", action="store_true", help="print the evidence line of every scenario run")
    a = ap.parse_args(argv)
    if a.command == "ofac-parse":
        from .traces import ofac
        if not a.inputs or not a.out:
            ap.error("ofac-parse needs --inputs sdnnew19.txt ... and --out events.csv (a file path)")
        r = ofac.parse_files(a.inputs)
        ofac.write_events_csv(a.out, r["events"], r["renames"])
        print(f"{len(r['events'])} events, {len(r['renames'])} renames -> {a.out}")
        for f, d in r["diag"].items():
            print(f"  {f}: date blocks {d['date_blocks']}, headers {d['headers']}, entries {d['entries']}, long entries {d['long_entries']}")
            for h in d["unrecognised_headers"][:3]:
                print("     UNRECOGNISED HEADER:", h)
        return 0
    if a.command == "real":
        from . import hypotheses_real as hr
        try:
            res = hr.run_real(sections=tuple(a.only), force=a.force)
        except hr.GuardError as e:
            print("REFUSING TO RUN:", e)
            return 2
        print(hr.markdown(res))
        if a.out:
            a.out.mkdir(parents=True, exist_ok=True)
            (a.out / "real.json").write_text(json.dumps(res, indent=1, default=str) + "\n")
            (a.out / "real.md").write_text(hr.markdown(res))
            print(f"reports written to {a.out}/")
        return 0
    cmds = ["scenarios", "risk", "modelcheck", "scaled", "mediation", "hypotheses"] if a.command == "all" else [a.command]
    out: dict[str, str] = {}
    if "scenarios" in cmds:
        results = {s.id: s.execute() for s in ALL}
        out["scenarios.md"] = scenarios_md(results)
        print("## Attack scenarios (one per attack-tree leaf)\n\n" + out["scenarios.md"] + "\n")
        if a.details:
            for s in ALL:
                for v, o in results[s.id].items():
                    print(f"  {s.id:4s} {v:9s} {o.detail}")
        out["scenarios.json"] = json.dumps({sid: {v: dict(attack_succeeded=o.attack_succeeded, detail=o.detail,
                                                           metrics=o.metrics) for v, o in r.items()}
                                            for sid, r in results.items()}, indent=1, default=str)
    if "risk" in cmds:
        rows = risk.table()
        sens = risk.sensitivity()
        out["risk.md"] = risk.markdown_table(rows)
        out["sensitivity.json"] = json.dumps(sens, indent=1, default=str)
        print("## Risk assessment (rubric-derived)\n\n" + out["risk.md"] + "\n")
        print("Sensitivity:", json.dumps(sens, default=str), "\n")
    if "modelcheck" in cmds:
        print("## Mechanised consistency check\n")
        res = modelcheck.run(verbose=True)
        out["modelcheck.json"] = json.dumps(res, indent=1)
        print()
    if "scaled" in cmds:
        from . import modelcheck_scaled
        res = modelcheck_scaled.sweep(ks=(2, 3, 4, 5, 6), ns=(4, 6, 8, 12))
        out["modelcheck_scaled.md"] = modelcheck_scaled.markdown(res)
        out["modelcheck_scaled.json"] = json.dumps(res, indent=1)
        fd = risk.floor_dependence()
        out["floor_dependence.json"] = json.dumps(fd, indent=1, default=str)
        print("## Scaled composition / lag check (k chains x n participants; same semantics as the small model)\n\n"
              + out["modelcheck_scaled.md"] + "\n")
        print("Residual ranking without the trust-anchor floor (id, band):", [(i, risk.LV[b]) for i, b, _ in fd["without_floor"]], "\n")
    if "h11" in cmds:
        from . import hypotheses_v2 as hv2
        data = hv2.run_h11()
        ra, rb = hv2.h11a(data), hv2.h11b(data)
        out["h11.json"] = json.dumps(dict(H11a=dict(status=ra.status, evidence=ra.evidence), H11b=dict(status=rb.status, evidence=rb.evidence), data=data), indent=1, default=str)
        out["h11.md"] = f"| H11a | {ra.status} | {ra.evidence} |\n| H11b | {rb.status} | {rb.evidence} |"
        print("## H11 (independent oracle, seeds 40000-40599)\n\n" + out["h11.md"] + "\n")
    if "mediation" in cmds:
        out["mediation.md"] = mediation_md()
        print("## Mediation surface (executable Table 1)\n\n" + out["mediation.md"])
    if "hypotheses" in cmds:
        from . import hypotheses
        results = hypotheses.run_all()
        out["hypotheses.md"] = hypotheses.markdown(results)
        out["hypotheses.json"] = json.dumps({h.id: dict(statement=h.statement, status=r.status, evidence=r.evidence,
                                                        data=r.data) for h, r in results}, indent=1, default=str)
        print("\n## Research hypotheses (held-out seeds; outcomes are reported, not gated)\n\n" + out["hypotheses.md"])
    if a.out:
        a.out.mkdir(parents=True, exist_ok=True)
        for name, text in out.items():
            (a.out / name).write_text(text + "\n")
        print(f"reports written to {a.out}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
