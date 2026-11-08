"""Experiment A: anonymity sets of real token transfers under value bucketing and batching (plan section A).

Unit: a transfer event. k(event) = number of DISTINCT transactions that have an event in the same (time epoch, value bucket).
Epoch = floor(unix time / T) on a fixed grid. Value bucket: exact decimal value, or floor(ln(v) / ln(1 + r)) for a relative width r.
Zero-value events share one bucket. Reports are descriptive; no pass/fail test.
"""
from __future__ import annotations

import csv
import math
from collections import defaultdict
from decimal import Decimal
from pathlib import Path
from statistics import median

EPOCHS = {"1 min": 60, "10 min": 600, "1 hour": 3600, "6 hours": 21600, "1 day": 86400, "whole window": None}
BUCKETS = {"exact": 0.0, "1%": 0.01, "5%": 0.05, "10%": 0.10, "25%": 0.25}
TARGET_UNIQUE = 0.05


def load(path: str | Path) -> list[dict]:
    with open(path, newline="") as f:
        return [dict(timestamp=int(r["timestamp"]), tx=r["tx_hash"], value=Decimal(r["value"])) for r in csv.DictReader(f)]


def _bucket(v: Decimal, r: float):
    if v == 0:
        return "zero"
    return format(v.normalize(), "f") if r == 0 else math.floor(math.log(float(v)) / math.log1p(r))


def cell_stats(events: list[dict], epoch: int | None, r: float) -> dict:
    cells: dict[tuple, set] = defaultdict(set)
    keys = []
    for e in events:
        k = ((e["timestamp"] // epoch) if epoch else 0, _bucket(e["value"], r))
        cells[k].add(e["tx"])
        keys.append(k)
    ks = [len(cells[k]) for k in keys]
    n = len(ks)
    return dict(unique=sum(x == 1 for x in ks) / n, median_k=median(ks), ge5=sum(x >= 5 for x in ks) / n, ge20=sum(x >= 20 for x in ks) / n)


def analyse(events: list[dict]) -> dict:
    grid = {en: {bn: cell_stats(events, et, br) for bn, br in BUCKETS.items()} for en, et in EPOCHS.items()}
    # first bucket width (in grid order) at which fewer than 5% of events are unique, per epoch
    first_ok = {en: next((bn for bn in BUCKETS if grid[en][bn]["unique"] < TARGET_UNIQUE), None) for en in EPOCHS}
    txs = {e["tx"] for e in events}
    return dict(n_events=len(events), n_transactions=len(txs), t_first=min(e["timestamp"] for e in events), t_last=max(e["timestamp"] for e in events),
                grid=grid, first_bucket_below_5pct_unique=first_ok,
                a1_exact_1h_unique=grid["1 hour"]["exact"]["unique"], a2_10pct_1day_unique=grid["1 day"]["10%"]["unique"])


def markdown(res: dict) -> str:
    rows = ["| Epoch | " + " | ".join(BUCKETS) + " |", "|---|" + "---|" * len(BUCKETS)]
    for en in EPOCHS:
        rows.append(f"| {en} | " + " | ".join(f"{100 * res['grid'][en][bn]['unique']:.1f}% (k~{res['grid'][en][bn]['median_k']:g})" for bn in BUCKETS) + " |")
    return "Share of events that are unique (median anonymity set k in transactions), by epoch (rows) and value bucket width (columns):\n\n" + "\n".join(rows)
