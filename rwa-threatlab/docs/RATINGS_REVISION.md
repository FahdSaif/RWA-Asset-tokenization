# Post-hoc revision of three scope scores (after the inter-rater study)

**Status: post-hoc.** This revision was made after the inter-rater data (`docs/irr/scores_R1-R4.csv`) were available. It is not part
of the pre-registered hypotheses (`docs/PREREGISTRATION.md`). The original ratings in `src/rwa_threatlab/risk.py` (a frozen file)
are unchanged and remain the "as first rated" table; the revised table is computed by `src/rwa_threatlab/risk_revised.py`.

## What changed

The assessors' largest difference from the authors' ratings was the scope factor (G1) of the privacy scenarios D1 to D3. In the
original table the scope of the compliance scenarios (A1/A2, A3, B1, B3) was scored by the reach of the compromised component,
whereas D1 to D3 were scored per affected participant. The two readings were mixed. One rule is now applied to all scenarios:

> **G1 (scope).** The number of participants, transactions or assets that one attacker holding the capability described by the
> scenario can affect (the reach of the attack path, not the number of victims of a single execution). 3 = every participant or
> asset; 2 = the participants or assets served by one component, issuer or chain; 1 = a single participant or transaction.

Exactly three scores change. No other factor of any scenario changes (checked by `tests/test_risk_revised.py`).

| Scenario | Scope before | Scope after | Reason |
|---|---|---|---|
| D1 Timing and value correlation | 1 | 3 | a passive observer can correlate every participant |
| D2 Trail-granularity leakage | 1 | 3 | the Trail is readable by anyone and every entry carries the matched sub-rule |
| D3 Issuer-linkage deanonymisation | 1 | 2 | a colluding issuer reaches only the credentials it issued (as for C1) |

| Scenario | Before | After |
|---|---|---|
| D1 | Medium (12) | High (20) |
| D2 | Low-Med (9) | Med-High (15) |
| D3 | Low-Med (6) | Low-Med (8) |

A1/A2 is still the only Low residual scenario, and without the trust-anchor floor only B1 changes band. C1 was not changed: its
rating rests on persistence and legal exposure both being scored 3, and lowering either by one level would move it from Medium
(10) to Low-Med (8); the assessors scored both factors lower on average. This is reported as a sensitivity result in the paper.

## Reproduce

```
python scripts/make_revision_outputs.py     # docs/results/ratings_revised.json, irr.json, irr.md
python scripts/make_latex.py                # docs/latex/tab_rerate.tex, tab_irr.tex
```
