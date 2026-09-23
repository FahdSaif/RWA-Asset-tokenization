from arca.layer2_identity.did_registry import DIDRegistry, did_to_verify_key, generate_did
from arca.layer2_identity.verifiable_credentials import (
    CredentialIssuer,
    CredentialRevocationRegistry,
    verify_credential,
)


def test_did_key_format_and_signature_roundtrip():
    kp = generate_did()
    assert kp.did.startswith("did:key:z")
    message = b"arca test message"
    sig = kp.sign(message)
    did_to_verify_key(kp.did).verify(sig, message)  # raises if invalid


def test_did_registry_rotation_and_tamper_detection():
    kp1 = generate_did()
    kp2 = generate_did()
    reg = DIDRegistry()
    reg.register(kp1)
    reg.rotate_key(kp1.did, kp2)
    assert reg.verify_history_integrity(kp1.did) is True

    # tamper with history directly
    reg._history[kp1.did][0].public_key_multibase = "z" + "X" * 10
    assert reg.verify_history_integrity(kp1.did) is False


def test_credential_issue_and_verify_happy_path():
    issuer_kp = generate_did()
    subject_kp = generate_did()
    issuer = CredentialIssuer(issuer_kp)
    revocation = CredentialRevocationRegistry()

    vc = issuer.issue(subject_kp.did, "AccreditedInvestorCredential", {"accredited": True})
    assert verify_credential(vc, revocation) is True


def test_credential_forged_signature_rejected():
    issuer_kp = generate_did()
    impostor_kp = generate_did()
    subject_kp = generate_did()
    issuer = CredentialIssuer(issuer_kp)

    vc = issuer.issue(subject_kp.did, "AccreditedInvestorCredential", {"accredited": True})
    # Attacker swaps in a signature from a different key, but keeps the
    # issuer_did field claiming it's still the real issuer.
    vc.signature = impostor_kp.sign(b"unrelated payload")
    assert verify_credential(vc) is False


def test_credential_revocation_blocks_future_verification():
    issuer_kp = generate_did()
    subject_kp = generate_did()
    issuer = CredentialIssuer(issuer_kp)
    revocation = CredentialRevocationRegistry()

    vc = issuer.issue(subject_kp.did, "AccreditedInvestorCredential", {"accredited": True})
    assert verify_credential(vc, revocation) is True

    revocation.revoke(vc.id)
    assert verify_credential(vc, revocation) is False


def test_credential_expiry():
    import time

    issuer_kp = generate_did()
    subject_kp = generate_did()
    issuer = CredentialIssuer(issuer_kp)

    vc = issuer.issue(subject_kp.did, "TestCred", {"x": 1}, validity_seconds=0.05)
    assert verify_credential(vc) is True
    time.sleep(0.1)
    assert verify_credential(vc) is False
