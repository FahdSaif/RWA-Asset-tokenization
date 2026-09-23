"""
Layer 2 — Verifiable Credentials Management (paper Sec. V-D, "Verifiable
Credentials Management").

Credentials follow the shape of the W3C Verifiable Credentials Data Model
(https://www.w3.org/TR/vc-data-model/): a claims payload plus a proof.
Here the proof is a detached Ed25519 signature over the canonicalized
claim payload, produced by the issuer's did:key. This is a simplified
stand-in for a full JSON-LD/JWT-VC pipeline — enough to genuinely exercise
issuance, tamper-detection, and revocation, which is what the runtime
enforcement layer actually needs as input.

Credentials are never written on-chain in native form (per the paper);
they live in the holder's own store and are only ever used, in this
prototype, to *generate* a zero-knowledge attestation (see zkp_module.py)
that is what actually gets submitted with a transaction.
"""
from __future__ import annotations

import dataclasses
import json
import time
import uuid
from typing import Any, Dict, Optional

from arca.layer2_identity.did_registry import DIDKeyPair, did_to_verify_key
from cryptography.exceptions import InvalidSignature


def _canonicalize(obj: Dict[str, Any]) -> bytes:
    """Deterministic JSON serialization so sign/verify operate over
    identical bytes regardless of dict ordering."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()


@dataclasses.dataclass
class VerifiableCredential:
    id: str
    issuer_did: str
    subject_did: str
    credential_type: str          # e.g. "AccreditedInvestorCredential"
    claims: Dict[str, Any]        # e.g. {"jurisdictionOfResidence": "AU", "accredited": True}
    issuance_date: float
    expiration_date: Optional[float]
    signature: bytes

    def to_payload(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "issuer": self.issuer_did,
            "subject": self.subject_did,
            "type": self.credential_type,
            "claims": self.claims,
            "issuanceDate": self.issuance_date,
            "expirationDate": self.expiration_date,
        }


class CredentialRevocationRegistry:
    """Append-only revocation registry keyed by credential id. Propagated
    to the ZKP verification module so revoked credentials cannot be used
    to generate a subsequently-valid proof (paper Sec. VI-B, Threat Class III)."""

    def __init__(self):
        self._revoked: Dict[str, float] = {}

    def revoke(self, credential_id: str) -> None:
        self._revoked[credential_id] = time.time()

    def is_revoked(self, credential_id: str) -> bool:
        return credential_id in self._revoked


class CredentialIssuer:
    """
    A regulated credential issuer authorized under the governance framework
    (Sec. V-F). In production this would be a licensed KYC provider,
    exchange, or competent authority; here it is any party holding a DID
    keypair whose public key has been added to the governance module's
    authorized-issuer set (see layer4_governance.governance).
    """

    def __init__(self, issuer_keypair: DIDKeyPair):
        self.keypair = issuer_keypair

    def issue(
        self,
        subject_did: str,
        credential_type: str,
        claims: Dict[str, Any],
        validity_seconds: Optional[float] = None,
    ) -> VerifiableCredential:
        issuance_date = time.time()
        expiration_date = issuance_date + validity_seconds if validity_seconds else None
        payload = {
            "id": str(uuid.uuid4()),
            "issuer": self.keypair.did,
            "subject": subject_did,
            "type": credential_type,
            "claims": claims,
            "issuanceDate": issuance_date,
            "expirationDate": expiration_date,
        }
        signature = self.keypair.sign(_canonicalize(payload))
        return VerifiableCredential(
            id=payload["id"],
            issuer_did=self.keypair.did,
            subject_did=subject_did,
            credential_type=credential_type,
            claims=claims,
            issuance_date=issuance_date,
            expiration_date=expiration_date,
            signature=signature,
        )


def verify_credential(
    vc: VerifiableCredential,
    revocation_registry: Optional[CredentialRevocationRegistry] = None,
) -> bool:
    """
    Verifies:
      1. The issuer's signature over the claim payload (authenticity).
      2. The credential has not expired.
      3. The credential has not been revoked.

    Returns False rather than raising, so callers (e.g. the Transaction
    Validation Module) can fold this into a structured rejection reason
    instead of an unhandled exception.
    """
    try:
        verify_key = did_to_verify_key(vc.issuer_did)
        verify_key.verify(vc.signature, _canonicalize(vc.to_payload()))
    except (InvalidSignature, ValueError):
        return False

    if vc.expiration_date is not None and time.time() > vc.expiration_date:
        return False

    if revocation_registry is not None and revocation_registry.is_revoked(vc.id):
        return False

    return True
