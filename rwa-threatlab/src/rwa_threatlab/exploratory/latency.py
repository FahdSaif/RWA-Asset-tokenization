"""Experiment B: delay between OFAC listing of an Ethereum address and its on-chain blacklisting by USDC and USDT (plan section B).

Delay (days) = UTC date of the issuer's first blacklist event minus the date of first OFAC listing (date resolution only).
Addresses never blacklisted by the retrieval date are censored and reported as such. Descriptive; no test.
"""
from __future__ import annotations

import csv
import datetime as dt
from collections import defaultdict
from pathlib import Path
from statistics import median

TOKENS = ("USDC", "USDT")


def load_events(path: str | Path) -> list[dict]:
    with open(path, newline="") as f:
        return [dict(token=r["token"], address=r["address"].lower(), timestamp=int(r["timestamp"])) for r in csv.DictReader(f)]


def _q(xs: list[int], p: float) -> float:
    s = sorted(xs)
    return float(s[min(len(s) - 1, max(0, round(p * (len(s) - 1))))])


def _summ(delays: list[int], n_addr: int) -> dict:
    n = len(delays)
    out = dict(addresses=n_addr, blacklisted=n, share_blacklisted=n / n_addr if n_addr else None)
    if n:
        out.update(median_days=float(median(delays)), p25=_q(delays, .25), p75=_q(delays, .75), p90=_q(delays, .90),
                   within_1d=sum(d <= 1 for d in delays) / n, within_7d=sum(d <= 7 for d in delays) / n,
                   within_30d=sum(d <= 30 for d in delays) / n, before_listing=sum(d < 0 for d in delays) / n)
    return out


def analyse(ofac: dict[str, str], events: list[dict], as_of: str) -> dict:
    listed = {a: dt.date.fromisoformat(d) for a, d in ofac.items()}
    first: dict[tuple, int] = {}
    for e in events:
        a = e["address"]
        if a in listed:
            k = (e["token"], a)
            first[k] = min(first.get(k, e["timestamp"]), e["timestamp"])
    day = lambda ts: dt.datetime.fromtimestamp(ts, dt.timezone.utc).date()  # noqa: E731
    per_addr: dict[str, dict[str, int]] = defaultdict(dict)
    for (tok, a), ts in first.items():
        per_addr[a][tok] = (day(ts) - listed[a]).days
    res: dict = dict(as_of=as_of, ofac_addresses=len(listed), listing_dates=len(set(ofac.values())))
    for tok in TOKENS:
        res[tok] = _summ([v[tok] for v in per_addr.values() if tok in v], len(listed))
    anyd = [min(v.values()) for v in per_addr.values()]
    res["either"] = _summ(anyd, len(listed))
    by_date: dict[str, list[int]] = defaultdict(list)
    n_by_date: dict[str, int] = defaultdict(int)
    for a, d in ofac.items():
        n_by_date[d] += 1
        if a in per_addr:
            by_date[d].append(min(per_addr[a].values()))
    res["by_listing_date"] = {d: dict(addresses=n_by_date[d], blacklisted=len(by_date[d]),
                                      median_days=float(median(by_date[d])) if by_date[d] else None) for d in sorted(n_by_date)}
    meds = [v["median_days"] for v in res["by_listing_date"].values() if v["median_days"] is not None]
    res["median_of_date_medians"] = float(median(meds)) if meds else None
    res["dates_with_any_blacklisting"] = len(meds)
    return res


def markdown(res: dict) -> str:
    f = lambda x, p=False: "n/a" if x is None else (f"{100 * x:.0f}%" if p else f"{x:g}")  # noqa: E731
    rows = ["| Issuer | OFAC addresses | Blacklisted | Share | Median days | p90 days | Within 1 d | Within 7 d | Within 30 d |", "|---|---|---|---|---|---|---|---|---|"]
    for k in (*TOKENS, "either"):
        s = res[k]
        rows.append(f"| {k} | {s['addresses']} | {s['blacklisted']} | {f(s['share_blacklisted'], True)} | {f(s.get('median_days'))} | {f(s.get('p90'))} | "
                    f"{f(s.get('within_1d'), True)} | {f(s.get('within_7d'), True)} | {f(s.get('within_30d'), True)} |")
    return "\n".join(rows) + f"\n\nOFAC listing dates: {res['listing_dates']}; dates with at least one blacklisting: {res['dates_with_any_blacklisting']}; median of per-date medians: {f(res['median_of_date_medians'])} days."
