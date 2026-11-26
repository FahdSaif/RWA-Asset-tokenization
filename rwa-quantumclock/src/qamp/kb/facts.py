"""Fixed lists of algorithms."""
# Broken by a large quantum computer (Shor's algorithm).
QUANTUM_VULNERABLE_ALGORITHMS = frozenset({
    "secp256k1-ecdsa", "p256-ecdsa", "ed25519", "eddsa", "schnorr", "frost-schnorr", "bls12-381",
    "rsa", "ecdh", "pedersen-dlog",
})
POST_QUANTUM_ALGORITHMS = frozenset({"ml-dsa-44", "ml-dsa-65", "ml-dsa-87", "slh-dsa", "fn-dsa", "ml-kem-768"})
