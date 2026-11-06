# Limitations (read before relying on this code)

This repository is a **research simulation**, not a production compliance runtime.

* **No real cryptography.** HMAC-SHA256 stands in for digital signatures (verification needs the secret). Threshold
  approval is `t` distinct valid signatures, not FROST, so it does not hide who approved (paper threat T23).
  Selective disclosure is simulated with per-claim signatures; there are no zero-knowledge proofs, and blind issuance
  is an abstraction (the issuer simply never sees the credential id).
* **No blockchain.** "Runtime" means the Python objects in `system.py`. There is no consensus, networking,
  VM or fee model; consensus and cryptographic soundness are assumed, exactly as in the paper's Section 3.4.
* **The conformance suite is bounded testing, not formal verification.** It catches blatant faults and the
  origin-spoofing prefix defect, and scenario `A3b` shows a backdoored build that passes it. The paper's M2 calls for
  formal verification of a real Gateway; that is future work.
* **The model checker is tiny** (at most 34 reachable states per search). It checks that the paper's trees and
  mitigations are mutually consistent in a stated abstraction; it does not verify this code or any deployment.
  `E2` (misclassification) and the privacy branch are outside its reachability semantics.
* **All data is synthetic** (see `DATA.md`). The generators are realistic in shape (heavy-tailed gaps, Zipf-concentrated
  jurisdictions) but are not calibrated to any real system; read the boundaries and trends, not the absolute rates.
* **The fuzzer explores only the action space its author wrote,** and its oracle of truth is the author's model of legal
  eligibility. Its instrument was corrected three times after seeing results (`FINDINGS.md`, section B).
* **Risk ratings are ordinal** and were scored by one assessor; see the sensitivity analysis and the paper's
  Section 6.3.
* **P7 (state restore / hard fork) is deliberately not mediated** by the Gateway: it is a governance and social-consensus
  matter outside the runtime (paper Table 1).

Do not use this code to protect real assets.
