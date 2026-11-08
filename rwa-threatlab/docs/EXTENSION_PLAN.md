# Journal-extension plan (tracked changes to code and paper)

Status key: DONE = implemented and tested here; TODO-LOCAL = needs data or tools only available on the author's machine; TODO = not started.

| # | Reviewer risk | Change | Code | Status |
|---|---|---|---|---|
| 1a | Self-validating evaluation | **Step 1:** freeze method, pre-register H11-H16, seed ledger | `scripts/freeze.py`, `docs/FREEZE.json`, `docs/PREREGISTRATION.md` | DONE |
| 1b | Self-validating evaluation | **Step 2:** independent second oracle and differential test (H11a/H11b) | `oracle_independent.py`, `fuzz_observed.py`, `hypotheses_v2.py`, `docs/ORACLE_SPEC.md` | DONE (human-independent third implementation still recommended) |
| 2 | Tiny model, "exhaustive" overstated | Scale to k chains x n participants; random eligibility assignments; state-count growth reported | `modelcheck_scaled.py`, `python -m rwa_threatlab scaled` | DONE (still small; see limits) |
| 3 | Circular headline finding | Show ranking with and without the trust-anchor floor | `risk.floor_dependence()` | DONE |
| 4 | Single-assessor ratings | Inter-rater tooling (Krippendorff alpha, agreement, band agreement); blank assessor template | `irr.py`, `docs/irr/assessor_template.csv` | DONE (four assessors; analysis in `docs/results/irr.md`; scope revision in `docs/RATINGS_REVISION.md`) |
| 5 | Thin empirical grounding | **Steps 3-5:** OFAC replay (H12-H13, H16), on-chain timing (H14), bridge latency (H15): loaders, fuzzer hook, runner, guards | `traces/`, `fuzz_replay.py`, `hypotheses_real.py` | DONE for OFAC (H12, H13, H16; official run and replication in `docs/results/real/`); H14 run and confirmed (`docs/data/H14_DATA_NOTES.md`); H15 not run |
| 7 | Paper | LaTeX tables generated from the result files | `scripts/make_latex.py` | DONE |
| 6 | Reproducibility inconsistency | H10 now uses the paper's 20,000 trials (was 5,000, printing 71% vs the paper's 72%) | `hypotheses.py` | DONE |

Limits of item 2: state counts stay in the low hundreds because the model has one asset unit and one exogenous event. A
real model checker (TLA+/Apalache, Alloy) with several assets and concurrent events is the next step and is not claimed here.
