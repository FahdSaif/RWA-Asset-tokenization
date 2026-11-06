"""Metadata-level privacy simulations (branch D) with *realistic synthetic* generators.

All data here is synthetic and labelled as such (see docs/DATA.md). The generators use distributions that
resemble real traffic (heavy-tailed inter-arrival times, Zipf-concentrated jurisdictions, memoryless
presentation delays) and every result is reported over many seeds with a 95 % interval. Real traces can be
analysed with the same attacker through `load_event_pairs_csv` / `linkage_from_pairs`.
"""
from __future__ import annotations

import csv
import math
import random
import statistics
from pathlib import Path


def lognormal_gaps(rnd: random.Random, n: int, mean: float, sigma: float = 1.0) -> list[int]:
    mu = math.log(mean) - sigma ** 2 / 2
    return [max(1, round(rnd.lognormvariate(mu, sigma))) for _ in range(n)]


def _greedy_link(events: list[int], subs: list[tuple[int, float, int]]) -> float:
    """Attacker: match each observed submission to the latest unmatched earlier event."""
    subs = sorted(subs)                                  # ties broken by a random key (shuffled release)
    unmatched = sorted(range(len(events)), key=lambda i: events[i])
    correct = 0
    for t, _, truth in subs:
        cands = [i for i in unmatched if events[i] <= t]
        guess = cands[-1] if cands else unmatched[0]
        unmatched.remove(guess)
        correct += guess == truth
    return correct / len(events)


def timing_linkage(n: int = 300, mean_gap: float = 10.0, epoch: int | None = None, seed: int = 11,
                   jitter_mean: float = 2.0, sigma: float = 1.0) -> float:
    """D1: fraction of on-chain submissions linked to the off-chain event (e.g. an exchange withdrawal) that
    caused them. Heavy-tailed gaps; exponential reaction delay; `epoch` models batched, shuffled release (M9)."""
    rnd = random.Random(seed)
    events, t = [], 0
    for g in lognormal_gaps(rnd, n, mean_gap, sigma):
        t += g
        events.append(t)
    subs = []
    for i, e in enumerate(events):
        sub = e + 1 + int(rnd.expovariate(1 / jitter_mean)) if epoch is None else math.ceil((e + 1) / epoch) * epoch
        subs.append((sub, rnd.random(), i))
    return _greedy_link(events, subs)


def ci95(xs: list[float]) -> tuple[float, float, float]:
    m = statistics.fmean(xs)
    h = 1.96 * (statistics.stdev(xs) / math.sqrt(len(xs)) if len(xs) > 1 else 0.0)
    return m, max(0.0, m - h), min(1.0, m + h)


def linkage_stats(runs: int = 40, **kw) -> tuple[float, float, float]:
    return ci95([timing_linkage(seed=s, **kw) for s in range(runs)])


def epoch_sweep(ratios=(1, 2, 3, 5, 8, 10, 20), runs: int = 40, mean_gap: float = 10.0) -> list[dict]:
    """Linkage versus expected events per batching epoch."""
    return [dict(events_per_epoch=r, **dict(zip(("mean", "lo", "hi"),
            linkage_stats(runs, mean_gap=mean_gap, epoch=int(r * mean_gap))))) for r in ratios]


def zipf_weights(k: int, s: float = 1.0) -> list[float]:
    w = [1 / (i + 1) ** s for i in range(k)]
    z = sum(w)
    return [x / z for x in w]


def issuer_timing_linkage(delay_mean: float, n: int = 60, gap_mean: float = 3.0, seed: int = 5) -> float:
    """D3 residual channel: a blind issuer still sees issuance times. Poisson issuance, exponential presentation
    delay; the issuer links each presentation to the latest earlier issuance."""
    rnd = random.Random(seed)
    t, issue = 0.0, []
    for _ in range(n):
        t += rnd.expovariate(1 / gap_mean)
        issue.append(t)
    pres = sorted((issue[i] + rnd.expovariate(1 / delay_mean), i) for i in range(n))
    correct = 0
    for tp, truth in pres:
        guess = max((j for j in range(n) if issue[j] <= tp), key=lambda j: issue[j], default=0)
        correct += guess == truth
    return correct / n


def delay_sweep(delays=(1, 5, 20, 60, 200), runs: int = 40) -> list[dict]:
    return [dict(delay_mean=d, **dict(zip(("mean", "lo", "hi"),
            ci95([issuer_timing_linkage(d, seed=s) for s in range(runs)])))) for d in delays]


# ---- run the same attacker on REAL traces --------------------------------------------------------
def load_event_pairs_csv(path: str | Path) -> list[tuple[int, int]]:
    """CSV with header `event_tick,submit_tick` (e.g. exchange-withdrawal time, on-chain proof time)."""
    with open(path, newline="") as f:
        return [(int(r["event_tick"]), int(r["submit_tick"])) for r in csv.DictReader(f)]


def linkage_from_pairs(pairs: list[tuple[int, int]], seed: int = 0) -> float:
    rnd = random.Random(seed)
    events = [e for e, _ in pairs]
    return _greedy_link(events, [(s, rnd.random(), i) for i, (_, s) in enumerate(pairs)])
