"""ARCA Layer 1 orchestration — the grown-up version of the email-agent notebook.

Flow:   classify/score  ->  eligibility agent  ->  CRR (signed)  ->  governance gate
The gate is where a probabilistic recommendation is stopped or promoted. Only an
'approve' path yields something that will be forwarded to the chain.

Run the demo:  python compliance-ai/src/arca_ai/graph.py --demo
"""
from __future__ import annotations
import argparse
import sys

from .config import AGENT_KEY_PATH, GROQ_API_KEY, MODEL
from .agents.risk_scoring import score_transaction
from .agents.eligibility import evaluate_eligibility
from .governance_gate import evaluate, GovernanceDecision
from .crr import SignedCRR


def _maybe_llm():
    if not GROQ_API_KEY:
        return None
    try:
        from langchain_groq import ChatGroq
        return ChatGroq(model=MODEL, api_key=GROQ_API_KEY, temperature=0)
    except Exception:
        return None


def run_once(tx: dict, attested_facts: dict, decision: GovernanceDecision):
    risk = score_transaction(tx)
    llm = _maybe_llm()
    crr = evaluate_eligibility(tx, attested_facts, llm=llm)
    signed: SignedCRR = crr.sign(AGENT_KEY_PATH)

    admit, reason = evaluate(signed, decision)
    return {
        "risk": risk,
        "crr_id": signed.crr_id,
        "determination": crr.determination,
        "signature_valid": signed.verify(),
        "admitted_to_chain": admit,
        "reason": reason,
        "trace": crr.reasoning_trace,
    }


def _demo():
    tx = {"asset_id": 42, "jurisdiction": 36, "amount": 1_500_000, "cross_border": True, "counterparty_new": False}
    facts = {"meets_accreditation_threshold": True, "not_on_sanctions_list": True}

    print("== approve path ==")
    for k, v in run_once(tx, facts, GovernanceDecision("approve")).items():
        print(f"  {k}: {v}")

    print("\n== reject path (raw AI output does NOT reach the chain) ==")
    for k, v in run_once(tx, facts, GovernanceDecision("reject", "manual hold")).items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--demo", action="store_true")
    args = ap.parse_args()
    if args.demo:
        _demo()
    else:
        print("nothing to do; pass --demo", file=sys.stderr)
