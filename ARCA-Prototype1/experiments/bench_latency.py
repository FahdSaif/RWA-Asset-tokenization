"""Measure transfer-validation latency (submission -> inclusion) over N runs.
Report the median/p95 and DISCLOSE THE MACHINE in the paper. Writes CSV."""
from __future__ import annotations
import csv, os, sys, time, statistics
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "offchain"))

OUT = os.path.join(os.path.dirname(__file__), "..", "results", "raw", "latency.csv")
N = int(os.environ.get("ARCA_BENCH_N", "50"))

def run():
    try:
        from submit_compliant import submit
    except Exception as e:
        print(f"import error ({e})"); return
    samples = []
    try:
        for i in range(N):
            t0 = time.perf_counter()
            submit(asset_id=42)
            samples.append((time.perf_counter() - t0) * 1000.0)
    except Exception as e:
        print(f"[dry-run] node not reachable ({e}); no samples collected."); return

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", newline="") as f:
        w = csv.writer(f); w.writerow(["run", "latency_ms"])
        for i, s in enumerate(samples): w.writerow([i, f"{s:.3f}"])
    print(f"n={len(samples)} median={statistics.median(samples):.2f}ms "
          f"p95={statistics.quantiles(samples, n=20)[18]:.2f}ms -> {OUT}")

if __name__ == "__main__":
    run()
