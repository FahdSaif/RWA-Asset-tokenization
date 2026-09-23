"""
Layer 1 — Jurisdictional Regulatory Analysis Agent (paper Sec. V-C,
"Jurisdictional Regulatory Analysis Agent").

Ingests jurisdiction-level regulatory signal from the Regulatory Oracle
Network (Layer 4) — here, a real, dated snapshot of the FATF "grey" and
"black" lists (see data/fatf_lists.json and data/README.md for
provenance) plus ISO 3166 reference data via `pycountry` — and produces:

  1. A jurisdiction risk classification (`classify`), issued as a CRR.
  2. A *proposed* rule change (`propose_rule_update`) when a jurisdiction's
     classification changes in a way that should tighten or loosen
     enforcement — this is the artifact that gets handed to the
     Governance Module (Layer 4) for quorum approval before it can ever
     reach the Rule Registry (Layer 3). The agent never touches the
     active rule set directly, by design (Sec. IV-A, "adaptive
     intelligence with deterministic execution").
"""
from __future__ import annotations

import json
import pathlib
from typing import Dict, List, Optional

import pycountry

from arca.layer1_intelligence.crr import ComplianceRecommendationRecord, issue_crr
from arca.layer2_identity.did_registry import DIDKeyPair
from arca.layer3_runtime.models import Rule

_DATA_PATH = pathlib.Path(__file__).resolve().parents[2] / "data" / "fatf_lists.json"


def _encode_iso2(iso2: str) -> int:
    """Deterministic integer encoding of an ISO alpha-2 code, used as the
    'message' inside a Pedersen commitment for jurisdiction ZK proofs
    elsewhere in the pipeline (see zkp_module + eligibility_agent)."""
    iso2 = iso2.upper()
    return ord(iso2[0]) * 256 + ord(iso2[1])


class JurisdictionalRegulatoryAnalysisAgent:
    RISK_TIERS = ("low", "medium", "high", "prohibited")

    # A representative pool of jurisdictions active in tokenized RWA
    # markets (G20 members, major financial centres, and a few FATF
    # grey-listed jurisdictions included deliberately so classify() has
    # something real to exclude). This is NOT an exhaustive list of every
    # sovereign state — see allowed_jurisdiction_set()'s docstring for why
    # that bound is deliberate rather than an oversight.
    DEFAULT_CANDIDATE_POOL = [
        "AU", "US", "GB", "DE", "FR", "JP", "SG", "HK", "CH", "CA",
        "NZ", "NL", "IE", "LU", "AE", "KR", "SE", "NO", "DK", "FI",
        "BE", "AT", "ES", "IT", "PT", "IL", "ZA", "BR", "MX", "IN",
        "SY", "VE", "MM",  # deliberately includes FATF-listed jurisdictions to exercise filtering
    ]

    def __init__(self, keypair: DIDKeyPair, fatf_data_path: pathlib.Path = _DATA_PATH):
        self.keypair = keypair
        with open(fatf_data_path) as f:
            self._fatf = json.load(f)
        self._high_risk = {e["iso2"] for e in self._fatf["high_risk_call_for_action"]}
        self._grey_list = {e["iso2"] for e in self._fatf["increased_monitoring"]}

    def classify(self, iso2: str) -> str:
        iso2 = iso2.upper()
        if pycountry.countries.get(alpha_2=iso2) is None:
            raise ValueError(f"'{iso2}' is not a recognized ISO 3166-1 alpha-2 code")
        if iso2 in self._high_risk:
            return "prohibited"
        if iso2 in self._grey_list:
            return "high"
        return "low"

    def classify_with_crr(self, tx_id: str, iso2: str) -> ComplianceRecommendationRecord:
        tier = self.classify(iso2)
        country = pycountry.countries.get(alpha_2=iso2.upper())
        reasoning = [
            f"Jurisdiction {iso2.upper()} ({country.name}) checked against FATF snapshot "
            f"dated {self._fatf['_provenance']['retrieved']}.",
        ]
        if tier == "prohibited":
            reasoning.append(f"{iso2.upper()} appears on the FATF 'High-Risk Jurisdictions subject to a Call for Action' list.")
        elif tier == "high":
            reasoning.append(f"{iso2.upper()} appears on the FATF 'Jurisdictions under Increased Monitoring' list.")
        else:
            reasoning.append(f"{iso2.upper()} does not appear on either FATF list in the current snapshot.")
        return issue_crr(
            self.keypair,
            determination_type="jurisdiction_risk",
            context_id=tx_id,
            outcome=tier,
            reasoning_trace=reasoning,
            inputs={"iso2": iso2.upper(), "fatf_snapshot_date": self._fatf["_provenance"]["retrieved"]},
        )

    def allowed_jurisdiction_set(
        self,
        exclude_tiers: Optional[List[str]] = None,
        candidate_pool: Optional[List[str]] = None,
    ) -> List[str]:
        """Returns ISO alpha-2 codes NOT in the excluded risk tiers — this is
        the public allow-list against which sender jurisdiction ZK
        membership proofs are constructed and verified (see
        zkp_module.prove_membership / verify_membership and
        transaction_validator's 'require_jurisdiction_allowlist_proof' rule).

        `candidate_pool` bounds how many candidates the ZK OR-proof has to
        range over. This matters for a real reason, not just performance:
        the disjunctive Schnorr proof used here (zkp_module.py) is a
        simplified, from-scratch construction that costs O(n) elliptic-curve
        operations for n candidates — appropriate for a curated allow-list
        of tens of jurisdictions (which is what a real compliance policy
        for a specific asset offering typically is: "residents of these N
        approved jurisdictions"), but it does not scale to enumerating all
        ~195 sovereign states. A production system proving the identical
        predicate over an arbitrarily large set should compile it to a
        zk-SNARK/PLONK circuit instead (O(log n) or O(1) proof size) — which
        is exactly what the paper's Sec. V-D describes as the production
        approach, and what this prototype approximates rather than replaces.

        Defaults to a representative pool of jurisdictions active in
        tokenized RWA markets rather than the full ISO 3166 list.
        """
        exclude_tiers = exclude_tiers or ["prohibited"]
        excluded: set = set()
        if "prohibited" in exclude_tiers:
            excluded |= self._high_risk
        if "high" in exclude_tiers:
            excluded |= self._grey_list

        if candidate_pool is None:
            candidate_pool = self.DEFAULT_CANDIDATE_POOL
        return sorted(c for c in candidate_pool if c not in excluded)

    def propose_rule_update(
        self, iso2: str, asset_type: str, transaction_class: str = "*"
    ) -> Rule:
        """
        Translates a jurisdiction risk classification into a concrete,
        machine-enforceable Rule proposal. This Rule object is NOT yet
        active — it must still be wrapped in a GovernanceModule proposal,
        voted on, and finalized (Layer 4) before RuleRegistryModule
        (Layer 3) will accept it. This indirection is the paper's
        'adaptive intelligence with deterministic execution' principle.
        """
        tier = self.classify(iso2)
        rule_id = f"jurisdiction-{iso2.upper()}-{asset_type}-{transaction_class}"
        if tier == "prohibited":
            params = {"max_amount": 0}
        elif tier == "high":
            params = {"max_amount": 10_000}
        else:
            params = {"max_amount": 10_000_000}
        return Rule(
            rule_id=rule_id,
            asset_type=asset_type,
            jurisdiction=iso2.upper(),
            transaction_class=transaction_class,
            rule_type="max_transaction_amount",
            params=params,
        )
