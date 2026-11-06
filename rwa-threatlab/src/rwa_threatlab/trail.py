"""Compliance Trail: append-only, hash-chained record of every validation decision."""
from __future__ import annotations

from dataclasses import dataclass

from .crypto import digest

GENESIS = "0" * 64


@dataclass(frozen=True)
class TrailEntry:
    index: int
    tick: int
    tx_ref: str
    accepted: bool
    rule_version: int
    proof_ref: str
    detail: str
    prev: str
    hash: str


class Trail:
    def __init__(self) -> None:
        self._entries: list[TrailEntry] = []

    @property
    def entries(self) -> tuple[TrailEntry, ...]:
        return tuple(self._entries)

    def append(self, tick: int, tx_ref: str, accepted: bool, rule_version: int,
               proof_ref: str, detail: str) -> TrailEntry:
        prev = self._entries[-1].hash if self._entries else GENESIS
        index = len(self._entries)
        h = digest([index, tick, tx_ref, accepted, rule_version, proof_ref, detail, prev])
        e = TrailEntry(index, tick, tx_ref, accepted, rule_version, proof_ref, detail, prev, h)
        self._entries.append(e)
        return e

    def verify(self) -> tuple[bool, int | None]:
        """Return (ok, first_bad_index). Detects alteration, omission and reordering."""
        prev = GENESIS
        for i, e in enumerate(self._entries):
            h = digest([e.index, e.tick, e.tx_ref, e.accepted, e.rule_version, e.proof_ref, e.detail, prev])
            if e.index != i or e.prev != prev or e.hash != h:
                return False, i
            prev = e.hash
        return True, None
