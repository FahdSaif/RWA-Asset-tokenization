"""The scaled model must agree with the original at k=2, n=4 and keep the paper's safe/unsafe pattern at scale."""
from rwa_threatlab import modelcheck, modelcheck_scaled as ms


def test_reproduces_original_verdicts_at_k2_n4():
    el = ms.paper_eligibility(2, 4)
    orig = modelcheck.run(verbose=False)
    comp = {c["id"]: c["violation"] for c in orig["composition"]}
    lag = {c["id"]: c["violation"] for c in orig["lag"]}
    r = ms.run_on(el)
    assert r["alone"]["violation"] is False                              # I1, I2
    assert r["bridge_baseline"]["violation"] is comp["I3"] is True       # I3
    assert r["bridge_dest_mediated"]["violation"] is comp["I4"] is False  # I4
    assert r["lag_single_instance"]["violation"] is lag["B2"] is True    # B2
    assert r["lag_origin_only"]["violation"] is lag["E1"] is True        # E1
    assert r["lag_atomic"]["violation"] is lag["E1m"] is False           # E1m


def test_safe_claims_hold_for_every_random_instance():
    import random
    rnd = random.Random(99)
    for k in (2, 3, 4):
        for n in (4, 6):
            for _ in range(15):
                r = ms.run_on(ms.random_eligibility(k, n, rnd))
                assert not r["alone"]["violation"]
                assert not r["bridge_dest_mediated"]["violation"]
                assert not r["lag_atomic"]["violation"]


def test_composition_failure_persists_at_scale():
    for k in (3, 4, 5):
        assert ms.run_on(ms.paper_eligibility(k, 8))["bridge_baseline"]["violation"]
        assert ms.run_on(ms.paper_eligibility(k, 8))["lag_origin_only"]["violation"]
