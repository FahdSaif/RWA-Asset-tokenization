"""Real transaction timing for the D1 experiment (H14, addendum A4).

Input: a CSV with a `timestamp` column (unix seconds, or ISO-8601) of one on-chain activity series, e.g. transfers of one
token. The real series replaces the synthetic heavy-tailed inter-arrival process; the attacker, the reaction delay and the
batching rule are unchanged from `scenarios/privacy.py`. Gaps are rescaled so the mean gap is 10 ticks (as in the synthetic
runs), which keeps the *shape* (burstiness) and drops the absolute time scale.
"""
from __future__ import annotations

import csv
import math
import random
from datetime import datetime, timezone
from pathlib import Path

from ..scenarios.privacy import _greedy_link, ci95, epoch_sweep

RATIOS = (1, 2, 3, 5, 8, 10, 20)
BLOCK, BOOT, SEED, MEAN_TICKS, JITTER = 300, 40, 2026, 10.0, 2.0


def _ts(v: str) -> float:
    v = v.strip()
    try:
        return float(v)
    except ValueError:
        dt = datetime.fromisoformat(v.replace("Z", "+00:00"))
        return (dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt).timestamp()   # naive times are read as UTC


def load_timestamps(path: str | Path, column: str = "timestamp") -> list[float]:
    with open(path, newline="") as f:
        rd = csv.DictReader(f)
        if column not in (rd.fieldnames or []):
            raise ValueError(f"column {column!r} not found; have {rd.fieldnames}")
        return sorted(_ts(r[column]) for r in rd if r[column].strip())


def gaps_in_ticks(ts: list[float]) -> list[int]:
    raw = [b - a for a, b in zip(ts, ts[1:])]
    if len(raw) < 2 * BLOCK:
        raise ValueError(f"need at least {2 * BLOCK + 1} timestamps, got {len(ts)}")
    scale = MEAN_TICKS / (sum(raw) / len(raw))
    return [max(1, round(g * scale)) for g in raw]


def _linkage(gaps: list[int], epoch: int | None, rnd: random.Random) -> float:
    events, t = [], 0
    for g in gaps:
        t += g
        events.append(t)
    subs = []
    for i, e in enumerate(events):
        sub = e + 1 + int(rnd.expovariate(1 / JITTER)) if epoch is None else math.ceil((e + 1) / epoch) * epoch
        subs.append((sub, rnd.random(), i))
    return _greedy_link(events, subs)


def real_sweep(gaps: list[int], ratios=RATIOS, boot: int = BOOT, block: int = BLOCK, seed: int = SEED) -> list[dict]:
    """Linkage versus expected events per epoch, with circular block resampling of the real gap series."""
    out = []
    n = len(gaps)
    for r in ratios:
        vals = []
        for b in range(boot):
            rnd = random.Random(seed * 1000 + b)
            start = rnd.randrange(n)
            sample = [gaps[(start + j) % n] for j in range(block)]
            vals.append(_linkage(sample, int(r * MEAN_TICKS), rnd))
        m, lo, hi = ci95(vals)
        out.append(dict(events_per_epoch=r, mean=m, lo=lo, hi=hi))
    return out


def burstiness(gaps: list[int]) -> dict:
    """Coefficient of variation of the rescaled gaps (1 = Poisson; the synthetic log-normal with sigma=1 gives ~1.3)."""
    m = sum(gaps) / len(gaps)
    sd = (sum((g - m) ** 2 for g in gaps) / len(gaps)) ** 0.5
    return dict(n_gaps=len(gaps), mean_ticks=m, cv=sd / m)


def evaluate_h14(real: list[dict]) -> tuple[str, str]:
    first, last = real[0], real[-1]
    below = [r["events_per_epoch"] for r in real if r["hi"] < 0.25]
    smallest = min(below) if below else None
    ok = first["mean"] >= 0.25 and last["hi"] < 0.25 and smallest is not None and 2 <= smallest <= 10
    ev = (f"real timing: linkage {first['mean']:.0%} at {first['events_per_epoch']} event/epoch, "
          f"{last['mean']:.0%} (upper CI {last['hi']:.0%}) at {last['events_per_epoch']}; smallest ratio with upper CI < 25%: {smallest}")
    return ("CONFIRMED" if ok else "REFUTED"), ev


def synthetic_reference() -> list[dict]:
    return epoch_sweep(ratios=RATIOS, runs=BOOT)
