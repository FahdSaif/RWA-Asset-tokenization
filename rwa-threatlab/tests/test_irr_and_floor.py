"""Format and arithmetic tests for the inter-rater tooling. The scores below are test fixtures, not assessments."""
from rwa_threatlab import irr, risk


def test_alpha_is_one_for_identical_raters_and_low_for_disagreement():
    same = [[1, 1], [2, 2], [3, 3], [2, 2]]
    assert abs(irr.krippendorff_alpha_ordinal(same) - 1.0) < 1e-9
    opp = [[1, 3], [3, 1], [1, 3], [3, 1]]
    assert irr.krippendorff_alpha_ordinal(opp) < 0
    assert irr.krippendorff_alpha_ordinal([[2, 2], [2, 2]]) is None       # no variation: undefined


def test_authors_scores_through_irr_reproduce_the_paper_bands(tmp_path):
    p = tmp_path / "s.csv"
    lines = ["assessor,scenario,F1,F2,F3,G1,G2,G3"]
    for sid, _, _, _, _, F, G, _ in risk.S:
        lines.append(f"authors,{sid},{F[0]},{F[1]},{F[2]},{G[0]},{G[1]},{G[2]}")
        lines.append(f"copy,{sid},{F[0]},{F[1]},{F[2]},{G[0]},{G[1]},{G[2]}")
    p.write_text("\n".join(lines) + "\n")
    rep = irr.report(irr.load_scores(p))
    assert rep["band_agreement"] == 1.0
    assert all(v["exact"] == 1.0 for v in rep["per_factor"].values())
    base = {r["id"]: r["res"] for r in risk.table()}
    assert {s: b["authors"] for s, b in rep["bands"].items()} == base


def test_floor_dependence_only_moves_b1():
    d = risk.floor_dependence()
    assert [c[0] for c in d["band_changes"]] == ["B1"]
    assert d["without_floor"][0][0] != "B1"
