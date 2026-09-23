"""
Layer 2 — Zero-Knowledge Proof Verification Module (paper Sec. V-D,
"Zero-Knowledge Proof Verification Module").

Implements real elliptic-curve zero-knowledge machinery (not a mock):

  1. Pedersen commitments over brainpoolP256r1 (via `tinyec`), with the
     second generator H derived by hash-to-curve so that nobody — not
     even the implementer — knows log_G(H). This is what makes the
     commitment binding as well as hiding.
  2. A Schnorr sigma-protocol NIZK (Fiat-Shamir transform) proving
     knowledge of a commitment's opening (m, r).
  3. A disjunctive ("OR") composition of Schnorr proofs, which lets a
     participant prove a committed attribute equals ONE of a public list
     of allowed values, without revealing which one. This instantiates
     the paper's example predicate: "jurisdiction of residence is not on
     the applicable sanctions list" — proved as membership in the
     complement (allowed) set, without disclosing the actual jurisdiction.

This is a simplified, from-scratch construction intended to genuinely
demonstrate the privacy-preserving verification property end to end. It
is NOT a production zk-SNARK toolchain (the paper's discussion of SNARK
circuits and their transparent variants describes a much larger
engineering effort, explicitly left to future implementation work in
Sec. VII.5). For a production system, the same predicates should be
compiled to a circuit (e.g. Circom/snarkjs, or a Halo2 circuit) rather
than the ad-hoc protocol below.
"""
from __future__ import annotations

import dataclasses
import hashlib
import secrets
from typing import List, Optional, Sequence

from tinyec import registry
from tinyec.ec import Point

CURVE = registry.get_curve("brainpoolP256r1")
_N = CURVE.field.n  # group order
_P = CURVE.field.p  # field prime
_G = CURVE.g


def _sqrt_mod_p(a: int, p: int) -> Optional[int]:
    """Tonelli-Shanks modular square root. Returns None if a is a
    non-residue. p (brainpoolP256r1's field prime) is odd, so this
    general routine (rather than the p%4==3 shortcut) is used for
    portability across curve choices."""
    a %= p
    if a == 0:
        return 0
    if pow(a, (p - 1) // 2, p) != 1:
        return None  # non-residue
    if p % 4 == 3:
        return pow(a, (p + 1) // 4, p)
    # general Tonelli-Shanks
    q, s = p - 1, 0
    while q % 2 == 0:
        q //= 2
        s += 1
    z = 2
    while pow(z, (p - 1) // 2, p) != p - 1:
        z += 1
    m, c, t, r = s, pow(z, q, p), pow(a, q, p), pow(a, (q + 1) // 2, p)
    while t != 1:
        i, temp = 0, t
        while temp != 1:
            temp = (temp * temp) % p
            i += 1
        b = pow(c, 1 << (m - i - 1), p)
        m, c, t, r = i, (b * b) % p, (t * b * b) % p, (r * b) % p
    return r


def hash_to_curve_point(domain_tag: bytes) -> Point:
    """Try-and-increment hash-to-curve: deterministically finds a point on
    the curve from a domain-separation tag, with no discoverable discrete
    log relative to G. Used to derive the Pedersen second generator H."""
    counter = 0
    a, b, p = CURVE.a, CURVE.b, _P
    while True:
        x = int.from_bytes(
            hashlib.sha256(domain_tag + counter.to_bytes(4, "big")).digest(), "big"
        ) % p
        rhs = (pow(x, 3, p) + a * x + b) % p
        y = _sqrt_mod_p(rhs, p)
        if y is not None:
            pt = Point(CURVE, x, y)
            if CURVE.on_curve(pt.x, pt.y):
                return pt
        counter += 1


# Nothing-up-my-sleeve second generator: fixed domain tag => reproducible,
# but its discrete log w.r.t. G is unknown to anyone.
_H = hash_to_curve_point(b"ARCA-ZKP-Pedersen-H-v1")


def _point_to_bytes(pt: Point) -> bytes:
    return pt.x.to_bytes(32, "big") + pt.y.to_bytes(32, "big")


def _hash_challenge(*points_and_ints) -> int:
    h = hashlib.sha256()
    for item in points_and_ints:
        if isinstance(item, Point):
            h.update(_point_to_bytes(item))
        elif isinstance(item, int):
            h.update(item.to_bytes(32, "big", signed=False) if item >= 0 else item.to_bytes(32, "big", signed=True))
        else:
            h.update(bytes(item))
    return int.from_bytes(h.digest(), "big") % _N


@dataclasses.dataclass
class PedersenCommitment:
    point: Point


def commit(message: int, randomness: Optional[int] = None) -> "tuple[PedersenCommitment, int]":
    """Create C = message*G + randomness*H. Returns (commitment, randomness)
    so the caller can retain the opening for later proof generation."""
    r = randomness if randomness is not None else secrets.randbelow(_N - 1) + 1
    c = (message % _N) * _G + r * _H
    return PedersenCommitment(point=c), r


# ---------------------------------------------------------------------------
# Schnorr NIZK proof of knowledge of a Pedersen commitment opening (m, r)
# ---------------------------------------------------------------------------

@dataclasses.dataclass
class SchnorrOpeningProof:
    """Fiat-Shamir NIZK proof of knowledge of (m, r) such that
    C = m*G + r*H, without revealing m or r."""
    t: Point   # commitment to the proof's randomness
    e: int     # Fiat-Shamir challenge
    z_m: int   # response for m
    z_r: int   # response for r


def prove_opening(message: int, randomness: int, commitment: PedersenCommitment) -> SchnorrOpeningProof:
    k_m = secrets.randbelow(_N - 1) + 1
    k_r = secrets.randbelow(_N - 1) + 1
    t = k_m * _G + k_r * _H
    e = _hash_challenge(commitment.point, t)
    z_m = (k_m + e * message) % _N
    z_r = (k_r + e * randomness) % _N
    return SchnorrOpeningProof(t=t, e=e, z_m=z_m, z_r=z_r)


def verify_opening(commitment: PedersenCommitment, proof: SchnorrOpeningProof) -> bool:
    e_check = _hash_challenge(commitment.point, proof.t)
    if e_check != proof.e:
        return False
    lhs = proof.z_m * _G + proof.z_r * _H
    rhs = proof.t + proof.e * commitment.point
    return lhs.x == rhs.x and lhs.y == rhs.y


# ---------------------------------------------------------------------------
# Disjunctive (OR) proof: prove committed value == one of `allowed_values`,
# without revealing which. This is the actual privacy-preserving predicate
# proof the runtime enforcement layer consumes (e.g. "jurisdiction is in
# the allowed / non-sanctioned set").
# ---------------------------------------------------------------------------

@dataclasses.dataclass
class ORMembershipProof:
    commitment: Point
    branches: List[dict]  # each: {"t": Point, "e": int, "z": int}
    global_challenge: int


def prove_membership(
    message: int,
    randomness: int,
    commitment: PedersenCommitment,
    allowed_values: Sequence[int],
) -> ORMembershipProof:
    """
    Proves commitment.point opens to `message` (with randomness) AND that
    `message` is one of `allowed_values`, revealing nothing about which
    index matched. Standard Cramer-Damgard-Schoenmakers OR-composition of
    Schnorr proofs: the true branch is proved honestly; every other
    branch is *simulated* (its transcript is generated backwards from a
    randomly-chosen response, which is indistinguishable from a real one).

    KNOWN SIMPLIFICATION vs. the paper's threat model (Sec. VI-B, Threat
    Class III): this proves knowledge of *a self-chosen value* that
    happens to be in the allowed set — it does not, by itself, prove that
    value was attested by an authorized credential issuer. The paper's
    fuller design implies the ZKP is generated FROM a verified credential
    (proof of "I hold a validly-signed credential asserting attribute X",
    which requires verifying a signature *inside* the circuit — genuine
    zk-SNARK territory, e.g. a Circom/Halo2 circuit over the issuer's
    signature scheme). This prototype instead keeps the two checks
    separate and explicit: `eligibility_agent.py` verifies the ZK
    membership proof AND, independently, an issuer-signed Verifiable
    Credential's signature/revocation status — which is real,
    working issuer-binding, just not fused into a single circuit. Fusing
    them is exactly the kind of "empirical prototype implementation"
    work the paper defers to Sec. VII.
    """
    if message not in allowed_values:
        raise ValueError("message is not in allowed_values — cannot prove a false statement")

    true_index = list(allowed_values).index(message)
    n_branches = len(allowed_values)

    branch_t: List[Point] = [None] * n_branches       # type: ignore
    branch_e: List[Optional[int]] = [None] * n_branches
    branch_z: List[Optional[int]] = [None] * n_branches

    # For every FALSE branch: pick random challenge e_i and response z_i,
    # then derive t_i so the verification equation holds automatically
    # (simulation), matching the standard OR-proof construction.
    for i, v in enumerate(allowed_values):
        if i == true_index:
            continue
        e_i = secrets.randbelow(_N - 1) + 1
        z_i = secrets.randbelow(_N - 1) + 1
        target = commitment.point + (-v % _N) * _G  # C - v*G  (should equal r*H if v were true)
        t_i = z_i * _H + (-e_i % _N) * target
        branch_t[i], branch_e[i], branch_z[i] = t_i, e_i, z_i

    # For the TRUE branch: commit to fresh randomness k, defer its
    # challenge until the global Fiat-Shamir hash is computed.
    k_true = secrets.randbelow(_N - 1) + 1
    t_true = k_true * _H
    branch_t[true_index] = t_true

    all_t_bytes = b"".join(_point_to_bytes(t) for t in branch_t)
    e_global = _hash_challenge(commitment.point, all_t_bytes)

    sum_other_e = sum(branch_e[i] for i in range(n_branches) if i != true_index) % _N
    e_true = (e_global - sum_other_e) % _N
    z_true = (k_true + e_true * randomness) % _N

    branch_e[true_index] = e_true
    branch_z[true_index] = z_true

    branches = [
        {"t": branch_t[i], "e": branch_e[i], "z": branch_z[i]} for i in range(n_branches)
    ]
    return ORMembershipProof(commitment=commitment.point, branches=branches, global_challenge=e_global)


def verify_membership(
    proof: ORMembershipProof,
    allowed_values: Sequence[int],
) -> bool:
    if len(proof.branches) != len(allowed_values):
        return False

    e_sum = 0
    for branch, v in zip(proof.branches, allowed_values):
        target = proof.commitment + (-v % _N) * _G
        lhs = branch["z"] * _H
        rhs = branch["t"] + branch["e"] * target
        if lhs.x != rhs.x or lhs.y != rhs.y:
            return False
        e_sum = (e_sum + branch["e"]) % _N

    all_t_bytes = b"".join(_point_to_bytes(b["t"]) for b in proof.branches)
    e_check = _hash_challenge(proof.commitment, all_t_bytes)
    return e_sum == e_check == proof.global_challenge
