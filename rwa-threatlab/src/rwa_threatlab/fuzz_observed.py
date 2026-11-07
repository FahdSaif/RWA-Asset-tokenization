"""Observer for the fuzzer (H11). Records, per step, what an independent oracle needs: ticks, the action text and
the ledger balances. It subclasses the frozen fuzzer's run class and changes no behaviour (checked by a test)."""
from __future__ import annotations

from . import fuzz
from .config import Config


class ObservedRun(fuzz._Run):
    def __init__(self, cfg, adv, seed):
        super().__init__(cfg, adv, seed)
        self.log: list[dict] = []

    def step(self, i: int) -> None:
        tick_before, before = self.w.clock.now, self.holdings()
        super().step(i)
        self.log.append(dict(step=i, tick_before=tick_before, tick_after=self.w.clock.now,
                             action=self.result.actions[-1], before=before, after=self.holdings()))


def observe(cfg: Config, adv_name: str, seed: int, steps: int = 40, run_cls=ObservedRun):
    """Same as fuzz.run_trace, but also returns the step log."""
    r = run_cls(cfg, fuzz.ADVERSARIES[adv_name], seed)
    for i in range(steps):
        r.step(i)
    r.result.installs = list(r.installs)
    r.result.trail_ok = r.w.o.trail.verify()[0] and r.w.d.trail.verify()[0]
    return r.result, r.log
