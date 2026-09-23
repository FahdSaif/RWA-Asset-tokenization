"""
Layer 2 — Decentralized Identity Registry (paper Sec. IV-D / V-D "Layer 2").

Implements the *did:key* method (a real W3C-family DID method — no registry
server required, the DID is deterministically derived from the public key
itself) using Ed25519 keys. This gives every participant a stable,
cryptographically verifiable identifier that carries no personal data,
matching the paper's claim that "DID documents ... contain no personal
information; they provide only the cryptographic material required to
verify credential presentations."

The on-chain registry itself is modelled as an append-only, hash-linked
structure (see layer3_runtime.audit_log.HashChainLedger for the same
primitive reused for the audit trail) so that DID document updates are
tamper-evident, as required by the paper's "tamper-evident identity
history for each registered participant."

References:
  W3C DID Core: https://www.w3.org/TR/did-core/
  did:key method spec: https://w3c-ccg.github.io/did-key-spec/
"""
from __future__ import annotations

import base64
import dataclasses
import hashlib
import time
from typing import Dict, List, Optional

from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)
from cryptography.hazmat.primitives import serialization

# multicodec prefix for Ed25519 public keys (0xed01), used by did:key
_MULTICODEC_ED25519_PUB = bytes([0xED, 0x01])


def _base58btc_encode(data: bytes) -> str:
    """Minimal base58btc encoder (Bitcoin alphabet), used by did:key's
    multibase 'z' prefix. No external dependency required."""
    alphabet = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
    n = int.from_bytes(data, "big")
    if n == 0:
        encoded = alphabet[0]
    else:
        encoded = ""
        while n > 0:
            n, rem = divmod(n, 58)
            encoded = alphabet[rem] + encoded
    n_pad = len(data) - len(data.lstrip(b"\x00"))
    return alphabet[0] * n_pad + encoded


@dataclasses.dataclass
class DIDKeyPair:
    did: str
    public_key: Ed25519PublicKey
    private_key: Ed25519PrivateKey

    def sign(self, message: bytes) -> bytes:
        return self.private_key.sign(message)

    def public_key_multibase(self) -> str:
        raw = self.public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        return "z" + _base58btc_encode(_MULTICODEC_ED25519_PUB + raw)


def generate_did() -> DIDKeyPair:
    """Generate a fresh Ed25519 keypair and derive its did:key identifier."""
    sk = Ed25519PrivateKey.generate()
    pk = sk.public_key()
    raw = pk.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    method_id = "z" + _base58btc_encode(_MULTICODEC_ED25519_PUB + raw)
    did = f"did:key:{method_id}"
    return DIDKeyPair(did=did, public_key=pk, private_key=sk)


def did_to_verify_key(did: str) -> Ed25519PublicKey:
    """Recover the Ed25519 public key encoded in a did:key identifier."""
    if not did.startswith("did:key:z"):
        raise ValueError(f"Not a supported did:key identifier: {did}")
    method_id = did.split(":", 2)[2]
    # decode base58btc (strip leading 'z' multibase prefix)
    payload = _base58btc_decode(method_id[1:])
    if payload[:2] != _MULTICODEC_ED25519_PUB:
        raise ValueError("Unsupported multicodec prefix for did:key")
    raw_pub = payload[2:]
    return Ed25519PublicKey.from_public_bytes(raw_pub)


def _base58btc_decode(s: str) -> bytes:
    alphabet = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
    n = 0
    for ch in s:
        n = n * 58 + alphabet.index(ch)
    num_leading_zeros = len(s) - len(s.lstrip(alphabet[0]))
    body = n.to_bytes((n.bit_length() + 7) // 8, "big") if n else b""
    return b"\x00" * num_leading_zeros + body


@dataclasses.dataclass
class DIDDocumentVersion:
    version: int
    did: str
    public_key_multibase: str
    timestamp: float
    prev_hash: str
    entry_hash: str = dataclasses.field(init=False)

    def __post_init__(self):
        payload = f"{self.version}|{self.did}|{self.public_key_multibase}|{self.timestamp}|{self.prev_hash}"
        self.entry_hash = hashlib.sha256(payload.encode()).hexdigest()


class DIDRegistry:
    """
    On-chain DID registry, modelled as an append-only hash-linked log of
    DID *document versions*. No personal data is ever stored — only the
    DID string and its currently-bound public key material, matching the
    paper's Sec. "Verification and Identity Layer" description.
    """

    def __init__(self):
        self._history: Dict[str, List[DIDDocumentVersion]] = {}

    def register(self, keypair: DIDKeyPair) -> DIDDocumentVersion:
        prev_hash = "0" * 64
        version = DIDDocumentVersion(
            version=1,
            did=keypair.did,
            public_key_multibase=keypair.public_key_multibase(),
            timestamp=time.time(),
            prev_hash=prev_hash,
        )
        self._history[keypair.did] = [version]
        return version

    def rotate_key(self, did: str, new_keypair: DIDKeyPair) -> DIDDocumentVersion:
        """Key rotation, cryptographically linked to the prior version so the
        full identity history remains tamper-evident (append-only)."""
        if did not in self._history:
            raise KeyError(f"Unknown DID: {did}")
        history = self._history[did]
        prev = history[-1]
        version = DIDDocumentVersion(
            version=prev.version + 1,
            did=did,
            public_key_multibase=new_keypair.public_key_multibase(),
            timestamp=time.time(),
            prev_hash=prev.entry_hash,
        )
        history.append(version)
        return version

    def resolve(self, did: str) -> Optional[DIDDocumentVersion]:
        history = self._history.get(did)
        return history[-1] if history else None

    def verify_history_integrity(self, did: str) -> bool:
        """Recomputes the hash chain for a DID's document history and checks
        it has not been tampered with — the same tamper-evidence guarantee
        the paper requires of the Audit Log Module (Layer 3), applied here
        to identity history (Layer 2)."""
        history = self._history.get(did, [])
        expected_prev = "0" * 64
        for entry in history:
            if entry.prev_hash != expected_prev:
                return False
            payload = f"{entry.version}|{entry.did}|{entry.public_key_multibase}|{entry.timestamp}|{entry.prev_hash}"
            if hashlib.sha256(payload.encode()).hexdigest() != entry.entry_hash:
                return False
            expected_prev = entry.entry_hash
        return True
