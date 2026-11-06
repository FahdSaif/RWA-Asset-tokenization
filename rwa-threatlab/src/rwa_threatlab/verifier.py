"""Identity & Credential Verification Module."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .config import Config
from .credentials import Proof, claim_msg, status_msg
from .crypto import Pki


@dataclass(frozen=True)
class VerifyResult:
    ok: bool
    code: str


class VerificationModule:
    def __init__(self, pki: Pki, cfg: Config, registry: dict[str, frozenset[str] | None]):
        """registry: allow-listed issuers -> claim names they may attest (None = unrestricted)."""
        self.pki, self.cfg, self.registry = pki, cfg, registry

    def verify(self, proof: Proof | None, required: Iterable[tuple[str, str]], subject: str,
               now: int) -> VerifyResult:
        required = tuple(required)
        if not required:
            return VerifyResult(True, "OK")
        if proof is None:
            return VerifyResult(False, "NO_PROOF")
        if proof.subject != subject:
            return VerifyResult(False, "WRONG_SUBJECT")
        if not self.pki.known(proof.issuer):
            return VerifyResult(False, "UNKNOWN_ISSUER")
        if self.cfg.allowlist:
            if proof.issuer not in self.registry:
                return VerifyResult(False, "ISSUER_NOT_LISTED")
            scope = self.registry[proof.issuer]
            if self.cfg.scoped_issuance and scope is not None:
                if any(name not in scope for name, _ in required):
                    return VerifyResult(False, "OUT_OF_SCOPE")
        for name, value in required:
            if proof.claims.get(name) != value:
                return VerifyResult(False, "MISSING_CLAIM")
            if not self.pki.verify(proof.issuer, claim_msg(proof.cred_id, proof.subject, name, value),
                                   proof.sigs.get(name, "")):
                return VerifyResult(False, "BAD_SIGNATURE")
        st = proof.status
        if st.issuer != proof.issuer or not self.pki.verify(
                st.issuer, status_msg(st.issuer, st.tick, st.revoked), st.sig):
            return VerifyResult(False, "BAD_STATUS")
        if self.cfg.freshness_bound is not None and now - st.tick > self.cfg.freshness_bound:
            return VerifyResult(False, "STALE_STATUS")  # fail closed
        if proof.cred_id in st.revoked:
            return VerifyResult(False, "REVOKED")
        return VerifyResult(True, "OK")
