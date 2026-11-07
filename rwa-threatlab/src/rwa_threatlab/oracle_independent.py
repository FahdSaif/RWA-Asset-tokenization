"""Independent implementation of the oracle of truth, written from docs/ORACLE_SPEC.md only.

Imports nothing from the fuzzer. Its only inputs are the step log and the constants of the specification's fixture.
Limitation: the exogenous events (sanction/delist/revoke) are read from the fuzzer's own action text, so this checks the
oracle's eligibility, age and violation logic, not whether the fuzzer applied an event to the system correctly.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

PARTICIPANTS = ("u", "x", "z", "a1", "a2", "k1")
ACCREDITED = {"u": True, "x": False, "z": True, "a1": True, "a2": True, "k1": False}   # spec section 1
PERMANENTLY_LISTED_AT_START = ("z",)
L_DOC = 6
BEFORE_RUN = -1000
_EVENT = re.compile(r"^(sanction|delist|revoke)\((\w+)\)$")


@dataclass(frozen=True)
class Conventions:
    measure_at: str = "end"              # "end" | "action"            (spec section 5, row 1)
    origin: str = "earliest_active"      # "earliest_active" | "continuous"   (spec section 5, row 2)


FUZZER_CONVENTIONS = Conventions("end", "earliest_active")
NATURAL_CONVENTIONS = Conventions("action", "continuous")
ALL_CONVENTIONS = {
    "end/earliest": Conventions("end", "earliest_active"),
    "end/continuous": Conventions("end", "continuous"),
    "action/earliest": Conventions("action", "earliest_active"),
    "action/continuous": Conventions("action", "continuous"),
}


class _Truth:
    def __init__(self) -> None:
        self.listed = {n: BEFORE_RUN for n in PERMANENTLY_LISTED_AT_START}
        self.revoked: dict[str, int] = {}
        self.cont: dict[str, int | None] = {n: (None if self._elig(n) else BEFORE_RUN) for n in PARTICIPANTS}

    def _elig(self, n: str) -> bool:
        return ACCREDITED[n] and n not in self.listed and n not in self.revoked

    eligible = _elig

    def apply(self, action: str, tick: int) -> None:
        m = _EVENT.match(action)
        if not m or m.group(2) not in PARTICIPANTS:
            return
        kind, n = m.groups()
        was = self._elig(n)
        if kind == "sanction":
            self.listed.setdefault(n, tick)
        elif kind == "delist" and n not in PERMANENTLY_LISTED_AT_START:
            self.listed.pop(n, None)
        elif kind == "revoke":
            self.revoked.setdefault(n, tick)
        now = self._elig(n)
        if was and not now:
            self.cont[n] = tick
        elif now:
            self.cont[n] = None

    def since(self, n: str, origin: str) -> int:
        if origin == "continuous":
            return self.cont[n]  # type: ignore[return-value]
        starts = ([BEFORE_RUN] if not ACCREDITED[n] else []) + [t for t in (self.listed.get(n), self.revoked.get(n)) if t is not None]
        return min(starts)


def evaluate(log: list[dict], conv: Conventions = FUZZER_CONVENTIONS) -> list[dict]:
    truth, out = _Truth(), []
    for rec in log:
        truth.apply(rec["action"], rec["tick_before"])
        T = rec["tick_after"] if conv.measure_at == "end" else rec["tick_before"]
        for (chain, n), amt in rec["after"].items():
            if n in PARTICIPANTS and amt > rec["before"][(chain, n)] and not truth.eligible(n):
                age = T - truth.since(n, conv.origin)
                out.append(dict(step=rec["step"], chain=chain, name=n, age=age, within_lag=0 <= age <= L_DOC))
    return out


def compare(fuzzer_violations, oracle_violations) -> dict:
    """Differential comparison on one trace. Fuzzer violations are fuzz.Violation objects."""
    f = {(v.step, v.chain, v.name): v for v in fuzzer_violations}
    o = {(v["step"], v["chain"], v["name"]): v for v in oracle_violations}
    missing, extra = sorted(set(f) - set(o)), sorted(set(o) - set(f))
    age_diff = [k for k in f.keys() & o.keys() if f[k].lag != o[k]["age"]]
    class_diff = [k for k in f.keys() & o.keys() if (f[k].lag is not None and 0 <= f[k].lag <= L_DOC) != o[k]["within_lag"]]
    return dict(n_fuzzer=len(f), n_oracle=len(o), missing_in_oracle=missing, extra_in_oracle=extra,
                age_mismatch=age_diff, class_mismatch=class_diff,
                disagreements=len(missing) + len(extra) + len(age_diff) + len(class_diff))
