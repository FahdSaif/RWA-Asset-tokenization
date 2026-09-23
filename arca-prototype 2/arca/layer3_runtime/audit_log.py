"""
Layer 3 — Audit Log Module (paper Sec. V-E, "Audit Log Module").

An append-only, cryptographically hash-chained ledger. Every entry embeds
the hash of the previous entry, so altering or deleting any past record
changes that entry's hash and breaks every subsequent link — the same
tamper-evidence property the paper attributes to this module ("past
compliance records cannot be altered or deleted").

This is deliberately implemented as a minimal, dependency-free primitive
(SHA-256 hash chaining) rather than wrapping a real blockchain client,
because the property under test — append-only + tamper-evident — is
exactly what a hash chain gives you, and it lets every other module in
this prototype (DID history, rule registry changes, transaction outcomes,
governance decisions) share one auditable substrate without needing a
running node. `layer3_runtime.solidity` gives the same guarantee for a
real on-chain deployment, if one is available.
"""
from __future__ import annotations

import dataclasses
import hashlib
import json
import time
from typing import Any, Dict, List, Optional

GENESIS_HASH = "0" * 64


def _canonical(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)


@dataclasses.dataclass
class LedgerEntry:
    index: int
    event_type: str
    payload: Dict[str, Any]
    timestamp: float
    prev_hash: str
    entry_hash: str = dataclasses.field(init=False)

    def __post_init__(self):
        body = _canonical(
            {
                "index": self.index,
                "event_type": self.event_type,
                "payload": self.payload,
                "timestamp": self.timestamp,
                "prev_hash": self.prev_hash,
            }
        )
        self.entry_hash = hashlib.sha256(body.encode()).hexdigest()


class HashChainLedger:
    """Generic append-only hash-chained ledger, reused across the
    prototype for the compliance Audit Log, DID document history, and
    governance decision history."""

    def __init__(self):
        self._entries: List[LedgerEntry] = []

    def append(self, event_type: str, payload: Dict[str, Any]) -> LedgerEntry:
        prev_hash = self._entries[-1].entry_hash if self._entries else GENESIS_HASH
        entry = LedgerEntry(
            index=len(self._entries),
            event_type=event_type,
            payload=payload,
            timestamp=time.time(),
            prev_hash=prev_hash,
        )
        self._entries.append(entry)
        return entry

    def verify_integrity(self) -> bool:
        """Recomputes every hash in the chain. Returns False if any entry
        has been altered, reordered, or removed since it was appended."""
        expected_prev = GENESIS_HASH
        for entry in self._entries:
            if entry.prev_hash != expected_prev:
                return False
            recomputed = LedgerEntry(
                index=entry.index,
                event_type=entry.event_type,
                payload=entry.payload,
                timestamp=entry.timestamp,
                prev_hash=entry.prev_hash,
            )
            if recomputed.entry_hash != entry.entry_hash:
                return False
            expected_prev = entry.entry_hash
        return True

    def entries(self) -> List[LedgerEntry]:
        return list(self._entries)

    def query(self, event_type: Optional[str] = None) -> List[LedgerEntry]:
        if event_type is None:
            return self.entries()
        return [e for e in self._entries if e.event_type == event_type]

    def __len__(self) -> int:
        return len(self._entries)

    def tail_hash(self) -> str:
        return self._entries[-1].entry_hash if self._entries else GENESIS_HASH
