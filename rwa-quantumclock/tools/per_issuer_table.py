"""Per-issuer view of the frozen held-out plans (read only).

Run from rwa-quantumclock:  python tools/per_issuer_table.py
Writes results/held_out/per_issuer.md. Changes no other file."""
import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from qamp import __main__ as cli  # noqa: E402


def quarter(q):
    # Quarter 0 is 2027 Q1.
    return f"{2027 + q // 4} Q{q % 4 + 1}"


def main():
    dep = cli._load(argparse.Namespace())  # same data as the held-out run
    plans = json.loads((ROOT / "results/held_out/results.json").read_text())["results"]["main"]["plans"]
    qamp = plans["qamp_stochastic"]["starts"]
    asap = plans["asap_fifo"]["starts"]
    groups = defaultdict(list)
    for a in dep.anchors:
        groups[a.issuer_group].append(a)
    rows = []
    for g, anchors in groups.items():
        value = sum(a.value_usd for a in anchors) / 1e6
        observed = sum(1 for a in anchors if a.calendar.source.startswith("observed"))
        cap = dep.group_capacity.get(g, 2)
        qs = [qamp[a.anchor_id] for a in anchors]
        as_ = [asap[a.anchor_id] for a in anchors]
        rows.append((value, g, len(anchors), observed, cap, min(qs), max(qs), min(as_), max(as_)))
    rows.sort(key=lambda r: (-r[0], r[1]))
    out = ["# Per-issuer view of the held-out plans", "",
           "Source: results/held_out/results.json (frozen commit cb1c560). Anchor values overlap.", "",
           "| Issuer | Anchors | Anchor value (USD m) | Observed calendars | Capacity | QAMP starts | ASAP starts |",
           "|---|---|---|---|---|---|---|"]
    for v, g, n, o, c, q0, q1, a0, a1 in rows:
        out.append(f"| {g} | {n} | {v:,.0f} | {o} | {c} | {quarter(q0)} – {quarter(q1)} | {quarter(a0)} – {quarter(a1)} |")
    for name, s in (("QAMP", qamp), ("ASAP", asap)):
        by_year = defaultdict(int)
        for q in s.values():
            by_year[2027 + q // 4] += 1
        out.append(f"\n{name} starts by year: " + ", ".join(f"{y}: {n}" for y, n in sorted(by_year.items())))
    path = ROOT / "results/held_out/per_issuer.md"
    path.write_text("\n".join(out) + "\n")
    print("\n".join(out))


if __name__ == "__main__":
    main()
