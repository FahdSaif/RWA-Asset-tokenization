"""The revision changes exactly three scope scores and nothing else; the original table is untouched."""
from rwa_threatlab import risk, risk_revised as rr


def test_only_three_scope_scores_change():
    diffs = []
    for old, new in zip(risk.S, rr.revised_scenarios()):
        assert old[:5] == new[:5] and old[5] == new[5] and old[7] == new[7]          # id, names, adversary, F factors, mitigation
        for i, (a, b) in enumerate(zip(old[6], new[6])):
            if a != b:
                diffs.append((old[0], i, a, b))
    assert diffs == [("D1", 0, 1, 3), ("D2", 0, 1, 3), ("D3", 0, 1, 2)]


def test_original_ratings_are_reproduced_when_not_revised():
    assert {r["id"]: r["res"] for r in rr.table(False)} == {r["id"]: r["res"] for r in risk.table()}


def test_revised_bands_and_headline_claims():
    t = {r["id"]: r for r in rr.table(True)}
    assert (t["D1"]["I"], t["D1"]["res"], t["D1"]["P"]) == (5, 5, 20)       # High
    assert (t["D2"]["I"], t["D2"]["res"], t["D2"]["P"]) == (5, 4, 15)       # Med-High
    assert (t["D3"]["I"], t["D3"]["res"], t["D3"]["P"]) == (4, 2, 8)        # Low-Med
    h = rr.headline(True)
    assert h["low"] == ["A1/A2"]                                            # still the only Low residual
    assert h["floor_changes"] == ["B1"]                                     # the floor still binds only on B1
    assert h["medium_or_above"] == ["A3", "B1", "B3", "C1", "D1", "D2", "E1", "E2"]
    assert [k for k, _, _ in rr.ranking(True)[:2]] == ["D1", "D2"]
