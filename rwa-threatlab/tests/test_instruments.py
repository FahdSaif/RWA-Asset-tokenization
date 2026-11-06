"""Software tests for the research instruments themselves (fuzzer oracle, data loaders, determinism)."""
from rwa_threatlab import fuzz
from rwa_threatlab.config import Config
from rwa_threatlab.scenarios import privacy


def test_fuzzer_is_deterministic_per_seed():
    a = fuzz.run_trace(Config.hardened(), "quorum", 7, steps=25)
    b = fuzz.run_trace(Config.hardened(), "quorum", 7, steps=25)
    assert a.actions == b.actions and a.violations == b.violations


def test_fuzzer_oracle_is_sensitive_on_a_faulty_build():
    c = fuzz.campaign(Config.baseline(), "quorum", traces=30, steps=30)
    assert c["traces_with_violation"] > 20            # otherwise the instrument would be vacuous


def test_fuzzer_never_crashes_or_breaks_the_trail_on_either_build():
    for cfg in (Config.baseline(), Config.hardened()):
        c = fuzz.campaign(cfg, "quorum+censor", traces=40, steps=30)
        assert c["crashes"] == 0 and c["trail_integrity_failures"] == 0


def test_privacy_attacker_runs_on_external_csv(tmp_path):
    f = tmp_path / "pairs.csv"                          # tiny synthetic fixture; real traces use the same format
    f.write_text("event_tick,submit_tick\n" + "\n".join(f"{10 * i},{10 * i + 2}" for i in range(50)))
    pairs = privacy.load_event_pairs_csv(f)
    assert len(pairs) == 50 and privacy.linkage_from_pairs(pairs) > 0.9
