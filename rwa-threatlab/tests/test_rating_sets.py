"""Residual bands under the three rating sets (original, post-hoc revision, assessors' median) are pinned here.
If the scores file, the rubric or the revision changes, these tests fail."""
from rwa_threatlab import rating_sets, risk

EXPECTED = {  # id: (original, revised, median rounded down, median rounded up)
    "A1/A2": ("Low", "Low", "Low", "Low"),
    "A3": ("Medium", "Medium", "Low-Med", "Medium"),
    "B1": ("Medium", "Medium", "Medium", "Medium"),
    "B2": ("Low-Med", "Low-Med", "Low-Med", "Medium"),
    "B3": ("Medium", "Medium", "Medium", "Medium"),
    "C1": ("Medium", "Medium", "Low-Med", "Low-Med"),
    "C2": ("Low-Med", "Low-Med", "Low-Med", "Low-Med"),
    "D1": ("Medium", "High", "Low-Med", "Low-Med"),
    "D2": ("Low-Med", "Med-High", "High", "High"),
    "D3": ("Low-Med", "Low-Med", "Low", "Low"),
    "E1": ("Medium", "Medium", "Medium", "Medium"),
    "E2": ("Medium", "Medium", "Low-Med", "Low-Med"),
    "E3": ("Low-Med", "Low-Med", "Low-Med", "Low-Med"),
    "E4": ("Low-Med", "Low-Med", "Medium", "Medium"),
}


def test_bands_under_all_sets():
    res = rating_sets.compute()
    got = {r["id"]: tuple(r["bands"][k] for k in rating_sets.SETS) for r in res["rows"]}
    assert got == EXPECTED


def test_original_set_equals_primary_table():
    res = rating_sets.compute()
    assert {r["id"]: r["levels"]["original"] for r in res["rows"]} == {r["id"]: r["res"] for r in risk.table()}


def test_robust_and_dependent_findings():
    res = rating_sets.compute()
    assert res["same_in_all_sets"] == [("A1/A2", "Low"), ("B1", "Medium"), ("B3", "Medium"), ("C2", "Low-Med"),
                                       ("E1", "Medium"), ("E3", "Low-Med")]
    assert res["depends_on_rounding"] == ["A3", "B2"]
    assert res["depends_on_rating_set"] == ["C1", "D1", "D2", "D3", "E2", "E4"]
    d2 = next(r for r in res["rows"] if r["id"] == "D2")
    assert min(d2["levels"][k] for k in ("revised", "median_down", "median_up")) >= 4   # Med-High or above unless original


def test_assessors_support_only_the_d2_scope_change():
    chk = rating_sets.compute()["scope_revision_check"]
    assert chk["D1"]["assessors"] == [1, 1, 1, 1] and not chk["D1"]["assessors_support_revision"]
    assert chk["D3"]["assessors"] == [1, 1, 1, 1] and not chk["D3"]["assessors_support_revision"]
    assert chk["D2"]["assessors"] == [3, 2, 3, 3] and chk["D2"]["assessors_support_revision"]
