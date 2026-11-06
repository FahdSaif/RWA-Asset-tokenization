"""The rubric reproduces the paper's Table 4 and the model checker reproduces Table 5."""
import json

from rwa_threatlab import modelcheck, risk
from rwa_threatlab.__main__ import main

PAPER_RESIDUAL = {"A1/A2": "Low", "A3": "Medium", "B1": "Medium", "B2": "Low-Med", "B3": "Medium",
                  "C1": "Medium", "C2": "Low-Med", "D1": "Medium", "D2": "Low-Med", "D3": "Low-Med",
                  "E1": "Medium", "E2": "Medium", "E3": "Low-Med", "E4": "Low-Med"}


def test_rubric_reproduces_residual_ratings():
    rows = {r["id"]: risk.LV[r["res"]] for r in risk.table()}
    assert rows == PAPER_RESIDUAL


def test_trust_anchor_rows_are_the_highest_impact_medium_rows():
    rows = risk.table()
    top = {r["id"] for r in rows if r["res"] >= 3 and r["I"] == 5}
    assert top == {"A3", "B1", "B3", "C1"}
    assert [r["id"] for r in rows if r["res"] == 1] == ["A1/A2"]      # only the user path is Low


def test_sensitivity_claims():
    s = risk.sensitivity(trials=2000)
    assert [c[0] for c in s["floor_changes"]] == ["B1"]               # the floor binds only for B1
    assert s["e2_if_class_X"] == "Med-High"


def test_model_check_composition_and_lag():
    r = modelcheck.run(verbose=False)
    comp = {c["id"]: c["violation"] for c in r["composition"]}
    assert comp == {"I1": False, "I2": False, "I3": True, "I4": False}      # composition failure, no adversary
    lag = {c["id"]: c["violation"] for c in r["lag"]}
    assert lag == {"B2": True, "B2m": False, "E1": True, "E1m": False}


def test_model_check_minimal_attack_sets():
    r = modelcheck.run(verbose=False)
    ladder = {l["id"]: sorted(map(tuple, l["cuts"])) for l in r["ladder"]}
    assert ladder["L0"] == sorted([("admin_force",), ("upgrade",), ("gov_collude",), ("oracle_poison",),
                                   ("issuer_forge",), ("issuer_unlisted",)])
    assert ladder["L5"] == sorted([("issuer_forge",), ("gov_collude", "suppress_contest"),
                                   ("gov_collude", "oracle_poison", "oracle_second_feed")])
    assert r["faults_singleton_at_all_levels"]


def test_cli_all_runs(tmp_path, capsys):
    assert main(["all", "--out", str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert "Attack scenarios" in out and "Mechanised consistency check" in out
    assert (tmp_path / "scenarios.md").exists() and json.loads((tmp_path / "modelcheck.json").read_text())
