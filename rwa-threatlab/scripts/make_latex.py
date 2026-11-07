#!/usr/bin/env python3
"""Generate LaTeX (booktabs) tables from docs/results/*.json so the paper's numbers come straight from the code.

    python scripts/make_latex.py            # writes docs/latex/*.tex  (real-data tables appear once docs/results/real/real.json exists)

Add `\\usepackage{booktabs}` to the paper. Include a table with `\\input{tab_scaled.tex}` etc.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from rwa_threatlab import risk  # noqa: E402

RES, OUT = ROOT / "docs" / "results", ROOT / "docs" / "latex"


def esc(s) -> str:
    return str(s).replace("\\", r"\textbackslash{}").replace("&", r"\&").replace("%", r"\%").replace("_", r"\_").replace("#", r"\#")


def table(caption: str, label: str, header: list[str], rows: list[list], colspec: str) -> str:
    body = "\n".join(" & ".join(esc(c) for c in r) + r" \\" for r in rows)
    return (f"\\begin{{table}}[t]\n\\centering\\small\n\\caption{{{caption}}}\n\\label{{{label}}}\n\\begin{{tabular}}{{{colspec}}}\n\\toprule\n"
            + " & ".join(esc(h) for h in header) + " \\\\\n\\midrule\n" + body + "\n\\bottomrule\n\\end{tabular}\n\\end{table}\n")


def scaled() -> str | None:
    p = RES / "modelcheck_scaled.json"
    if not p.exists():
        return None
    d = json.loads(p.read_text())
    rows = []
    for r in d["rows"]:
        c, n = r["checks"], r["instances"]
        f = lambda k: f"{c[k]['violating']}/{n}"  # noqa: E731
        rows.append([r["chains"], r["participants"], n, max(v["max_states"] for v in c.values()), f("alone"), f("bridge_baseline"),
                     f("bridge_dest_mediated"), f("lag_origin_only"), f("lag_atomic")])
    return table("Scaled composition and lag check: number of eligibility assignments (out of the instances tried) that admit a "
                 "violation. A single instance is safe, a baseline bridge is not, destination mediation and atomic activation close the gaps.",
                 "tab:scaled", ["$k$", "$n$", "inst.", "max states", "alone", "baseline bridge", "+ dest. mediation", "lag, origin only", "lag, atomic"],
                 rows, "rrrrlllll").replace("\\$k\\$", "$k$").replace("\\$n\\$", "$n$")


def floor() -> str:
    w, wo = risk.ranking(True), risk.ranking(False)
    nm = {s[0]: s[1] for s in risk.S}
    rows = [[i, nm[i], risk.LV[b], score, risk.LV[dict((x[0], x[1]) for x in wo)[i]]] for i, b, score in w]
    return table("Residual ranking with the trust-anchor floor and, in the last column, the band without it (only B1 changes). "
                 "Score is $L_{res}\\times I$.", "tab:floor", ["ID", "Scenario", "Residual band", "Score", "Band without floor"], rows, "llrrl").replace("\\$L\\_{res}\\textbackslash{}times I\\$", "")


def h11() -> str | None:
    p = RES / "h11.json"
    if not p.exists():
        return None
    d = json.loads(p.read_text())["data"]
    rows = [[k, v["traces"], v["violations"], v["disagreements"]] for k, v in d["cells"].items()]
    rows.append(["total", "", d["totals"]["violations"], d["totals"]["disagreements"]])
    t1 = table("H11a: independent oracle versus the fuzzer's oracle on the reserved seeds.", "tab:h11", ["Cell", "Traces", "Violations compared", "Disagreements"], rows, "lrrr")
    rows2 = [[k, f"{v['within']}/{v['violations']}", v["to_within"], v["to_beyond"], v["h1_unexplained"]] for k, v in d["sensitivity"].items()]
    t2 = table("H11b: sensitivity of the lag classification to the two readings of the definition (measurement tick/age origin).", "tab:h11b",
               ["Convention", "Within lag", "Flip to within", "Flip to beyond", "H1 unexplained"], rows2, "lrrrr")
    return t1 + "\n" + t2


def cuts() -> str | None:
    p = RES / "modelcheck.json"
    if not p.exists():
        return None
    d = json.loads(p.read_text())
    LB, RB, NL = "\\{", "\\}", " \\\\"
    fmt = lambda c: LB + ", ".join(esc(x) for x in c) + RB  # noqa: E731
    rows = [[esc(l["id"]), esc(l["name"]), "; ".join(fmt(c) for c in l["cuts"])] for l in d["ladder"]]
    body = "\n".join(" & ".join(r) + NL for r in rows)
    return ("\\begin{table}[t]\n\\centering\\small\n\\caption{Minimal adversary capability sets that reach a violation as mitigations are added "
            "(implementation faults A1, A2 omitted).}\n\\label{tab:cuts}\n\\begin{tabular}{lp{4.6cm}p{6.8cm}}\n\\toprule\nLevel & Added & Minimal attack sets"
            + NL + "\n\\midrule\n" + body + "\n\\bottomrule\n\\end{tabular}\n\\end{table}\n")


def real() -> str | None:
    p = RES / "real" / "real.json"
    if not p.exists():
        return None
    d = json.loads(p.read_text())
    rows = []
    if "ofac" in d:
        rows += [[k, s, e] for k, (s, e) in d["ofac"]["status"].items()] + [["H16", *d["ofac"]["H16"]]]
    if "timing" in d:
        rows.append(["H14", *d["timing"]["status"]])
    if "bridge" in d:
        rows.append(["H15", *d["bridge"]["status"]])
    return table("Pre-registered real-trace experiments (real traces, simulated compliance layer).", "tab:real", ["ID", "Outcome", "Evidence"], rows, "llp{9cm}")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    made = []
    for name, fn in (("tab_scaled", scaled), ("tab_floor", floor), ("tab_cuts", cuts), ("tab_h11", h11), ("tab_real", real)):
        tex = fn()
        if tex:
            (OUT / f"{name}.tex").write_text(tex)
            made.append(name)
    print("wrote", ", ".join(f"docs/latex/{m}.tex" for m in made))
    return 0


if __name__ == "__main__":
    sys.exit(main())
