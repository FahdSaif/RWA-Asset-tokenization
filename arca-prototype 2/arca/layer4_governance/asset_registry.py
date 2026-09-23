"""
Layer 4 — Token Standards and Asset Registry (paper Sec. V-F, "Token
Standards and Asset Registry").

An on-chain registry of tokenized-asset metadata: asset type, issuing
jurisdiction, applicable regulatory classification, the compliance rule
references that apply to it, and custodianship information. The
Transaction Validation Module (Layer 3) consults this registry — rather
than trusting fields asserted by the transaction submitter — to
determine which rules actually apply, which is what "enables the
validation logic to identify the precise compliance requirements
applicable to each transaction without ambiguity."
"""
from __future__ import annotations

import dataclasses
import time
from typing import Dict, List, Optional

from arca.layer3_runtime.audit_log import HashChainLedger


@dataclasses.dataclass(frozen=True)
class AssetRecord:
    asset_id: str
    asset_type: str            # "real_estate" | "commodity" | "security" | ...
    issuing_jurisdiction: str  # ISO alpha-2
    regulatory_classification: str  # e.g. "MiCA-ART", "SEC-Reg-D", "unclassified"
    custodian_did: str
    registered_at: float


class AssetRegistry:
    def __init__(self, audit_log: HashChainLedger):
        self.audit_log = audit_log
        self._assets: Dict[str, AssetRecord] = {}

    def register_asset(
        self,
        asset_id: str,
        asset_type: str,
        issuing_jurisdiction: str,
        regulatory_classification: str,
        custodian_did: str,
    ) -> AssetRecord:
        if asset_id in self._assets:
            raise ValueError(f"asset_id '{asset_id}' already registered")
        record = AssetRecord(
            asset_id=asset_id,
            asset_type=asset_type,
            issuing_jurisdiction=issuing_jurisdiction.upper(),
            regulatory_classification=regulatory_classification,
            custodian_did=custodian_did,
            registered_at=time.time(),
        )
        self._assets[asset_id] = record
        self.audit_log.append(
            "asset_registry.registered",
            dataclasses.asdict(record),
        )
        return record

    def get(self, asset_id: str) -> Optional[AssetRecord]:
        return self._assets.get(asset_id)

    def all_assets(self) -> List[AssetRecord]:
        return list(self._assets.values())
