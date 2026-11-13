#!/usr/bin/env python3
"""Write the data behind the paper's two result figures as CSV files (no new data: both come from stored inputs and results).

  docs/results/figures/h14_linkage.csv     H14 linkage by events per epoch, real and synthetic timing, with 95% intervals
                                           (copied from docs/results/real_timing/real.json)
  docs/results/figures/latency_delays.csv  per OFAC-listed address, days from first OFAC listing to first blacklisting by
                                           USDC and by USDT (recomputed with the code of Exploratory B from the committed data)

    python scripts/make_figure_data.py [--out FOLDER]
"""
import argparse
import csv
import datetime as dt
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from rwa_threatlab.exploratory import latency, ofac_addresses  # noqa: E402


def h14_rows(root: Path = ROOT) -> list[dict]:
    t = json.loads((root / "docs/results/real_timing/real.json").read_text())["timing"]
    syn = {r["events_per_epoch"]: r for r in t["synthetic"]}
    return [dict(events_per_epoch=r["events_per_epoch"], real=r["mean"], real_lo=r["lo"], real_hi=r["hi"],
                 synthetic=syn[r["events_per_epoch"]]["mean"], synthetic_lo=syn[r["events_per_epoch"]]["lo"],
                 synthetic_hi=syn[r["events_per_epoch"]]["hi"]) for r in t["real"]]


def delay_rows(root: Path = ROOT) -> list[dict]:
    """Same rule as latency.analyse: UTC date of the issuer's first blacklist event minus the date of first OFAC listing."""
    ofac = ofac_addresses.extract(root / "docs/data/raw")
    events = latency.load_events(root / "docs/data/exploratory/blacklist_events_ofac_subset.csv")
    listed = {a: dt.date.fromisoformat(d) for a, d in ofac.items()}
    first: dict = {}
    for e in events:
        if e["address"] in listed:
            k = (e["token"], e["address"])
            first[k] = min(first.get(k, e["timestamp"]), e["timestamp"])
    day = lambda ts: dt.datetime.fromtimestamp(ts, dt.timezone.utc).date()  # noqa: E731
    rows = []
    for a in sorted(listed):
        r = dict(address=a, ofac_listed=listed[a].isoformat())
        for tok in latency.TOKENS:
            r[f"{tok}_days"] = (day(first[(tok, a)]) - listed[a]).days if (tok, a) in first else ""
        rows.append(r)
    return rows


def _write(path: Path, rows: list[dict]) -> None:
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default=str(ROOT / "docs" / "results" / "figures"))
    out = Path(ap.parse_args().out)
    out.mkdir(parents=True, exist_ok=True)
    _write(out / "h14_linkage.csv", h14_rows())
    _write(out / "latency_delays.csv", delay_rows())
    print(f"wrote {out / 'h14_linkage.csv'} and {out / 'latency_delays.csv'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
