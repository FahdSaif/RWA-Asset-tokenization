"""Software tests for the independent oracle and its differential harness (exploratory seeds only: 0-399)."""
from rwa_threatlab import fuzz, fuzz_observed as fo, oracle_independent as oi
from rwa_threatlab.config import Config


def rec(step, tb, ta, action, before=0, after=0, who=("O", "a1")):
    return dict(step=step, tick_before=tb, tick_after=ta, action=action, before={who: before}, after={who: after})


def test_lag_boundary_and_measurement_tick():
    log = [rec(0, 10, 12, "sanction(a1)"), rec(1, 14, 17, "transfer(O:u->a1,fresh)", 0, 1)]
    end = oi.evaluate(log, oi.Conventions("end", "earliest_active"))[0]
    act = oi.evaluate(log, oi.Conventions("action", "earliest_active"))[0]
    assert (end["age"], end["within_lag"]) == (7, False)          # 17 - 10: one tick outside the window
    assert (act["age"], act["within_lag"]) == (4, True)           # 14 - 10
    log2 = [rec(0, 10, 12, "sanction(a1)"), rec(1, 13, 16, "transfer", 0, 1)]
    assert oi.evaluate(log2, oi.FUZZER_CONVENTIONS)[0]["within_lag"] is True    # age exactly 6 is inside


def test_origin_conventions_differ_with_overlapping_reasons():
    log = [rec(0, 10, 11, "sanction(a1)"), rec(1, 20, 21, "revoke(a1)"), rec(2, 25, 26, "delist(a1)"),
           rec(3, 26, 27, "transfer", 0, 1)]
    e = oi.evaluate(log, oi.Conventions("action", "earliest_active"))[0]
    c = oi.evaluate(log, oi.Conventions("action", "continuous"))[0]
    assert (e["age"], c["age"]) == (6, 16)          # earliest active reason is the revocation at 20; continuous since 10


def test_eligible_participant_never_violates_and_z_is_never_delisted():
    assert oi.evaluate([rec(0, 1, 2, "transfer", 0, 1, ("O", "u"))]) == []
    z = [rec(0, 1, 2, "delist(z)"), rec(1, 3, 4, "transfer", 0, 1, ("O", "z"))]
    assert len(oi.evaluate(z)) == 1


def test_observer_does_not_change_fuzzer_behaviour():
    for s in range(0, 15):
        res, _ = fo.observe(Config.baseline(), "none", s)
        ref = fuzz.run_trace(Config.baseline(), "none", s)
        key = lambda r: ([(v.step, v.chain, v.name, v.kind, v.lag) for v in r.violations], r.actions)  # noqa: E731
        assert key(res) == key(ref)


def _disagreements(cls, seeds=range(0, 50)):
    n = 0
    for s in seeds:
        for cfg, adv in ((Config.baseline(), "none"), (Config.hardened(), "issuer")):
            res, log = fo.observe(cfg, adv, s, run_cls=cls)
            n += oi.compare(res.violations, oi.evaluate(log, oi.FUZZER_CONVENTIONS))["disagreements"]
    return n


def test_oracles_agree_on_exploratory_seeds():
    assert _disagreements(fo.ObservedRun) == 0


def test_differential_test_has_power_against_planted_faults():
    class NoRevoke(fo.ObservedRun):
        def eligible(self, n): return fuzz.ACCREDITED[n] and n not in self.sanctioned_since

    class AgeOffByOne(fo.ObservedRun):
        def inelig_since(self, n):
            s = super().inelig_since(n)
            return None if s is None else s + 1

    class K1Blind(fo.ObservedRun):
        def eligible(self, n): return True if n == "k1" else super().eligible(n)

    for mutant in (NoRevoke, AgeOffByOne, K1Blind):
        assert _disagreements(mutant) > 0, mutant.__name__
