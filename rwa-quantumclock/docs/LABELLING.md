# RQ1 labelling protocol (the true answers for discovery)

RQ1 asks: how well does QAMP find the places where a token's code trusts a signature or a key? To score it, we need
the true answer for each token and each kind of place ("surface"). This page says how those answers are made.

## Who decides which surface

| Surfaces | Decided by | Why |
|---|---|---|
| `eip2612_permit`, `eip712_domain`, `erc2771_forwarder`, `erc1271_contract_signature`, `access_control_roles`, `enumerable_roles`, `upgradeable_proxy`, `ownable_admin` | **the deployed bytecode** (`python -m qamp facts` → `data/labels_bytecode.csv`) | Each has a fixed function ID that is either in the code or not. No judgement needed. |
| `external_compliance_module`, `signed_parameter_update`, `ecrecover_direct`, `ecdsa_library`, `p256_verifier`, `bls_precompile` | **a person reading the verified source** (you, twice) | These cannot be read reliably from bytecode. |
| `controller_eoa`, `controller_multisig`, `controller_timelock` | **chain data**, and **not scored** | Discovery reads the same chain data, so scoring them would be circular. They are reported as "observed, not inferred". |

## Changes to this protocol (2026-11-27, before any hand label was made)

1. **`ownable_admin` moved to the bytecode labels.** Present if the code contains `owner()` or
   `transferOwnership(address)`. Before, it was to be labelled by hand.
2. **The three controller surfaces are no longer scored**, for the reason in the table above.
3. **One label per distinct source code.** 100 tokens use only 32 distinct verified sources (for example, 44 Ondo
   tokens share one, 20 Backed tokens another). You label the first token of each group; `python -m qamp labels`
   copies the label to every token with identical code (`data/code_groups.csv`) and says so in the notes column.
   Results are reported both per token (100) and per distinct code (32), so the large groups cannot hide errors.

With these changes, each pass is **192 rows** (32 codes × 6 surfaces) instead of 1,000.

## What each hand-labelled surface means

Mark `present = 1` if the **deployed code** (the implementation, for a proxy) has an externally callable path that
does the following; otherwise `0`. Code that is only in comments does not count. Library code that is compiled in and
can be called does count.

| Surface | Present when the contract… |
|---|---|
| `external_compliance_module` | asks another contract whether a transfer or holder is allowed (for example a compliance or identity registry) |
| `signed_parameter_update` | accepts a signed message to change a setting such as a price, rate or limit |
| `ecrecover_direct` | calls `ecrecover` itself to check a signature |
| `ecdsa_library` | checks a signature through a library (for example OpenZeppelin `ECDSA.recover` or `SignatureChecker`) |
| `p256_verifier` | checks a P-256 (secp256r1, passkey) signature |
| `bls_precompile` | checks a BLS signature |

Write the file and line as evidence (for example `sources/0x96f6….impl.sol.txt:123`). Use `notes` for anything
unsure.

## How to do it

1. **Do not look at QAMP's discovery output** before or while labelling.
2. Copy `data/labels_sheet_blank.csv` to `data/labels_A.csv`. Open it in Excel or Numbers.
3. For each row, open the `source_file` (in `data/`, or on GitHub) and fill in `present` (1 or 0), `annotator` (A),
   `evidence` and, if needed, `notes`.
4. **At least two weeks later**, without opening `labels_A.csv`, do the same again from a fresh copy of the blank sheet
   into `data/labels_B.csv` (annotator B). A colleague may do pass B instead; that is stronger but optional.
5. Agreement between the passes:
   `python -c "from qamp.discovery.cbom import read_labels, cohen_kappa; print(cohen_kappa(read_labels('data/labels_A.csv'), read_labels('data/labels_B.csv')))"`.
   Report Cohen's kappa (intra-rater if you did both passes).
6. Settle each disagreement and note how in `notes`. Save the result as `data/labels_manual.csv`.
7. Run `python -m qamp labels` (merges bytecode and hand labels into `data/labels.csv`). Commit all label files
   **before** running `python -m qamp discover --labels data/labels.csv`.
