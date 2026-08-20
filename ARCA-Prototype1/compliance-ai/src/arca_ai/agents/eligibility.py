"""Investor Eligibility Evaluation Agent (paper §V-C).

Given a proposed transaction and the attested credential facts (which arrive as
ZK-verified booleans, NOT raw personal data), decide eligibility and emit a
reasoning trace. The LLM is used for the interpretation/explanation; the decision
it returns is structured so the runtime can act on it deterministically.
"""
from __future__ import annotations
from ..crr import CRR


def evaluate_eligibility(tx: dict, attested_facts: dict, llm=None) -> CRR:
    trace = []
    # Deterministic core: the actual gate is a boolean over attested facts.
    accredited = bool(attested_facts.get("meets_accreditation_threshold", False))
    not_sanctioned = bool(attested_facts.get("not_on_sanctions_list", False))
    outcome = accredited and not_sanctioned

    trace.append(f"asset={tx.get('asset_id')} jurisdiction={tx.get('jurisdiction')}")
    trace.append(f"accreditation_predicate={accredited}")
    trace.append(f"sanctions_predicate={not_sanctioned}")

    # Optional: ask the LLM for a human-readable rationale (explainability), but the
    # decision above is what the runtime enforces — the model does not get a vote.
    if llm is not None:
        try:
            rationale = llm.invoke(
                "Explain, in two sentences, an eligibility decision given: "
                f"accredited={accredited}, not_sanctioned={not_sanctioned}."
            ).content
            trace.append(f"rationale: {rationale.strip()}")
        except Exception as e:
            trace.append(f"rationale unavailable: {e}")

    return CRR(
        determination="eligible" if outcome else "ineligible",
        outcome=outcome,
        reasoning_trace=trace,
        inputs={"tx": tx, "attested_facts": attested_facts},
        agent_id="eligibility-agent-v0",
    )
