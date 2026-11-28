# Language-model classifier with a larger answer limit: plan (post-registration)

Written and committed on 2026-11-29, **before** any run.
This is a post-registration analysis. It is not part of the pre-registered study in
`docs/PREREGISTRATION.md`. **H10 stays REFUTED**, as decided in the frozen run, whatever this run shows.

## Why

In the frozen H10 run (`docs/steps/08_ai_runs.md`), 85 of 100 answers were cut off at the frozen limit of
2,000 answer tokens, so they could not be read and their entries were dropped. Where answers were complete,
precision matched the rules (0.667 vs 0.670). The question here is: **how well does the same model classify
when its answers are not cut off?**

## Ground rules

1. No code in `src/` changes. The answer limit is already a setting of the frozen classifier
   (`LLMClassifier(max_tokens=...)`). The script lives in `tools/`.
2. **Same model as the frozen run.** The notebook takes, from the models the key can use, the one whose
   SHA-256 fingerprint equals the frozen fingerprint
   (`model-sha256:7d811269d13fd7df0fd2cb573cbd1b11679a1ae347c179b3daf22b12408604c4`). If it is not available,
   the run stops; no other model is used. Temperature 0, as in the frozen code.
3. **Same evidence as the frozen run**: the same findings (ABI, verified source and controllers, as in
   `python -m qamp discover --source-dir data/sources`), the same 100 tokens, the same citation check.
4. The model's name is not printed or saved; every output records only its fingerprint. The API key is
   typed into a hidden prompt, not saved, and deleted from the provider's console after the run.
5. The same network wrapper as the frozen run (retries when the service is busy).
6. Everything is reported, whatever the result.

## Arms

| Arm | Prompt | Answer limit |
|-----|--------|--------------|
| A | the frozen prompt, unchanged | 8,000 tokens |
| B | the frozen prompt with a smaller answer format: each element only `surface`, `algorithm` and `evidence` (no signer, role, note) | 8,000 tokens |

Arm A changes only the limit, so it isolates the cut-off. Arm B also shortens the answers.
One prompt per surface (about 14 times more calls) is not run, for cost; this is reported.

## What we measure

- Answers that could not be read (cut off or not valid JSON), entries kept and dropped, invented citations.
- Precision, recall and F1 with the frozen `score()`, against all labels, the bytecode labels and the hand
  labels, per token (100) and per distinct code (32), next to the rules and the frozen run.

## Outputs

- `tools/llm_rerun.py` and `notebooks/llm_rerun.ipynb`
- Executed notebook and a cropped screenshot in `notebooks/runs/` (Colab output only)
- `results/exploratory/llm_rerun.json` and `.md`, and the prompt-and-answer logs with the model name
  replaced by its fingerprint
- Manuscript: the result reported next to the frozen H10 result, labelled post-registration.
