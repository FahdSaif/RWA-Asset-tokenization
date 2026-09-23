"""
Compliance Recommendation Record (paper Sec. V-C, "Compliance
Recommendation Record" / Sec. III's stated contribution: "a
governance-validated Compliance Recommendation Record (CRR) interface
that converts probabilistic AI recommendations into deterministically
enforced rules").

Every AI agent in Layer 1 emits its output as a CRR: a signed, structured
record containing the determination, a human-readable reasoning trace,
and a commitment to the inputs used. This is the formal interface object
that crosses from the probabilistic Compliance Intelligence Layer into
the deterministic Runtime Enforcement Layer.
"""
from __future__ import annotations

import dataclasses
import hashlib
import json
import time
import uuid
from typing import Any, Dict, List, Optional

from arca.layer2_identity.did_registry import DIDKeyPair, did_to_verify_key
from cryptography.exceptions import InvalidSignature


def _canonical(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str).encode()


def commit_to_inputs(inputs: Dict[str, Any]) -> str:
    """Cryptographic commitment to the input data used for a determination,
    so a CRR can later be audited against the actual inputs without
    having to publish those inputs on-chain."""
    return hashlib.sha256(_canonical(inputs)).hexdigest()


@dataclasses.dataclass
class ComplianceRecommendationRecord:
    record_id: str
    agent_did: str                 # generating agent's identity
    determination_type: str        # e.g. "eligibility", "risk_score", "rule_update", "anomaly"
    context_id: str                # binds this determination to a tx_id or party DID, preventing replay
    outcome: Any                    # bool / float / structured value
    reasoning_trace: List[str]      # human-interpretable steps (XAI requirement, Sec. IV-C)
    input_commitment: str           # commit_to_inputs(...) of the evaluated inputs
    timestamp: float
    signature: bytes = dataclasses.field(default=b"", repr=False)

    def unsigned_payload(self) -> Dict[str, Any]:
        return {
            "record_id": self.record_id,
            "agent_did": self.agent_did,
            "determination_type": self.determination_type,
            "context_id": self.context_id,
            "outcome": self.outcome,
            "reasoning_trace": self.reasoning_trace,
            "input_commitment": self.input_commitment,
            "timestamp": self.timestamp,
        }


def issue_crr(
    agent_keypair: DIDKeyPair,
    determination_type: str,
    context_id: str,
    outcome: Any,
    reasoning_trace: List[str],
    inputs: Dict[str, Any],
) -> ComplianceRecommendationRecord:
    crr = ComplianceRecommendationRecord(
        record_id=str(uuid.uuid4()),
        agent_did=agent_keypair.did,
        determination_type=determination_type,
        context_id=context_id,
        outcome=outcome,
        reasoning_trace=reasoning_trace,
        input_commitment=commit_to_inputs(inputs),
        timestamp=time.time(),
    )
    crr.signature = agent_keypair.sign(_canonical(crr.unsigned_payload()))
    return crr


def verify_crr(crr: ComplianceRecommendationRecord) -> bool:
    """Verifies the generating agent's signature over the CRR payload.
    Used by the Transaction Validation Module before it will accept a
    CRR as input to an enforcement decision (Sec. V-E)."""
    try:
        verify_key = did_to_verify_key(crr.agent_did)
        verify_key.verify(crr.signature, _canonical(crr.unsigned_payload()))
        return True
    except (InvalidSignature, ValueError):
        return False
