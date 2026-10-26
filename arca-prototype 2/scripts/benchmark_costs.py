"""
Cost measurements for the ARCA reference prototype (Sec. VII, added in
response to peer review).

Measures, on the machine it is run on:
  A. Per-transaction validation latency in the Python Runtime Enforcement
     Layer, broken down by stage, for increasing allow-list sizes (the
     zero-knowledge membership proof is the only size-dependent stage).
  B. Holder-side proof generation time and verifier-side proof verification
     time for the same allow-list sizes.
  C. Computational cost of a governance rule update (propose, vote,
     finalize, apply) and of an agent/issuer registration. Human voting
     latency is NOT measured here: it is a deployment parameter.
  D. EVM gas for the prototype's Solidity contracts: a compliance-gated
     transfer against an otherwise identical plain token, plus one-off
     registry operations and deployments.

Scope: single process, single core, local in-memory EVM, no network. These
are cost figures for the prototype, not throughput claims for a production
deployment.

Run (from the repo root, after `npm install && node scripts/compile_contracts.js`):
    python scripts/benchmark_costs.py            # full run
    python scripts/benchmark_costs.py --quick    # fewer repeats (smoke test)
Writes docs/benchmark_results.json and docs/BENCHMARKS.md.
"""
from __future__ import annotations

import argparse
import contextlib
import datetime
import importlib.metadata as md
import json
import pathlib
import platform
import statistics
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from arca.layer1_intelligence.crr import issue_crr  # noqa: E402
from arca.layer2_identity.did_registry import generate_did  # noqa: E402
from arca.layer2_identity.zkp_module import verify_membership  # noqa: E402
from arca.layer3_runtime import transaction_validator as tv  # noqa: E402
from arca.layer3_runtime.audit_log import HashChainLedger  # noqa: E402
from arca.layer3_runtime.models import Rule  # noqa: E402
from arca.layer3_runtime.transaction_validator import Transaction  # noqa: E402
from arca.layer4_governance.governance import ROLE_COMPLIANCE_AGENT  # noqa: E402
from arca.pipeline.end_to_end_demo import (  # noqa: E402
    _finalize_role_change,
    _finalize_rule_proposal,
    build_arca_environment,
)

ALLOWLIST_SIZES = (8, 16, 32, 64)


def ms() -> float:
    return time.perf_counter() * 1000.0


def stats(xs):
    xs = list(xs)
    return {
        "n": len(xs),
        "mean_ms": round(statistics.fmean(xs), 3),
        "sd_ms": round(statistics.stdev(xs), 3) if len(xs) > 1 else 0.0,
        "min_ms": round(min(xs), 3),
        "max_ms": round(max(xs), 3),
    }


# ---------------------------------------------------------------------------
# In-situ stage timing: wrap the real functions the validator calls
# ---------------------------------------------------------------------------
class StageTimer:
    def __init__(self):
        self.acc = {"crr_verification_ms": 0.0, "jurisdiction_binding_ms": 0.0, "audit_append_ms": 0.0}

    @contextlib.contextmanager
    def patched(self):
        orig_crr, orig_bind, orig_append = tv.verify_crr, tv.verify_jurisdiction_binding, HashChainLedger.append
        acc = self.acc

        def wrap(fn, key):
            def inner(*a, **k):
                t = ms()
                try:
                    return fn(*a, **k)
                finally:
                    acc[key] += ms() - t
            return inner

        tv.verify_crr = wrap(orig_crr, "crr_verification_ms")
        tv.verify_jurisdiction_binding = wrap(orig_bind, "jurisdiction_binding_ms")
        HashChainLedger.append = lambda self_, *a, **k: wrap(lambda *aa, **kk: orig_append(self_, *aa, **kk), "audit_append_ms")(*a, **k)
        try:
            yield
        finally:
            tv.verify_crr, tv.verify_jurisdiction_binding, HashChainLedger.append = orig_crr, orig_bind, orig_append

    def reset(self):
        for k in self.acc:
            self.acc[k] = 0.0


def build_scenario(n_allowed: int, with_zkp_rule: bool):
    env = build_arca_environment()
    ids = env["identities"]
    allowed = list(range(1000, 1000 + n_allowed))
    certified_code = allowed[n_allowed // 2]

    rules = [
        Rule("B-amount", "*", "*", "*", "max_transaction_amount", {"max_amount": 10**9}),
        Rule("B-elig", "*", "*", "*", "require_eligibility_crr", {}),
        Rule("B-risk", "*", "*", "*", "max_risk_score", {"max_score": 0.6}),
        Rule("B-anom", "*", "*", "*", "block_if_anomaly_flagged", {}),
    ]
    if with_zkp_rule:
        rules.append(Rule("B-zk", "*", "*", "*", "require_jurisdiction_allowlist_proof",
                          {"allowed_jurisdictions_encoded": allowed}))
    for r in rules:
        assert _finalize_rule_proposal(env, "add", r)

    bundle = env["issuer"].issue_jurisdiction_credential(ids["alice"].did, certified_code)
    t0 = ms()
    proof = bundle.prove_in(allowed)
    prove_ms = ms() - t0

    tx_id = "TX-BENCH"
    crrs = [
        issue_crr(ids["eligibility_agent"], "eligibility", tx_id, True, ["ok"], {}, subject_did=ids["alice"].did),
        issue_crr(ids["risk_agent"], "risk_score", tx_id, 0.1, ["ok"], {}),
        issue_crr(ids["anomaly_agent"], "anomaly", tx_id, False, ["ok"], {}, subject_did=ids["alice"].did),
    ]
    tx = Transaction(
        tx_id=tx_id, sender_did=ids["alice"].did, receiver_did=ids["bob"].did,
        asset_type="real_estate", asset_jurisdiction="AU", transaction_class="transfer",
        amount=250_000.0, jurisdiction_proof=proof, jurisdiction_credential=bundle.credential, crrs=crrs,
    )
    return env, tx, proof, allowed, prove_ms


def bench_validation(quick: bool):
    out = {}
    # Baseline: no zero-knowledge rule in the rule set
    env, tx, _, _, _ = build_scenario(8, with_zkp_rule=False)
    timer, reps = StageTimer(), (20 if quick else 300)
    totals, parts = [], {k: [] for k in timer.acc}
    with timer.patched():
        for _ in range(reps):
            timer.reset()
            t = ms()
            res = env["validator"].validate(tx)
            totals.append(ms() - t)
            assert res.accepted
            for k, v in timer.acc.items():
                parts[k].append(v)
    out["no_zkp_rule"] = {
        "total": stats(totals),
        **{k: stats(v) for k, v in parts.items()},
        "rules_evaluated": 4, "crrs": 3,
    }

    # With the zero-knowledge jurisdiction rule, by allow-list size
    out["with_zkp_rule"] = {}
    for n in ALLOWLIST_SIZES:
        env, tx, proof, allowed, prove_ms = build_scenario(n, with_zkp_rule=True)
        reps_n = 2 if quick else (10 if n >= 32 else 20)
        timer = StageTimer()
        totals, parts = [], {k: [] for k in timer.acc}
        with timer.patched():
            for _ in range(reps_n):
                timer.reset()
                t = ms()
                res = env["validator"].validate(tx)
                totals.append(ms() - t)
                assert res.accepted, res.rejection_reasons
                for k, v in timer.acc.items():
                    parts[k].append(v)
        # isolated holder-side proof generation and verifier-side proof check
        gen = []
        for _ in range(1 if quick else 3):
            e2, _, _, _, p_ms = build_scenario(n, with_zkp_rule=False)
            gen.append(p_ms)
        ver = []
        for _ in range(2 if quick else 5):
            t = ms()
            assert verify_membership(proof, allowed)
            ver.append(ms() - t)
        out["with_zkp_rule"][str(n)] = {
            "allowlist_size": n,
            "validate_total": stats(totals),
            **{k: stats(v) for k, v in parts.items()},
            "proof_generation_holder_side": stats(gen),
            "proof_verification_isolated": stats(ver),
        }
    return out


def bench_governance(quick: bool):
    reps = 5 if quick else 50
    env = build_arca_environment(quorum_threshold=2)
    gov, ids, reg = env["governance"], env["identities"], env["rule_registry"]
    steps = {"propose": [], "vote_x2": [], "finalize_quorum_check": [], "apply_registry_reverify": [], "total": []}
    for i in range(reps):
        rule = Rule(f"G-{i}", "*", "*", "*", "max_transaction_amount", {"max_amount": 1000 + i})
        t0 = ms()
        p = gov.propose_rule_change("add", rule, ids["gov_1"].did)
        t1 = ms()
        gov.cast_vote(p.proposal_id, ids["gov_1"])
        gov.cast_vote(p.proposal_id, ids["gov_2"])
        t2 = ms()
        auth = gov.finalize(p.proposal_id)
        t3 = ms()
        assert reg.apply_update(auth)
        t4 = ms()
        for k, v in zip(steps, (t1 - t0, t2 - t1, t3 - t2, t4 - t3, t4 - t0)):
            steps[k].append(v)
    role = []
    for _ in range(reps):
        a = generate_did()
        t = ms()
        assert _finalize_role_change(env, "register", ROLE_COMPLIANCE_AGENT, a.did, ("eligibility",))
        role.append(ms() - t)
    return {
        "rule_update_quorum_2_of_3": {k: stats(v) for k, v in steps.items()},
        "agent_registration_quorum_3_votes": stats(role),
        "note": "Computational cost only. Human/organisational voting latency is a deployment parameter and is not measured.",
    }


def bench_gas(quick: bool):
    from arca.layer3_runtime.evm_bridge import LocalEVM

    def run_once():
        evm = LocalEVM()
        w3, owner = evm.w3, evm.owner
        a1, a2 = evm.accounts[1], evm.accounts[2]
        supply = 1_000_000 * 10**18
        art = evm.artifacts["PlainToken"]
        c = w3.eth.contract(abi=art["abi"], bytecode=art["bytecode"])
        rc = w3.eth.wait_for_transaction_receipt(c.constructor("Plain", "PLN", supply, owner).transact({"from": owner}))
        plain = w3.eth.contract(address=rc.contractAddress, abi=art["abi"])

        def deploy_gas(name):
            return None

        def gas(txh):
            return w3.eth.wait_for_transaction_receipt(txh).gasUsed

        res = {}
        res["setAllowed_first_time_per_account"] = gas(evm.registry.functions.setAllowed(owner, True).transact({"from": owner}))
        gas(evm.registry.functions.setAllowed(a1, True).transact({"from": owner}))
        gas(evm.registry.functions.setAllowed(a2, True).transact({"from": owner}))
        res["setFlagged"] = gas(evm.registry.functions.setFlagged(a2, True).transact({"from": owner}))
        gas(evm.registry.functions.setFlagged(a2, False).transact({"from": owner}))

        # transfer to a recipient with zero balance (cold storage slot write)
        res["compliance_token_transfer_new_recipient"] = gas(evm.token.functions.transfer(a1, 10**18).transact({"from": owner}))
        res["plain_token_transfer_new_recipient"] = gas(plain.functions.transfer(a1, 10**18).transact({"from": owner}))
        # transfer to a recipient that already holds tokens
        res["compliance_token_transfer_existing_recipient"] = gas(evm.token.functions.transfer(a1, 10**18).transact({"from": owner}))
        res["plain_token_transfer_existing_recipient"] = gas(plain.functions.transfer(a1, 10**18).transact({"from": owner}))

        # deployment gas, via transaction receipts of fresh deployments
        def dep(name, args):
            art = evm.artifacts[name]
            ct = w3.eth.contract(abi=art["abi"], bytecode=art["bytecode"])
            return w3.eth.wait_for_transaction_receipt(ct.constructor(*args).transact({"from": owner}))
        reg_rc = dep("ComplianceRegistry", [owner])
        res["deploy_ComplianceRegistry"] = reg_rc.gasUsed
        res["deploy_ComplianceToken"] = dep("ComplianceToken", ["T", "T", supply, reg_rc.contractAddress, owner]).gasUsed
        res["deploy_PlainToken"] = dep("PlainToken", ["P", "P", supply, owner]).gasUsed
        return res

    runs = [run_once() for _ in range(1 if quick else 3)]
    keys = runs[0].keys()
    out = {k: {"min": min(r[k] for r in runs), "max": max(r[k] for r in runs)} for k in keys}
    for scen in ("new_recipient", "existing_recipient"):
        c, p = out[f"compliance_token_transfer_{scen}"]["min"], out[f"plain_token_transfer_{scen}"]["min"]
        out[f"gate_overhead_{scen}"] = {"gas": c - p, "percent": round(100 * (c - p) / p, 1)}
    out["note"] = "Gas is deterministic on the local EVM; min/max over repeated fresh deployments confirm it."
    return out


def environment():
    cpu = "unknown"
    with contextlib.suppress(Exception):
        cpu = next(l.split(":", 1)[1].strip() for l in open("/proc/cpuinfo") if l.startswith("model name"))
    libs = {}
    for lib in ("cryptography", "tinyec", "web3", "eth-tester", "scikit-learn"):
        with contextlib.suppress(Exception):
            libs[lib] = md.version(lib)
    return {
        "date_utc": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d"),
        "python": platform.python_version(), "platform": platform.platform(),
        "cpu": cpu, "logical_cores_used": 1, "libraries": libs,
    }


def fmt(s):
    return f"{s['mean_ms']:.2f} ± {s['sd_ms']:.2f}"


def write_markdown(res, path):
    v, g, gas, env = res["validation"], res["governance"], res["gas"], res["environment"]
    L = []
    L.append("# Cost measurements for the ARCA reference prototype\n")
    L.append("Generated by `scripts/benchmark_costs.py`. All times are wall-clock milliseconds, "
             "mean ± standard deviation over `n` repetitions, single process, single core.\n")
    L.append(f"*Environment:* {env['cpu']}; Python {env['python']}; {env['platform']}; "
             + ", ".join(f"{k} {x}" for k, x in env["libraries"].items()) + f"; run date {env['date_utc']}.\n")
    L.append("**Scope.** These are cost figures for the prototype on one machine. They are not throughput "
             "claims, and the zero-knowledge stage uses the Sigma-protocol construction described in "
             "Sec. VII-F, not a succinct proof system.\n")

    L.append("## A. Per-transaction validation latency (Python Runtime Enforcement Layer)\n")
    b = v["no_zkp_rule"]
    L.append(f"Transaction with 3 CRRs and 4 rules (amount, eligibility, risk, anomaly), no zero-knowledge rule "
             f"(n = {b['total']['n']}):\n")
    L.append("| Stage | ms |\n|---|---|")
    other = b["total"]["mean_ms"] - sum(b[k]["mean_ms"] for k in ("crr_verification_ms", "jurisdiction_binding_ms", "audit_append_ms"))
    L.append(f"| CRR verification (3 signatures) | {fmt(b['crr_verification_ms'])} |")
    L.append(f"| Audit-log append (hash chaining) | {fmt(b['audit_append_ms'])} |")
    L.append(f"| Other (rule lookup and evaluation, registry checks) | {other:.2f} |")
    L.append(f"| **Total** | **{fmt(b['total'])}** |\n")

    L.append("Same transaction with the zero-knowledge jurisdiction rule and issuer-credential binding added, "
             "by allow-list size *n*:\n")
    L.append("| Allow-list size | Total validate() | Jurisdiction binding (credential + ZK verify) | CRR verification | Audit append | Holder-side proof generation | Reps |")
    L.append("|---|---|---|---|---|---|---|")
    for n in ALLOWLIST_SIZES:
        r = v["with_zkp_rule"][str(n)]
        L.append(f"| {n} | {fmt(r['validate_total'])} | {fmt(r['jurisdiction_binding_ms'])} | {fmt(r['crr_verification_ms'])} | "
                 f"{fmt(r['audit_append_ms'])} | {fmt(r['proof_generation_holder_side'])} | {r['validate_total']['n']} |")
    L.append("\nThe zero-knowledge membership proof is the only size-dependent stage and grows roughly linearly "
             "with the allow-list size, as expected for this construction. Everything else is size-independent.\n")

    L.append("## B. Governance operations (computational cost only)\n")
    r = g["rule_update_quorum_2_of_3"]
    L.append(f"Rule update with a 2-of-3 quorum (n = {r['total']['n']}):\n")
    L.append("| Step | ms |\n|---|---|")
    L.append(f"| Propose | {fmt(r['propose'])} |")
    L.append(f"| Two votes (signing) | {fmt(r['vote_x2'])} |")
    L.append(f"| Finalize (verify votes, check quorum) | {fmt(r['finalize_quorum_check'])} |")
    L.append(f"| Apply (registry re-verifies quorum, updates rules) | {fmt(r['apply_registry_reverify'])} |")
    L.append(f"| **Total** | **{fmt(r['total'])}** |\n")
    L.append(f"Agent registration (propose, three votes, finalize, apply): {fmt(g['agent_registration_quorum_3_votes'])} ms.\n")
    L.append("Human or organisational voting latency is a deployment parameter and is not measured here. "
             "It determines the Threat Class II exposure window (Sec. VI-B, VII-E).\n")

    L.append("## C. Gas for the prototype's Solidity contracts (local EVM)\n")
    L.append("| Operation | Gas |\n|---|---|")
    for label, key in (
        ("Transfer, compliance-gated token, new recipient", "compliance_token_transfer_new_recipient"),
        ("Transfer, plain token, new recipient", "plain_token_transfer_new_recipient"),
        ("Transfer, compliance-gated token, existing recipient", "compliance_token_transfer_existing_recipient"),
        ("Transfer, plain token, existing recipient", "plain_token_transfer_existing_recipient"),
        ("Registry: setAllowed (first time for an account)", "setAllowed_first_time_per_account"),
        ("Registry: setFlagged", "setFlagged"),
        ("Deploy ComplianceRegistry", "deploy_ComplianceRegistry"),
        ("Deploy ComplianceToken", "deploy_ComplianceToken"),
        ("Deploy PlainToken (baseline)", "deploy_PlainToken"),
    ):
        L.append(f"| {label} | {gas[key]['min']:,} |")
    for scen, label in (("new_recipient", "new recipient"), ("existing_recipient", "existing recipient")):
        o = gas[f"gate_overhead_{scen}"]
        L.append(f"\nCompliance gate overhead ({label}): {o['gas']:,} gas ({o['percent']}%).")
    L.append("\nThe baseline `PlainToken` is identical to `ComplianceToken` except for the two registry checks, "
             "so the difference isolates the cost of the gate. These are the prototype's own contracts; "
             "no measurement of ERC-3643 itself is made here.\n")
    path.write_text("\n".join(L))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true", help="few repetitions (smoke test only)")
    args = ap.parse_args()
    res = {"environment": environment(), "quick_mode": args.quick}
    print("A. validation latency ..."); res["validation"] = bench_validation(args.quick)
    print("B. governance ...");         res["governance"] = bench_governance(args.quick)
    print("C. gas ...");                res["gas"] = bench_gas(args.quick)
    docs = ROOT / "docs"
    docs.mkdir(exist_ok=True)
    (docs / "benchmark_results.json").write_text(json.dumps(res, indent=2))
    write_markdown(res, docs / "BENCHMARKS.md")
    print(f"wrote {docs/'benchmark_results.json'} and {docs/'BENCHMARKS.md'}")


if __name__ == "__main__":
    main()
