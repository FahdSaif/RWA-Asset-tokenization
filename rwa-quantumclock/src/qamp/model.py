"""Core data classes.

Time is discrete, in quarters. Quarter 0 is the first quarter of ``config.START_YEAR``. A *commitment calendar*
gives the quarters at which a migration of an anchor can take effect (a credential re-issuance, a key-rotation
ceremony, a governance or custody renewal). This is the decision-window idea of the authors' project-governance
work: a decision taken too late to complete before a renewal waits for the next one.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class Calendar:
    """Renewal boundaries of an anchor: every ``period`` quarters, starting at ``phase`` (0 <= phase < period).

    ``source`` records where the calendar comes from: "observed" (on-chain governance history), "documented"
    (an issuer's published policy, with URL) or "assumed" (a documented default, to be replaced).
    """
    period: int = 4
    phase: int = 0
    source: str = "assumed"

    def next_boundary(self, q: float) -> int:
        """First renewal boundary at or after quarter ``q``."""
        if self.period <= 1:
            return int(-(-q // 1))  # ceil
        k = -(-(q - self.phase) // self.period)  # ceil((q - phase) / period)
        b = int(self.phase + max(k, 0) * self.period)
        return b if b >= q else b + self.period


@dataclass
class Anchor:
    """A trust anchor: a key, or a set of keys, whose signature the compliance infrastructure accepts.

    Fields marked *observed* come from chain data; others are labelled in ``provenance``.
    """
    anchor_id: str
    role: str                      # upgrade_admin | owner_admin | role_holder | credential_issuer | oracle | quorum
    controller_type: str           # eoa | multisig | timelock | unknown | none | not_readable | ...
    algorithm: str = "secp256k1-ecdsa"
    n_keys: int = 1                # keys an attacker must forge (threshold for a multisig)
    key_exposed: Optional[bool] = None   # public key visible on-chain (None: not observed)
    controller_address: Optional[str] = None
    timelock_quarters: int = 0     # extra execution time from an observed timelock delay
    tokens: list[str] = field(default_factory=list)     # token addresses this anchor controls
    capabilities: list[str] = field(default_factory=list)  # pause, freeze_blacklist, forced_transfer_recovery, ...
    value_usd: float = 0.0         # value at risk: sum of market caps of controlled tokens
    signs_records: bool = False    # produces retained evidentiary records (trust-now-forge-later)
    issuer_group: str = ""         # organisation that must carry out the migration (capacity constraint)
    calendar: Calendar = field(default_factory=Calendar)
    migration_quarters: int = 2    # planned execution time of a migration (quarters)
    migration_cost: float = 1.0    # relative cost units
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
    """Two instances of the same token whose bridge accepts the source instance's state as valid."""
    anchor_id: str
    a: str
    b: str


@dataclass
class Deployment:
    tokens: list[Token]
    anchors: list[Anchor]
    bridges: list[Bridge] = field(default_factory=list)
    source: str = ""

    def anchor(self, anchor_id: str) -> Anchor:
        for a in self.anchors:
            if a.anchor_id == anchor_id:
                return a
        raise KeyError(anchor_id)
