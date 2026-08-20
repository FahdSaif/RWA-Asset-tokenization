"""The gate. Nothing the AI produces takes effect until it passes here.

This is the human/institutional oversight step from the paper. In the prototype it
does two things: (1) verifies the CRR signature, and (2) applies a governance
decision (approve / edit / reject) before the CRR is forwarded to the chain's
governance pallet for admission. Reject and edit both stop the raw AI output.
"""
from __future__ import annotations
from dataclasses import dataclass
from .crr import SignedCRR


@dataclass
class GovernanceDecision:
    action: str            # "approve" | "edit" | "reject"
    note: str = ""


def evaluate(signed: SignedCRR, decision: GovernanceDecision) -> tuple[bool, str]:
    """Returns (admit_to_chain, reason)."""
    if not signed.verify():
        return False, "signature verification failed — CRR refused before governance"
    if decision.action == "reject":
        return False, f"governance rejected: {decision.note}"
    if decision.action == "edit":
        # An edited rule must be re-signed by the agent before admission; the point
        # is that the *unedited* AI output does not pass through.
        return False, f"governance requested edit: {decision.note} (re-sign required)"
    if decision.action == "approve":
        return True, "approved — forwarding to governance pallet for admission"
    return False, f"unknown action: {decision.action}"
