# Runbook: from the prototype to the pre-registered run

Steps that need you are marked **[you]**. Nothing here pushes anything anywhere on its own. No step involves
interviews, questionnaires or outside participants.

## 1. Put the folder in the repository [you]

1. Create `qamp/` at the repository root, beside `rwa-threatlab/`, and upload the files.
2. `cd qamp && python -m pip install -e ".[dev]" && python -m pytest -q`. All tests must pass.
3. Do not modify `rwa-threatlab/`: QAMP imports its census code. The published tag `v1.8-paper` and
   `v1.9-cs-submission` must keep reproducing the earlier papers.

## 2. Fix the sample, then extract Ethereum data [you]

> **Do not run the notebook yet.** Version 0.2 extends it (governance events, bytecode, other chains) so that it is
> run once. You can already do step 2.1 (fix the sample) and commit it.

1. Decide the extension of the sample **before fetching**. The rule is written at the top of `data/sample_tokens.txt`:
   append rows 26-100 of the Etherscan "Real World Assets" token page sorted by market cap, in the order displayed, no
   exclusions, with the date seen. Commit, then tag the commit `qamp-q1-plan`.
2. Open `notebooks/Q1_fetch_anchor_facts.ipynb` in Google Colab. Check that `REPO_REF = "qamp-q1-plan"`.
   *Runtime, Run all*. Paste a **new** Etherscan key when asked. It reads verified source, proxy slots, owner and
   defaultAdmin, AccessControl role members, and for every controlling address code, nonce, Safe threshold and owners,
   timelock delay. Expect roughly 30-60 API calls per token.
3. Unzip `qamp_q1_data.zip` into `qamp/data/` (gives `q1_raw.json`, `q1_summary.json`, `sources/`). Commit. Delete the
   key on etherscan.io/apidashboard.
4. `python -m qamp facts` checks the digest and writes `data/anchor_facts.json` (key exposure per controller).
   From now on `census`, `plan` and `experiments` use observed exposure and observed role members automatically.

## 3. Calendars and capacity (from on-chain data; no interviews)

Decision (2026-11-25): no interviews or questionnaires. Renewal calendars, execution times and capacity come from
on-chain governance history; what the chain cannot show stays a documented default and is varied in the exploratory
sensitivity grid (`python -m qamp sensitivity`).

* **Planned for v0.2** (extends the notebook before it is run): Safe `AddedOwner` / `RemovedOwner` /
  `ChangedThreshold` and AccessControl `RoleGranted` / `RoleRevoked` events per controller → observed rotation cadence
  (renewal period and phase) and observed execution time; the largest number of key changes an issuer made in one
  quarter → capacity estimate.
* Until then the defaults in `docs/ASSUMPTIONS.md` apply. A manual `data/calendars.csv`
  (`anchor_id,period_quarters,phase_quarter,source`) is still supported for documented public evidence (for example an
  issuer's published key-rotation policy), with `source` = `documented: <URL, date>`.

## 4. RQ1 ground truth: labelled inventories [you]

* **Planned for v0.2:** objective labels from deployed runtime bytecode for every surface that has a function selector
  (`permit`, `isTrustedForwarder`, `isValidSignature`, role functions, upgrade functions).
* You label only the surfaces bytecode cannot decide (for example direct `ecrecover` use in source), following
  `docs/LABELLING.md`: twice, at least two weeks apart, and report intra-rater agreement (Cohen's kappa). A supervisor or
  colleague as second annotator is optional and stronger. Then

```bash
python -m qamp discover --source-dir data/sources --labels data/labels.csv          # rules (H9)
ANTHROPIC_API_KEY=... python -m qamp discover --source-dir data/sources --labels data/labels.csv --llm   # LLM (H10)
```

The LLM run logs every prompt and response to `results/discovery/llm_log.jsonl` (commit it). Pin the model name in
`src/qamp/discovery/classify.py` (`LLMClassifier(model=...)`) before the run and record it in the pre-registration.

## 5. RQ4 explanations: automatic checks (no assessor study)

`python -m qamp plan` writes `results/plan/plan.md`: one rationale per anchor, every sentence cited.
**Planned for v0.2:** automatic metrics instead of human ratings: citation validity (every cited rule, evidence item,
plan decision and guard check exists and supports the sentence) and counterfactual consistency (change one fact, and
the rationale changes accordingly). The absence of a human usefulness study is stated as a limitation.

## 6. Freeze and pre-register [you]

1. Review `docs/PREREGISTRATION.md` with your supervisors (no outside people are involved at any step). Approve or revise the hypotheses **before** the held-out
   run, and record any change and its reason in the addendum section (the development pilot has been run and must be
   disclosed; the held-out seeds have never been used).
2. Commit, tag `qamp-v1.0-frozen`, archive on Zenodo, register on OSF with the tag and commit hash.

## 7. The held-out run (once)

```bash
python -m qamp experiments --held-out --frozen-commit <sha of qamp-v1.0-frozen>
```

Writes `results/held_out/` (results.json, hypotheses.md, main_table.md). Commit as is. Report every hypothesis,
whatever its outcome. Re-running with other seeds or settings after seeing the result is exploratory and must be
labelled as such.

## 8. Anonymised review copy

ESWA review is double-anonymised. For submission, create an anonymised mirror (for example anonymous.4open.science)
of a branch that contains only `qamp/` (and the census files it reads), or a separate clean repository.
