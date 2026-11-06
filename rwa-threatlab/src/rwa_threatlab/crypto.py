"""Simulated cryptography.

HMAC-SHA256 stands in for a digital-signature scheme so the simulation is dependency-free and
deterministic. It models *who can produce a valid signature* (holders of a key), which is all the
threat model needs. It is NOT a secure signature scheme for production (verification needs the
secret). Replace with Ed25519 / FROST threshold signatures in a real system.
"""
from __future__ import annotations

import hashlib
import hmac
import json
from typing import Any


def _default(o: Any) -> Any:
    if isinstance(o, (set, frozenset)):
        return sorted(o, key=repr)
    if hasattr(o, "__dict__"):
        return o.__dict__
    return repr(o)


def canon(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=_default).encode()


def digest(obj: Any) -> str:
    return hashlib.sha256(canon(obj)).hexdigest()


class Signer:
    """Holder of a signing key. Copying a Signer models key theft."""

    def __init__(self, key_id: str, secret: bytes):
        self.key_id = key_id
        self._secret = secret

    def sign(self, msg: str) -> str:
        return hmac.new(self._secret, msg.encode(), hashlib.sha256).hexdigest()


class Pki:
    """Directory that can verify signatures by key id (simulated public-key infrastructure)."""

    def __init__(self, seed: str = "rwa-threatlab"):
        self._seed = seed
        self._secrets: dict[str, bytes] = {}

    def register(self, key_id: str) -> Signer:
        secret = hashlib.sha256(f"{self._seed}/{key_id}".encode()).digest()
        self._secrets[key_id] = secret
        return Signer(key_id, secret)

    def known(self, key_id: str) -> bool:
        return key_id in self._secrets

    def verify(self, key_id: str, msg: str, sig: str) -> bool:
        secret = self._secrets.get(key_id)
        if secret is None:
            return False
        expected = hmac.new(secret, msg.encode(), hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, sig)
