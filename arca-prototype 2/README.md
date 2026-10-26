# ARCA Prototype

A reference implementation of the **AI-Assisted Runtime Compliance Architecture (ARCA)**,
the conceptual architecture proposed in:

> Saifuddin, F., Jadidi, Z., Muthukkumarasamy, V. *"AI-Assisted Runtime Compliance
> Architecture for Tokenized Real-World Assets."* IEEE Access (submitted).

The paper presents ARCA as a conceptual architecture and reports this repository as a
preliminary reference implementation and automated test suite (Sec. VII). It is a
working, tested implementation of all four layers, built to be read alongside the paper
rather than instead of it, and it establishes feasibility at prototype scale only (see
"Scope and limitations" below). See
[`docs/PAPER_TO_CODE_MAPPING.md`](docs/PAPER_TO_CODE_MAPPING.md) for a section-by-section
index into the code.

It is a **research prototype**, not compliance software — see
[Scope and Limitations](#scope-and-limitations) before using it for anything beyond
reproducing or extending the paper's analytical claims.

## What's actually real here, and what's synthetic

Being upfront about this matters more than it usually would, for a repo like this one:

| | Real | Synthetic / simplified, and why |
|---|---|---|
| **Cryptography** | did:key generation (W3C spec-compliant Ed25519), Verifiable Credential signatures, Pedersen commitments, Schnorr NIZK proofs, hash-chained audit log — all real, working elliptic-curve math and hashing, not mocked. | The ZK OR-proof for set membership is a real but hand-rolled Sigma protocol, not a production zk-SNARK circuit. See the limitation note in `arca/layer2_identity/zkp_module.py`. |
| **On-chain layer** | Real, compilable, deployable Solidity (`ComplianceRegistry.sol`, `ComplianceToken.sol`), compiled with `solc` and run on a real (local, in-memory) EVM via `web3.py`. | Not audited, not gas-optimized, and the "governance" owner is a single EOA in the demo rather than a real multisig/governance contract. |
| **Regulatory reference data** | FATF grey/black list — a real, dated, cited snapshot (see `data/README.md`). | Deliberately a *snapshot*, not a live feed — see below for why that's the architecturally correct choice, not a shortcut. |
| **ML risk model** | A real GradientBoostingClassifier, trained and evaluated with real scikit-learn/SHAP code, achieving genuine held-out separation (ROC-AUC ≈ 0.87). | Trained on a *documented synthetic* transaction dataset. Real AML transaction data is confidential and cannot be published here — see `data/README.md`. |
| **Governance / oracle consensus** | Real Ed25519 signature verification, real quorum-counting logic, tested against forged votes and compromised minority providers. | The "participants" are demo keypairs generated in-process, not real institutions. |

## Repository layout

```
arca/
  layer1_intelligence/   # Compliance Intelligence Layer (Sec. V-C)
    jurisdiction_agent.py
    eligibility_agent.py
    risk_scoring_agent.py
    anomaly_detection_agent.py
    crr.py                # Compliance Recommendation Record
  layer2_identity/        # Verification and Identity Layer (Sec. V-D)
    did_registry.py
    verifiable_credentials.py
    zkp_module.py
  layer3_runtime/         # Runtime Enforcement Layer (Sec. V-E)
    models.py             # shared Rule model + predicate evaluator
    rule_registry.py
    transaction_validator.py
    audit_log.py
    evm_bridge.py          # optional on-chain demo (Python <-> local EVM)
    contracts/             # Solidity source + compiled build artifacts
  layer4_governance/      # Asset and Governance Layer (Sec. V-F)
    governance.py
    oracle_network.py
    asset_registry.py
  pipeline/
    end_to_end_demo.py    # wires all 4 layers together (Sec. V-G)
data/                      # see data/README.md for full provenance
notebooks/                 # executed, saved-with-output walkthroughs
scripts/                   # dataset generation, contract compilation, notebook build
tests/                     # pytest suite, including tests/test_threat_model.py
docs/                      # paper-to-code mapping + a Table 3 consistency check
```

## Setup

```bash
python -m venv .venv && source .venv/bin/activate   # optional but recommended
pip install -r requirements.txt
```

That's enough for every layer **except** the on-chain demo. For that, you also need
Node.js (18+):

```bash
npm install
node scripts/compile_contracts.js
```

(`web3.py`'s `EthereumTesterProvider` is a fully local, in-memory EVM — no real network,
testnet, or RPC endpoint is needed for `evm_bridge.py` or the on-chain tests.)

## Running things

```bash
# Regenerate the synthetic training dataset (also happens automatically
# the first time the risk-scoring agent runs, if missing)
python scripts/generate_synthetic_transactions.py

# Run the full cross-layer pipeline demo (Sec. V-G), printed step by step
python -m arca.pipeline.end_to_end_demo

# Run the test suite (82 tests: unit tests per layer, the threat-model suite, and the
# trust-check tests for unauthorized recommendations and false jurisdiction claims)
pytest tests/ -v

# Just the threat-model tests, mapped 1:1 onto paper Sec. VI-B
pytest tests/test_threat_model.py -v

# Just the trust-check tests (agent authorization, issuer-bound jurisdiction proofs)
pytest tests/test_trust_checks.py -v

# Reproduce the cost measurements (validation latency, governance cost, EVM gas);
# needs `npm install && node scripts/compile_contracts.js` first. Writes
# docs/BENCHMARKS.md and docs/benchmark_results.json (about 10 minutes on one core)
python scripts/benchmark_costs.py

# Regenerate the property-mapping (Table 3) consistency check
python docs/property_mapping_check.py
```

Notebooks in `notebooks/` are checked in **already executed** (with saved outputs and
the SHAP/timing plots they generate), so you can read them on GitHub without running
anything. To re-run them yourself:

```bash
pip install jupyter nbformat nbclient
jupyter nbconvert --to notebook --execute --inplace notebooks/01_risk_scoring_model.ipynb
```

## A worked example: what the pipeline actually does

Running `python -m arca.pipeline.end_to_end_demo` walks through one full transaction
lifecycle:

1. **Layer 4 → Layer 1**: the Jurisdictional Regulatory Analysis Agent classifies a
   jurisdiction against the real FATF snapshot.
2. **Layer 1 → Layer 4 → Layer 3**: the agent *proposes* a rule change; it only becomes
   enforceable once a governance quorum signs off, at which point the Rule Registry
   applies it. The agent never writes to the active rule set directly.
3. **Layer 4**: the asset is registered.
4. **Layer 2**: an authorized issuer signs a credential carrying a commitment to the
   holder's jurisdiction; the holder generates a zero-knowledge proof, about that
   issuer-certified commitment, that the jurisdiction is on an allow-list, without
   revealing which one.
5. **Layer 1**: the Eligibility, Risk-Scoring, and Anomaly-Detection agents each evaluate
   the transaction independently and issue a signed Compliance Recommendation Record —
   the risk score comes with a real SHAP-based explanation, not just a number.
6. **Layer 3**: the Transaction Validation Module retrieves the active rules, checks that
   each CRR is signed by a governance-registered agent approved for that determination
   type, verifies that the jurisdiction proof is bound to a credential from an authorized
   issuer, evaluates the combined determination, and produces an accept/reject decision.
7. **Layer 3**: the outcome — and every prior step — is written to a hash-chained,
   tamper-evident audit log.

## Threat model, made executable

Paper Sec. VI-B analyzes four threat classes. `tests/test_threat_model.py` turns each
one into a runnable demonstration:

- **Threat Class I** (Direct Protocol Bypass): a "raw" transaction submitted with zero
  attestations is rejected by the validator — and, on-chain, a `transfer()` call to a
  non-allow-listed address reverts regardless of how it was constructed.
- **Threat Class II** (Stale Rule Exploitation): the test shows *both halves* of the
  paper's own honest analysis — the governance-latency window really is exploitable
  before quorum is reached, and it really does close once quorum completes.
- **Threat Class III** (Fraudulent Credential Presentation): a forged issuer signature,
  a revoked credential, and a post-issuance-tampered CRR are each independently caught
  and rejected. `tests/test_trust_checks.py` extends this with two further cases found
  in review: recommendations signed by a key that is not an approved compliance agent
  (including an approved agent acting outside its role, and a revoked agent), and false
  jurisdiction claims (a self-chosen commitment, a proof about a different value than
  the one the issuer certified, an unauthorized or revoked issuer, and a credential
  issued to someone else), and recommendations about the wrong participant (an eligibility
  or anomaly CRR must name the transaction's sender, so one party cannot borrow another's
  clean result).
- **Threat Class IV** (Oracle Data Manipulation): a single compromised *authorized*
  provider cannot override a majority consensus, and an unauthorized outsider cannot
  manufacture consensus even by submitting multiple reports.

## Cost measurements

`docs/BENCHMARKS.md` reports per-transaction validation latency by stage and by allow-list
size, governance-operation cost (computational only), and EVM gas for the prototype's
contracts against an otherwise identical plain token. They are single-machine prototype
figures, not throughput claims.

## Scope and limitations

Read this before using any of this beyond reproducing the paper's results:

- **Not audited, not production-ready.** The Solidity contracts, the governance model,
  and the credential-revocation scheme are all deliberately minimal reference
  implementations. A real deployment needs a security audit, a real multisig/governance
  contract instead of a single owner key, and a real PKI/issuer-authorization process.
- **The ZK proofs are real but not SNARKs.** `zkp_module.py`'s OR-proof genuinely is a
  zero-knowledge proof — the soundness and (computational) zero-knowledge properties
  hold for the Sigma-protocol construction implemented — but it scales O(n) in allow-list
  size (see `docs/BENCHMARKS.md`). The proof itself shows only that a committed value is
  in the allowed set; the link to an issuer is made outside the proof, by requiring that
  the committed value equal the commitment an authorized issuer signed for the sender
  (`layer2_identity/jurisdiction_binding.py`). That gives issuer binding without
  verifying a signature inside a circuit, which the paper's Sec. V-D describes as the
  production approach and which this prototype does not implement.
- **Who may sign is governed, but the governance is still a simulation.** Compliance
  agents and credential issuers are registered, and revoked, by quorum-signed
  authorizations (`layer3_runtime/role_registry.py`). The Solidity registry is unchanged
  and still uses a single owner key; the quorum logic exists only in the Python layer.
  Eligibility and anomaly CRRs name the participant they evaluated (signed into the
  record) and are ignored unless that participant is the transaction sender. A
  risk-score CRR describes the transaction rather than one participant, so the
  prototype relies on the risk agent computing it from network-observed data; the
  provenance of the features it is given is not verified here.
- **The on-chain demo shows interface equivalence, not protocol-level enforcement.** The
  Solidity token checks compliance inside its transfer function, as token-level standards
  such as ERC-3643 do, so it demonstrates the same mechanism rather than anything
  stronger. The Python validator is the sole code path in the prototype; it is not a
  chain runtime or consensus-level hook.
- **The ML risk model is trained on synthetic data.** See `data/README.md`. Retrain on
  your own institution's data before drawing any conclusion beyond "the architecture
  can carry a real trained model with real explainability."
- **The FATF/regulatory data is a dated snapshot**, not a live feed — by design (see
  `data/README.md`), but you still need to refresh it (or wire up
  `arca/layer4_governance/oracle_network.py` to a live source, per
  `scripts/fetch_regulatory_data.py`) before relying on it for anything current.
- **Table 2's comparative analysis is not re-derived here.** This repo doesn't include
  working implementations of the four alternative architectures the paper compares
  ARCA against — see `docs/PAPER_TO_CODE_MAPPING.md`, "What this repo does not claim."
- **Governance latency is a real, acknowledged residual vulnerability**, not something
  this prototype claims to have solved — see the Threat Class II discussion above and
  in the paper's Sec. VIII-C.

## License

MIT — see [`LICENSE`](LICENSE). Please cite the paper if you use this code; see
[`CITATION.cff`](CITATION.cff).
