"""
Layer 2 -- binding a jurisdiction zero-knowledge proof to an issuer-certified
credential (paper Sec. V-D; Threat Class III in Sec. VI-B).

A membership proof on its own only shows that *some* value the prover
chose is in the allowed set. This check additionally requires that the
value proved about is the one an AUTHORIZED ISSUER certified for THIS
sender:

  1. a JurisdictionCredential is presented;
  2. its issuer signature verifies, it is unexpired and not revoked;
  3. its issuer is currently authorized (governance-approved);
  4. its subject is the transaction sender;
  5. the proof's commitment equals the commitment the issuer signed;
  6. the zero-knowledge membership proof verifies against the allow-list.

The same function is used by the Transaction Validation Module (the
enforcement point) and by the Eligibility agent (so its CRR cannot say
"eligible" on the strength of an unbound proof).
"""
from __future__ import annotations

from typing import Callable, Optional, Sequence, Tuple

from arca.layer2_identity.verifiable_credentials import (
    JURISDICTION_CREDENTIAL_TYPE,
    CredentialRevocationRegistry,
    VerifiableCredential,
    verify_credential,
)
from arca.layer2_identity.zkp_module import ORMembershipProof, point_to_hex, verify_membership


def verify_jurisdiction_binding(
    proof: Optional[ORMembershipProof],
    credential: Optional[VerifiableCredential],
    sender_did: str,
    allowed_values: Sequence[int],
    revocation_registry: CredentialRevocationRegistry,
    is_authorized_issuer: Callable[[str], bool],
) -> Tuple[bool, str]:
    """Returns (ok, reason). Fails closed: any problem yields ok=False."""
    if proof is None:
        return False, "no jurisdiction proof submitted"
    if credential is None:
        return False, "no issuer-certified jurisdiction credential submitted"
    if credential.credential_type != JURISDICTION_CREDENTIAL_TYPE:
        return False, "credential is not a JurisdictionCredential"
    if not verify_credential(credential, revocation_registry):
        return False, "jurisdiction credential invalid, expired or revoked"
    if not is_authorized_issuer(credential.issuer_did):
        return False, "jurisdiction credential issuer is not an authorized issuer"
    if credential.subject_did != sender_did:
        return False, "jurisdiction credential was not issued to the transaction sender"
    certified = credential.claims.get("jurisdictionCommitment")
    try:
        proof_commitment = point_to_hex(proof.commitment)
    except Exception:
        return False, "malformed jurisdiction proof"
    if not isinstance(certified, str) or certified != proof_commitment:
        return False, "proof is not about the issuer-certified jurisdiction commitment"
    try:
        if not verify_membership(proof, list(allowed_values)):
            return False, "zero-knowledge membership proof failed verification"
    except Exception:
        return False, "malformed jurisdiction proof"
    return True, "jurisdiction proof bound to an issuer-certified credential and verified"
