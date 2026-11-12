# rwa-threatlab

**Executable threat model, reference implementation and adversarial evaluation for runtime-enforced compliance in tokenised real-world-asset (RWA) systems.**

[![CI](https://github.com/FahdSaif/RWA-Asset-tokenization/actions/workflows/rwa-threatlab-ci.yml/badge.svg)](https://github.com/FahdSaif/RWA-Asset-tokenization/actions)
![python](https://img.shields.io/badge/python-3.10%2B-blue) ![deps](https://img.shields.io/badge/dependencies-none-green) ![license](https://img.shields.io/badge/license-MIT-lightgrey)

Companion code for the paper *"A Threat-Modelling Framework for Runtime-Enforced Compliance in Tokenised Real-World Asset Systems"*
(conference version: SDLT 2026; a journal extension with pre-registered real-data experiments is in preparation; Fahd Saifuddin). The paper builds a STRIDE-based threat model, attack trees and a risk assessment for
architectures that enforce compliance in the protocol runtime. This repository makes the analysis **runnable and
falsifiable**:

* a **reference implementation** of the five-module architecture (Compliance Gateway, Parameter Store, Verification
  Module, hash-chained Trail, quorum Governance) plus an oracle aggregator and a two-chain bridge;
* **17 executable attack scenarios**, one per attack-tree leaf, each run against a *baseline* build, a *hardened* build
  and, where predicted, a *residual-risk* variant;
* an **adversarial stateful fuzzer** with an oracle of truth, which found **three genuine defects** in the first
  implementation of the paper's own mitigations (see [`docs/FINDINGS.md`](docs/FINDINGS.md));
* **pre-stated research hypotheses**, reported as CONFIRMED / REFUTED on held-out seeds, kept separate from the software tests;
* the paper's **risk rubric**, sensitivity analysis and an explicit-state **model checker**;
* **realistic synthetic data generators** with a datasheet ([`docs/DATA.md`](docs/DATA.md)) and loaders for real traces.

The code itself uses only the Python standard library. Three optional packages (`pytest`, `pycryptodome`, `openpyxl`, installed by the `dev` extra) are needed only to run all 100 software tests.

## Two kinds of checks, deliberately separate

| | Software tests (`pytest`, 100) | Research hypotheses (`rwa_threatlab hypotheses`, H1-H10; pre-registered H11-H16 in `docs/PREREGISTRATION.md`) |
|---|---|---|
| Question | Does the code do what it says? | Do the paper's claims hold? |
| May fail? | No. A failure is a bug. | **Yes.** Reported as CONFIRMED / REFUTED / INCONCLUSIVE. |
| Seeds | fixed | **held-out**, never used for debugging |

## Quick start

```bash
git clone https://github.com/FahdSaif/RWA-Asset-tokenization
cd RWA-Asset-tokenization/rwa-threatlab
python -m pip install -e ".[dev]"
python -m pytest -q                         # software tests
python -m rwa_threatlab all                 # scenarios, rubric, model check, mediation audit, hypotheses
python -m rwa_threatlab hypotheses          # only the research hypotheses (about a minute)
python examples/walkthrough_quorum_collusion.py
```

## Attack scenarios

Produced by `python -m rwa_threatlab scenarios`; asserted in [`tests/test_scenarios.py`](tests/test_scenarios.py).

| ID | Tree node | Scenario | Adversary | Baseline | Hardened | Residual |
|---|---|---|---|---|---|---|
| A1 | A1 | Raw / node-level transaction with no validation hook | Adv1 | attack succeeds | blocked | n/a |
| A2 | A2 | Gateway software defect (origin spoofing) | Adv1/2 | attack succeeds | blocked | n/a |
| A3a | A3 | Privileged forced transfer / recovery operation | Adv5 | attack succeeds | blocked | **attack succeeds** |
| A3b | A3 | Runtime upgrade that alters the Gateway | Adv5/6 | attack succeeds | blocked | **attack succeeds** |
| B1 | B1a+B1b | Quorum collusion defeating the challenge window | Adv5 | attack succeeds | blocked | **attack succeeds** |
| B2 | B2 | Rule-activation latency window | Adv2 | attack succeeds | blocked | **attack succeeds** |
| B3 | B3a+B3b | Poisoned regulatory-data feed | Adv4 | attack succeeds | blocked | **attack succeeds** |
| C1a | C1a | Unlisted or out-of-scope issuer | Adv2/3 | attack succeeds | blocked | n/a |
| C1 | C1 | Compromised, listed, in-scope issuer | Adv3 | attack succeeds | attack succeeds | n/a |
| C2 | C2 | Revoked credential inside the status lag | Adv2 | attack succeeds | blocked | **attack succeeds** |
| D1 | D1 | Timing / value correlation | Adv1 | attack succeeds | blocked | **attack succeeds** |
| D2 | D2 | Trail-granularity leakage and error oracle | Adv1 | attack succeeds | blocked | n/a |
| D3 | D3a+D3b | Issuer-linkage deanonymisation | Adv3 | attack succeeds | blocked | **attack succeeds** |
| E1 | E1 | Cross-chain rule-propagation lag | Adv2 | attack succeeds | blocked | **attack succeeds** |
| E2 | E2 | Jurisdictional misclassification | Adv2 | attack succeeds | blocked | **attack succeeds** |
| E3 | E3a+E3b | Bridge identity discontinuity | Adv2 | attack succeeds | blocked | n/a |
| E4 | E4 | Cross-chain revocation lag | Adv2 | attack succeeds | blocked | **attack succeeds** |


## Research hypotheses (held-out seeds)

Held-out seeds from 30000; 600 traces x 40 steps per fuzz cell.

| ID | Hypothesis | Prediction | Outcome | Evidence |
|---|---|---|---|---|
| H1 | Hardened build, no anchor capability: no violation outside the documented lag windows. | 0 unexplained and 0 adversary-attributed violations | **CONFIRMED** | 2400 traces x 40 steps: 0 unexplained, 0 adversary-attributed, 3 inside documented lag windows, 0 crashes/trail failures |
| H1b | Instrument sensitivity: the same fuzzer finds violations in the baseline build. | > 0 violations | **CONFIRMED** | instrument sensitivity: the baseline build shows 152 violations over 600 traces with no adversary; a fuzzer that finds nothing there would be vacuous |
| H2 | A colluding quorum without censorship cannot corrupt the rule set. | no harmful relaxation; only the backdoored-upgrade route remains | **CONFIRMED** | colluding quorum, no censorship: 336/600 traces violate; every violation goes through an installed backdoored upgrade; harmful relaxations: 0; attributed sets {'upgrade': 1049} |
| H2b | The bounded conformance suite stops blatant faulty upgrades but not trigger-based backdoors. | permissive installs = 0; backdoored installs > 0 | **CONFIRMED** | guarded upgrades: permissive builds installed 0, trigger-based backdoored builds installed 561 (bounded conformance tests catch blatant faults, not triggers) |
| H3 | Censorship of contestation is what opens branch B1. | relax violations: 0 without, > 0 with censorship | **CONFIRMED** | rule-set corruption via relaxation: 0 without censorship vs 624 with censorship |
| H4 | A compromised listed issuer defeats every technical mitigation (trust-anchor floor). | violations exist and are all attributed to the issuer | **CONFIRMED** | compromised listed issuer vs hardened build: 230/600 traces violate, all attributed to ['issuer'] (trust-anchor floor) |
| H5 | Cross-instance violations arise from composition with no adversary capability. | I1, I2 safe; I3 unsafe; I4 safe; E3 baseline attack | **CONFIRMED** | composition without adversary capabilities: model check {'I1': False, 'I2': False, 'I3': True, 'I4': False}; implementation E3 baseline attack True, hardened False |
| H6 | Batching reduces timing linkage only when enough traffic shares an epoch. | linkage >= 25% at 1 event/epoch and < 25% at 20 | **CONFIRMED** | timing linkage falls from 53% (1 event/epoch) to 5% (20/epoch); drops below 25% (CI upper bound) from 5 events per epoch |
| H7 | Logging the matched sub-rule leaks identity information that rule-class logging does not. | > 1 bit vs 0 bits | **CONFIRMED** | sub-rule logging leaks 2.64 bits (worst-5% anonymity set 19); class-level logging leaks 0.00; rejection codes 3 -> 1 |
| H8 | Blind issuance defeats the credential-id join but not issuer timing correlation. | >= 50% linked at 1-tick delay, < 10% at 60-tick delay | **CONFIRMED** | blind issuance removes the credential-id join but timing remains: issuer links 76% at 1-tick delay and 7% at 60-tick delay |
| H9 | Immediate tightening trades an integrity attack for a bounded availability attack. | freeze succeeds, then expires | **CONFIRMED** | false tightening freezes an honest holder (availability attack succeeds) for 50 ticks and is then undone: honest holder u: REJECTED during freeze, OK after expiry |
| H10 | Rubric ratings are stable under small perturbations. | descriptive only | **DESCRIPTIVE** | rubric robustness (not a test): A1/A2 stays in the lowest band in 72% of perturbed assessments; >=3 of 4 trust-anchor rows stay >= Medium in 76%; mean band shift 0.64 |


**Read [`docs/FINDINGS.md`](docs/FINDINGS.md) alongside this table.** These outcomes follow three defect fixes and three
corrections to the fuzzing instrument, each prompted by a failed expectation and each disclosed with the seeds it consumed.

## Freeze and pre-registration

The measuring instrument is frozen (`docs/FREEZE.json`, checked by `tests/test_freeze.py` and `python scripts/freeze.py check`).
New hypotheses H11-H16, their seed ranges and pass/fail criteria are fixed in
[`docs/PREREGISTRATION.md`](docs/PREREGISTRATION.md) before the corresponding experiments are run.

**Journal-extension results (pre-registered, seeds 40,000-40,599).** H11a CONFIRMED: an oracle implemented separately from
[`docs/ORACLE_SPEC.md`](docs/ORACLE_SPEC.md) agrees with the fuzzer's oracle on all 2,824 violations in 8 cells (0 disagreements);
a test plants four faults in the fuzzer's oracle and the comparison catches each. H11b CONFIRMED: the fuzzer's end-of-step lag
measurement is conservative (31 of 2,824 violations would count as within-lag if measured at the transfer tick; none the other way).
See `docs/PREREGISTRATION.md` addendum A2 and section 7 for what this does not check.

## Where the evidence is (start here)

| What | Where |
|---|---|
| Pre-registration (OSF, 7 Nov 2026) | https://osf.io/64atb; `docs/PREREGISTRATION.md`; tag `v1.3-prereg-real` |
| Real OFAC replay (H12, H13, H16), official run and replication | `docs/results/real/`; tag `v1.3-real-results` |
| Real transaction timing (H14), official run and replication | `docs/results/real_timing/`; data and selection notes in `docs/data/` (`H14_DATA_NOTES.md`); tag `v1.3-prereg-timing` |
| Assessor study and post-hoc scope revision | `docs/irr/`, `docs/results/irr.md`, `docs/RATINGS_REVISION.md` |
| Exploratory measurements on real Ethereum data (A anonymity sets, B OFAC-to-blacklist delay, C census of privileged control) | plan `docs/EXPLORATORY_PLAN.md` and `docs/EXPLORATORY_PLAN_C_ADDENDUM.md` (fixed before the data were analysed; tags `v1.6-exploratory-plan`, `v1.6-census-plan`); results `docs/results/exploratory/` (tags `v1.6-exploratory-data`, `v1.6-census-data`) |
| Final state cited by the paper | tag `v1.7-paper` |

Every result folder was produced by a manually triggered GitHub Actions run from a fixed tag and was re-run independently with an identical result. The exploratory analyses are **not** part of the OSF registration; their plans were committed and tagged before the data were analysed.

## Reproduce the paper's results

Each row gives the claim, the command that regenerates it and the folder that holds the stored evidence. Pass `--out` with a new folder so stored results are not overwritten (the converter `scripts/make_revision_outputs.py` writes into `docs/results/`; `git checkout -- docs/results` restores it). Runs refuse to start if tracked files are uncommitted or the frozen instrument changed (`--force` overrides and is logged).

| Claim in the paper | Command (from `rwa-threatlab/`) | Stored evidence |
|---|---|---|
| 17 attack scenarios: baseline, hardened, residual | `python -m rwa_threatlab scenarios` † | `docs/results/scenarios.md` |
| Risk rubric, sensitivity, trust-anchor floor | `python -m rwa_threatlab risk` † | `docs/results/risk.md`, `floor_dependence.json` |
| Model check, and scaled check (up to 6 chains, 12 participants) | `python -m rwa_threatlab modelcheck` †; `python -m rwa_threatlab scaled` † | `docs/results/modelcheck_scaled.md` |
| Hypotheses H1 to H10 (held-out seeds) | `python -m rwa_threatlab hypotheses` † | `docs/results/hypotheses.md` |
| H11: second oracle (2,824 violations, 0 disagreements) | `python -m rwa_threatlab h11` † | `docs/results/h11.md` |
| H12, H13, H16: replay of real OFAC histories | `python -m rwa_threatlab real --only ofac` † (see `docs/REAL_DATA_RUNBOOK.md`) | `docs/results/real/` |
| H14: real USDY transaction timing | `python -m rwa_threatlab real --only timing` † | `docs/results/real_timing/` |
| Inter-rater study and ratings revision | `python scripts/make_revision_outputs.py` † | `docs/results/irr.md`, `docs/RATINGS_REVISION.md` |
| Residual bands under three rating sets (original, revised, assessors' median) | `python scripts/make_rating_sets.py --out FOLDER` | `docs/results/rating_sets.md` |
| Exploratory A: anonymity sets of USDY transfers | `python -m rwa_threatlab.exploratory.run kanon` † | `docs/results/exploratory/kanon/` |
| Exploratory B: OFAC listing to USDC/USDT blacklisting | `python -m rwa_threatlab.exploratory.run latency` † | `docs/results/exploratory/latency/` |
| Exploratory C: census of 25 tokenised-asset contracts | `python -m rwa_threatlab.exploratory.run census` † | `docs/results/exploratory/census/` |

† Re-run from a clean clone of `main` on 11 November 2026: the result content was identical to the stored files (only provenance fields such as commit hash, date and Python version differ). The real-data and exploratory results were also produced by the manually triggered GitHub Actions workflows (run links in the results folders) and re-run independently with identical results. H15 (bridge latency) was not run. The real-data inputs are committed in `docs/data/`; the Etherscan data of the exploratory analyses were retrieved on 8 November 2026 and are stored there, so these commands need neither network access nor an API key.

## Real-trace experiments (H12-H16)

`python -m rwa_threatlab ofac-parse ...` turns OFAC's change archive into events; `python -m rwa_threatlab real` replays them
in the fuzzer and analyses real on-chain timing and bridge latency. Step-by-step: [`docs/REAL_DATA_RUNBOOK.md`](docs/REAL_DATA_RUNBOOK.md).
Design and criteria: [`docs/PREREGISTRATION.md`](docs/PREREGISTRATION.md) addenda A3-A5. LaTeX tables for the paper:
`python scripts/make_latex.py`. The scaled composition check is `python -m rwa_threatlab scaled`.

## Inter-rater data and ratings revision

The blank scoring pack, anonymised scores of four assessors and the converter are in [`docs/irr/`](docs/irr/README.md). After the
inter-rater study the scope factor of D1 to D3 was re-scored under one rule (post-hoc; see [`docs/RATINGS_REVISION.md`](docs/RATINGS_REVISION.md)).
The original ratings in `risk.py` are unchanged and are the paper's primary table; the revision is one of three rating sets in a
robustness check (`python scripts/make_rating_sets.py`; results in `docs/results/rating_sets.md`).

## Risk rubric

| ID | Scenario | Node | Adv | L | I | Inherent | Mit. | L_res | Residual |
|---|---|---|---|---|---|---|---|---|---|
| A1/A2 | Unmediated path or Gateway defect | A1, A2 | Adv1/2 | 3 | 5 | Med-High | T | 1 | **Low** |
| A3 | Privileged path (upgrade, admin, recovery) | A3 | Adv5/6 | 3 | 5 | Med-High | P | 2 | **Medium** |
| B1 | Quorum collusion | B1a, B1b | Adv5 | 2 | 5 | Medium | P | 2 | **Medium** |
| B2 | Rule-activation latency window | B2 | Adv2 | 4 | 3 | Medium | P | 3 | **Low-Med** |
| B3 | Regulatory-oracle poisoning | B3a, B3b | Adv4 | 3 | 5 | Med-High | P | 2 | **Medium** |
| C1 | Compromised or forged issuer | C1a | Adv3 | 3 | 5 | Med-High | P | 2 | **Medium** |
| C2 | Revoked credential in lag window | C2 | Adv2 | 4 | 3 | Medium | P | 3 | **Low-Med** |
| D1 | Timing and value correlation | D1 | Adv1 | 5 | 3 | Med-High | P | 4 | **Medium** |
| D2 | Trail-granularity leakage | D2 | Adv1 | 4 | 3 | Medium | P | 3 | **Low-Med** |
| D3 | Issuer-linkage deanonymisation | D3a, D3b | Adv3 | 3 | 3 | Low-Med | P | 2 | **Low-Med** |
| E1 | Cross-chain rule-propagation lag | E1 | Adv2 | 4 | 4 | Med-High | P | 3 | **Medium** |
| E2 | Jurisdictional misclassification | E2 | Adv2 | 5 | 3 | Med-High | P | 4 | **Medium** |
| E3 | Bridge identity discontinuity | E3a, E3b | Adv2 | 4 | 3 | Medium | T | 2 | **Low-Med** |
| E4 | Cross-chain revocation lag | E4 | Adv2 | 4 | 3 | Medium | P | 3 | **Low-Med** |


## Data

**Synthetic data and real traces.** The scenario worlds, the fuzzer and the privacy experiments (H1-H10) use synthetic generators,
realistic in shape (heavy-tailed event gaps, Zipf-concentrated jurisdictions, memoryless delays), with 95 % intervals over many
seeds; they are not calibrated to any production system. The pre-registered real-trace experiments (H12, H13, H16) replay the order of
add and remove events of OFAC's public SDN change files (2019 to 2023) in the fuzzer, and H14 uses the real transaction timing of one
tokenised asset (Ondo USDY, 4,996 transactions over 131.5 days; confirmed); the compliance layer is always simulated.
H15 (bridge latency) is pre-registered but was not run. The exploratory analyses add real Ethereum data: the 10,000 USDY transfer events of H14 (A), the on-chain blacklist events of USDC and USDT for the OFAC-listed addresses (B), and on-chain observations of 25 tokenised-asset contracts (C). See [`docs/DATA.md`](docs/DATA.md), [`docs/results/real/`](docs/results/real/) (OFAC run),
[`docs/results/real_timing/`](docs/results/real_timing/) (H14 run) and [`docs/results/exploratory/`](docs/results/exploratory/) (exploratory runs).

## Layout

```
src/rwa_threatlab/   crypto trail credentials rules ledger verifier gateway governance oracle system bridge attacks config
                     fuzz.py (adversarial fuzzer)  hypotheses.py (research hypotheses)  risk.py  modelcheck.py
                     scenarios/ (17 attacks + privacy generators)
tests/               software tests          docs/  ARCHITECTURE PAPER_MAPPING FINDINGS DATA LIMITATIONS results/
examples/ scripts/
```

## Scope and honesty

A research simulation. HMAC stands in for signatures, there are no zero-knowledge proofs and no real chain, the upgrade
conformance suite is bounded testing, the model checker is tiny, and the fuzzer explores only the actions its authors wrote.
See [`docs/LIMITATIONS.md`](docs/LIMITATIONS.md). Do not use this code to protect real assets.

## Authorship, responsibility and AI assistance

The research design (reference architecture, mediation surface, adversary model, rating method, hypotheses and the
pre-registered protocol) is the authors' work, and the authors are responsible for the code, experiments and conclusions.
The use of an AI assistant in producing parts of the software and documentation is stated, with its scope, in
[`docs/DISCLOSURE.md`](docs/DISCLOSURE.md), which matches the declaration in the manuscript.

## Citation and licence

[`CITATION.cff`](CITATION.cff); MIT, see [`LICENSE`](LICENSE).
