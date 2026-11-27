# Runbook: from the prototype to the pre-registered run

Steps that need you are marked **[you]**. Nothing here pushes anything anywhere on its own. No step involves
interviews, questionnaires or outside participants.

## 1. Put the folder in the repository [you]

1. The folder is `rwa-quantumclock/` at the repository root, beside `rwa-threatlab/` (the Python package inside is
   `qamp`, the system's name in the paper).
2. `cd rwa-quantumclock && python -m pip install -e ".[dev]" && python -m pytest -q`. All tests must pass.
3. Do not modify `rwa-threatlab/`: QAMP imports its census code. The published tag `v1.8-paper` and
   `v1.9-cs-submission` must keep reproducing the earlier papers.

## 2. Fix the sample, then extract the data [you]

1. The sample is fixed **before fetching** (done on 2026-11-26): the 25 census tokens plus the first 75 other tokens on
   Etherscan's "Real World Assets" page sorted by market cap. The pages were saved in Chrome as "Webpage, Single File"
   and converted with `python tools/build_sample.py page1.mhtml page2.mhtml page3.mhtml`, which writes
   `data/sample_tokens.txt` and `data/etherscan_rwa_snapshot_2026-11-26.txt` (every row read, with the SHA-256 of each
   saved page). Commit both, then tag the commit `quantumclock-q1-plan` (pre-release, not latest).
2. Open `notebooks/Q1_fetch_anchor_facts.ipynb` in Google Colab (File → Open notebook → GitHub). Check
   `REPO_REF = "quantumclock-q1-plan"`. *Runtime, Run all*. Paste a **new** Etherscan key when asked. It observes, per
   token: verified source and ABI, proxy slots, owner, defaultAdmin, totalSupply, symbol, AccessControl role members,
   every controlling address (EOA or contract, nonce, Safe threshold and owners, timelock delay), the governance-event
   history, runtime bytecode, and the same address on 12 other EVM chains. Expect about one hour for 100 tokens; if
   the session stops, run Cell 2 again (finished tokens are skipped). Chains your key's plan does not cover are
   recorded as errors: expected, and reported.
3. Unzip `qamp_q1_data.zip` into `rwa-quantumclock/data/` (gives `q1_raw.json`, `q1_summary.json`, `sources/`,
   `bytecode/`). Commit. Delete the key on etherscan.io/apidashboard.
4. `python -m qamp facts` checks the digest and writes `data/anchor_facts.json` (key exposure),
   `data/labels_bytecode.csv` (objective RQ1 labels) and `results/observed/observed_summary.json` (calendars by source,
   issuer capacity, multi-chain instances). From now on `census`, `plan`, `discover` and `experiments` use the extended
   sample and the observations automatically.

## 3. Calendars, capacity and instances (from on-chain data; no interviews)

Decision (2026-11-25): no interviews or questionnaires. Rules, all in `src/qamp/observed.py`:

* **Renewal calendar** of an anchor: with at least 3 days on which its key set changed (Safe owner or threshold
  changes, ownership or admin transfers, role grants and revocations), period = median gap in quarters (1-8) and phase
  = quarter of the last change. Anchors with fewer changes keep the documented default. Alternative for the
  sensitivity analysis: `--calendar-policy lower_bound` (no rotation in two or more years → 8 quarters).
* **Capacity** of an issuer group: the largest number of its anchors whose key set changed within one quarter (1-4);
  groups without changes keep the default.
* **Issuer groups**: tokens that share a controlling address form one group, plus the name rule.
* **Instances on other chains**: code at the same address with the same symbol; value share by totalSupply. Bridges
  between instances are assumed (stated in the paper). RQ3 uses this observed topology when it exists, otherwise the
  labelled synthetic one.
* Documented policies (an issuer's published key-rotation policy) can still be given in `data/calendars.csv`
  (`anchor_id,period_quarters,phase_quarter,source` with `source` = `documented: <URL, date>`); they take precedence.

## 4. RQ1 ground truth [you]

* Surfaces with a function selector are labelled objectively from runtime bytecode (`data/labels_bytecode.csv`,
  written by `facts`).
* You label only the surfaces bytecode cannot decide (`ecrecover_direct`, `ecdsa_library`, `p256_verifier`,
  `bls_precompile`, `external_compliance_module`, `ownable_admin`, `signed_parameter_update`) from the verified source in
  `data/sources/`, following `docs/LABELLING.md`: twice, at least two weeks apart; report intra-rater agreement. A
  colleague as second annotator is optional and stronger. Save the adjudicated result as `data/labels_manual.csv`.
* `python -m qamp labels` merges both into `data/labels.csv` (bytecode wins for its surfaces). Then

```bash
python -m qamp discover --source-dir data/sources --labels data/labels.csv          # rules (H9)
ANTHROPIC_API_KEY=... python -m qamp discover --source-dir data/sources --labels data/labels.csv --llm   # LLM (H10)
```

The LLM run logs every prompt and response to `results/discovery/llm_log.jsonl` (commit it). Pin the model name in
`src/qamp/discovery/classify.py` (`LLMClassifier(model=...)`) before the run and record it in the pre-registration.

## 5. RQ4 explanations: automatic checks (no assessor study)

```bash
python -m qamp explain-check                       # citation validity, faithfulness, counterfactual consistency (H12)
ANTHROPIC_API_KEY=... python -m qamp explain-check --llm   # share of LLM-rephrased sentences that stay grounded (H13)
```

Faithfulness checks that every value in a sentence (quarter, date, number) is supplied by a fact the sentence cites,
no more often than supplied; it does not detect a swap of two supported values (stated as a limitation). The absence of
a human usefulness study is stated as a limitation.

## 6. Freeze and pre-register [you]

1. Record the decisions in `docs/PREREGISTRATION.md` section 6 (no outside people are involved at any step). Approve or revise the hypotheses **before** the held-out
   run, and record any change and its reason in the addendum section (the development pilot has been run and must be
   disclosed; the held-out seeds have never been used).
2. Commit, tag `quantumclock-v1.0-frozen`, archive on Zenodo, register on OSF with the tag and commit hash.

## 7. The held-out run (once)

```bash
python -m qamp experiments --held-out --frozen-commit <sha of quantumclock-v1.0-frozen>
```

Writes `results/held_out/` (results.json, hypotheses.md, main_table.md). Commit as is. Report every hypothesis,
whatever its outcome. Re-running with other seeds or settings after seeing the result is exploratory and must be
labelled as such.

## 8. Anonymised review copy

ESWA review is double-anonymised. For submission, create an anonymised mirror (for example anonymous.4open.science)
of a branch that contains only `rwa-quantumclock/` (and the census files it reads), or a separate clean repository.
