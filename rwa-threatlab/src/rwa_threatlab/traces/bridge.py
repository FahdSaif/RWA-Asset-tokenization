"""Real bridge latency (H15, descriptive; addendum A5).

Input CSV with either `latency_seconds`, or `src_timestamp` and `dst_timestamp` (unix seconds or ISO-8601), one row per
completed bridge transfer. Reports quantiles and the share above fixed thresholds. No tick mapping is imposed.
"""
from __future__ import annotations

import csv
from pathlib import Path

from .timing import _ts

THRESHOLDS = (60, 300, 3600)


def load_latencies(path: str | Path, src_col: str = "src_timestamp", dst_col: str = "dst_timestamp",
                   lat_col: str = "latency_seconds") -> tuple[list[float], int]:
    out, dropped = [], 0
    with open(path, newline="") as f:
        rd = csv.DictReader(f)
        cols = rd.fieldnames or []
        for r in rd:
            if lat_col in cols and r[lat_col].strip():
                v = float(r[lat_col])
            elif src_col in cols and dst_col in cols:
                v = _ts(r[dst_col]) - _ts(r[src_col])
            else:
                raise ValueError(f"need column {lat_col!r} or {src_col!r}+{dst_col!r}; have {cols}")
            if v < 0:
                dropped += 1
            else:
                out.append(v)
    return out, dropped


def q(xs: list[float], p: float) -> float:
    s = sorted(xs)
    i = min(len(s) - 1, max(0, round(p * (len(s) - 1))))
    return s[i]


def summarise(lat: list[float], dropped: int = 0) -> dict:
    if len(lat) < 100:
        raise ValueError(f"need at least 100 transfers, got {len(lat)}")
    return dict(n=len(lat), dropped_negative=dropped, median_s=q(lat, 0.5), p95_s=q(lat, 0.95), p99_s=q(lat, 0.99),
                max_s=max(lat), share_over={str(t): sum(x > t for x in lat) / len(lat) for t in THRESHOLDS})
