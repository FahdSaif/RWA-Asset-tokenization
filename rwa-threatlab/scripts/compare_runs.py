#!/usr/bin/env python3
"""Compare two `real.json` files (official run vs independent replication) field by field.

    python scripts/compare_runs.py official/real.json replication/real.json

Ignored (they legitimately differ between machines): provenance.python, ci_run, ci_ref, git_commit, git_clean, forced.
Everything else must match exactly: the results, the dataset hashes, the raw-file hashes and the freeze digest.
Exit code 0 = identical, 1 = differences (all printed).
"""
import json
import sys

IGNORE = {"python", "ci_run", "ci_ref", "git_commit", "git_clean", "forced"}


def diff(a, b, path=""):
    out = []
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            if path == "provenance" and k in IGNORE:
                continue
            if k not in a or k not in b:
                out.append(f"{path}/{k}: present in only one file")
            else:
                out += diff(a[k], b[k], f"{path}/{k}" if path else k)
    elif isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            out.append(f"{path}: length {len(a)} vs {len(b)}")
        else:
            for i, (x, y) in enumerate(zip(a, b)):
                out += diff(x, y, f"{path}[{i}]")
    elif a != b:
        out.append(f"{path}: {a!r} vs {b!r}")
    return out


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    d = diff(json.load(open(sys.argv[1])), json.load(open(sys.argv[2])))
    print("IDENTICAL (ignoring machine-specific provenance fields)" if not d else "DIFFERENCES:\n  " + "\n  ".join(d))
    sys.exit(1 if d else 0)
