"""Explanations of a plan, and checks that they are true.

Each sentence must cite what it is based on:
  [R:rule] a rule, [E:evidence] a contract finding, [P:anchor] the plan, [G:anchor] the bridge check.

Checks (RQ4):
  citation validity   every sentence cites something that exists
  faithfulness        every date or number comes from what it cites
  counterfactual      change one fact, and only the matching sentences change"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from . import config
from .loss import effective_quarter

CITE = re.compile(r"\[(R|E|P|G):([^\]]+)\]")


@dataclass
class Rationale:
    anchor_id: str
    sentences: list[str]
    allowed: set[str] = field(default_factory=set)
    facts: dict[str, list[str]] = field(default_factory=dict)   # cited id -> values it gives


def allowed_ids(anchor, inference, evidence_ids: list[str], guard_ids: list[str]) -> set[str]:
    s = {f"R:{r}" for r in inference.fired()} | {f"E:{e}" for e in evidence_ids} | {f"P:{anchor.anchor_id}"}
    s |= {f"G:{g}" for g in guard_ids}
    return s


def write(anchor, start_q, inference, evidence_ids: list[str], guard_result=None) -> Rationale:
    c = inference.conclusions
    E = effective_quarter(anchor, start_q)
    lines = []
    p = f"[P:{anchor.anchor_id}]"
    if start_q is None:
        lines.append(f"No migration is scheduled for this anchor {p}.")
    else:
        latest = None
        b = anchor.calendar.next_boundary(start_q + max(1, anchor.migration_quarters) + anchor.timelock_quarters)
        latest = b - max(1, anchor.migration_quarters) - anchor.timelock_quarters
        lines.append(f"Start the migration in {config.quarter_label(start_q)}; with a planned execution time of "
                     f"{anchor.migration_quarters} quarter(s) it takes effect at the renewal boundary {config.quarter_label(E)} {p}.")
        lines.append(f"The decision window for that boundary closes at the start of {config.quarter_label(latest)}; "
                     f"a later start waits {anchor.calendar.period} quarter(s) for the next boundary {p}.")
    for r in inference.trace:
        then = r["then"]
        if "deadline_hard" in then:
            lines.append(f"The algorithm {anchor.algorithm} is disallowed after {then['deadline_hard']} under NIST IR 8547 [R:{r['rule']}].")
        elif "deadline_soft" in then:
            lines.append(f"It is deprecated after {then['deadline_soft']} [R:{r['rule']}].")
        elif "retention_years" in then:
            lines.append(f"The anchor signs compliance records that must remain evidence for {then['retention_years']} years [R:{r['rule']}].")
        elif "urgency" in then and "exposed_key_forgery" in then["urgency"]:
            lines.append(f"Its public key can be attacked as soon as a CRQC exists [R:{r['rule']}].")
        elif "urgency" in then and "single_key_admin" in then["urgency"]:
            lines.append(f"A single externally owned account controls the token [R:{r['rule']}].")
        elif "flags" in then and "discovery_incomplete" in then["flags"]:
            lines.append(f"The key holders could not be read on-chain and must be identified first [R:{r['rule']}].")
    for e in evidence_ids[:3]:
        lines.append(f"Inventory evidence: {e.split(':', 2)[-1]} [E:{e}].")
    if guard_result is not None:
        g = f"[G:{guard_result.anchor_id}]"
        lines.append(("The bridged instances are migrated together; the model check found no mixed-state violation " + g + ".")
                     if not guard_result.violation else ("The model check found a mixed-state violation; see the trace " + g + "."))
    allowed = allowed_ids(anchor, inference, evidence_ids, [guard_result.anchor_id] if guard_result else [])
    facts: dict[str, list[str]] = {f"P:{anchor.anchor_id}": []}
    if start_q is not None:
        facts[f"P:{anchor.anchor_id}"] = [config.quarter_label(start_q), config.quarter_label(E), config.quarter_label(latest),
                                          str(anchor.migration_quarters), str(anchor.calendar.period)]
    for r in inference.trace:
        facts[f"R:{r['rule']}"] = [str(v) for v in r["then"].values() if isinstance(v, (str, int, float))] + [anchor.algorithm]
    for e in evidence_ids:
        facts[f"E:{e}"] = _values(e.split(":", 2)[-1])
    if guard_result is not None:
        facts[f"G:{guard_result.anchor_id}"] = []
    return Rationale(anchor.anchor_id, lines, allowed, facts)


_STATIC = re.compile(r"NIST IR 8547|\[[RPEG]:[^\]]+\]")
_VALUE = re.compile(r"\b\d{4} Q[1-4]\b|\b\d{4}-\d{2}-\d{2}\b|(?<![\w.])\d+(?:\.\d+)?(?![\w.])")


def _values(text: str) -> list[str]:
    """Dates, quarters and numbers a sentence states."""
    t = _STATIC.sub(" ", text)
    out = []
    for m in _VALUE.finditer(t):
        v = m.group(0)
        out.append(str(int(float(v))) if re.fullmatch(r"\d+\.0", v) else v)
    return out


def faithful(sentence: str, facts: dict[str, list[str]]) -> bool:
    """True if every value in the sentence comes from what it cites, no more often than given.

    Does not catch two valid values swapped."""
    from collections import Counter
    cites = [f"{k}:{v}" for k, v in CITE.findall(sentence)]
    support: Counter = Counter()
    for c in dict.fromkeys(cites):
        support.update(str(int(float(x))) if re.fullmatch(r"\d+\.0", x) else x for x in facts.get(c, []))
    need = Counter(_values(sentence))
    return bool(cites) and all(support[v] >= n for v, n in need.items())


def scores(rationales: list[Rationale]) -> dict:
    n = sum(len(r.sentences) for r in rationales)
    valid = sum(len(validate(r.sentences, r.allowed)[0]) for r in rationales)
    faith = sum(faithful(s, r.facts) for r in rationales for s in r.sentences)
    return dict(sentences=n, citation_validity=valid / n if n else None, faithfulness=faith / n if n else None)


def counterfactual_consistency(dep, ctx: dict, starts: dict, kb, evidence: dict[str, list[str]] | None = None) -> dict:
    """Changes one fact at a time and checks that only the matching sentences change."""
    import copy
    from .kb.engine import anchor_facts
    evidence = evidence or {}
    cases, passed, fails = 0, 0, []

    def tagged(r: Rationale, tag: str) -> list[str]:
        return [x for x in r.sentences if f"[{tag}" in x]

    for a in dep.anchors:
        t = starts.get(a.anchor_id)
        ev = evidence.get(a.anchor_id, [])
        base = write(a, t, ctx[a.anchor_id]["inference"], ev)
        if t is not None and t < config.PLAN_LAST_QUARTER:
            cases += 1
            alt = write(a, t + 1, ctx[a.anchor_id]["inference"], ev)
            non_p_same = [x for x in base.sentences if "[P:" not in x] == [x for x in alt.sentences if "[P:" not in x]
            p_changed = tagged(base, "P:") != tagged(alt, "P:")
            ok = non_p_same and p_changed
            passed += ok
            if not ok:
                fails.append((a.anchor_id, "start"))
        for field_name, values in (("signs_records", (True, False)), ("key_exposed", (None, False)),
                                   ("controller_type", ("eoa", "multisig"))):
            if field_name == "controller_type" and a.role not in ("upgrade_admin", "owner_admin"):
                continue
            for v in values:
                b = copy.deepcopy(a)
                setattr(b, field_name, v)
                inf = kb.infer(anchor_facts(b))
                r = write(b, t, inf, ev)
                cases += 1
                if field_name == "signs_records":
                    ok = bool([x for x in r.sentences if "remain evidence" in x]) == v
                elif field_name == "key_exposed":
                    ok = bool([x for x in r.sentences if "attacked as soon as" in x]) == (v is not False)
                else:
                    ok = bool([x for x in r.sentences if "single externally owned account" in x]) == (v == "eoa")
                ok = ok and all(validate([x], r.allowed)[0] for x in r.sentences) and all(faithful(x, r.facts) for x in r.sentences)
                passed += ok
                if not ok:
                    fails.append((a.anchor_id, f"{field_name}={v}"))
    return dict(cases=cases, consistency=passed / cases if cases else None, failures=fails[:20])


def rephrase_with_llm(r: Rationale, transport) -> tuple[list[str], int]:
    """Asks an LLM to reword the explanation for an auditor; keeps only sentences that pass the checks."""
    prompt = ("Rewrite the following rationale for a compliance auditor in plain English, one sentence per line. Keep every "
              "bracketed citation exactly as written at the end of the sentence it supports; do not add facts or citations.\n\n"
              + "\n".join(r.sentences))
    out = [x.strip() for x in transport(prompt).splitlines() if x.strip()]
    kept, dropped = validate(out, r.allowed)
    kept = [x for x in kept if faithful(x, r.facts)]
    return kept, len(out) - len(kept)


def validate(text_sentences: list[str], allowed: set[str]) -> tuple[list[str], int]:
    """Keeps sentences that cite at least one fact and only known facts."""
    kept, dropped = [], 0
    for s in text_sentences:
        cites = [f"{k}:{v}" for k, v in CITE.findall(s)]
        if cites and all(c in allowed for c in cites):
            kept.append(s)
        else:
            dropped += 1
    return kept, dropped
