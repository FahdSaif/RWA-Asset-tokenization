"""Compliance Recommendation Record: the formal interface between the AI layer
and the governance gate (paper §V-C).

A CRR carries the determination, a reasoning trace, a cryptographic commitment to
the inputs, and the generating agent's signature. The governance pallet refuses
anything whose signature doesn't verify against an authorized agent key — so this
signing step is what stops a raw model output from ever becoming an enforceable
rule.
"""
from __future__ import annotations
import hashlib
import json
import os
import time
from dataclasses import dataclass, asdict, field
from typing import Any

from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey, Ed25519PublicKey,
)
from cryptography.hazmat.primitives import serialization


def _load_or_create_key(path: str) -> Ed25519PrivateKey:
    if os.path.exists(path):
        with open(path, "rb") as f:
            return serialization.load_pem_private_key(f.read(), password=None)
    key = Ed25519PrivateKey.generate()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        ))
    return key


@dataclass
class CRR:
    determination: str                 # e.g. "eligible" / "ineligible"
    outcome: bool
    reasoning_trace: list[str]
    inputs: dict[str, Any]
    agent_id: str
    ts: float = field(default_factory=time.time)

    def input_commitment(self) -> str:
        blob = json.dumps(self.inputs, sort_keys=True).encode()
        return hashlib.sha256(blob).hexdigest()

    def crr_id(self) -> str:
        core = {
            "determination": self.determination,
            "outcome": self.outcome,
            "commitment": self.input_commitment(),
            "agent_id": self.agent_id,
            "ts": self.ts,
        }
        return hashlib.sha256(json.dumps(core, sort_keys=True).encode()).hexdigest()

    def sign(self, key_path: str) -> "SignedCRR":
        key = _load_or_create_key(key_path)
        cid = self.crr_id()
        sig = key.sign(bytes.fromhex(cid))
        pub = key.public_key().public_bytes(
            serialization.Encoding.Raw, serialization.PublicFormat.Raw
        )
        return SignedCRR(crr=self, crr_id=cid, signature=sig.hex(), agent_pubkey=pub.hex())


@dataclass
class SignedCRR:
    crr: CRR
    crr_id: str
    signature: str
    agent_pubkey: str

    def verify(self) -> bool:
        """The check the governance gate performs on-chain (mirrored here)."""
        try:
            pub = Ed25519PublicKey.from_public_bytes(bytes.fromhex(self.agent_pubkey))
            pub.verify(bytes.fromhex(self.signature), bytes.fromhex(self.crr_id))
            return self.crr_id == self.crr.crr_id()
        except Exception:
            return False

    def to_json(self) -> str:
        d = asdict(self)
        return json.dumps(d, indent=2)
