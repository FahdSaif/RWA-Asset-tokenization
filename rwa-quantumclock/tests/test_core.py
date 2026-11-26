"""Software tests. They must always pass; a failure is a bug."""
import json

import numpy as np
import pytest

from qamp import baselines, config, evaluate, explain, guard, planner, scenarios
from qamp.data import load_census, read_tokens, summary
from qamp.discovery import RulesClassifier, scan_abi, scan_source
from qamp.discovery.abi import scan_controllers
from qamp.discovery.cbom import cohen_kappa, score, to_cbom
from qamp.discovery.classify import LLMClassifier
from qamp.kb import load_kb
from qamp.kb.engine import KnowledgeBase, Rule, anchor_facts
from qamp.loss import LossParams, anchor_loss, anchor_loss_vec, effective_quarter
from qamp.model import Anchor, Calendar


@pytest.fixture(scope="module")
def dep():
    return load_census()


@pytest.fixture(scope="module")
def kb():
    return load_kb()


# --- data

def test_census_tokens_and_caps():
    rows = read_tokens()
    assert len(rows) == 25
    assert rows[0]["symbol"] == "USDY" and rows[0]["market_cap_usd"] == 2_388_027_199


def test_census_anchors(dep):
    s = summary(dep)
    assert s["tokens"] == 25
    backed = [a for a in dep.anchors if a.controller_address == "0x49754062e35f7591b93cc4f9915965be89643a65"]
    assert len(backed) == 1, "one anchor per controlling key"
    assert backed[0].n_keys == 2 and len(backed[0].tokens) == 8
    assert set(backed[0].provenance["roles"]) == {"upgrade_admin", "owner_admin"}
    assert sum(a.controller_type == "eoa" for a in dep.anchors) == 2


# --- calendar, loss

@pytest.mark.parametrize("period,phase,q,expected", [(4, 0, 0, 0), (4, 0, 1, 4), (4, 1, 1, 1), (4, 3, 0, 3), (4, 3, 4, 7), (1, 0, 2.5, 3)])
def test_next_boundary(period, phase, q, expected):
    assert Calendar(period, phase).next_boundary(q) == expected


def test_window_costs_a_period():
    a = Anchor("x", "upgrade_admin", "eoa", migration_quarters=2, calendar=Calendar(4, 0))
    assert effective_quarter(a, 2) == 4          # in time
    assert effective_quarter(a, 3) == 8          # one quarter late: waits a full period
    assert effective_quarter(a, 2, delta=1) == 8  # a delay misses the date


def test_loss_properties():
    a = Anchor("x", "upgrade_admin", "eoa", value_usd=1e9, signs_records=True)
    p = LossParams()
    # migrated in time, but records from the last 5 years can still be disputed
    assert anchor_loss(a, 10, 12.0, 5, p) == pytest.approx(p.rho_records * 1e9 * 10 / 4)
    b = Anchor("z", "upgrade_admin", "eoa", value_usd=1e9, signs_records=False)
    assert anchor_loss(b, 10, 12.0, 5, p) == 0.0
    assert anchor_loss(a, 20, 12.0, 0, p) > anchor_loss(a, 16, 12.0, 0, p) > 0
    assert anchor_loss(a, 5, 60.0, 5, p) == 0.0                                       # arrival after 2040
    T = np.array([3.0, 12.0, 70.0])
    assert np.allclose(anchor_loss_vec(a, 20, T, 5, p), [anchor_loss(a, 20, t, 5, p) for t in T])
    pq = Anchor("y", "upgrade_admin", "eoa", value_usd=1e9, algorithm="ml-dsa-65")
    assert anchor_loss(pq, None, 1.0, 5, p) == 0.0


# --- scenarios

def test_weibull_matches_survey_points():
    for p10, p15 in [(0.28, 0.51), (0.49, 0.70)]:
        k, lam = scenarios.weibull_params(p10, p15)
        assert abs(1 - np.exp(-((10 / lam) ** k)) - p10) < 1e-9
        assert abs(1 - np.exp(-((15 / lam) ** k)) - p15) < 1e-9


def test_scenarios_reproducible_and_conditional():
    a = scenarios.sample(500, 3, seed=5)
    b = scenarios.sample(500, 3, seed=5)
    assert np.array_equal(a.crqc_quarter, b.crqc_quarter) and np.array_equal(a.delta, b.delta)
    assert (a.crqc_quarter >= 0).all()
    assert set(np.unique(a.delta)) <= {-1, 0, 1}


# --- knowledge base

def test_kb_rules_have_sources(kb):
    for r in kb.rules:
        assert r.source.get("title") and r.source.get("clause") and r.source.get("url")
    assert kb.unverified() == []


def test_kb_inference(dep, kb):
    a = next(a for a in dep.anchors if a.controller_type == "eoa")
    inf = kb.infer(anchor_facts(a))
    c = inf.conclusions
    assert c["deadline_hard"] == "2035-12-31" and c["deadline_soft"] == "2030-12-31"
    assert "single_key_admin" in c["urgency"]
    assert "NIST8547-DISALLOW" in inf.fired()


def test_kb_fixpoint_and_aggregation():
    rules = [Rule("A", {"fact": "x", "eq": 1}, {"set": {"y": 2}, "retention_years": 3}, {"title": "t"}),
             Rule("B", {"fact": "y", "eq": 2}, {"retention_years": 6, "deadline_hard": "2031-01-01"}, {"title": "t"}),
             Rule("C", {"fact": "x", "eq": 1}, {"deadline_hard": "2030-01-01"}, {"title": "t"})]
    inf = KnowledgeBase(rules).infer({"x": 1})
    assert inf.conclusions["retention_years"] == 6 and inf.conclusions["deadline_hard"] == "2030-01-01"
    assert inf.fired() == ["A", "B", "C"]


# --- planner and baselines

def test_planner_optimal_on_own_objective(dep, kb):
    ctx = planner.kb_context(dep, kb)
    ss = scenarios.sample(2000, len(dep.anchors), seed=3)
    pp = planner.PlanParams()
    C, F = planner.expected_cost_matrix(dep, ctx, ss, LossParams(), pp)
    p = planner.solve(dep, C, F, pp)
    obj = lambda pl: sum(C[i, pl.starts[a.anchor_id]] for i, a in enumerate(dep.anchors))  # noqa: E731
    for name, f in baselines.LIST_BASELINES.items():
        b = f(dep, ctx=ctx, lp=LossParams(), pp=pp)
        assert obj(p) <= obj(b) + 1e-6, name


def test_capacity_respected(dep, kb):
    ctx = planner.kb_context(dep, kb)
    ss = scenarios.sample(500, len(dep.anchors), seed=4)
    pp = planner.PlanParams(capacity=1)
    p = planner.plan(dep, kb, ss, pp=pp, ctx=ctx)
    use = {}
    for a in dep.anchors:
        t = p.starts[a.anchor_id]
        for q in range(t, t + max(1, a.migration_quarters)):
            use[(a.issuer_group, q)] = use.get((a.issuer_group, q), 0) + 1
    assert max(use.values()) <= 1


def test_hard_deadline_respected(dep, kb):
    ctx = planner.kb_context(dep, kb)
    p = planner.plan(dep, kb, scenarios.sample(500, len(dep.anchors), seed=6), ctx=ctx)
    for a in dep.anchors:
        assert effective_quarter(a, p.starts[a.anchor_id]) <= ctx[a.anchor_id]["hard_q"]


# --- guard

def test_guard_detects_mixed_state():
    eff = {"a@eth": 4, "a@l2": 12}
    r = guard.check_component("a", eff, [("a@eth", "a@l2")], horizon=20)
    assert r.violation and any(x.startswith("forge@a@l2") for x in r.trace)
    assert not guard.check_component("a", {"a@eth": 8, "a@l2": 8}, [("a@eth", "a@l2")], horizon=20).violation
    assert not guard.check_component("a", eff, [("a@eth", "a@l2")], horizon=20, bridge_policy="pause_revalidate").violation


def test_guarded_plan_resolves(dep, kb):
    top = sorted(dep.anchors, key=lambda a: -a.value_usd)[:4]
    d2 = guard.expand_instances(dep, {a.anchor_id: ["ethereum", "l2"] for a in top})
    ctx = planner.kb_context(d2, kb)
    ss = scenarios.sample(500, len(d2.anchors), seed=7)
    C, F = planner.expected_cost_matrix(d2, ctx, ss, LossParams(), planner.PlanParams())
    p, rounds, res, hist = guard.guarded_plan(d2, lambda cp: planner.solve(d2, C, F, planner.PlanParams(), coupling=cp))
    assert not any(g.violation for g in res)
    assert abs(sum(a.value_usd for a in d2.anchors) - sum(a.value_usd for a in dep.anchors)) < 1


# --- discovery and explanations

SOL = """pragma solidity ^0.8.20;
// ecrecover( in a comment is not evidence
contract T is AccessControl, EIP712 {
    function permit(address o, address s, uint v, uint d, uint8 v8, bytes32 r, bytes32 ss) external {
        address signer = ecrecover(_hashTypedDataV4(h), v8, r, ss);
    }
    function _authorizeUpgrade(address) internal override onlyRole(UPGRADER_ROLE) {}
}"""


def test_source_scan_lines_and_comments():
    f = scan_source("0xabc", SOL)
    rec = [x for x in f if x.surface == "ecrecover_direct"]
    assert len(rec) == 1 and rec[0].location.endswith(":5")
    assert {x.surface for x in f} >= {"eip2612_permit", "eip712_domain", "access_control_roles", "upgradeable_proxy"}


def test_abi_discovery_on_census(dep):
    F = [f for t in dep.tokens for f in scan_abi(t.address, t.abi_functions)] + scan_controllers(dep)
    E = RulesClassifier().classify(F)
    assert sum(e.surface == "eip2612_permit" for e in E) == 15
    cb = to_cbom(E, "t")
    assert cb["specVersion"] == "1.6" and len(cb["components"]) == len(E)
    json.dumps(cb)


def test_llm_classifier_drops_hallucinated_citations(tmp_path):
    f = scan_source("0xabc", SOL)
    good = f[0].evidence_id
    fake = json.dumps([{"surface": f[0].surface, "algorithm": "secp256k1-ecdsa", "signer": "s", "anchor_role": "holder",
                        "compliance_relevant": False, "evidence": [good], "note": "ok"},
                       {"surface": "ecrecover_direct", "algorithm": "secp256k1-ecdsa", "signer": "s", "anchor_role": "holder",
                        "compliance_relevant": True, "evidence": ["src:0xabc:made-up:99"], "note": "bad"}])
    clf = LLMClassifier(transport=lambda prompt: fake, log_path=tmp_path / "log.jsonl")
    out = clf.classify(f)
    assert len(out) == 1 and clf.hallucinated == 1 and clf.dropped == 1
    assert (tmp_path / "log.jsonl").read_text().count("\n") == 1


def test_scoring_and_kappa():
    from qamp.discovery.classify import InventoryEntry
    e = [InventoryEntry("0xa", "eip2612_permit", "secp256k1-ecdsa", "", "", True, False, ["x"], "rules"),
         InventoryEntry("0xa", "erc2771_forwarder", "secp256k1-ecdsa", "", "", True, True, ["y"], "rules")]
    labels = {("0xa", "eip2612_permit"): True, ("0xa", "erc2771_forwarder"): False, ("0xa", "ecrecover_direct"): True}
    s = score(e, labels)["overall"]
    assert (s["tp"], s["fp"], s["fn"]) == (1, 1, 1) and abs(s["f1"] - 0.5) < 1e-9
    assert cohen_kappa(labels, labels) == 1.0


def test_explanations_are_cited(dep, kb):
    ctx = planner.kb_context(dep, kb)
    a = dep.anchors[0]
    r = explain.write(a, 0, ctx[a.anchor_id]["inference"], ["abi:x:eip2612_permit"])
    kept, dropped = explain.validate(r.sentences, r.allowed)
    assert dropped == 0 and kept
    kept2, dropped2 = explain.validate(["Unsupported claim.", "Bad cite [R:NOT-A-RULE]."], r.allowed)
    assert kept2 == [] and dropped2 == 2


# --- statistics

def test_sign_flip_test():
    rng = np.random.default_rng(0)
    assert evaluate.sign_flip_test(rng.normal(0, 1, 400)) > 0.01
    assert evaluate.sign_flip_test(rng.normal(1, 1, 400)) < 0.001
    assert evaluate.sign_flip_test(np.zeros(10)) == 1.0


def test_held_out_seeds_disjoint():
    assert config.HELD_OUT_SEED_BASE - config.DEV_SEED_BASE >= 1000


def test_explanation_checks_can_fail(dep, kb):
    ctx = planner.kb_context(dep, kb)
    a = next(x for x in dep.anchors if x.signs_records)
    r = explain.write(a, 4, ctx[a.anchor_id]["inference"], [])
    assert explain.scores([r]) == dict(sentences=len(r.sentences), citation_validity=1.0, faithfulness=1.0)
    plan_sentence = next(s for s in r.sentences if s.startswith("Start the migration"))
    tampered = plan_sentence.replace("2028 Q1", "2029 Q1", 1)        # a valid value used twice
    assert tampered != plan_sentence and not explain.faithful(tampered, r.facts)
    assert not explain.faithful(plan_sentence.replace("2028 Q1", "2030 Q2", 1), r.facts)   # a value not in the facts
    ret = next(s for s in r.sentences if "remain evidence" in s)
    assert not explain.faithful(ret.replace("evidence for 5", "evidence for 9"), r.facts)
    assert not explain.faithful("The key is safe until 2040 Q1 [R:NIST8547-DISALLOW].", r.facts)
    kept, dropped = explain.rephrase_with_llm(r, lambda prompt: "\n".join([plan_sentence, tampered, "No citation here."]))
    assert kept == [plan_sentence] and dropped == 2


def test_counterfactual_consistency(dep, kb):
    ctx = planner.kb_context(dep, kb)
    starts = {a.anchor_id: 0 for a in dep.anchors}
    res = explain.counterfactual_consistency(dep, ctx, starts, kb)
    assert res["cases"] > len(dep.anchors) and res["consistency"] == 1.0
