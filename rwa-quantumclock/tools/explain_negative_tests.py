"""POST-REGISTRATION: do the explanation checks reject wrong sentences?

Rebuilds the 781 template sentences of the frozen explanation run, makes wrong copies of them (one kind of error
each), and counts how many each check rejects. Plan written before the run: docs/EXPLAIN_NEGATIVE_TESTS_PLAN.md.
No API calls. Changes no code in src/ and no frozen result. Not part of the pre-registration.

Run from rwa-quantumclock:  python tools/explain_negative_tests.py
Writes results/exploratory/explain_negative_tests.json and .md."""
import argparse
import hashlib
import json
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from qamp import __main__ as cli, config, evaluate, explain, planner, scenarios  # noqa: E402
from qamp.kb import load_kb  # noqa: E402

KINDS = {
    "N1": "Value changed to one not in the cited facts",
    "N2": "Two valid values swapped",
    "N3": "Valid value in the wrong place",
    "N4": "Statement reversed",
    "N5": "Wrong regulation named",
    "N6": "Unsupported reason added",
    "N7": "Right citation, wrong claim",
    "N8": "Wrong deadline date",
}
REVERSALS = [("is disallowed", "is allowed"), ("is deprecated", "is not deprecated"),
             ("can be attacked", "cannot be attacked"), ("must remain", "need not remain"),
             ("could not be read", "could be read"), ("A single externally owned account controls",
                                                      "No single externally owned account controls"),
             ("found no mixed-state violation", "found a mixed-state violation")]
QUARTER = re.compile(r"^(\d{4}) Q([1-4])$")
DATE = re.compile(r"^(\d{4})(-\d{2}-\d{2})$")


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


def build():
    """The 781 template sentences, exactly as in the frozen explanation run (qamp/__main__.py)."""
    from qamp.discovery import RulesClassifier, scan_abi
    from qamp.discovery.abi import scan_controllers
    dep = cli._load(argparse.Namespace())
    kb = load_kb()
    ctx = planner.kb_context(dep, kb)
    ss = scenarios.sample(5_000, len(dep.anchors), seed=config.DEV_SEED_BASE + 21)
    p = planner.plan(dep, kb, ss, ctx=ctx)
    entries = RulesClassifier().classify([f for t in dep.tokens for f in scan_abi(t.address, t.abi_functions)]
                                         + scan_controllers(dep))
    ev_tok = {}
    for e in entries:
        ev_tok.setdefault(e.token, []).extend(e.evidence)
    evidence = {a.anchor_id: [e for t in a.tokens for e in ev_tok.get(t, [])][:3] for a in dep.anchors}

    def rationales():
        return {a.anchor_id: explain.write(a, p.starts[a.anchor_id], ctx[a.anchor_id]["inference"], evidence[a.anchor_id])
                for a in dep.anchors}
    return rationales


# --- frozen checks and the strict check

def frozen_ok(s, r):
    return bool(explain.validate([s], r.allowed)[0]) and explain.faithful(s, r.facts)


def strict_ok(s, rebuilt):
    return s in set(rebuilt.sentences)


# --- wrong copies

def value_spans(s):
    # dates, quarters and numbers outside citations and outside "NIST IR 8547"
    masked = explain._STATIC.sub(lambda m: " " * len(m.group(0)), s)
    return [(m.start(), m.end(), m.group(0)) for m in explain._VALUE.finditer(masked)]


def kind_of(v):
    return "quarter" if QUARTER.match(v) else "date" if DATE.match(v) else "number"


def bump(v, by):
    if QUARTER.match(v):
        y, q = QUARTER.match(v).groups()
        return f"{int(y) + by} Q{q}"
    if DATE.match(v):
        y, rest = DATE.match(v).groups()
        return f"{int(y) + by}{rest}"
    return str(int(float(v)) + by) if float(v).is_integer() else str(float(v) + by)


def put(s, span, new):
    a, b, _ = span
    return s[:a] + new + s[b:]


def mutate(kind, s, r):
    sp = value_spans(s)
    if kind == "N1":
        return put(s, sp[0], bump(sp[0][2], 1)) if sp else None
    if kind == "N2":
        for j in range(1, len(sp)):
            if sp[j][2] != sp[0][2]:
                a, b = sp[0], sp[j]
                return s[:a[0]] + b[2] + s[a[1]:b[0]] + a[2] + s[b[1]:]
        return None
    if kind == "N3":
        if not sp:
            return None
        v = sp[0][2]
        pool = sorted({x for vals in r.facts.values() for x in vals
                       if x != v and kind_of(x) == kind_of(v) and re.fullmatch(r"[\d .Q-]+", x)})
        return put(s, sp[0], pool[0]) if pool else None
    if kind == "N4":
        for a, b in REVERSALS:
            if a in s:
                return s.replace(a, b, 1)
        return None
    if kind == "N5":
        return s.replace("NIST IR 8547", "the EU AML directive", 1) if "NIST IR 8547" in s else None
    if kind == "N6":
        m = explain.CITE.search(s)
        return s[:m.start()].rstrip() + ", because the issuer asked for it " + s[m.start():] if m else None
    if kind == "N7":
        cites = [f"{k}:{v}" for k, v in explain.CITE.findall(s)]
        other = [c for c in sorted(r.allowed) if c not in cites]
        if not cites or not other:
            return None
        return s.replace(f"[{cites[0]}]", f"[{other[0]}]", 1)
    if kind == "N8":
        m = re.search(r"(disallowed|deprecated) after (\d{4})(-\d{2}-\d{2})", s)
        if not m:
            return None
        return s[:m.start(2)] + str(int(m.group(2)) - 2) + s[m.end(2):]
    raise ValueError(kind)


def reworded(rats):
    """The 821 sentences the language model wrote in the frozen H13 run, read from its log (no new calls)."""
    log = ROOT / "results" / "explain" / "llm_log.jsonl"
    out = []
    for line in log.read_text().splitlines():
        rec = json.loads(line)
        r = rats.get(rec["token"])
        if r is None:
            continue
        out += [(rec["token"], x.strip()) for x in rec["response"].splitlines() if x.strip()]
    return out


def main():
    t0 = time.time()
    h_before = hashes()
    rationales = build()
    rats = rationales()
    rebuilt = rationales()           # built a second time for the strict check
    pairs = [(aid, s) for aid, r in rats.items() for s in r.sentences]
    base_frozen = sum(frozen_ok(s, rats[aid]) for aid, s in pairs)
    base_strict = sum(strict_ok(s, rebuilt[aid]) for aid, s in pairs)
    if len(pairs) != 781 or base_frozen != 781:
        raise SystemExit(f"stop: expected 781 sentences that all pass, got {len(pairs)} with {base_frozen} passing")

    rows, examples = {}, {}
    for k in KINDS:
        n = rej_frozen = rej_strict = 0
        missed = []
        for aid, s in pairs:
            m = mutate(k, s, rats[aid])
            if m is None or m == s:
                continue
            n += 1
            fz, st = frozen_ok(m, rats[aid]), strict_ok(m, rebuilt[aid])
            rej_frozen += not fz
            rej_strict += not st
            if fz and len(missed) < 2:
                missed.append(dict(original=s, wrong=m))
        rows[k] = dict(error=KINDS[k], wrong_sentences=n,
                       rejected_frozen=rej_frozen, rejected_frozen_share=round(rej_frozen / n, 3) if n else None,
                       rejected_strict=rej_strict, rejected_strict_share=round(rej_strict / n, 3) if n else None)
        examples[k] = missed

    rw = reworded(rats)
    rw_frozen = sum(frozen_ok(x, rats[aid]) for aid, x in rw)
    rw_strict = sum(strict_ok(x, rebuilt[aid]) for aid, x in rw)

    h_after = hashes()
    res = dict(
        meta=dict(post_registration=True, plan="docs/EXPLAIN_NEGATIVE_TESTS_PLAN.md", runtime_s=round(time.time() - t0, 1),
                  env=evaluate.environment(), src_kb_hash_before=h_before, src_kb_hash_after=h_after,
                  src_kb_unchanged=h_before == h_after, git_lines_changed_src_kb=git_changed_lines()),
        control=dict(sentences=len(pairs), accepted_frozen=base_frozen, accepted_strict=base_strict),
        wrong=rows,
        examples_missed_by_frozen=examples,
        reworded_h13=dict(sentences=len(rw), accepted_frozen=rw_frozen,
                          accepted_frozen_share=round(rw_frozen / len(rw), 3) if rw else None,
                          accepted_strict=rw_strict, accepted_strict_share=round(rw_strict / len(rw), 3) if rw else None),
    )
    out = ROOT / "results" / "exploratory"
    out.mkdir(parents=True, exist_ok=True)
    (out / "explain_negative_tests.json").write_text(json.dumps(res, indent=1))
    md = ["# POST-REGISTRATION: negative tests of the explanation checks", "",
          "Plan committed before the run: docs/EXPLAIN_NEGATIVE_TESTS_PLAN.md. Frozen code; no API calls. Not pre-registered.", "",
          f"Code and rules unchanged during the run: {res['meta']['src_kb_unchanged']} "
          f"(git lines changed in src/ and kb/: {res['meta']['git_lines_changed_src_kb']}).", "",
          f"Control: {len(pairs)} correct sentences; accepted by the frozen checks {base_frozen}, by the strict check {base_strict}.", "",
          "| ID | Error | Wrong sentences | Rejected, frozen checks | Rejected, strict check |", "|---|---|---|---|---|"]
    for k, r in rows.items():
        f = f"{r['rejected_frozen']} ({r['rejected_frozen_share']:.1%})" if r["wrong_sentences"] else "–"
        st = f"{r['rejected_strict']} ({r['rejected_strict_share']:.1%})" if r["wrong_sentences"] else "–"
        md.append(f"| {k} | {r['error']} | {r['wrong_sentences']} | {f} | {st} |")
    q = res["reworded_h13"]
    md += ["", f"Sentences reworded by the language model in the frozen H13 run: {q['sentences']}; accepted by the frozen "
           f"checks {q['accepted_frozen']} ({q['accepted_frozen_share']:.1%}), by the strict check {q['accepted_strict']} "
           f"({q['accepted_strict_share']:.1%}).", "", "## Examples the frozen checks accepted", ""]
    for k, ex in examples.items():
        for e in ex[:1]:
            md += [f"- {k} original: {e['original']}", f"  wrong: {e['wrong']}"]
    (out / "explain_negative_tests.md").write_text("\n".join(md) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    main()
