"""Runner for the exploratory analyses: python -m rwa_threatlab.exploratory.run {kanon,latency} [--out DIR] [--force]

Refuses to run if tracked files are uncommitted or the frozen instrument changed (same guard as the pre-registered runs), unless --force
(which is recorded). Each experiment writes to its own folder, so results are never overwritten.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .. import hypotheses_real as hr
from . import kanon, latency, ofac_addresses

ROOT = Path(__file__).resolve().parents[3]
DATA = "docs/data/exploratory"


def run(exp: str, root: Path = ROOT, guard: bool = True, force: bool = False) -> dict:
    if exp == "kanon":
        files = {"events": root / DATA / "usdy_events.csv"}
        prov = hr.provenance(root, files, guard, force)
        res = kanon.analyse(kanon.load(files["events"]))
        md = kanon.markdown(res)
    elif exp == "latency":
        files = {"blacklist_events": root / DATA / "blacklist_events_ofac_subset.csv", "summary": root / DATA / "blacklist_summary.json"}
        prov = hr.provenance(root, files, guard, force)
        ofac = ofac_addresses.extract(root / "docs/data/raw")
        prov["ofac_raw_sources"] = {p.name: hr.sha256(p) for p in sorted((root / "docs/data/raw").glob("sdnnew*.txt"))}
        as_of = json.loads(files["summary"].read_text())["retrieved_utc"][:10]
        res = latency.analyse(ofac, latency.load_events(files["blacklist_events"]), as_of)
        md = latency.markdown(res)
    else:
        raise SystemExit(f"unknown experiment {exp!r}")
    return dict(experiment=exp, label="exploratory; plan: docs/EXPLORATORY_PLAN.md", provenance=prov, result=res, markdown=md)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("exp", choices=["kanon", "latency"])
    ap.add_argument("--out", type=Path)
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args(argv)
    try:
        out = run(a.exp, force=a.force)
    except hr.GuardError as e:
        print("REFUSING TO RUN:", e)
        return 2
    print(out["markdown"])
    if a.out:
        a.out.mkdir(parents=True, exist_ok=True)
        (a.out / "result.json").write_text(json.dumps(out, indent=1, default=str) + "\n")
        (a.out / "result.md").write_text(out["markdown"] + "\n")
        print(f"\nwritten to {a.out}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
