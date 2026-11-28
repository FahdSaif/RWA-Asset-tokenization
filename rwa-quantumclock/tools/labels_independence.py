"""POST-REGISTRATION: how much do the discovery results rest on the hand labels, and do those labels agree with a
mechanical reading of the deployed code?

Plan written before the run: docs/LABELS_INDEPENDENCE_PLAN.md. Reads committed files only; no API calls.
Changes no code in src/ and no frozen result. Not part of the pre-registration.

Run from rwa-quantumclock:  python tools/labels_independence.py
Writes results/exploratory/labels_independence.json and .md."""
import csv
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from qamp import evaluate  # noqa: E402
from qamp.discovery.cbom import cohen_kappa, read_labels, score  # noqa: E402
from qamp.observed import BYTECODE_SURFACES, MANUAL_SURFACES, OBSERVED_ONLY_SURFACES  # noqa: E402

DATA = ROOT / "data"
DISC = ROOT / "results" / "discovery"
# fixed addresses of the signature checks (plan, part B)
TARGETS = {0x01: "ecdsa"} | {0x100: "p256"} | {a: "bls" for a in range(0x0B, 0x12)}
CALLS = (0xFA, 0xF1)                         # STATICCALL, CALL


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


def entries(path):
    return [SimpleNamespace(token=e["token"], surface=e["surface"]) for e in json.loads(path.read_text())
            if e["surface"] not in OBSERVED_ONLY_SURFACES]


def prf(s):
    o = s["overall"]
    r = lambda x: round(x, 3) if x is not None else None  # noqa: E731
    return dict(tp=o["tp"], fp=o["fp"], fn=o["fn"], precision=r(o["precision"]), recall=r(o["recall"]), f1=r(o["f1"]))


# --- part B: mechanical reading of the deployed code

def instructions(code_hex):
    b = bytes.fromhex(code_hex[2:] if code_hex.startswith("0x") else code_hex)
    out, i = [], 0
    while i < len(b):
        op = b[i]
        if 0x60 <= op <= 0x7F:
            n = op - 0x5F
            out.append((i, op, int.from_bytes(b[i + 1:i + 1 + n], "big")))
            i += 1 + n
        else:
            out.append((i, op, None))
            i += 1
    return out


def between_ok(op):
    # GAS, PUSH0-PUSH32, DUP, SWAP
    return op == 0x5A or 0x5F <= op <= 0x7F or 0x80 <= op <= 0x9F


def called_targets(code_hex):
    """Which signature-check addresses the code calls, with the offset of each call."""
    found = {}
    ins = instructions(code_hex)
    for i, (off, op, val) in enumerate(ins):
        if not (0x60 <= op <= 0x7F) or val not in TARGETS:
            continue
        for j in range(i + 1, min(i + 4, len(ins))):
            if ins[j][1] in CALLS:
                found.setdefault(TARGETS[val], []).append(off)
                break
            if not between_ok(ins[j][1]):
                break
    return found


def main():
    t0 = time.time()
    h_before = hashes()
    labels = {k: v for k, v in read_labels(DATA / "labels.csv").items() if k[1] not in OBSERVED_ONLY_SURFACES}
    reps = {r["code_group"] for r in csv.DictReader(open(DATA / "code_groups.csv", newline=""))}
    rules, llm = entries(DISC / "inventory_rules.json"), entries(DISC / "inventory_llm.json")

    # A. scores by label source
    sources = dict(all=None, bytecode=set(BYTECODE_SURFACES), hand=set(MANUAL_SURFACES))
    part_a = {}
    for name, inv in (("rules", rules), ("language_model", llm)):
        for src, surf in sources.items():
            lab = {k: v for k, v in labels.items() if surf is None or k[1] in surf}
            ent = [e for e in inv if surf is None or e.surface in surf]
            part_a[f"{name}_{src}_per_token"] = dict(labels=len(lab), positives=sum(lab.values()), **prf(score(ent, lab)))
            labr = {k: v for k, v in lab.items() if k[0] in reps}
            entr = [e for e in ent if e.token.lower() in reps]
            part_a[f"{name}_{src}_per_code"] = dict(labels=len(labr), positives=sum(labr.values()), **prf(score(entr, labr)))

    # B. mechanical check, one row per distinct code
    raw = {t["address"].lower(): t for t in json.loads((DATA / "q1_raw.json").read_text())["tokens"]}
    hand = {(r["token"].lower(), r["surface"]): r["present"].strip() == "1"
            for r in csv.DictReader(open(DATA / "labels_manual.csv", newline=""))}
    pred = {(e.token.lower(), e.surface) for e in rules}
    rows, mech, lab_b, rule_b = [], {}, {}, {}
    for rep in sorted(reps):
        t = raw.get(rep, {})
        bc = t.get("bytecode") or {}
        code = bc.get("implementation") if t.get("is_proxy") and bc.get("implementation") else bc.get("token")
        if not code or code in ("0x", "0x0"):
            rows.append(dict(code=rep, note="no deployed code"))
            continue
        found = called_targets(code)
        row = dict(code=rep, calls={k: [hex(o) for o in v[:3]] for k, v in found.items()})
        for kind, surfs in (("ecdsa", ("ecrecover_direct", "ecdsa_library")), ("p256", ("p256_verifier",)),
                            ("bls", ("bls_precompile",))):
            m = kind in found
            h = any(hand.get((rep, s), False) for s in surfs)
            p = any((rep, s) in pred for s in surfs)
            mech[(rep, kind)], lab_b[(rep, kind)], rule_b[(rep, kind)] = m, h, p
            row[kind] = dict(mechanical=m, hand_label=h, rules=p)
        rows.append(row)

    def compare(other, kind):
        keys = [k for k in mech if k[1] == kind]
        t = dict(both=sum(mech[k] and other[k] for k in keys), mechanical_only=sum(mech[k] and not other[k] for k in keys),
                 other_only=sum(other[k] and not mech[k] for k in keys), neither=sum(not mech[k] and not other[k] for k in keys))
        t["agreement"] = round(sum(mech[k] == other[k] for k in keys) / len(keys), 3) if keys else None
        k_ = cohen_kappa({k: mech[k] for k in keys}, {k: other[k] for k in keys}) if keys else None
        t["kappa"] = round(k_, 3) if k_ is not None else None
        t["disagreements"] = [k[0] for k in keys if mech[k] != other[k]]
        return t
    part_b = {kind: dict(hand_labels=compare(lab_b, kind), rules=compare(rule_b, kind)) for kind in ("ecdsa", "p256", "bls")}

    h_after = hashes()
    res = dict(meta=dict(post_registration=True, plan="docs/LABELS_INDEPENDENCE_PLAN.md", runtime_s=round(time.time() - t0, 1),
                         env=evaluate.environment(), distinct_codes=len(reps), src_kb_hash_before=h_before,
                         src_kb_hash_after=h_after, src_kb_unchanged=h_before == h_after,
                         git_lines_changed_src_kb=git_changed_lines()),
               human_check_40_rows="not done", scores_by_label_source=part_a, mechanical_check=part_b, mechanical_rows=rows)
    out = ROOT / "results" / "exploratory"
    out.mkdir(parents=True, exist_ok=True)
    (out / "labels_independence.json").write_text(json.dumps(res, indent=1))

    md = ["# POST-REGISTRATION: independence of the discovery labels", "",
          "Plan committed before the run: docs/LABELS_INDEPENDENCE_PLAN.md. Committed files only; no API calls. Not pre-registered.", "",
          f"Code and rules unchanged during the run: {res['meta']['src_kb_unchanged']} "
          f"(git lines changed in src/ and kb/: {res['meta']['git_lines_changed_src_kb']}). The 40-row human check was not done.", "",
          "## A. Scores by label source", "",
          "| Classifier | Labels | Unit | Labels (positives) | Precision | Recall | F1 |", "|---|---|---|---|---|---|---|"]
    for k, v in part_a.items():
        name, src, unit = k.split("_per_")[0].rsplit("_", 1)[0], k.split("_per_")[0].rsplit("_", 1)[1], k.split("_per_")[1]
        md.append(f"| {name} | {src} | {unit} | {v['labels']} ({v['positives']}) | {v['precision']} | {v['recall']} | {v['f1']} |")
    md += ["", f"## B. Mechanical check of signature verification ({len(reps)} distinct codes)", "",
           "| Check | Compared with | Both | Mechanical only | Other only | Neither | Agreement | Kappa |",
           "|---|---|---|---|---|---|---|---|"]
    for kind, v in part_b.items():
        for who, t in v.items():
            md.append(f"| {kind} | {who} | {t['both']} | {t['mechanical_only']} | {t['other_only']} | {t['neither']} | "
                      f"{t['agreement']} | {t['kappa']} |")
    md += ["", "Disagreements (distinct code):"]
    for kind, v in part_b.items():
        for who, t in v.items():
            if t["disagreements"]:
                md.append(f"- {kind} vs {who}: " + ", ".join(t["disagreements"]))
    (out / "labels_independence.md").write_text("\n".join(md) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    main()
