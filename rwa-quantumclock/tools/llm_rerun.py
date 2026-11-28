"""POST-REGISTRATION: the language-model classifier with a larger answer limit.

Plan written before the run: docs/LLM_RERUN_PLAN.md. Same model (checked by fingerprint in the notebook), same evidence
and same scoring as the frozen H10 run; only the answer limit (arm A), and also the answer format (arm B), change.
Changes no code in src/. H10 stays REFUTED. Not part of the pre-registration.

Needs ANTHROPIC_API_KEY and QAMP_LLM_MODEL in the environment (the notebook sets both and never prints the model name).
Run from rwa-quantumclock:  python tools/llm_rerun.py A   (then B, then: python tools/llm_rerun.py report)
Writes results/exploratory/llm_rerun_<arm>.json, llm_rerun_<arm>_log.jsonl, and llm_rerun.json and .md."""
import argparse
import csv
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from qamp import __main__ as cli, config, evaluate  # noqa: E402
from qamp.discovery import classify as clf_mod  # noqa: E402
from qamp.discovery import scan_abi, scan_source  # noqa: E402
from qamp.discovery.abi import scan_controllers  # noqa: E402
from qamp.discovery.cbom import read_labels, score  # noqa: E402
from qamp.observed import BYTECODE_SURFACES, MANUAL_SURFACES, OBSERVED_ONLY_SURFACES  # noqa: E402

OUT = ROOT / "results" / "exploratory"
FROZEN_TAG = "model-sha256:7d811269d13fd7df0fd2cb573cbd1b11679a1ae347c179b3daf22b12408604c4"
LIMIT = 8000

# arm B: the frozen prompt with a smaller answer format (only surface, algorithm, evidence)
COMPACT = """You are auditing the cryptographic inventory of a tokenised real-world-asset contract on Ethereum.
Below are evidence items (id, kind, surface hint, location, snippet). Return ONLY a JSON list. Each element:
{"surface": <one of %s>, "algorithm": <e.g. secp256k1-ecdsa, p256-ecdsa, bls12-381, contract-defined>,
 "evidence": [<evidence ids from the list below, at least one>]}
Do not invent evidence ids. Omit a surface if the evidence does not support it. No other text.
Evidence:
%s"""


def hashes():
    # fingerprint of the frozen code and rules, to show nothing changed
    files = sorted(list((ROOT / "src").rglob("*.py")) + list((ROOT / "kb").glob("*.yaml")))
    h = hashlib.sha256()
    for p in files:
        h.update(str(p.relative_to(ROOT)).encode())
        h.update(p.read_bytes())
    return h.hexdigest()


def git_changed_lines():
    try:
        r = subprocess.run(["git", "-C", str(ROOT), "diff", "--numstat", "HEAD", "--", "src", "kb"],
                           capture_output=True, text=True, check=True)
    except (OSError, subprocess.CalledProcessError):
        return None
    return sum(int(a) + int(b) for a, b, *_ in (ln.split("\t") for ln in r.stdout.splitlines()) if a.isdigit())


def findings():
    # the same evidence as the frozen run: python -m qamp discover --source-dir data/sources
    dep = cli._load(argparse.Namespace())
    fs = [f for t in dep.tokens for f in scan_abi(t.address, t.abi_functions)] + scan_controllers(dep)
    for p in sorted((config.DATA_DIR / "sources").glob("0x*.sol*")):
        fs += scan_source(p.name.split(".")[0].lower(), p.read_text())
    return fs


def unreadable(log):
    # answers whose JSON list cannot be read (cut off or not valid JSON)
    n = 0
    for line in log.read_text().splitlines():
        raw = json.loads(line)["response"]
        try:
            json.loads(raw[raw.find("["): raw.rfind("]") + 1])
        except (json.JSONDecodeError, ValueError):
            n += 1
    return n


def scores(entries):
    labels = {k: v for k, v in read_labels(config.DATA_DIR / "labels.csv").items() if k[1] not in OBSERVED_ONLY_SURFACES}
    reps = {r["code_group"] for r in csv.DictReader(open(config.DATA_DIR / "code_groups.csv", newline=""))}
    ents = [e for e in entries if e.surface not in OBSERVED_ONLY_SURFACES]
    out = {}
    for src, surf in (("all", None), ("bytecode", set(BYTECODE_SURFACES)), ("hand", set(MANUAL_SURFACES))):
        lab = {k: v for k, v in labels.items() if surf is None or k[1] in surf}
        ent = [e for e in ents if surf is None or e.surface in surf]
        for unit, keep in (("token", None), ("code", reps)):
            lb = {k: v for k, v in lab.items() if keep is None or k[0] in keep}
            en = [e for e in ent if keep is None or e.token.lower() in keep]
            o = score(en, lb)["overall"]
            out[f"{src}_per_{unit}"] = {k: (round(v, 3) if isinstance(v, float) else v) for k, v in o.items()}
    return out


def run_arm(arm):
    model = os.environ.get("QAMP_LLM_MODEL", "")
    tag = "model-sha256:" + hashlib.sha256(model.encode()).hexdigest()
    if tag != FROZEN_TAG:
        raise SystemExit("stop: the model is not the one used in the frozen run")
    t0 = time.time()
    h_before = hashes()
    if arm == "B":
        clf_mod.PROMPT = COMPACT          # only for this process; the file in src/ is unchanged
    log = OUT / f"llm_rerun_{arm}_log.jsonl"
    OUT.mkdir(parents=True, exist_ok=True)
    log.unlink(missing_ok=True)
    clf = clf_mod.LLMClassifier(model=model, log_path=log, max_tokens=LIMIT)
    fs = findings()
    entries = clf.classify(fs)
    res = dict(arm=arm, answer_limit=LIMIT, prompt="frozen" if arm == "A" else "compact", model=FROZEN_TAG,
               answers=len({f.token for f in fs}), unreadable_answers=unreadable(log),
               entries_kept=len(entries), entries_dropped=clf.dropped, invented_citations=clf.hallucinated,
               scores=scores(entries), runtime_s=round(time.time() - t0, 1), env=evaluate.environment(),
               src_kb_unchanged=h_before == hashes(), git_lines_changed_src_kb=git_changed_lines())
    log.write_text(log.read_text().replace(model, FROZEN_TAG))      # name replaced by its fingerprint
    (OUT / f"llm_rerun_{arm}.json").write_text(json.dumps(res, indent=1))
    print(f"arm {arm}: {res['answers']} answers, {res['unreadable_answers']} unreadable, "
          f"F1 {res['scores']['all_per_token']['f1']}")


def report():
    lab = json.loads((ROOT / "results" / "exploratory" / "labels_independence.json").read_text())["scores_by_label_source"]
    arms = {a: json.loads((OUT / f"llm_rerun_{a}.json").read_text()) for a in ("A", "B")}
    md = ["# POST-REGISTRATION: language-model classifier with a larger answer limit", "",
          "Plan committed before the run: docs/LLM_RERUN_PLAN.md. Same model as the frozen H10 run (checked by fingerprint), "
          "same evidence and scoring. H10 stays REFUTED. Not pre-registered.", "",
          "| Run | Answer limit | Unreadable answers | Entries kept / dropped | Invented citations |", "|---|---|---|---|---|",
          "| Frozen H10 run | 2,000 | 85 of 100 | 59 / 85 | 0 |"]
    for a, r in arms.items():
        md.append(f"| Arm {a} ({r['prompt']} prompt) | {r['answer_limit']:,} | {r['unreadable_answers']} of {r['answers']} | "
                  f"{r['entries_kept']} / {r['entries_dropped']} | {r['invented_citations']} |")
    md += ["", "F1 (precision / recall)", "", "| Labels | Unit | Rules | Frozen H10 run | Arm A | Arm B |", "|---|---|---|---|---|---|"]
    for key in ("all_per_token", "all_per_code", "bytecode_per_token", "bytecode_per_code", "hand_per_token", "hand_per_code"):
        rr, fz = lab[f"rules_{key}"], lab[f"language_model_{key}"]
        cell = lambda s: f"{s['f1']} ({s['precision']} / {s['recall']})"  # noqa: E731
        md.append(f"| {key.split('_per_')[0]} | {key.split('_per_')[1]} | {cell(rr)} | {cell(fz)} | "
                  f"{cell(arms['A']['scores'][key])} | {cell(arms['B']['scores'][key])} |")
    for a, r in arms.items():
        md.append(f"\nArm {a}: code and rules unchanged {r['src_kb_unchanged']} (git lines changed in src/ and kb/: "
                  f"{r['git_lines_changed_src_kb']}); run time {r['runtime_s']} s.")
    (OUT / "llm_rerun.json").write_text(json.dumps(dict(post_registration=True, plan="docs/LLM_RERUN_PLAN.md", arms=arms), indent=1))
    (OUT / "llm_rerun.md").write_text("\n".join(md) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("what", choices=("A", "B", "report"))
    a = ap.parse_args()
    report() if a.what == "report" else run_arm(a.what)
