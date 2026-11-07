"""Replay of real sanctions-list histories inside the fuzzer (addendum A3).

`ReplayRun` replaces the fuzzer's random sanction/delist actions with scripted events and changes nothing else. The
scripted action is executed by the frozen fuzzer's own `a_sanction` / `a_delist` (the random choice is forced to the
scripted participant), so no fuzzer semantics are duplicated. The step log is recorded (as in `fuzz_observed`), which
lets the independent oracle be re-run on every replay trace.
"""
from __future__ import annotations

import dataclasses

from . import oracle_independent as oi
from .config import Config
from .fuzz import ADVERSARIES
from .fuzz_observed import ObservedRun
from .traces import ofac


class _Force:
    """Random-source shim: the first `choice` returns `value` (if it is a valid option); everything else is delegated."""

    def __init__(self, rnd, value):
        self._r, self._v, self.used = rnd, value, False

    def choice(self, seq):
        if not self.used and self._v in seq:
            self.used = True
            return self._v
        return self._r.choice(seq)

    def __getattr__(self, k):
        return getattr(self._r, k)


class ReplayRun(ObservedRun):
    def __init__(self, cfg, adv, seed, schedule: dict[int, tuple[str, str]]):
        super().__init__(cfg, adv, seed)
        self.schedule, self._now = schedule, None
        self.applied = self.skipped = 0

    def menu(self):
        if self._now is not None:
            return [(self._inject, 1)]
        return [(f, w) for f, w in super().menu() if f.__name__ not in ("a_sanction", "a_delist")]

    def step(self, i):
        self._now = self.schedule.get(i)
        try:
            super().step(i)
        finally:
            self._now = None

    def _inject(self):
        kind, name = self._now
        valid = (name not in self.sanctioned_since) if kind == "sanction" else (name in self.sanctioned_since and name != "z")
        if not valid:
            self.skipped += 1
            return f"{kind}(skip)"
        saved, self.rnd = self.rnd, _Force(self.rnd, name)
        try:
            desc = self.a_sanction() if kind == "sanction" else self.a_delist()
        finally:
            self.rnd = saved
        self.applied += 1
        return desc


def replay_trace(cfg: Config, adv_name: str, seed: int, schedule: dict, steps: int = 40):
    r = ReplayRun(cfg, ADVERSARIES[adv_name], seed, schedule)
    for i in range(steps):
        r.step(i)
    r.result.installs = list(r.installs)
    r.result.trail_ok = r.w.o.trail.verify()[0] and r.w.d.trail.verify()[0]
    return r


def replay_campaign(cfg: Config, adv_name: str, events, renames, window: tuple[str, str], variant: str,
                    seed0: int, traces: int, steps: int = 40) -> dict:
    hist = ofac.build_histories(events, renames, *window)
    pool = ofac.volatile_pool(hist)
    dated = ofac.dated_histories(events, renames, *window)
    kinds = {"documented-lag": 0, "adversary": 0, "UNEXPLAINED": 0}
    with_v = crashes = bad_trails = scheduled = applied = skipped = oracle_dis = oracle_cmp = 0
    caps: dict[str, int] = {}
    installs: dict[str, int] = {}
    examples: list[dict] = []
    for s in range(seed0, seed0 + traces):
        entries = ofac.sample_entries(pool, s)
        sched = ofac.make_schedule(entries, dated, variant, steps)
        r = replay_trace(cfg, adv_name, s, sched, steps)
        res = r.result
        scheduled += len(sched)
        applied += r.applied
        skipped += r.skipped
        crashes += res.crashed is not None
        bad_trails += not res.trail_ok
        for n in res.installs:
            installs[n] = installs.get(n, 0) + 1
        with_v += bool(res.violations)
        cmp_ = oi.compare(res.violations, oi.evaluate(r.log, oi.FUZZER_CONVENTIONS))
        oracle_cmp += cmp_["n_fuzzer"]
        oracle_dis += cmp_["disagreements"]
        for v in res.violations:
            kinds[v.kind] += 1
            if v.kind == "adversary":
                k = "+".join(v.caps)
                caps[k] = caps.get(k, 0) + 1
            if v.kind == "UNEXPLAINED" and len(examples) < 3:
                examples.append(dict(seed=s, variant=variant, violation=dataclasses.asdict(v), actions=res.actions[: v.step + 1]))
        if res.crashed and len(examples) < 3:
            examples.append(dict(seed=s, variant=variant, crash=res.crashed, actions=res.actions))
    return dict(adversary=adv_name, variant=variant, traces=traces, steps=steps, traces_with_violation=with_v,
                violations=kinds, adversary_cap_sets=dict(sorted(caps.items())), installs=installs, crashes=crashes,
                trail_integrity_failures=bad_trails, events_scheduled=scheduled, events_applied=applied,
                events_skipped=skipped, oracle_compared=oracle_cmp, oracle_disagreements=oracle_dis, examples=examples,
                pool_size=len(pool))
