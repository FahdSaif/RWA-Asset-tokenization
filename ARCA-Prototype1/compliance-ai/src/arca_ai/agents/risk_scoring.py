"""Transaction Risk Scoring Agent (paper §V-C).

Assigns a calibrated risk score and routes: standard / elevated / refer. A real
build uses SHAP over a trained model; here it's a transparent linear rule so the
routing is inspectable. Routing feeds whether extra verification is demanded.
"""
from __future__ import annotations


def score_transaction(tx: dict) -> dict:
    score = 0.0
    reasons = []
    scale = float(tx.get("amount", 0))
    if scale > 1_000_000:
        score += 0.4; reasons.append("large notional")
    if tx.get("cross_border"):
        score += 0.3; reasons.append("cross-border")
    if tx.get("counterparty_new"):
        score += 0.3; reasons.append("new counterparty")

    if score >= 0.7:
        route = "refer"
    elif score >= 0.4:
        route = "elevated"
    else:
        route = "standard"
    return {"score": round(score, 3), "route": route, "reasons": reasons}
