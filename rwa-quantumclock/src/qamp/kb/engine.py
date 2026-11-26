"""Rule engine.

Rules live in kb/*.yaml, each with its source. The engine applies them to an anchor until
nothing changes and records which rules fired, so every conclusion can be cited.

Conditions: all / any / not, or {"fact": name, <op>: value}.
Conclusions: deadlines and dates (earliest wins), retention years (largest wins),
urgency and flags (collected), set (new facts for later rules)."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from .. import config

_OPS = {
    "eq": lambda a, b: a == b,
    "ne": lambda a, b: a != b,
    "in": lambda a, b: a in b,
    "not_in": lambda a, b: a not in b,
    "gt": lambda a, b: a is not None and a > b,
    "ge": lambda a, b: a is not None and a >= b,
    "lt": lambda a, b: a is not None and a < b,
    "le": lambda a, b: a is not None and a <= b,
    "contains_any": lambda a, b: bool(set(a or []) & set(b)),
    "is_null": lambda a, b: (a is None) == bool(b),
    "is_true": lambda a, b: (a is True) == bool(b),
    "is_false": lambda a, b: (a is False) == bool(b),
}


@dataclass
class Rule:
    id: str
    when: dict
    then: dict
    source: dict
    description: str = ""


@dataclass
class Inference:
    facts: dict
    conclusions: dict
    trace: list[dict] = field(default_factory=list)

    def fired(self) -> list[str]:
        return [t["rule"] for t in self.trace]


def _eval(cond: dict, facts: dict) -> bool:
    if "all" in cond:
        return all(_eval(c, facts) for c in cond["all"])
    if "any" in cond:
        return any(_eval(c, facts) for c in cond["any"])
    if "not" in cond:
        return not _eval(cond["not"], facts)
    name = cond["fact"]
    ops = [k for k in cond if k != "fact"]
    if len(ops) != 1 or ops[0] not in _OPS:
        raise ValueError(f"bad condition {cond}")
    op = ops[0]
    return _OPS[op](facts.get(name), cond[op])


class KnowledgeBase:
    def __init__(self, rules: list[Rule]):
        ids = [r.id for r in rules]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate rule ids")
        self.rules = rules

    def infer(self, facts: dict) -> Inference:
        facts = dict(facts)
        concl: dict[str, Any] = dict(urgency=[], flags=[])
        trace: list[dict] = []
        fired: set[str] = set()
        changed = True
        while changed:
            changed = False
            for r in self.rules:
                if r.id in fired or not _eval(r.when, facts):
                    continue
                fired.add(r.id)
                changed = True
                trace.append(dict(rule=r.id, then=r.then, source=r.source.get("title", ""), clause=r.source.get("clause", ""),
                                  verified=bool(r.source.get("verified", False))))
                for k, v in r.then.items():
                    if k in ("deadline_hard", "deadline_soft", "target_date"):
                        v = str(v)
                        concl[k] = min(concl[k], v) if k in concl else v
                    elif k == "retention_years":
                        concl[k] = max(concl.get(k, 0), v)
                    elif k in ("urgency", "flags"):
                        for x in v:
                            if x not in concl[k]:
                                concl[k].append(x)
                    elif k == "set":
                        facts.update(v)
                    else:
                        raise ValueError(f"rule {r.id}: unknown conclusion {k}")
        return Inference(facts=facts, conclusions=concl, trace=trace)

    def unverified(self) -> list[str]:
        return [r.id for r in self.rules if not r.source.get("verified", False)]


def load_kb(kb_dir: Path = config.KB_DIR, exclude: tuple[str, ...] = ()) -> KnowledgeBase:
    rules: list[Rule] = []
    for p in sorted(Path(kb_dir).glob("*.yaml")):
        for d in yaml.safe_load(p.read_text()) or []:
            if d["id"] in exclude:
                continue
            for req in ("id", "when", "then", "source"):
                if req not in d:
                    raise ValueError(f"{p.name}: rule missing {req}: {d}")
            rules.append(Rule(id=d["id"], when=d["when"], then=d["then"], source=d["source"],
                              description=d.get("description", "")))
    return KnowledgeBase(rules)


def anchor_facts(anchor, jurisdictions: tuple[str, ...] = ("US", "EU")) -> dict:
    """The facts about an anchor that the rules can see."""
    return dict(
        anchor_id=anchor.anchor_id, role=anchor.role, controller_type=anchor.controller_type,
        algorithm=anchor.algorithm, quantum_vulnerable=anchor.quantum_vulnerable, key_exposed=anchor.key_exposed,
        n_keys=anchor.n_keys, capabilities=list(anchor.capabilities), signs_records=anchor.signs_records,
        value_usd=anchor.value_usd, n_tokens=len(anchor.tokens), n_instances=len(anchor.instances),
        jurisdictions=list(jurisdictions),
    )
