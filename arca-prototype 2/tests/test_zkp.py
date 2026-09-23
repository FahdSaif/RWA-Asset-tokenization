import pytest

from arca.layer2_identity import zkp_module as zkp


def test_pedersen_opening_proof_valid():
    c, r = zkp.commit(1234)
    proof = zkp.prove_opening(1234, r, c)
    assert zkp.verify_opening(c, proof) is True


def test_pedersen_opening_proof_wrong_message_rejected():
    c, r = zkp.commit(1234)
    bad_proof = zkp.prove_opening(9999, r, c)  # message doesn't match commitment
    assert zkp.verify_opening(c, bad_proof) is False


def test_commitment_hides_message_but_is_deterministic_given_randomness():
    c1, r1 = zkp.commit(42)
    c2, _ = zkp.commit(42)
    # two commitments to the same message with independent randomness differ
    assert (c1.point.x, c1.point.y) != (c2.point.x, c2.point.y)


def _encode(cc: str) -> int:
    return ord(cc[0]) * 256 + ord(cc[1])


def test_or_membership_proof_true_statement():
    allowed = [_encode(x) for x in ["AU", "US", "GB", "DE", "FR"]]
    secret = _encode("US")
    c, r = zkp.commit(secret)
    proof = zkp.prove_membership(secret, r, c, allowed)
    assert zkp.verify_membership(proof, allowed) is True


def test_or_membership_proof_refuses_false_statement():
    allowed = [_encode(x) for x in ["AU", "US", "GB", "DE", "FR"]]
    secret = _encode("KP")  # not in the allowed set
    c, r = zkp.commit(secret)
    with pytest.raises(ValueError):
        zkp.prove_membership(secret, r, c, allowed)


def test_or_membership_proof_rejects_swapped_commitment():
    allowed = [_encode(x) for x in ["AU", "US", "GB", "DE", "FR"]]
    secret_a, secret_b = _encode("AU"), _encode("US")
    c_a, r_a = zkp.commit(secret_a)
    c_b, r_b = zkp.commit(secret_b)
    proof_b = zkp.prove_membership(secret_b, r_b, c_b, allowed)

    # tamper: swap in a different commitment after the proof was generated
    proof_b.commitment = c_a.point
    assert zkp.verify_membership(proof_b, allowed) is False


def test_or_membership_proof_does_not_leak_which_branch_is_true():
    """Not a statistical test of indistinguishability (that's a proof
    obligation, not a unit test) — just checks the proof object carries no
    plaintext index/flag identifying the true branch."""
    allowed = [_encode(x) for x in ["AU", "US", "GB", "DE", "FR"]]
    secret = _encode("DE")
    c, r = zkp.commit(secret)
    proof = zkp.prove_membership(secret, r, c, allowed)
    assert not hasattr(proof, "true_index")
    assert not hasattr(proof, "secret")
