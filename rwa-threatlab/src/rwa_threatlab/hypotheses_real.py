"""Pre-registered real-trace experiments H12-H16 (addenda A3-A5 of docs/PREREGISTRATION.md).

Real data enter only through loaders in `traces/`; the compliance layer stays simulated, so results are labelled
"real traces, simulated compliance layer". The runner refuses to start unless (1) every dataset is declared in
docs/data/datasets.json with no 'TODO', (2) tracked files are committed, and (3) the frozen instrument is intact.
Seeds 50,000-50,599 per cell, run once (spent ranges are logged in the pre-registration).
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import platform
import subprocess
from pathlib import Path

from . import fuzz_replay
from .config import Config
from .traces import bridge, ofac, timing

ROOT = Path(__file__).resolve().parents[2]
REAL_SEED0, TRACES, STEPS = 50_000, 600, 40
WINDOW = ("2019-01-01", "2023-12-31")
VARIANTS = ("spread", "burst")
CELLS = [("baseline", Config.baseline, "none"), ("hardened", Config.hardened, "none"), ("hardened", Config.hardened, "quorum"),
         ("hardened", Config.hardened, "quorum+censor"), ("hardened", Config.hardened, "issuer")]


class GuardError(RuntimeError):
    pass


def sha256(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _git(*args: str, root: Path = ROOT) -> str | None:
    try:
        return subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, check=True).stdout.strip()
    except Exception:  # noqa: BLE001 - git missing or not a repository
        return None


def _freeze_state(root: Path) -> tuple[bool, str]:
    if not (root / "scripts" / "freeze.py").exists():
        return False, "scripts/freeze.py not found"
    spec = importlib.util.spec_from_file_location("freeze", root / "scripts" / "freeze.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    if not m.FREEZE.exists():
        return False, "no docs/FREEZE.json"
    old = json.loads(m.FREEZE.read_text())
    diff = m.changed(old, m.snapshot())
    return not diff, ", ".join(diff) if diff else old["tree_digest"][:12]


def check_declarations(ds: dict, sections: tuple[str, ...]) -> None:
    bad = [f"{s}.{k}" for s in sections for k, v in ds.get(s, {}).items()
           if not k.startswith("_") and isinstance(v, str) and "TODO" in v]
    missing = [s for s in sections if s not in ds]
    if bad or missing:
        raise GuardError(f"declare the datasets first (addenda A3-A5): missing {missing}, unfilled {bad[:8]}")


def provenance(root: Path, files: dict[str, Path], guard: bool, force: bool) -> dict:
    prov = dict(python=platform.python_version(), git_commit=_git("rev-parse", "HEAD", root=root),
                files={k: dict(path=str(p.relative_to(root)) if p.is_relative_to(root) else str(p), sha256=sha256(p)) for k, p in files.items()})
    dirty = _git("status", "--porcelain", "--untracked-files=no", "--", ".", root=root)
    prov["git_clean"] = None if dirty is None else (dirty == "")
    ok, info = _freeze_state(root)
    prov["freeze_intact"], prov["freeze_info"] = ok, info
    if guard and not force:
        if prov["git_clean"] is not True:
            raise GuardError("tracked files have uncommitted changes (or this is not a git repository): commit the "
                             "pre-registration addenda and datasets.json, tag, then run (or pass --force and it is logged)")
        if not ok:
            raise GuardError(f"frozen instrument changed: {info}")
    prov["forced"] = bool(guard and force)
    if os.environ.get("GITHUB_RUN_ID"):
        prov["ci_run"] = f"{os.environ.get('GITHUB_SERVER_URL', 'https://github.com')}/{os.environ.get('GITHUB_REPOSITORY')}/actions/runs/{os.environ['GITHUB_RUN_ID']}"
        prov["ci_ref"] = os.environ.get("GITHUB_REF")
    return prov


# ---- evaluation rules (fixed in the pre-registration) ----------------------------------------------------------
def _relax(c: dict) -> int:
    return sum(v for k, v in c["adversary_cap_sets"].items() if "relax" in k)


def evaluate_ofac(cells: dict) -> dict:
    g = lambda b, a, v: cells[f"{b}/{a}/{v}"]  # noqa: E731
    out = {}
    h12 = []
    for v in VARIANTS:
        c = g("hardened", "none", v)
        h12.append(c["violations"]["UNEXPLAINED"] == 0 and c["violations"]["adversary"] == 0 and c["crashes"] + c["trail_integrity_failures"] == 0)
    applied = sum(g("hardened", "none", v)["events_applied"] for v in VARIANTS)
    out["H12"] = ("INCONCLUSIVE" if applied == 0 else "CONFIRMED" if all(h12) else "REFUTED",
                  "; ".join(f"{v}: {g('hardened', 'none', v)['violations']} over {g('hardened', 'none', v)['traces']} traces, "
                            f"{g('hardened', 'none', v)['events_applied']} real events applied" for v in VARIANTS))
    nb = [sum(g("baseline", "none", v)["violations"].values()) for v in VARIANTS]
    out["H12b"] = ("CONFIRMED" if all(n > 0 for n in nb) else "INCONCLUSIVE", f"baseline violations per variant: {dict(zip(VARIANTS, nb))}")
    dis = sum(c["oracle_disagreements"] for c in cells.values())
    cmp_ = sum(c["oracle_compared"] for c in cells.values())
    out["H12c"] = ("CONFIRMED" if dis == 0 and cmp_ > 0 else "REFUTED" if dis else "INCONCLUSIVE",
                   f"independent oracle vs fuzzer oracle on replay traces: {cmp_} violations compared, {dis} disagreements")
    ok2 = ok3 = ok4 = True
    for v in VARIANTS:
        q, qc, iss = g("hardened", "quorum", v), g("hardened", "quorum+censor", v), g("hardened", "issuer", v)
        other = {k for k in q["adversary_cap_sets"] if set(k.split("+")) - {"upgrade"}}
        ok2 &= _relax(q) == 0 and not other
        ok3 &= _relax(q) == 0 and _relax(qc) > 0
        ok4 &= iss["traces_with_violation"] > 0 and set(iss["adversary_cap_sets"]) <= {"issuer"} and iss["violations"]["UNEXPLAINED"] == 0
    out["H13a"] = ("CONFIRMED" if ok2 else "REFUTED", "H2 under replay: colluding quorum, no censorship, no harmful relaxation (both variants)")
    out["H13b"] = ("CONFIRMED" if ok3 else "REFUTED", "H3 under replay: relaxation harm only with censorship (both variants)")
    out["H13c"] = ("CONFIRMED" if ok4 else "REFUTED", "H4 under replay: issuer-attributed violations only, none unexplained (both variants)")
    return out


def run_ofac(events, renames, window=WINDOW, traces=TRACES, steps=STEPS, seed0=REAL_SEED0) -> dict:
    hist = ofac.build_histories(events, renames, *window)
    pool = ofac.volatile_pool(hist)
    rel = ofac.relisted(hist)
    meta = dict(window=list(window), events_in_window=ofac.by_year(events, *window), entries_with_history=len(hist),
                volatile_pool=len(pool), relisted_entries=len(rel), relisted_examples=rel[:5])
    if len(pool) < len(ofac.PARTICIPANTS):
        return dict(meta=meta, cells={}, status={"H12": ("INCONCLUSIVE", f"volatile pool has {len(pool)} entries, need {len(ofac.PARTICIPANTS)}")},
                    H16=("INCONCLUSIVE", "pool too small"))
    cells = {}
    for build, mk, adv in CELLS:
        for v in VARIANTS:
            cells[f"{build}/{adv}/{v}"] = fuzz_replay.replay_campaign(mk(), adv, events, renames, window, v, seed0, traces, steps)
    h16 = ("CONFIRMED", f"{len(rel)} entries were removed and later re-added in the window") if rel else \
          ("INCONCLUSIVE", "no entry was removed and re-added in the window: the F3-style scenario is not exercised by real data")
    return dict(meta=meta, cells=cells, status=evaluate_ofac(cells), H16=h16)


def run_timing(csv_path: str | Path, column: str = "timestamp") -> dict:
    gaps = timing.gaps_in_ticks(timing.load_timestamps(csv_path, column))
    real = timing.real_sweep(gaps)
    status, ev = timing.evaluate_h14(real)
    return dict(burstiness=timing.burstiness(gaps), real=real, synthetic=timing.synthetic_reference(), status=(status, ev))


def run_bridge(csv_path: str | Path, src_col: str = "src_timestamp", dst_col: str = "dst_timestamp", lat_col: str = "latency_seconds") -> dict:
    lat, dropped = bridge.load_latencies(csv_path, src_col, dst_col, lat_col)
    s = bridge.summarise(lat, dropped)
    return dict(summary=s, status=("DESCRIPTIVE", f"n={s['n']}; median {s['median_s']:.0f}s, p95 {s['p95_s']:.0f}s, p99 {s['p99_s']:.0f}s"))


def run_real(root: Path = ROOT, sections=("ofac", "timing", "bridge"), guard: bool = True, force: bool = False,
             datasets: dict | None = None, traces: int = TRACES, steps: int = STEPS, seed0: int = REAL_SEED0) -> dict:
    ds = datasets if datasets is not None else json.loads((root / "docs/data/datasets.json").read_text())
    if guard:
        check_declarations(ds, tuple(sections))
    files = {s: root / ds[s]["events_csv" if s == "ofac" else "csv"] for s in sections}
    out = dict(provenance=provenance(root, files, guard, force), datasets={s: ds[s] for s in sections}, label="real traces, simulated compliance layer")
    if "ofac" in sections:
        ev, rn = ofac.load_events_csv(files["ofac"])
        w = (ds["ofac"].get("window_start", WINDOW[0]), ds["ofac"].get("window_end", WINDOW[1]))
        out["ofac"] = run_ofac(ev, rn, w, traces, steps, seed0)
        raw = root / ds["ofac"].get("raw_dir", "docs/data/raw")
        if raw.is_dir():
            out["provenance"]["raw_sources"] = {f.name: sha256(f) for f in sorted(raw.glob("*")) if f.is_file()}
    if "timing" in sections:
        out["timing"] = run_timing(files["timing"], ds["timing"].get("timestamp_column", "timestamp"))
    if "bridge" in sections:
        b = ds["bridge"]
        out["bridge"] = run_bridge(files["bridge"], b.get("src_column", "src_timestamp"), b.get("dst_column", "dst_timestamp"), b.get("latency_column", "latency_seconds"))
    return out


def markdown(res: dict) -> str:
    rows = ["| ID | Outcome | Evidence |", "|---|---|---|"]
    if "ofac" in res:
        for k, (s, e) in res["ofac"]["status"].items():
            rows.append(f"| {k} | **{s}** | {e} |")
        s, e = res["ofac"]["H16"]
        rows.append(f"| H16 | **{s}** | {e} |")
    if "timing" in res:
        s, e = res["timing"]["status"]
        rows.append(f"| H14 | **{s}** | {e} |")
    if "bridge" in res:
        s, e = res["bridge"]["status"]
        rows.append(f"| H15 | **{s}** | {e} |")
    return "\n".join(rows) + f"\n\nLabel: {res['label']}. Commit {res['provenance']['git_commit']}.\n"
