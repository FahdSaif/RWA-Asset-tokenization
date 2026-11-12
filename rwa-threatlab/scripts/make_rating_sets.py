#!/usr/bin/env python3
"""Write docs/results/rating_sets.json and rating_sets.md: residual bands under the original ratings, the post-hoc
revision and the assessors' median (both roundings). Post-hoc robustness check; no rating is changed.

    python scripts/make_rating_sets.py [--out FOLDER]
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from rwa_threatlab import rating_sets  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default=str(ROOT / "docs" / "results"))
    out = Path(ap.parse_args().out)
    out.mkdir(parents=True, exist_ok=True)
    res = rating_sets.compute()
    (out / "rating_sets.json").write_text(json.dumps(res, indent=1) + "\n")
    (out / "rating_sets.md").write_text(rating_sets.markdown(res) + "\n")
    print(f"wrote {out / 'rating_sets.json'} and {out / 'rating_sets.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
