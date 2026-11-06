"""Issuers, verifiable-credential-like objects, status (revocation) proofs, presentations."""
from __future__ import annotations

from dataclasses import dataclass, field

from .crypto import Pki, Signer


def claim_msg(cred_id: str, subject: str, name: str, value: str) -> str:
    return f"claim|{cred_id}|{subject}|{name}|{value}"


def status_msg(issuer: str, tick: int, revoked: frozenset[str]) -> str:
    return f"status|{issuer}|{tick}|{','.join(sorted(revoked))}"


@dataclass
class Credential:
    cred_id: str
    subject: str
    issuer: str
    claims: dict[str, str]
    sigs: dict[str, str]


@dataclass(frozen=True)
class StatusProof:
    issuer: str
    tick: int
    revoked: frozenset[str]
    sig: str


@dataclass
class Proof:
    """A presentation: selectively disclosed claims plus a status proof (a ZK proof in production)."""
    subject: str
    issuer: str
    cred_id: str
    claims: dict[str, str]
    sigs: dict[str, str]
    status: StatusProof


class Issuer:
    """Credential issuer. `blind=True` models blind issuance: the issuer never learns cred_id,
    so its issuance log cannot be joined with on-chain presentations (mitigation M11)."""

    def __init__(self, name: str, pki: Pki, blind: bool = False):
        self.name = name
        self.signer: Signer = pki.register(name)
        self.blind = blind
        self.issuance_log: list[dict] = []
        self._revoked: set[str] = set()
        self._serial = 0

    def issue(self, subject: str, claims: dict[str, str], tick: int,
              cred_id: str | None = None) -> Credential:
        if cred_id is None:
            self._serial += 1
            cred_id = f"{self.name}-{self._serial:05d}"
        sigs = {k: self.signer.sign(claim_msg(cred_id, subject, k, v)) for k, v in claims.items()}
        entry = {"identity": subject, "tick": tick}
        if not self.blind:
            entry["cred_id"] = cred_id
        self.issuance_log.append(entry)
        return Credential(cred_id, subject, self.name, dict(claims), sigs)

    def revoke(self, cred_id: str) -> None:
        self._revoked.add(cred_id)

    def status(self, tick: int) -> StatusProof:
        rev = frozenset(self._revoked)
        return StatusProof(self.name, tick, rev, self.signer.sign(status_msg(self.name, tick, rev)))


def present(cred: Credential, reveal: list[str], status: StatusProof) -> Proof:
    return Proof(cred.subject, cred.issuer, cred.cred_id,
                 {k: cred.claims[k] for k in reveal}, {k: cred.sigs[k] for k in reveal}, status)
