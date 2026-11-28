# Independence of the discovery labels: plan (post-registration)

Written and committed on 2026-11-29, **before** any run.
This is a post-registration analysis. It is not part of the pre-registered study in
`docs/PREREGISTRATION.md`. The pre-registered results (H9 and H10 refuted) stay as they are.

## Why

RQ1 is scored against 1,000 labels from two sources (`docs/LABELLING.md`):

- **800 bytecode labels** (8 surfaces), decided mechanically by function IDs in the deployed code;
- **192 hand labels** (6 surfaces, one per distinct code), made by the AI assistant that also wrote the
  discovery rules. These are not independent of the system.

The planned 40-row human check (`data/labels_check_blank.csv`) was not done and will not be done. It is
reported as not done. Nobody else fills it in: a second pass by an AI assistant would not be independent.

Two questions: (A) How much of the RQ1 result rests on the hand labels? (B) Do the hand labels agree with
an independent, mechanical reading of the deployed code, where one is possible?

## Ground rules

1. No code in `src/` changes. The script lives in `tools/`. We record the `src/` and `kb/` fingerprints.
2. No API calls. Only committed files are read: `data/labels.csv`, `data/labels_manual.csv`,
   `data/code_groups.csv`, `data/q1_raw.json`, `results/discovery/inventory_rules.json` and
   `results/discovery/inventory_llm.json` (the frozen H10 output).
3. The mechanical check below is fixed now and is not changed after it is compared with the labels.
4. Disagreements are listed, not settled. Everything is reported, whatever the result.

## A. Scores by label source

Precision, recall and F1 of the frozen rules and of the frozen language-model classifier, separately for
the bytecode labels and for the hand labels, per token (100) and per distinct code (32). Scoring uses the
frozen `score()` function.

## B. Mechanical check of signature verification in the deployed code

Signature checks run through fixed addresses called from the contract code: `ecrecover` at 0x01, the P-256
verifier at 0x100 (RIP-7212) and the BLS12-381 functions at 0x0b to 0x11 (EIP-2537).

Rule, fixed now: read the deployed code (the implementation's code for a proxy, otherwise the token's).
Step through the instructions. A target counts as **called** if a `PUSH` of the target address is followed,
within the next three instructions, by `STATICCALL` or `CALL`, and the instructions in between are only
`GAS`, `PUSH`, `DUP` or `SWAP`.

Compared, per distinct code (32):

| Mechanical result | Hand labels compared |
|---|---|
| 0x01 called | `ecrecover_direct` or `ecdsa_library` present (both compile to a call to 0x01) |
| 0x100 called | `p256_verifier` |
| 0x0b–0x11 called | `bls_precompile` |

Reported: the 2x2 table, raw agreement and Cohen's kappa (frozen `cohen_kappa()`), and every disagreement
with its token and code offset. The same comparison is made for the rules' predictions. The other three
hand-labelled surfaces (`external_compliance_module`, `signed_parameter_update`, and the split between direct
and library calls) cannot be checked this way; that is reported as a limitation.

## Outputs

- `tools/labels_independence.py`
- `notebooks/labels_independence.ipynb`, the run copy and a cropped screenshot in `notebooks/runs/`
- `results/exploratory/labels_independence.json` and `.md`
- Manuscript: the RQ1 and H10 results reported by label source; the direction of the possible bias stated
  (labels written by the rules' author favour the rules); the mechanical check; the 40-row check reported
  as not done.
