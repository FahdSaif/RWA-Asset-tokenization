"""Measure ZK proof-generation / verification cost and proof size by invoking the
circuit scripts. Substantiates the paper's 'within practical range' claim with
YOUR numbers, not a citation. Writes CSV."""
from __future__ import annotations
import csv, json, os, subprocess, sys

ROOT = os.path.join(os.path.dirname(__file__), "..")
CIRC = os.path.join(ROOT, "circuits")
OUT = os.path.join(ROOT, "results", "raw", "zkp.csv")
N = int(os.environ.get("ARCA_ZK_N", "20"))

def _node(script, *args):
    p = subprocess.run(["node", os.path.join("scripts", script), *args],
                       cwd=CIRC, capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(p.stderr)
    return json.loads(p.stdout.strip().splitlines()[-1])

def run():
    if not os.path.exists(os.path.join(CIRC, "build", "accreditation_final.zkey")):
        print("[setup needed] run: cd circuits && npm run compile && npm run setup")
        return
    rows = []
    try:
        for i in range(N):
            pr = _node("prove.js", "1500000", "1000000")
            ve = _node("verify.js")
            rows.append({"run": i, "prove_ms": pr["prove_ms"],
                         "verify_ms": ve["verify_ms"], "proof_bytes": pr["proof_size_bytes"]})
    except Exception as e:
        print(f"error running circuit scripts: {e}"); return
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["run", "prove_ms", "verify_ms", "proof_bytes"])
        w.writeheader(); w.writerows(rows)
    avg_p = sum(r["prove_ms"] for r in rows) / len(rows)
    avg_v = sum(r["verify_ms"] for r in rows) / len(rows)
    print(f"n={len(rows)} avg_prove={avg_p:.1f}ms avg_verify={avg_v:.2f}ms -> {OUT}")

if __name__ == "__main__":
    run()
