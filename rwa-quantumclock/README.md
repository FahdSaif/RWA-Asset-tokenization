# QAMP: Quantum-Aware Migration Planner

**An auditable expert system that plans when, and in what order, the signing keys behind tokenised real-world assets
(RWAs) should move to post-quantum cryptography, timed to the renewal windows those keys depend on.**

Companion code, data and results for the manuscript *"QAMP: an auditable knowledge-based expert system for planning
post-quantum key migration in regulated tokenised-asset platforms"* (Fahd Saifuddin), prepared for *Expert Systems
with Applications*. It builds on `../rwa-threatlab` (threat model, model checker, census of 25 tokenised-asset
contracts) and uses the same census classification.

- **The whole experiment at a glance, with diagrams:** [docs/EXPERIMENT.md](docs/EXPERIMENT.md)
- **A dated page for every step (what was done, checks, what went wrong):** [docs/steps/](docs/steps/README.md)
- **What was fixed before the held-out run:** [docs/PREREGISTRATION.md](docs/PREREGISTRATION.md)

## Status

| | |
|---|---|
| Data | Observed: top 100 RWA tokens on Etherscan, Ethereum blocks 26,496,449 and 26,503,940 |
| Code frozen | commit `cb1c560`, tag `quantumclock-v1.0-frozen` (decisions D1–D20 recorded before the run) |
| Held-out run | done once, seeds from 50,000; tag `quantumclock-v1.0-results` |
| AI runs (H10, H13) | done on the frozen code; tag `quantumclock-v1.0-ai` (model recorded only as a SHA-256 fingerprint) |
| Hypotheses | **14 decided: 8 confirmed, 6 refuted.** Refutations are reported in full. |
| After the held-out run | per-issuer view of the frozen plans; exploratory sensitivity of costs to the loss settings (not pre-registered) |

## Headline results (held-out run)

| | |
|---|---|
| Sample | 100 tokens, 108 controllers, 75 anchors, 28 issuer groups, 20,514 events |
| Mean realised cost, QAMP | USD 369.6m (95% CI 312.8–426.1) |
| Mean realised cost, ASAP | USD 409.2m; difference USD 39.5m (CI 31.5–48.2), Holm-adjusted p = 0.0006 |
| Ignoring renewal windows | USD 29.5m more (H3 confirmed) |
| Bridged (multi-chain) anchors | 13 of 13 had a forgery path when planned separately; none after the guard (H6 confirmed) |
| Explanations | 781 sentences: citation validity, faithfulness and counterfactual consistency all 1.0 (H12 confirmed) |
| Rule-based discovery | recall 0.852, precision 0.670, F1 0.750 (H9 refuted: target recall was 0.90) |
| AI classifier | F1 0.156 against 0.750 for the rules (H10 refuted) |
| AI rewording of explanations | 55.4% of sentences still verifiable (H13 refuted) |
| Exploratory sensitivity | QAMP stayed cheaper than ASAP, greedy risk and Mosca in all 14 loss settings tested |

Dollar figures are values of a stated loss model with assumed parameters, not forecasts of real losses.

## Where to find what

| Paper item | File |
|---|---|
| Main results table and figure, hypothesis verdicts | `results/held_out/` (`results.json`, `main_table.md`, `hypotheses.md`) |
| Sensitivity run: one placeholder role holder per issuer | `results/held_out_roles_per_issuer/` |
| Discovery (RQ1): rules and AI classifier | `results/discovery/`, `results/ai_runs/decisions.json` |
| Explanation checks (RQ4) and AI rewording log | `results/explain/` |
| Observed facts about the 100 tokens | `results/observed/observed_summary.json` |
| Plans issuer by issuer (supplementary Table S2) | `results/held_out/per_issuer.md` (made by `tools/per_issuer_table.py`, read only) |
| Exploratory sensitivity (supplementary Table S3) | `results/exploratory/` (made by `tools/loss_sensitivity.py`) |
| Knowledge-base rules with their source clauses | `kb/*.yaml` |
| Labels and how they were made | `data/labels*.csv`, [docs/LABELLING.md](docs/LABELLING.md) |
| Executed notebooks and screenshots of every Colab run | `notebooks/runs/` |
| Use of an AI assistant | [docs/DISCLOSURE.md](docs/DISCLOSURE.md) |

## Modules

| Module | What it does | Research question |
|---|---|---|
| `discovery/` | Cryptographic inventory (CycloneDX 1.6 CBOM) from ABIs, observed controllers and verified Solidity source; rule classifier and an optional AI classifier that must cite evidence ids | RQ1 |
| `kb/` + `qamp/kb/` | Rule knowledge base: NIST IR 8547 dates, G7 roadmap targets, FATF / EU AMLD / SEC 17a-4 retention, exposure rules; each rule cites its source clause; forward-chaining inference with a trace | all |
| `scenarios.py` | When a quantum computer may arrive, fitted to the GRI 2025 expert survey; execution delays | RQ2 |
| `planner.py` | Planner (integer program, HiGHS via SciPy): one start quarter per anchor, renewal boundaries, capacity per issuer, hard deadlines from the knowledge base; fewest deadline misses first, then lowest cost | RQ2 |
| `baselines.py` | ASAP, deadline-driven, annual review, Mosca ranking, greedy risk, adapted readiness score, oracle | RQ2 |
| `guard.py` | Bounded model check of partly migrated bridged copies; couples them and plans again | RQ3 |
| `explain.py` | Rationales in which every sentence cites a rule, evidence item or plan fact; automatic checks (citation validity, faithfulness, counterfactual consistency); optional AI rewording | RQ4 |
| `extraction.py` + `notebooks/Q1_*.ipynb`, `Q1b_*.ipynb` | Read-only collection in Colab: source, ABI, controllers, role members, governance events, bytecode, same address on other chains | data |
| `observed.py` | Turns the collected data into facts: key exposure, renewal calendars, issuer capacity and groups, multi-chain copies, bytecode labels | data, RQ1 |
| `keccak.py` | Keccak-256 in pure Python, so that no selector or event topic is typed by hand | — |
| `evaluate.py`, `hypotheses.py` | Harness, statistics (paired sign-flip test with Holm correction; Wilcoxon as a check; bootstrap CIs), hypothesis decisions | all |

## Quick start

```bash
cd rwa-quantumclock
python -m pip install -e ".[dev]"        # numpy, scipy, pyyaml; pytest for tests
python -m pytest -q                      # software tests (must pass)
python -m qamp discover                  # CBOM -> results/discovery/
python -m qamp explain-check             # explanation checks -> results/explain/
python -m qamp experiments --quick       # development run, about 10 s (development seeds: not evidence)
python tools/per_issuer_table.py         # per-issuer view of the frozen held-out plans
python tools/loss_sensitivity.py --quick # quick test of the exploratory sensitivity script
```

The held-out run was made once, after the code was frozen; see [docs/RUNBOOK.md](docs/RUNBOOK.md). A later run in a
fresh Colab environment (2026-11-28, `notebooks/runs/`) reproduced the main QAMP and ASAP figures exactly.

## Two kinds of checks, kept separate (as in rwa-threatlab)

| | Software tests (`pytest`) | Research hypotheses (`python -m qamp experiments`) |
|---|---|---|
| Question | Does the code do what it says? | Do the paper's claims hold under the stated model? |
| May fail? | No. A failure is a bug. | **Yes.** CONFIRMED / REFUTED |
| Seeds | fixed | development seeds from 0; held-out seeds from 50,000, used once |

## What is observed and what is assumed

Observed: the 100 tokens, their market values, controllers, role members, Safe owners and thresholds, governance
events, key exposure (51 controllers), 28 renewal calendars, issuer capacity and copies on other chains. Sourced:
regulatory dates and retention periods (`kb/*.yaml`) and the expert-survey ranges. Assumed: migration durations and
costs, the loss parameters, calendars for the other 47 anchors, and bridges between copies. Every anchor records where
each field came from. No interviews or questionnaires are used. [docs/ASSUMPTIONS.md](docs/ASSUMPTIONS.md) lists every
assumption.

## Folder layout

```
rwa-quantumclock/
├── src/qamp/            the QAMP package
├── kb/                  knowledge-base rules (YAML, with sources)
├── data/                sample, collected data (with SHA-256 digests), labels
├── notebooks/           Colab notebooks; runs/ holds executed copies and screenshots
├── tools/               sample builder; read-only per-issuer view; exploratory sensitivity script
├── results/             held_out/ is the evidence; dev*/ are development pilots, not evidence;
│                        exploratory/ is not pre-registered
├── tests/
└── docs/                EXPERIMENT, steps/, PREREGISTRATION, RUNBOOK, ASSUMPTIONS, LABELLING, SAFE,
                         PAPER_MAPPING, DISCLOSURE, Q1B_PLAN, ROADMAP
```
