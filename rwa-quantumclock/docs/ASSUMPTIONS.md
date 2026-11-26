# Assumptions and limitations

Every value below enters the model. "Status" says whether it is observed, sourced, or assumed; assumed values are
recorded in every run and should be varied in the sensitivity analysis or replaced by on-chain observations
(no interviews or questionnaires are used; decision of 2026-11-25).

| Item | Value | Status | Where | How it will be replaced or varied |
|---|---|---|---|---|
| Sample | 25 Etherscan "Real World Assets" tokens, top by market cap, 2026-11-08 | observed | rwa-threatlab census | extended to 100 (RUNBOOK step 2) |
| Value at risk | market cap shown by Etherscan, summed over tokens an anchor controls | observed (snapshot) | `data.py` | re-read at extraction |
| Controllers | EIP-1967 admin, owner/defaultAdmin, multisig threshold, timelock delay | observed | census | role members added by the notebook |
| Role holders | one unobserved anchor per token with compliance or mint/burn capabilities | assumed | `data.py` | observed members (notebook) |
| Key exposure | unknown → treated as exposed (KB rule EXP-KEY-UNKNOWN) | assumed, conservative | `kb/30_exposure.yaml` | EOA nonce > 0; Safe: exposed owners ≥ threshold |
| Algorithm | secp256k1 ECDSA for all EVM keys | observed (EVM) | `data.py` | source scan can add P-256 / BLS |
| Renewal calendar | every 4 quarters, phase from a hash of issuer group and role | **assumed** until the notebook runs | `data._calendar_for` | observed key-change cadence, ≥ 3 change days (`observed.calendars_from_events`); documented policies in `data/calendars.csv` |
| Migration time | EOA 1 quarter; multisig, timelock, unobserved 2 quarters | **assumed** | `data._defaults` | not observable on-chain (the chain shows the final transaction, not the preparation); sensitivity |
| Execution deviation | {−1, 0, +1} quarters with p = (0.15, 0.55, 0.30) | **assumed** (as in the authors' IJPM model) | `scenarios.py` | sensitivity |
| Capacity | 2 concurrent migrations per issuer group | **assumed** until the notebook runs | `PlanParams.capacity` | most anchors an issuer changed in one quarter (`observed.capacity_from_events`); sensitivity 1-3 |
| Issuer group | tokens sharing a controller (zero address excluded) + name rule | observed + **assumed** name rule | `observed.issuer_groups` | — |
| Migration cost | USD 1m × cost units (1-2.0), falling 10% a year | **assumed** | `PlanParams` | sensitivity |
| CRQC arrival | Weibull through GRI 2025: 28-49% within 10 y, 51-70% within 15 y; conditional on none before 2027 | sourced + modelling choice | `scenarios.py` | shift −2 y (H8); fixed low/high interpretation |
| Attack hazard | 1.0 per year once a window is open | **assumed** | `LossParams` | sensitivity 0.25-4 |
| Hidden-key weight | 0.25 (on-spend window only) | **assumed** | `LossParams` | sensitivity |
| Record value ρ | 0.002 × value per year of repudiable records | **assumed** | `LossParams` | sensitivity |
| Retention | 5 y (FATF R.11, EU AMLD Art. 40), 6 y (SEC 17a-4(a)) | sourced | `kb/20_retention.yaml` | — |
| Deadlines | deprecated after 2030, disallowed after 2035 (NIST IR 8547 final); G7 2030-32 example, non-binding | sourced | `kb/10_standards.yaml` | — |
| Jurisdictions | US and EU for all anchors | **assumed** | `kb.engine.anchor_facts` | issuer documentation |
| Bridged instances (RQ3) | top-6 anchors by value get a second instance ("l2"), value split 0.7/0.3 | **synthetic** until the notebook runs | `evaluate.run_guard` | same address and symbol on other chains, value share by totalSupply (`observed.topology_from_raw`); bridges between instances assumed |

## Limitations to state in the paper

* The planner optimises a stated loss model; its absolute dollar figures are not forecasts of losses.
* The guard is a bounded model check of an abstraction (one forged position, one anchor component), not a
  verification of any bridge.
* The census is a snapshot of one chain; role-based control was not readable before the notebook.
* Development results showed that, under the assumed calendars and capacity, timing-aware planning differs little
  from as-soon-as-possible scheduling (see results/dev). Whether that holds with observed calendars is an open
  empirical question, which is why the calendars must be observed, not tuned.
* HNDL (harvest now, decrypt later) on off-chain KYC channels is described but not modelled (no data).
* No human evaluation of the explanations' usefulness (no assessor study): RQ4 uses automatic citation-validity and
  counterfactual-consistency checks.
* RQ1 labels not decidable from bytecode come from one annotator (intra-rater agreement reported) unless a colleague
  acts as second annotator.
* Instances deployed at a different address on another chain are not found (same-address rule).
* Bytecode labels can contain false positives (a 4-byte constant that equals a selector) and miss functions reached
  through non-standard dispatch (for example diamond proxies).
* Faithfulness checks values, not their roles: swapping two supported values in a sentence is not detected.
