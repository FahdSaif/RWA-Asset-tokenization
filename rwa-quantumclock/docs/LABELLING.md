# RQ1 labelling protocol (ground-truth cryptographic inventories)

**Unit.** A pair (token address, surface type). Surface types are the keys of `RULES` in
`src/qamp/discovery/classify.py` (for example `eip2612_permit`, `erc2771_forwarder`, `access_control_roles`,
`ecrecover_direct`, `upgradeable_proxy`, `external_compliance_module`, `controller_multisig`).

**Material.** For each token in `data/sample_tokens.txt`: the verified source in `data/sources/` (token and
implementation) and the Etherscan contract page. Annotators do **not** see QAMP's output.

**Rule.** `present = 1` if the deployed code (implementation for a proxy) accepts a public-key signature, or delegates
authority to a key, through that surface; `0` if not. An inherited library function that can never be reached still
counts as present if it is externally callable. Record the file and line (or the controller address) as evidence.

**Procedure.**
1. Surfaces with a function selector are labelled objectively from deployed runtime bytecode (planned for v0.2).
   You label the remaining pairs twice, at least two weeks apart, in `data/labels_A.csv` and `data/labels_B.csv`
   (template: `data/labels_template.csv`), without looking at the first pass. A colleague may act as second annotator
   instead (optional, stronger).
2. Compute agreement: `python -c "from qamp.discovery.cbom import read_labels, cohen_kappa; print(cohen_kappa(read_labels('data/labels_A.csv'), read_labels('data/labels_B.csv')))"`.
   Report Cohen's kappa in the paper (intra-rater if you labelled both passes).
3. Adjudicate disagreements together; write `data/labels.csv` with a `notes` column explaining each resolution.
4. Commit all three files **before** running `discover --labels`.
