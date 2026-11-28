"""EXPLORATORY: how much do the cost results depend on the assumed loss settings?

Changes one setting at a time (attack hazard, hidden-key weight, record value rho),
keeps the rest at the frozen base values, and compares QAMP with ASAP, greedy risk and Mosca.
Uses the held-out seeds (50,000) and the frozen code. Not part of the pre-registration.

Run from rwa-quantumclock:  python tools/loss_sensitivity.py
Quick test:                 python tools/loss_sensitivity.py --quick
Writes results/exploratory/loss_sensitivity.json and .md (or *_quick.* with --quick)."""
import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from qamp import __main__ as cli, config, evaluate  # noqa: E402
from qamp.kb import load_kb  # noqa: E402
from qamp.loss import LossParams  # noqa: E402

BASE = dict(hazard_per_year=1.0, hidden_weight=0.25, rho_records=0.002)
GRID = [("hazard_per_year", v) for v in (0.25, 0.5, 1.0, 2.0, 4.0)] + \
       [("hidden_weight", v) for v in (0.0, 0.1, 0.25, 0.5, 1.0)] + \
       [("rho_records", v) for v in (0.0, 0.002, 0.01, 0.05)]
OTHERS = ("asap_fifo", "greedy_risk", "mosca")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true", help="small run to test the script")
    args = ap.parse_args()
    n_plan, n_eval = (2_000, 200) if args.quick else (20_000, 2_000)
    dep = cli._load(argparse.Namespace())  # same data as the held-out run
    kb = load_kb()
    rows = []
    t0 = time.time()
    for name, value in GRID:
        lp = LossParams(**{**BASE, name: value})
        rc = evaluate.RunConfig(n_plan=n_plan, n_eval=n_eval, seed_base=config.HELD_OUT_SEED_BASE,
                                oracle=False, lp=lp)
        r = evaluate.run_policies(dep, kb, rc, include=("qamp_stochastic",) + OTHERS)
        row = dict(setting=name, value=value, qamp_mean=r["summary"]["qamp_stochastic"]["mean"] / 1e6)
        for o in OTHERS:
            t = r["tests"][o]
            row[o + "_minus_qamp"] = t["mean_diff"] / 1e6
            row[o + "_ci95"] = [x / 1e6 for x in t["mean_diff_ci95"]]
        rows.append(row)
        print(name, value, f"QAMP {row['qamp_mean']:.1f}", f"ASAP-QAMP {row['asap_fifo_minus_qamp']:+.1f}", flush=True)
    meta = dict(exploratory=True, seed_base=config.HELD_OUT_SEED_BASE, n_plan=n_plan, n_eval=n_eval,
                base=BASE, runtime_s=time.time() - t0, env=evaluate.environment())
    out = ROOT / "results" / "exploratory"
    out.mkdir(parents=True, exist_ok=True)
    tag = "loss_sensitivity" + ("_quick" if args.quick else "")
    (out / f"{tag}.json").write_text(json.dumps(dict(meta=meta, rows=rows), indent=1))
    md = ["# EXPLORATORY: sensitivity of costs to the loss settings", "",
          f"Held-out seeds from {config.HELD_OUT_SEED_BASE}; {n_plan:,} planning and {n_eval:,} evaluation scenarios; "
          "one setting changed at a time; base: hazard 1.0, hidden weight 0.25, rho 0.002. "
          "Differences in USD m; positive means QAMP is cheaper. Not pre-registered.", "",
          "| Setting | Value | QAMP mean | ASAP - QAMP (95% CI) | Greedy - QAMP | Mosca - QAMP |",
          "|---|---|---|---|---|---|"]
    for r in rows:
        lo, hi = r["asap_fifo_ci95"]
        md.append(f"| {r['setting']} | {r['value']} | {r['qamp_mean']:.1f} | {r['asap_fifo_minus_qamp']:+.1f} "
                  f"({lo:.1f} to {hi:.1f}) | {r['greedy_risk_minus_qamp']:+.1f} | {r['mosca_minus_qamp']:+.1f} |")
    (out / f"{tag}.md").write_text("\n".join(md) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    main()
