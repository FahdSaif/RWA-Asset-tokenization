# Negative tests of the explanation checks: plan (post-registration)

Written and committed on 2026-11-28, **before** any run.
This is a post-registration analysis. It is not part of the pre-registered study in
`docs/PREREGISTRATION.md`. The pre-registered results (H12 confirmed, H13 refuted) stay as they are.

## Why

All 781 template sentences passed the explanation checks (H12). But the checks were only ever shown
correct sentences. The faithfulness check (`faithful()` in `src/qamp/explain.py`) tests that every
number and date in a sentence appears among the values of what it cites. It does not test meaning, and
its own comment says it does not catch two valid values swapped. This analysis asks: **which kinds of
wrong sentence do the frozen checks reject, and which do they let through?**

## Ground rules

1. No code in `src/` changes. The test script lives in `tools/`. We record the `src/` and `kb/`
   fingerprints before and after.
2. The 781 sentences are rebuilt exactly as in the frozen explanation run (same data, rules, plan seeds
   and evidence). The run must reproduce 781 sentences that all pass, or it stops.
3. No API calls and no randomness, except where stated, with a fixed seed (20261128).
4. Everything is reported, whatever the result.

## Wrong sentences (one kind of error per sentence)

Each wrong sentence keeps its citations unless the error is about the citation.

| ID | Error | How it is made | Applies to |
|----|-------|----------------|------------|
| N1 | Value changed to one not in the cited facts | add 1 to the first year or number | sentences with a value |
| N2 | Two valid values swapped | swap the first two different values in the sentence | sentences with two different values |
| N3 | Valid value in the wrong place | replace a value with another value from the same rationale's facts | sentences with a value |
| N4 | Statement reversed | fixed word swaps, e.g. "is disallowed" → "is allowed", "can be attacked" → "cannot be attacked", "must remain" → "need not remain", "could not be read" → "could be read" | sentences with one of these phrases |
| N5 | Wrong regulation named | "NIST IR 8547" → "the EU AML directive" | deadline sentences |
| N6 | Unsupported reason added | append ", because the issuer asked for it" before the citation | every sentence |
| N7 | Right citation, wrong claim | replace the sentence's citation with another citation from the same rationale | sentences whose rationale has another citation |
| N8 | Wrong deadline date | shift the year of the deadline date by −2 | deadline sentences |

Control: the 781 unchanged sentences (to count false rejections).

## Checks compared

- **Frozen checks:** citation validity and faithfulness, as used for H12.
- **Strict check (new, in `tools/` only):** rebuild the anchor's rationale with the frozen template from
  the same plan, rules and evidence, and accept a sentence only if it matches a rebuilt sentence exactly. Also applied to the 821
  sentences the language model wrote in the frozen H13 run (from `results/explain/llm_log.jsonl`, no new
  calls), to show its cost: it rejects any rewording.

## What we measure

- For each error type: number of wrong sentences, and the share rejected by each check.
- False rejections of the 781 correct sentences, for each check.
- Share of the 821 reworded sentences accepted by the strict check (frozen checks: 55.4%).

## Outputs

- `tools/explain_negative_tests.py`
- `notebooks/explain_negative_tests.ipynb`, the run copy and a cropped screenshot in `notebooks/runs/`
- `results/exploratory/explain_negative_tests.json` and `.md`
- Manuscript: the check is described as what it is (values and dates traced to their sources), with its
  measured blind spots, in the results, the limitations and the supplementary file.
