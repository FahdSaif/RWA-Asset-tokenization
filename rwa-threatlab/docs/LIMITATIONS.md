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
* **The model checker is tiny** (at most 34 reachable states per search in the original model, and a few hundred in the scaled version). It checks that the paper's trees and
  mitigations are mutually consistent in a stated abstraction; it does not verify this code or any deployment.
  `E2` (misclassification) and the privacy branch are outside its reachability semantics.
* **Most data is synthetic** (see `DATA.md`). The generators are realistic in shape (heavy-tailed gaps, Zipf-concentrated
  jurisdictions) but are not calibrated to any real system; read the boundaries and trends, not the absolute rates. Only the
  real-trace experiments use real data: H12, H13 and H16 (OFAC change files, order of events only) and H14 (the inter-arrival times of
  one token's transactions, one window; the off-chain events an attacker would correlate with remain simulated). H15 was not run.
* **The fuzzer explores only the action space its author wrote,** and its oracle of truth is the author's model of legal
  eligibility. Its instrument was corrected three times after seeing results (`FINDINGS.md`, section B).
* **Risk ratings are ordinal.** They were first scored by the authors and then by four assessors (`docs/irr/`; agreement is high
  for some factors and weak for others, see `docs/results/irr.md`). The scope scores of D1 to D3 were revised post-hoc
  (`docs/RATINGS_REVISION.md`); the original ratings are retained in `risk.py`. See also the sensitivity analysis and the paper's
  Section 6.3.
* **P7 (state restore / hard fork) is deliberately not mediated** by the Gateway: it is a governance and social-consensus
  matter outside the runtime (paper Table 1).

Do not use this code to protect real assets.
* **Real-trace experiments are partial.** OFAC entry identity is a heuristic (the archive has no stable id; alias rows count as
  separate entries). The replay keeps the real order of events but not their real time gaps, so lag windows are tested in
  compressed time. Revocations, participants and credentials remain synthetic. The timing experiment replaces only the
  inter-arrival process; the off-chain event pairing is still assumed. One bridge route and one token series are single
  samples, not a survey.
* **Oracle independence is limited.** The second oracle (`oracle_independent.py`) is separate code written from
  `docs/ORACLE_SPEC.md`, but by the same team that wrote the fuzzer, and it reads sanction/delist/revoke events from the
  fuzzer's own action log. A third implementation by someone who has not read the fuzzer is recommended.
* **The scaled model check is still small** (at most a few hundred states: one asset unit, one exogenous event). A real model
  checker with several assets and concurrent events is future work.
