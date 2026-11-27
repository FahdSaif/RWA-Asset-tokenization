# Pre-registration

Status: **decided 2026-11-27** (section 6). Frozen with the public git tag `quantumclock-v1.0-frozen` before the
held-out run (no OSF registration, D19). No interviews, questionnaires or outside participants are
involved at any step.

## 1. Questions

* RQ1 How accurately does a knowledge-grounded discovery module inventory the signature surfaces of tokenised-asset
  contracts, with rules alone and with an LLM classifier? (Ground truth: objective labels from runtime bytecode where a
  surface has a selector; the author's double-coded labels otherwise.)
* RQ2 When does timing-aware planning (decision windows at renewal boundaries) reduce realized cost (expected exposure
  loss plus migration spend) relative to common policies and readiness-scoring approaches?
* RQ3 Does independent migration of bridged instances break compliance claims, and does the model-checked guard
  prevent it? (Observed multi-chain instances where they exist; otherwise the labelled synthetic topology.)
* RQ4 Are the system's rationales faithful: does every sentence cite an existing fact that supplies its values, do
  rationales change consistently when one fact changes, and can an LLM rephrase them without losing grounding?
  (Automatic checks; no assessor study.)

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
| H11 | RQ2 | Timing pays when commitments are long and capacity is tight. | With 8-quarter renewals and one migration at a time per issuer, QAMP is at least 10% cheaper than ASAP (p < 0.01). | decision-window theory (alignment matters for long, irreversible commitments); informed by the exploratory pilot grid | `tight` |
| H12 | RQ4 | The system's own rationales are faithful to the facts they cite. | Citation validity 1.0, faithfulness >= 0.99 and counterfactual consistency >= 0.95. | design claim (verifiable by construction; reported as a property of the system) | `explanations` |
| H13 | RQ4 | An LLM can rephrase rationales for auditors without losing grounding. | At least 95% of LLM-rephrased sentences keep valid citations and pass the faithfulness check. | design claim | `explanations` |
| H9 | RQ1 | Rules-based discovery from ABI and verified source finds the signature surfaces. | Overall recall >= 0.90 against the adjudicated labels. | design claim | `discovery` |
| H10 | RQ1 | A knowledge-grounded LLM classifier improves on rules alone. | LLM F1 > rules F1 with no more than 5% of entries dropped for invalid citations. | design claim | `discovery` |

Primary test for differences in realized cost: two-sided paired sign-flip permutation test on the mean difference per
evaluation scenario (20,000 sign flips), Holm correction across the comparisons of one experiment, alpha = 0.01. The
mean is tested because the objective is an expectation and losses are heavy-tailed. Secondary (reported, not decisive):
Wilcoxon signed-rank (medians), bootstrap 95% CIs of the mean difference.

## 3. Design

* Data: the sample in `data/sample_tokens.txt` at tag `quantumclock-q1-plan`; observations from
  `notebooks/Q1_fetch_anchor_facts.ipynb` (`data/q1_raw.json`, digest in `data/q1_summary.json`).
* Model inputs from observations (rules in `src/qamp/observed.py`): key exposure; role members; renewal calendars
  (policy `observed_only`: at least 3 key-change days); issuer capacity; issuer groups; multi-chain instances. Documented
  defaults where the chain shows nothing (`docs/ASSUMPTIONS.md`).
* Planning scenarios 20,000; evaluation scenarios 2,000; oracle on the first 200 evaluation scenarios.
* Seeds: held-out base 50,000 (`config.HELD_OUT_SEED_BASE`): planning base+1, evaluation base+2, guard base+11/base+12.
  These seeds have not been used.
* Experiments: `main` (all policies and ablations), `period1` (all calendars renew every quarter), `accelerated`
  (CRQC two years earlier), `tight` (8-quarter renewals, capacity 1), `guard` (observed topology if any, else
  synthetic), `explanations` (H12; H13 with `explain-check --llm`).
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
| H11 | CONFIRMED |
| H12 | CONFIRMED |
| H13 | PENDING DATA |
| H9 | PENDING DATA |
| H10 | PENDING DATA |

Main observations of the pilot: under the assumed annual calendars and capacity, QAMP was significantly cheaper than
the deadline-driven, annual-review and Mosca policies but not than as-soon-as-possible scheduling (difference about
USD 0.5m on about USD 306m); the pessimistic-margin planner was worse than the stochastic one (the reverse of the
authors' earlier project-governance result); the guard removed all mixed-state violations. An exploratory grid
(`results/dev_sensitivity/`) showed that the advantage over ASAP grows with the renewal period and shrinks with
capacity: about 20-24% with annual renewals and capacity 1, 34-39% with two-yearly renewals and capacity 1, and no
significant difference with half-yearly renewals or capacity 2-3.

### 4b. Development outcomes on the real data (not evidence)

After the census pilot, the same hypotheses were run on development seeds with the real data (steps 4 to 6 in
`docs/steps/`). Several changes were made along the way; each is decided in section 6.

| ID | Census pilot | Real data, Q1 only (step 4) | Real data with Q1b (step 5) |
|---|---|---|---|
| H1 | REFUTED | REFUTED | CONFIRMED |
| H2 | REFUTED | CONFIRMED | REFUTED |
| H2b | INCONCLUSIVE | CONFIRMED | CONFIRMED |
| H3 | REFUTED | REFUTED | CONFIRMED |
| H4 | CONFIRMED | REFUTED | REFUTED |
| H5 | REFUTED | REFUTED | REFUTED |
| H6 | CONFIRMED | CONFIRMED | CONFIRMED |
| H7 | CONFIRMED | REFUTED | CONFIRMED |
| H8 | REFUTED | REFUTED | CONFIRMED |
| H11 | CONFIRMED | CONFIRMED | CONFIRMED |
| H12 | CONFIRMED | CONFIRMED | CONFIRMED |
| H9 | pending | pending | **REFUTED (final: recall 0.852; does not depend on seeds)** |
| H10, H13 | pending | pending | pending |

The ground truth for RQ1 changed from "the author's double-coded labels" (section 1) to labels made by an AI
assistant with file-and-line evidence and an optional 40-row human check (`docs/LABELLING.md`; section 6, D8 and D15).

## 5. Decisions the author must take before freezing (record each in section 6)

1. Keep H1, H3 and H5 as stated (theory-derived; the pilot suggests they may be refuted) or revise them. Either is
   legitimate if recorded with its reason before the held-out run; revising them *to match the pilot* must be said so.
2. Keep H11 (formulated after the exploratory grid; say so if kept).
3. The calendar policy for the held-out run: `observed_only` (default) or `lower_bound`; the other is exploratory.
4. The LLM model name and version for H10 and H13.
5. Whether the sensitivity grid is exploratory (recommended) or confirmatory.

These, and the later ones, are decided in section 6.

## 6. Addenda: decisions before the freeze (2026-11-27)

Decided by the author alone (sole author; no one else consulted), after the development runs and **before** the
held-out seeds were used. Evidence for each item is in `docs/steps/`.

**Changes made after seeing data, accepted as disclosed deviations**

| # | Change | Reason | Version, step |
|---|---|---|---|
| D1 | Issuers grouped by any shared controller, named after their largest token | The admin/owner-only rule split one issuer into "issuers" named after the stocks it tokenises | v0.3.1, step 3 |
| D2 | One anchor per shared beacon | One key upgrades 44 tokens; counting it 44 times was wrong | v0.3.1, step 3 |
| D3 | Soft 2035 deadline: fewest misses first, then lowest cost; overloaded issuers are named; a missing plan stops the run | With the Q1 data alone no plan existed, and it was scored silently as "no migration" | v0.3.2, step 4 |
| D4 | Cost-first mode as an ablation; price of compliance as a descriptive figure (no new hypothesis) | Shows the trade-off between deadline misses and expected loss | v0.3.2, step 4 |
| D5 | Q1b top-up collection (role holders from `minter()` etc.), rule tagged before fetching | The headline depended on whether Backed's role keys are shared | v0.3.3, step 5 |
| D6 | The main run uses the Q1b role holders | Observed facts replace placeholders | v0.3.4, step 5 |
| D7 | Labelling protocol: `ownable_admin` from bytecode; controller surfaces not scored; one label per distinct code | Removes circular scoring; 1,000 rows → 192 | v0.3.5, step 6 |
| D8 | Source labels made by an AI assistant with file-and-line evidence, at the author's request; not independent of the system | Time | v0.3.6, step 6 |

**Hypotheses**

| # | Decision |
|---|---|
| D9 | H1, H2, H2b, H3, H4, H5, H6, H7, H8, H12 and H13 kept exactly as written in section 2. |
| D10 | H5 keeps its definition; the oracle uses the same priority (deadline first) as QAMP's default. |
| D11 | H11 kept, and reported as **formulated after the exploratory pilot grid**. |
| D12 | H9 is final: **REFUTED** (recall 0.852 < 0.90). It does not depend on seeds and is not re-run. |
| D13 | H10 kept as written; run after the freeze with the model fixed on the run day and named in the paper's AI declaration (the repository names no tool). |

**Settings for the held-out run**

| # | Decision |
|---|---|
| D14 | Primary outcome for RQ2: realised cost (expected loss plus migration spend). Deadline misses and the price of compliance are secondary and descriptive. |
| D15 | No human check of the AI-made labels. H9 and H10 are reported with the caveat that their ground truth was made by an AI assistant that also drafted the discovery rules. |
| D16 | Role holders that cannot be read: one placeholder key per token (main run); one per issuer as the sensitivity run. |
| D17 | Calendar policy `observed_only`; `lower_bound` is exploratory. |
| D18 | The sensitivity grid is exploratory. |
| D19 | No OSF registration. The public, dated git tag `quantumclock-v1.0-frozen` is the record of what was fixed. |
| D20 | The held-out run is done once: `python -m qamp experiments --held-out --frozen-commit <sha>` (and the per-issuer sensitivity run), outputs committed unchanged. |
