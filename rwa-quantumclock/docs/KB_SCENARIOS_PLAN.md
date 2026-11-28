# Knowledge-base scenario analysis: plan (post-registration)

Written and committed on 2026-11-28, **before** any scenario is run.
This is a post-registration analysis. It is not part of the pre-registered study in
`docs/PREREGISTRATION.md`. The pre-registered results, including the negative ones, stay as they are.

## Why

In the frozen run, only two rule conclusions reach the planner: the hard deadline
(2036 Q1 for all 75 anchors, never binding) and the record retention period
(6 years for 57 anchors, 0 for 18). So the frozen run does not show what happens when the
rules change. This analysis asks one question: **if the rules change, does the plan change
in the way the rules say it should, and do the explanations follow?**

## Ground rules

1. No code in `src/` changes. Scenarios are extra YAML rule files only, loaded with the
   existing `load_kb` and `kb_context`. We record the `src/` file hashes before and after.
2. No hypotheses about QAMP being better. We report what changes, including higher costs,
   missed deadlines and wrong explanation wording.
3. Same data, same settings as the held-out run: seed 50,000, 20,000 planning scenarios,
   2,000 evaluation scenarios, compliance-first priority.
4. Every scenario rule uses a source already in the knowledge base and already verified.
   No new references.
5. Everything is reported, whatever the result.

## Scenarios

| ID | What changes | Rule source (already in the KB) |
|----|--------------|---------------------------------|
| S0 | Nothing (frozen knowledge base) | — |
| S1 | Hard deadline 2030-12-31 for compliance-critical anchors | NIST IR 8547 deprecation date, treated as binding |
| S2 | Hard deadline 2032-12-31 for compliance-critical anchors | G7 example timeframe, treated as binding |
| S3 | Hard deadline 2030-12-31 for all quantum-vulnerable anchors | NIST IR 8547 deprecation date, treated as binding |
| S4a | Jurisdictions: EU only | FATF R.11, EU AMLD Art. 40 |
| S4b | Jurisdictions: US only | FATF R.11, SEC 17a-4 |
| S4c | No retention rules | — |
| S5 | EU retention extended to 10 years (the longest period wins) | EU AMLD Art. 40 (further period of up to 5 years) |
| S6 | S3 with capacity 1 per issuer | as S3 |

S1–S3 and S5 are "what if a regulator made this binding" cases. They are not claims that
these rules apply today.

We also report one descriptive count with no run (D1): the missing-evidence flags
(exposure not observed 60, discovery incomplete 50) and the anchors they affect.

## What we measure

- **M1** Anchors whose start quarter differs from S0.
- **M2** Deadline misses, in total and per issuer.
- **M3** Mean realised cost on the evaluation scenarios, and the paired difference from S0
  with a 95% interval.
- **M4** Price of compliance: compliance-first cost minus cost-first cost.
- **M5** Value whose keys take effect by 2030 and by 2032.
- **M6** Rules fired per anchor, and which rule decided each deadline and retention value.
- **M7** Lines changed in `src/` (expected 0).
- **M8** Explanation checks: validity and faithfulness scores, and how many sentences cite a
  scenario rule.

## Checks we expect to pass (correctness, not superiority)

- S1, S3: every affected anchor takes effect by 2031 Q1, or is counted as a miss.
- S4c: retention is 0 for every anchor.
- S5: EU record-signing anchors get 10 years; others are unchanged.
- S6: `diagnose()` reports the issuers that cannot fit, or the planner counts the misses.

## Known limitation, recorded now

The explanation template words every hard deadline as "disallowed ... under NIST IR 8547",
whichever rule set it. In S2 the sentence will cite the right rule ID but name the wrong
source. We will count and report these sentences (M8). We will not change the template in
this analysis.

## Outputs

- `tools/kb_scenarios.py`, `kb_scenarios/` (one folder of rule files per scenario)
- `notebooks/kb_scenarios.ipynb`, the run copy and a cropped screenshot in `notebooks/runs/`
- `results/exploratory/kb_scenarios.json` and `.md`
- A section in the supplementary file and a short subsection in the paper, both labelled
  post-registration.
