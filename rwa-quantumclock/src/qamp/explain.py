"""Grounded explanations of a migration plan.

Every sentence of a rationale must cite at least one identifier of a fact the system produced:
  [R:<rule id>]      a knowledge-base rule that fired for the anchor
  [E:<evidence id>]  a discovery evidence item (ABI, source line or controller)
  [P:<anchor id>]    the planner's decision for the anchor (start, effective quarter, window)
  [G:<anchor id>]    the guard's check of the anchor's bridged component
The deterministic writer composes sentences from these facts. An optional LLM writer may rephrase them; its output
passes through ``validate``, which drops any sentence without a citation or with an unknown identifier and reports
how many were dropped (RQ4 rates the surviving text).
"""
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
    return Rationale(anchor.anchor_id, lines, allowed)


def validate(text_sentences: list[str], allowed: set[str]) -> tuple[list[str], int]:
    """Keep sentences whose citations are all allowed and that cite at least one fact."""
    kept, dropped = [], 0
    for s in text_sentences:
        cites = [f"{k}:{v}" for k, v in CITE.findall(s)]
        if cites and all(c in allowed for c in cites):
            kept.append(s)
        else:
            dropped += 1
    return kept, dropped
