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
    ap.add_argument("command", choices=["scenarios", "risk", "modelcheck", "mediation", "hypotheses", "all"], nargs="?", default="all")
    ap.add_argument("--out", type=Path, help="write reports (markdown/json) to this directory")
    ap.add_argument("--details", action="store_true", help="print the evidence line of every scenario run")
    a = ap.parse_args(argv)
    cmds = ["scenarios", "risk", "modelcheck", "mediation", "hypotheses"] if a.command == "all" else [a.command]
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
