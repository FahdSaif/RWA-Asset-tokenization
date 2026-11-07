#!/usr/bin/env python3
"""Convert returned assessor workbooks (assessor_scoring_pack.xlsx) into the CSV read by rwa_threatlab.irr.

    python scripts/xlsx_to_irr.py --out scores.csv assessor1.xlsx assessor2.xlsx ...

Refuses any workbook that is marked simulated or synthetic (so test files cannot be reported as real assessments) unless
--allow-synthetic is given; in that case the output file name is forced to contain 'SYNTHETIC'.
"""
import argparse
import csv
import sys
from pathlib import Path

from openpyxl import load_workbook

COLS = ["F1", "F2", "F3", "G1", "G2", "G3"]
MARKERS = ("simulat", "synthetic", "not a real", "test data", "fake")


def read(path: Path) -> tuple[str, list[dict], bool]:
    wb = load_workbook(path, data_only=True)
    sc = wb["Scoring"]
    code = str(sc["B2"].value or "").strip()
    flagged = any(isinstance(c.value, str) and any(m in c.value.lower() for m in MARKERS)
                  for s in wb for row in s.iter_rows() for c in row) or any(m in code.lower() for m in ("syn", "simul"))
    rows = []
    for r in range(6, 20):
        sid = sc.cell(r, 1).value
        vals = [sc.cell(r, c).value for c in range(5, 11)]
        if sid and any(v is not None for v in vals):
            if any(v is not None and v not in (1, 2, 3) for v in vals):
                raise ValueError(f"{path.name} row {sid}: scores must be 1, 2 or 3, got {vals}")
            rows.append(dict(assessor=code, scenario=str(sid).strip(), **{k: ("" if v is None else v) for k, v in zip(COLS, vals)}))
    if not code:
        raise ValueError(f"{path.name}: assessor code (Scoring!B2) is empty")
    return code, rows, flagged


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+")
    ap.add_argument("--out", required=True)
    ap.add_argument("--allow-synthetic", action="store_true")
    a = ap.parse_args()
    out, all_rows, codes, any_flag = Path(a.out), [], [], False
    for f in a.files:
        code, rows, flagged = read(Path(f))
        if code in codes:
            raise SystemExit(f"duplicate assessor code {code!r}")
        codes.append(code); all_rows += rows; any_flag |= flagged
        print(f"{Path(f).name}: assessor {code}, {len(rows)} scenarios{'  [MARKED SYNTHETIC]' if flagged else ''}")
    if any_flag and not a.allow_synthetic:
        raise SystemExit("REFUSED: at least one workbook is marked simulated/synthetic. Real assessments only (or --allow-synthetic for a pipeline test).")
    if any_flag and "SYNTHETIC" not in out.name.upper():
        out = out.with_name("SYNTHETIC_" + out.name)
    with open(out, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["assessor", "scenario"] + COLS)
        w.writeheader(); w.writerows(all_rows)
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
