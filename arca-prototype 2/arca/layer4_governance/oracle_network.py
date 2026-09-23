"""
Layer 4 — Regulatory Oracle Network (paper Sec. V-F, "Regulatory Oracle
Network").

Delivers external regulatory data (sanctions lists, jurisdiction risk
classifications, accreditation thresholds) to the Compliance
Intelligence Layer. Two properties from the paper are implemented for
real here, not just described:

  1. "Each oracle data feed is cryptographically signed by its
     authorized provider and validated before ingestion" — every
     `OracleReport` carries an Ed25519 signature from the reporting
     provider's DID, checked against the Governance Module's
     authorized-provider set (Sec. VI-B, Threat Class IV).
  2. "Multi-source consensus mechanisms are applied where independent
     oracle feeds are available for the same regulatory datum" — a
     regulatory value is only accepted once a governance-defined quorum
     of *independently signed* reports agree on it, so a single
     compromised or malicious provider cannot corrupt the input to the
     Compliance Intelligence Layer on their own.
"""
from __future__ import annotations

import collections
import dataclasses
import json
import time
from typing import Any, Dict, List, Optional, Set

from arca.layer2_identity.did_registry import DIDKeyPair, did_to_verify_key
from arca.layer3_runtime.audit_log import HashChainLedger
from cryptography.exceptions import InvalidSignature


def _canonical(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str).encode()


@dataclasses.dataclass
class OracleReport:
    provider_did: str
    datum_key: str          # e.g. "fatf_grey_list_membership:SY"
    value: Any               # e.g. True / "prohibited" / 0.05
    reported_at: float
    signature: bytes = dataclasses.field(default=b"", repr=False)

    def payload(self) -> dict:
        return {
            "provider_did": self.provider_did,
            "datum_key": self.datum_key,
            "value": self.value,
            "reported_at": self.reported_at,
        }


def submit_report(provider_keypair: DIDKeyPair, datum_key: str, value: Any) -> OracleReport:
    report = OracleReport(
        provider_did=provider_keypair.did,
        datum_key=datum_key,
        value=value,
        reported_at=time.time(),
    )
    report.signature = provider_keypair.sign(_canonical(report.payload()))
    return report


class RegulatoryOracleNetwork:
    def __init__(
        self,
        audit_log: HashChainLedger,
        authorized_providers: Set[str],
        consensus_quorum: int = 2,
    ):
        self.audit_log = audit_log
        self.authorized_providers = authorized_providers
        self.consensus_quorum = consensus_quorum

    def _verify_report(self, report: OracleReport) -> bool:
        if report.provider_did not in self.authorized_providers:
            return False
        try:
            did_to_verify_key(report.provider_did).verify(report.signature, _canonical(report.payload()))
            return True
        except (InvalidSignature, ValueError):
            return False

    def ingest(self, datum_key: str, reports: List[OracleReport]) -> Optional[Any]:
        """
        Attempts to reach consensus on a single regulatory datum from
        multiple independently-submitted reports.

        Returns the consensus value if `consensus_quorum` (or more)
        *distinct, authorized* providers independently reported the same
        value; returns None otherwise (e.g. if a minority of compromised
        providers reported a different value — Threat Class IV). Every
        ingestion attempt, successful or not, is recorded on the audit
        ledger.
        """
        valid_reports = [r for r in reports if r.datum_key == datum_key and self._verify_report(r)]
        by_provider: Dict[str, OracleReport] = {}
        for r in valid_reports:
            by_provider.setdefault(r.provider_did, r)  # first valid report per provider only

        tally: Dict[str, int] = collections.Counter(json.dumps(r.value, sort_keys=True, default=str) for r in by_provider.values())
        consensus_value = None
        if tally:
            top_value_json, top_count = tally.most_common(1)[0]
            if top_count >= self.consensus_quorum:
                consensus_value = json.loads(top_value_json)

        self.audit_log.append(
            "oracle.ingest",
            {
                "datum_key": datum_key,
                "n_reports_submitted": len(reports),
                "n_valid_authorized_reports": len(by_provider),
                "n_distinct_providers": len(by_provider),
                "consensus_reached": consensus_value is not None,
                "consensus_value": consensus_value,
            },
        )
        return consensus_value
