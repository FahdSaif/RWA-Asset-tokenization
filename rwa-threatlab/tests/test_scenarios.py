"""Every attack-tree leaf, executed against baseline / hardened / residual builds.
The expected matrix is the paper's claim for each leaf (Tables 2-4, Section 4)."""
import pytest

from rwa_threatlab.scenarios import ALL

# (baseline, hardened, residual)  True = the attack succeeds.  None = no residual variant.
EXPECTED = {
    "A1": (True, False, None), "A2": (True, False, None),
    "A3a": (True, False, True), "A3b": (True, False, True),
    "B1": (True, False, True), "B2": (True, False, True), "B3": (True, False, True),
    "C1a": (True, False, None), "C1": (True, True, None), "C2": (True, False, True),
    "D1": (True, False, True), "D2": (True, False, None), "D3": (True, False, True),
    "E1": (True, False, True), "E2": (True, False, True), "E3": (True, False, None), "E4": (True, False, True),
}


def test_every_scenario_has_an_expectation():
    assert {s.id for s in ALL} == set(EXPECTED)


@pytest.mark.parametrize("scenario", ALL, ids=lambda s: s.id)
def test_scenario_matches_paper(scenario):
    res = scenario.execute()
    base, hard, resid = EXPECTED[scenario.id]
    assert res["baseline"].attack_succeeded is base, res["baseline"].detail
    assert res["hardened"].attack_succeeded is hard, res["hardened"].detail
    if resid is None:
        assert "residual" not in res
    else:
        assert res["residual"].attack_succeeded is resid, res["residual"].detail


def test_trust_anchor_floor_no_technical_mitigation_removes_issuer_compromise():
    c1 = next(s for s in ALL if s.id == "C1").execute()
    assert c1["hardened"].attack_succeeded          # C1 survives every mitigation (paper, Sections 4.4-4.5)


def test_privileged_path_residual_reduces_to_governance():
    a3a = next(s for s in ALL if s.id == "A3a").execute()
    assert not a3a["hardened"].attack_succeeded and a3a["residual"].attack_succeeded
    assert "OK" in a3a["residual"].detail           # succeeded only after the rule set itself was corrupted


def test_privacy_metrics():
    d1 = next(s for s in ALL if s.id == "D1").execute()
    assert d1["baseline"].metrics["linkage"] > 0.5 and d1["hardened"].metrics["linkage"] < 0.2
    d2 = next(s for s in ALL if s.id == "D2").execute()
    assert d2["baseline"].metrics["bits"] > 1.5 and d2["hardened"].metrics["bits"] == 0.0
    assert d2["baseline"].metrics["p5_anonymity_set"] < d2["baseline"].metrics["anonymity_set"]
    assert d2["baseline"].metrics["distinct_error_codes"] == 3 and d2["hardened"].metrics["distinct_error_codes"] == 1


def test_b2_residual_is_an_availability_attack_that_expires():
    b2 = next(s for s in ALL if s.id == "B2").execute()
    assert b2["residual"].metrics["restored"] is True
