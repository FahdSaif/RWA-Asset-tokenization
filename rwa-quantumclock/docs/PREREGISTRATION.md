# Pre-registration (DRAFT for the authors' approval)

Status: **draft**. Not yet registered. To be reviewed with the supervisors, frozen (tag `qamp-v1.0-frozen`), archived and
registered on OSF before the held-out run.

## 1. Questions

* RQ1 How accurately does a knowledge-grounded discovery module inventory the signature surfaces of tokenised-asset
  contracts, with rules alone and with an LLM classifier?
* RQ2 Does timing-aware planning (decision windows at renewal boundaries) reduce realized cost (expected exposure loss
  plus migration spend) relative to common policies and recent readiness-scoring approaches?
* RQ3 Does independent migration of bridged instances break compliance claims, and does the model-checked guard prevent it?
* RQ4 Are the system's rationales faithful: does every sentence cite an existing fact that supports it, and do rationales
  change consistently when a fact changes? (Automatic checks; no assessor study.)

## 2. Hypotheses and decision rules (fixed in `src/qamp/hypotheses.py`)

| ID | RQ | Hypothesis | Prediction / decision rule | Source of the prediction | Experiment |
|---|---|---|---|---|---|
| H1 | RQ2 | Timing-aware stochastic planning beats every list baseline. | QAMP-stochastic has lower realized cost than each of the six list baselines (paired sign-flip test on the mean, Holm, p < 0.01). | design claim of the paper | `main` |
| H2 | RQ2 | Planning with a pessimistic execution time is more robust than stochastic planning. | QAMP-pessimistic has lower realized cost than QAMP-stochastic (p < 0.01). | authors' project-governance paper (pessimistic execution time most robust) | `main` |
| H2b | RQ2 | Among deterministic planners, a pessimistic margin beats the expected execution time. | QAMP-pessimistic cheaper than QAMP-expected (p < 0.01). | authors' project-governance paper | `main` |
| H3 | RQ2 | Ignoring renewal boundaries costs value (the decision-window effect). | QAMP without windows (plans as if every quarter were a boundary) costs more than QAMP (p < 0.01). | decision-window theory | `main` |
| H4 | RQ2 | With renewals every quarter, timing-aware planning gives no advantage over ASAP. | On period-1 calendars, QAMP and ASAP differ by < 0.1% or not significantly (p >= 0.05). | authors' project-governance paper (alignment benefit disappears with refundable commitments) | `period1` |
| H5 | RQ2 | Timing-aware planning closes most of the gap to perfect foresight. | QAMP closes at least 50% of the cost gap between ASAP and the oracle. | authors' project-governance paper (renewal-dated gates captured 83% of ideal value) | `main` |
| H6 | RQ3 | Independent planning of bridged instances breaks its own protection claim; the guard prevents it. | At least one mixed-state violation without the guard, none with it, and the independent planner underestimates its realized loss by at least 10%. | authors' bridge composition result | `guard` |
| H7 | RQ3 | Guarded planning is cheaper in realized cost than independent planning. | Independent planning costs more than guarded planning (p < 0.01). | design claim | `guard` |
| H8 | RQ2 | H1 holds when the CRQC timeline is two years earlier. | Same as H1 under shift_years = 2. | robustness | `accelerated` |
| H11 | RQ2 | Timing pays when commitments are long and capacity is tight. | With 8-quarter renewals and one migration at a time per issuer, QAMP is at least 10% cheaper than ASAP (p < 0.01). | decision-window theory; informed by the exploratory pilot grid (results/dev_sensitivity) | `tight` |
| H9 | RQ1 | Rules-based discovery from ABI and verified source finds the signature surfaces. | Overall recall >= 0.90 against the adjudicated labels. | design claim | `discovery` |
| H10 | RQ1 | A knowledge-grounded LLM classifier improves on rules alone. | LLM F1 > rules F1 with no more than 5% of entries dropped for invalid citations. | design claim | `discovery` |

Primary test for differences in realized cost: two-sided paired sign-flip permutation test on the mean difference per
evaluation scenario (20,000 sign flips), Holm correction across the comparisons of one experiment, alpha = 0.01. The
mean is tested because the objective is an expectation and losses are heavy-tailed. Secondary (reported, not decisive):
Wilcoxon signed-rank (medians), bootstrap 95% CIs of the mean difference.

## 3. Design

* Data: the sample in `data/sample_tokens.txt` at tag `qamp-q1-plan`; observations from `notebooks/Q1_fetch_anchor_facts.ipynb`;
  observed governance cadence and capacity (v0.2) where the chain shows them; documented defaults otherwise.
* No interviews, questionnaires or outside participants.
* Planning scenarios 20,000; evaluation scenarios 2,000; oracle on the first 200 evaluation scenarios.
* Seeds: held-out base 50000 (`config.HELD_OUT_SEED_BASE`): planning base+1, evaluation base+2, guard base+11/base+12.
  These seeds have not been used.
* Experiments: `main` (all policies and ablations), `period1` (all calendars renew every quarter), `accelerated`
  (CRQC two years earlier), `tight` (8-quarter renewals, capacity 1), `guard` (synthetic topology: top-6 anchors by value bridged to a second instance, value 0.7/0.3).
* Command: `python -m qamp experiments --held-out --frozen-commit <sha>`; outputs committed unchanged.

## 4. Disclosure of the development pilot

The hypotheses were drafted after a development run on development seeds (base 0) with the 25-contract census and the
assumed calendars (`results/dev/`). Its outcomes, which are **not evidence**:

| ID | Development outcome |
|---|---|
| H1 | REFUTED |
| H2 | REFUTED |
| H2b | INCONCLUSIVE |
| H3 | REFUTED |
| H4 | CONFIRMED |
| H5 | REFUTED |
| H6 | CONFIRMED |
| H7 | CONFIRMED |
| H8 | REFUTED |
| H11 | CONFIRMED (36% cheaper than ASAP; formulated after the exploratory grid) |
| H9 | PENDING DATA |
| H10 | PENDING DATA |

Main observations of the pilot: under the assumed annual calendars and capacity, QAMP was significantly cheaper than
the deadline-driven, annual-review and Mosca policies but not than as-soon-as-possible scheduling (difference about
USD 0.5m on about USD 306m); the pessimistic-margin planner was worse than the stochastic one (the reverse of the
authors' earlier project-governance result); the guard removed all mixed-state violations. An exploratory grid
(`results/dev_sensitivity/`) showed that the advantage over ASAP grows with the renewal period and shrinks with
capacity: about 20-24% with annual renewals and capacity 1, 34-39% with two-yearly renewals and capacity 1, and no
significant difference with half-yearly renewals or capacity 2-3.

## 5. Decisions the authors must take before freezing (record each in section 6)

1. Keep H1, H3 and H5 as stated (theory-derived; the pilot suggests they may be refuted) or revise them. Either is
   legitimate if recorded with its reason before the held-out run; revising them *to match the pilot* must be said so.
2. Whether observed calendars and capacities replace the defaults for the held-out run (recommended: yes, for every
   anchor where the chain shows a rotation history).
3. The LLM model name and version for H10.
4. Whether to keep H11. It follows from the decision-window theory, but it was formulated after the exploratory grid
   (`results/dev_sensitivity/sensitivity.md`) showed the effect on development seeds; say so if it is kept.
5. Whether to add the sensitivity grid (capacity 1-4, hazard 0.25-4, cost decline 0-20%) as exploratory (recommended)
   or confirmatory.

## 6. Addenda

(empty)
