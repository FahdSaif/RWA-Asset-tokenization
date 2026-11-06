"""Mitigation / defect switches. `Config.baseline()` is a naive build with implementation faults and
no mitigations; `Config.hardened()` applies M1-M15 of the paper. Scenarios flip individual switches."""
from __future__ import annotations

import dataclasses
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    # --- implementation faults (class-T mitigations M1/M2 remove them) ---
    legacy_raw_path: bool = False        # A1: a raw / node-level path reaches the balance primitive
    defect_origin_spoof: bool = False    # A2: Gateway skips evaluation for memos starting "SYS:"
    p2_mediated: bool = True             # P2: VM / contract transfers routed through the Gateway
    p3_mediated: bool = True             # P3: system hooks routed through the Gateway
    # --- M3 privileged operations ---
    priv_via_gateway: bool = True        # P5 forced transfer / recovery evaluated by the Gateway
    guarded_upgrade: bool = True         # P6 upgrades: time-lock, attested build, conformance suite
    upgrade_timelock: int = 3
    # --- M4 / M5 governance ---
    challenge_window: int = 5            # ticks relaxations wait before activation (0 = none)
    asymmetric_activation: bool = True   # tightenings activate immediately (with expiry)
    tighten_expiry: int = 50
    # --- M6 oracle hardening ---
    auto_ingest_oracle: bool = False
    multi_source_k: int = 2
    provenance_independent_contestation: bool = True
    bulk_delist_threshold: int = 1       # 0 disables the anomaly flag
    # --- M7 / M8 issuers ---
    allowlist: bool = True
    scoped_issuance: bool = True
    freshness_bound: int | None = 3      # M8/M15: max age of a status proof (None = unbounded)
    # --- M10 / T12 minimisation ---
    log_granularity: str = "class"       # "subrule" leaks the matched sub-rule (D2)
    uniform_errors: bool = True
    # --- cross-chain (M12-M14) ---
    dest_mediation: bool = True
    profile_most_restrictive: bool = True
    pending_flag: bool = True

    def replace(self, **kw) -> "Config":
        return dataclasses.replace(self, **kw)

    @classmethod
    def baseline(cls) -> "Config":
        return cls(legacy_raw_path=True, defect_origin_spoof=True, p2_mediated=False, p3_mediated=False,
                   priv_via_gateway=False, guarded_upgrade=False, upgrade_timelock=0, challenge_window=0,
                   asymmetric_activation=False, tighten_expiry=0, auto_ingest_oracle=True, multi_source_k=1,
                   provenance_independent_contestation=False, bulk_delist_threshold=0, allowlist=False,
                   scoped_issuance=False, freshness_bound=None, log_granularity="subrule",
                   uniform_errors=False, dest_mediation=False, profile_most_restrictive=False,
                   pending_flag=False)

    @classmethod
    def hardened(cls) -> "Config":
        return cls()
