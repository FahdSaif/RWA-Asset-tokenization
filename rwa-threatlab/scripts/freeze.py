#!/usr/bin/env python3
"""Freeze the measuring instrument so that later changes cannot be made silently after seeing results.

  python scripts/freeze.py write --reason "initial freeze"     write/refresh docs/FREEZE.json
  python scripts/freeze.py check                               exit 1 if any frozen file differs

Files are hashed after normalising line endings (CRLF -> LF), so the hashes are the same on Windows and Linux.
Changing a frozen file is allowed, but only deliberately: re-run `write` with a reason, log the deviation in
docs/PREREGISTRATION.md (section 6) and tag a new release. New experiments go in NEW files, not in frozen ones.
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import platform
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FREEZE = ROOT / "docs" / "FREEZE.json"

SRC = "src/rwa_threatlab/"
FROZEN = sorted(
    [SRC + f"{m}.py" for m in (
        "crypto", "trail", "credentials", "rules", "ledger", "verifier", "gateway", "governance", "oracle",
        "system", "bridge", "attacks", "config", "fuzz", "hypotheses", "risk", "modelcheck", "modelcheck_scaled", "irr",
        "oracle_independent", "fuzz_observed", "hypotheses_v2", "fuzz_replay", "hypotheses_real", "traces/__init__", "traces/ofac",
        "traces/timing", "traces/bridge")] + ["docs/ORACLE_SPEC.md", "tests/fixtures/ofac_format_fixture.txt", "tests/fixtures/ofac_real_excerpt_2022.txt"]
    + [str(p.relative_to(ROOT)).replace("\\", "/") for p in (ROOT / "src/rwa_threatlab/scenarios").glob("*.py")]
    + ["tests/" + t for t in ("test_components.py", "test_instruments.py", "test_risk_and_model.py", "test_scenarios.py",
                              "test_modelcheck_scaled.py", "test_irr_and_floor.py", "test_oracle_independent.py", "test_real_traces.py")]
)
# Reference outputs of the frozen code (regenerate with `python -m rwa_threatlab all --out docs/results`).
REFERENCE = ["docs/results/hypotheses.json", "docs/results/scenarios.json", "docs/results/risk.md",
             "docs/results/modelcheck.json", "docs/results/sensitivity.json"]


def digest(rel: str) -> str:
    data = (ROOT / rel).read_bytes().replace(b"\r\n", b"\n")
    return hashlib.sha256(data).hexdigest()


def snapshot() -> dict:
    files = {r: digest(r) for r in FROZEN}
    ref = {r: digest(r) for r in REFERENCE if (ROOT / r).exists()}
    tree = hashlib.sha256("\n".join(f"{k}:{v}" for k, v in sorted({**files, **ref}.items())).encode()).hexdigest()
    return dict(files=files, reference_outputs=ref, tree_digest=tree)


def changed(old: dict, new: dict) -> list[str]:
    out = []
    for sect in ("files", "reference_outputs"):
        for k in sorted(set(old.get(sect, {})) | set(new.get(sect, {}))):
            if old.get(sect, {}).get(k) != new.get(sect, {}).get(k):
                out.append(k)
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["write", "check"])
    ap.add_argument("--reason", default="")
    a = ap.parse_args(argv)
    snap = snapshot()
    if a.cmd == "check":
        if not FREEZE.exists():
            print("no docs/FREEZE.json: instrument is not frozen"); return 1
        old = json.loads(FREEZE.read_text())
        diff = changed(old, snap)
        if diff:
            print("FROZEN FILES CHANGED since the freeze:\n  " + "\n  ".join(diff))
            print("If deliberate: scripts/freeze.py write --reason '...', log it in PREREGISTRATION.md section 6, retag.")
            return 1
        print(f"frozen instrument intact ({len(snap['files'])} files, tree {snap['tree_digest'][:12]})")
        return 0
    old = json.loads(FREEZE.read_text()) if FREEZE.exists() else None
    if old and not a.reason:
        print("re-freezing an existing freeze needs --reason"); return 2
    history = (old or {}).get("history", [])
    if old:
        history.append(dict(date=old.get("created"), tree_digest=old["tree_digest"], superseded_because=a.reason,
                            changed_files=changed(old, snap)))
    rec = dict(created=datetime.date.today().isoformat(), reason=a.reason or "initial freeze",
               python=platform.python_version(), **snap, history=history)
    FREEZE.write_text(json.dumps(rec, indent=1, sort_keys=True) + "\n")
    print(f"wrote {FREEZE.relative_to(ROOT)}  tree {snap['tree_digest'][:12]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
