"""Turn results/raw/*.csv into the figures for the evaluation section.
Generates PNGs into results/figures/. These are real figures — use them to
replace the placeholder Fig 2/3/4 in the manuscript where appropriate."""
from __future__ import annotations
import os
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

RAW = os.path.join(os.path.dirname(__file__), "..", "results", "raw")
FIG = os.path.join(os.path.dirname(__file__), "..", "results", "figures")

def latency():
    p = os.path.join(RAW, "latency.csv")
    if not os.path.exists(p): return
    df = pd.read_csv(p)
    plt.figure()
    plt.hist(df["latency_ms"], bins=20)
    plt.xlabel("transfer validation latency (ms)"); plt.ylabel("count")
    plt.title("Runtime validation latency")
    plt.tight_layout(); plt.savefig(os.path.join(FIG, "latency_hist.png"), dpi=200)

def zkp():
    p = os.path.join(RAW, "zkp.csv")
    if not os.path.exists(p): return
    df = pd.read_csv(p)
    plt.figure()
    plt.boxplot([df["prove_ms"], df["verify_ms"]], labels=["prove", "verify"])
    plt.ylabel("ms"); plt.title("ZK proof cost (accreditation predicate)")
    plt.tight_layout(); plt.savefig(os.path.join(FIG, "zkp_cost.png"), dpi=200)

if __name__ == "__main__":
    os.makedirs(FIG, exist_ok=True)
    latency(); zkp()
    print("figures ->", FIG)
