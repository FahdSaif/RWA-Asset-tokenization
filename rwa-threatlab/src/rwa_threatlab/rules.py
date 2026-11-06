"""Compliance rules, versioned rule sets, and the Compliance Parameter Store."""
from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field


@dataclass(frozen=True)
class SubRule:
    id: str
    requires: tuple[tuple[str, str], ...]  # (claim name, value) pairs that must all be proven


@dataclass(frozen=True)
class Rule:
    asset: str
    class_label: str
    subrules: tuple[SubRule, ...]  # eligible if ANY sub-rule is satisfied


@dataclass(frozen=True)
class RuleSet:
    version: int
    rules: tuple[Rule, ...]
    sanctioned: frozenset[str] = frozenset()

    def rule_for(self, asset: str) -> Rule | None:
        for r in self.rules:
            if r.asset == asset:
                return r
        return None


def classify_change(old: RuleSet, new: RuleSet) -> str:
    """'relax' if the change can admit someone previously rejected (mixed changes count as relax),
    'tighten' if it can only reject more, else 'none'. Drives asymmetric activation (M5)."""
    relax = bool(old.sanctioned - new.sanctioned)
    tight = bool(new.sanctioned - old.sanctioned)
    ro = {r.asset: r for r in old.rules}
    rn = {r.asset: r for r in new.rules}
    for asset in set(ro) | set(rn):
        a, b = ro.get(asset), rn.get(asset)
        if a is None and b is not None:
            tight = True
        elif b is None and a is not None:
            relax = True
        elif a is not None and b is not None:
            sa = {(s.id, s.requires) for s in a.subrules}
            sb = {(s.id, s.requires) for s in b.subrules}
            if sb - sa:
                relax = True
            if sa - sb:
                tight = True
    return "relax" if relax else "tighten" if tight else "none"


@dataclass
class ParameterStore:
    """Authoritative, versioned set of rules. Modified only through the governance path."""
    history: list[tuple[RuleSet, int, str]] = field(default_factory=list)

    @property
    def active(self) -> RuleSet:
        return self.history[-1][0]

    def activate(self, rs: RuleSet, tick: int, via: str) -> RuleSet:
        version = (self.history[-1][0].version + 1) if self.history else 1
        rs = dataclasses.replace(rs, version=version)
        self.history.append((rs, tick, via))
        return rs
