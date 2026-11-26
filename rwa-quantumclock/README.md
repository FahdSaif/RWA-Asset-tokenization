# QAMP: Quantum-Aware Migration Planner

**An expert system that plans the post-quantum migration of the compliance trust anchors of tokenised real-world-asset
(RWA) infrastructure, timed to the commitments those anchors carry.**

Companion code for a manuscript in preparation for *Expert Systems with Applications* (Fahd Saifuddin). It builds on
`../rwa-threatlab` (threat model, model checker, census of 25 tokenised-asset contracts) and imports its census
classification so that both studies use one definition.

| Module | What it does | Research question |
|---|---|---|
| `discovery/` | Cryptographic inventory (CycloneDX 1.6 CBOM) from ABIs, observed controllers and verified Solidity source; rules classifier and an optional LLM classifier that must cite evidence ids | RQ1 |
| `kb/` + `qamp/kb/*.yaml` | Rule knowledge base: NIST IR 8547 dates, G7 roadmap targets, FATF / EU AMLD / SEC 17a-4 retention, exposure rules; each rule cites its source clause; inference trace | all |
| `scenarios.py` | CRQC-arrival distribution fitted to the GRI 2025 expert survey; execution-time deviations | RQ2 |
| `planner.py` | Decision-window-aware stochastic MILP (HiGHS via SciPy): start quarter per anchor, renewal boundaries, capacity per issuer, hard deadlines from the KB | RQ2 |
| `baselines.py` | ASAP, deadline-driven, annual review, Mosca ranking, greedy risk, adapted KG readiness score, oracle | RQ2 |
| `guard.py` | Bounded model check of mixed-cryptography states across bridged instances; couples and re-plans | RQ3 |
| `explain.py` | Rationales in which every sentence cites a rule, evidence item, plan decision or guard check; automatic checks (citation validity, faithfulness, counterfactual consistency); optional LLM rephrasing | RQ4 |
| `extraction.py` + `notebooks/Q1_fetch_anchor_facts.ipynb` | Observation (Colab, your Etherscan key): source, ABI, controllers, role members, governance-event history, runtime bytecode, the same address on 12 other EVM chains | data |
| `observed.py` | Classification of the observations: key exposure, renewal calendars, issuer capacity and groups, multi-chain instances, objective bytecode labels | data, RQ1 |
| `keccak.py` | Keccak-256 in pure Python, so that no selector or event topic is typed by hand | — |
| `evaluate.py`, `hypotheses.py` | Harness, statistics (paired sign-flip test on means, Holm; Wilcoxon secondary; bootstrap CIs), pre-stated hypotheses | all |

## Quick start

```bash
cd rwa-quantumclock
python -m pip install -e ".[dev]"        # numpy, scipy, pyyaml; pytest for tests
python -m pytest -q                      # software tests (must pass)
python -m qamp census                    # anchors from the real census -> results/census/
python -m qamp discover                  # CBOM -> results/discovery/
python -m qamp plan                      # plan with cited rationales -> results/plan/plan.md
python -m qamp explain-check             # RQ4 automatic checks -> results/explain/
python -m qamp sensitivity               # exploratory grid -> results/dev_sensitivity/
python -m qamp experiments --quick       # development run, about 10 s
python -m qamp experiments               # full development run, about 30 s
```

Development runs use development seeds and are **not evidence**. The pre-registered run uses held-out seeds once, after
the instrument is frozen: see `docs/RUNBOOK.md` and `docs/PREREGISTRATION.md`.

## Two kinds of checks, kept separate (as in rwa-threatlab)

| | Software tests (`pytest`) | Research hypotheses (`python -m qamp experiments`) |
|---|---|---|
| Question | Does the code do what it says? | Do the paper's claims hold under the stated model? |
| May fail? | No. A failure is a bug. | **Yes.** CONFIRMED / REFUTED / INCONCLUSIVE / PENDING DATA |
| Seeds | fixed | development seeds now; held-out seeds once, after freezing |

## What is observed and what is assumed

Observed (real data): the 25 contracts, their market caps, ABIs and controllers (rwa-threatlab census, 2026-11-08);
regulatory dates and retention periods (sources in `kb/*.yaml`); the CRQC survey ranges. Until the extraction notebook runs, renewal calendars, issuer
capacity, key exposure and bridged instances are documented defaults (RQ3 uses a labelled synthetic topology); after
it runs they are observed where the chain shows them. Migration times and costs stay assumed. No interviews or
questionnaires are used. Every anchor records the provenance of each field.
`docs/ASSUMPTIONS.md` lists every assumption and how it will be replaced or varied.

## Folder layout

```
rwa-quantumclock/
├── src/qamp/            package (the system is called QAMP in the paper)
├── kb/                  knowledge-base rules (YAML, with sources)
├── data/                sample_tokens.txt, templates; notebook output goes here
├── notebooks/           Q1_fetch_anchor_facts.ipynb (Colab, Etherscan)
├── experiments/         (reserved for frozen configurations)
├── results/             generated; dev/ is a development pilot, not evidence
├── tests/
└── docs/                RUNBOOK, ASSUMPTIONS, PREREGISTRATION (draft), LABELLING, PAPER_MAPPING, DISCLOSURE
```
