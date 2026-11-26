"""Data classes.

Time is counted in quarters; quarter 0 is 2027 Q1. A migration only takes effect at an anchor's
next renewal date, so starting too late means waiting for the following one."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class Calendar:
    """Renewal dates of an anchor: every `period` quarters, starting at `phase`.

    `source` says where it came from: observed, documented or assumed."""
    period: int = 4
    phase: int = 0
    source: str = "assumed"

    def next_boundary(self, q: float) -> int:
        """First renewal date at or after quarter q."""
        if self.period <= 1:
            return int(-(-q // 1))  # round up
        k = -(-(q - self.phase) // self.period)  # round up
        b = int(self.phase + max(k, 0) * self.period)
        return b if b >= q else b + self.period


@dataclass
class Anchor:
    """A key (or set of keys) whose signature the system trusts. `provenance` says what was observed."""
    anchor_id: str
    role: str                      # e.g. upgrade_admin, owner_admin, role_holder
    controller_type: str           # e.g. eoa, multisig, timelock
    algorithm: str = "secp256k1-ecdsa"
    n_keys: int = 1                # keys an attacker must forge
    key_exposed: Optional[bool] = None   # public key visible on-chain? None = unknown
    controller_address: Optional[str] = None
    timelock_quarters: int = 0     # extra delay from a timelock
    tokens: list[str] = field(default_factory=list)     # tokens it controls
    capabilities: list[str] = field(default_factory=list)  # e.g. pause, freeze_blacklist
    value_usd: float = 0.0         # market cap it controls
    signs_records: bool = False    # signs records that must be kept
    issuer_group: str = ""         # issuer that does the work
    calendar: Calendar = field(default_factory=Calendar)
    migration_quarters: int = 2    # planned time, in quarters
    migration_cost: float = 1.0    # relative cost
    instances: list[str] = field(default_factory=lambda: ["ethereum"])
    provenance: dict = field(default_factory=dict)

    @property
    def quantum_vulnerable(self) -> bool:
        from .kb.facts import QUANTUM_VULNERABLE_ALGORITHMS
        return self.algorithm in QUANTUM_VULNERABLE_ALGORITHMS


@dataclass
class Token:
    address: str
    rank: int
    name: str
    symbol: str
    market_cap_usd: float
    contract_name: str = ""
    is_proxy: bool = False
    abi_functions: list[str] = field(default_factory=list)
    categories: dict = field(default_factory=dict)


@dataclass
class Bridge:
    """Two copies of a token on different chains, joined by a bridge."""
    anchor_id: str
    a: str
    b: str


@dataclass
class Deployment:
    tokens: list[Token]
    anchors: list[Anchor]
    bridges: list[Bridge] = field(default_factory=list)
    source: str = ""
    group_capacity: dict = field(default_factory=dict)      # issuer -> migrations at once
    observed_topology: dict = field(default_factory=dict)   # anchor -> {chain: value share}

    def anchor(self, anchor_id: str) -> Anchor:
        for a in self.anchors:
            if a.anchor_id == anchor_id:
                return a
        raise KeyError(anchor_id)
