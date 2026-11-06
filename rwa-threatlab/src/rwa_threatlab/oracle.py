"""Regulatory-data oracle feeds and the aggregator that turns them into governance proposals (M6)."""
from __future__ import annotations

import dataclasses
from dataclasses import dataclass
from typing import TYPE_CHECKING

from .crypto import Pki, Signer
from .governance import Proposal

if TYPE_CHECKING:  # pragma: no cover
    from .system import Instance


def listing_msg(feed: str, tick: int, sanctioned: frozenset[str]) -> str:
    return f"listing|{feed}|{tick}|{','.join(sorted(sanctioned))}"


@dataclass(frozen=True)
class Listing:
    feed: str
    tick: int
    sanctioned: frozenset[str]
    sig: str


class OracleFeed:
    def __init__(self, name: str, pki: Pki):
        self.name = name
        self.signer: Signer = pki.register(name)

    def publish(self, sanctioned: set[str] | frozenset[str], tick: int) -> Listing:
        s = frozenset(sanctioned)
        return Listing(self.name, tick, s, self.signer.sign(listing_msg(self.name, tick, s)))


class OracleAggregator:
    def __init__(self, inst: "Instance"):
        self.inst = inst
        self.flags: list[str] = []

    def ingest(self, listings: list[Listing]) -> Proposal | None:
        inst, cfg = self.inst, self.inst.cfg
        valid = [l for l in listings
                 if inst.pki.verify(l.feed, listing_msg(l.feed, l.tick, l.sanctioned), l.sig)]
        groups: dict[frozenset[str], set[str]] = {}
        for l in valid:
            groups.setdefault(l.sanctioned, set()).add(l.feed)
        best = max(groups.items(), key=lambda kv: len(kv[1]), default=None)
        if best is None or len(best[1]) < cfg.multi_source_k:
            self.flags.append("no-consensus")          # multi-source cross-validation (M6)
            return None
        consensus = best[0]
        active = inst.store.active
        if consensus == active.sanctioned:
            return None
        candidate = dataclasses.replace(active, sanctioned=consensus)
        p = inst.governance.propose("rules", candidate, source="oracle", proposer="oracle")
        removed = active.sanctioned - consensus
        bulk = cfg.bulk_delist_threshold and len(removed) >= cfg.bulk_delist_threshold
        if bulk:
            self.flags.append("bulk-delisting")        # anomaly flag forces human review
        if cfg.auto_ingest_oracle and not bulk:
            inst.governance.auto_authorise(p.pid)
        return p
