# Pre-registration and freeze record (v1.1)

Purpose: the journal version adds new experiments (independent oracle, replay of real regulatory events, real timing and
bridge data). To avoid the researcher degree of freedom disclosed in `FINDINGS.md` section B (changing the method after
seeing a result), everything below is written **before** any of the new experiments is run. Git tag `v1.1-frozen` is
the timestamp. Optionally also register this file on OSF (https://osf.io/registries) for an independent timestamp.

## 1. What is frozen

`docs/FREEZE.json` holds SHA-256 hashes (line endings normalised) of the simulator, fuzzer, scenarios, the original
hypotheses H1-H10, the rubric, both model checkers, the inter-rater tool, the existing tests and the reference outputs in
`docs/results/`. `python scripts/freeze.py check` and `tests/test_freeze.py` fail if any of them changes.

Rules for new work:
1. New experiments go in **new files** (`oracle_independent.py`, `hypotheses_v2.py`, `traces/`), never inside a frozen file.
2. `__main__.py` may gain commands (it is glue, not the instrument).
3. If a frozen file must change, it is a **deviation**: re-freeze with `--reason`, log it in section 6, spend the seed range
   that exposed it, and retag.

## 2. Seed ledger

| Seeds | Use | Status |
|---|---|---|
| 0-399 | exploratory (F1-F3 defects, fuzzer debugging) | spent |
| 10,000-10,599 | first held-out run (H2/H3 refuted by instrument error C2) | spent |
| 20,000-20,599 | second held-out run (instrument error C3) | spent |
| 30,000-30,599 | final confirmation of H1-H9 (reported in the conference paper) | spent, seen |
| **40,000-40,599** | **H11** (independent oracle) | **spent** (one run; see section 7) |
| **50,000-50,599** | **H12-H13** (replay of real regulatory events), per fuzz cell and variant | reserved, unused (addendum A3) |
| 60,000-69,999 | reruns after a logged deviation, in blocks of 600, in order | reserved, unused |

Each reserved range is run **once**. If an instrument error is found, log it (section 6), discard that range, and use the
next block of section 60,000+. At most three attempts per hypothesis; all attempts are reported.

## 3. Hypotheses (prediction and criterion fixed now)

Outcomes are CONFIRMED, REFUTED or INCONCLUSIVE (the run did not exercise the condition). REFUTED results are reported.

| ID | Hypothesis | Prediction / criterion | Seeds |
|---|---|---|---|
| H11 | An oracle written separately from the paper's eligibility definition agrees with the fuzzer's oracle. | On every (build, adversary) cell of H1-H4, the two oracles report the **same set of violation events** (tick, chain, participant) and the same split into within-lag (ineligible for at most `L_DOC` = 6 ticks) versus beyond-lag. **0 disagreements** = CONFIRMED. Any disagreement is inspected; one that is not traced to a documented ambiguity in the definition = REFUTED. | 40,000-40,599 |
| H12 | The hardened build stays free of unexplained violations when real regulatory events drive the fuzzer. | Real OFAC SDN additions/removals replayed in order (protocol in addendum A3); hardened build, no adversary: **0 UNEXPLAINED and 0 adversary-attributed** violations (documented-lag allowed). | 50,000-50,599 |
| H12b | The replay is not vacuous. | Baseline build under the same replay: **> 0 violations**. | 50,000-50,599 |
| H13 | H2, H3 and H4 conclusions do not depend on the synthetic event stream. | Under the replayed events: colluding quorum without censorship produces 0 harmful relaxations; with censorship > 0; compromised listed issuer produces violations **all** attributed to the issuer. | 50,000-50,599 |
| H14 | The batching boundary of H6 survives real transaction timing. | With real inter-arrival times (addendum A4), timing linkage is >= 25% at 1 event per epoch and its 95% CI upper bound is < 25% at 20 events per epoch; the smallest tested ratio with upper bound < 25% lies in [2, 10] (the synthetic result is 5). | none (deterministic data; bootstrap seed 2026) |
| H15 | (descriptive, no pass/fail) Real bridge latency. | Report median, 95th and 99th percentile origin-to-destination latency and how it compares with the model's documented relay window (mapping in addendum A5). | none |
| H16 | (coverage check) Real regulatory data contains the pattern that exposed F3. | The chosen OFAC window contains **at least one** entry that is removed and later re-added. If none, report that the F3-style scenario is not exercised by real data (INCONCLUSIVE for that aspect, not a pass). | none |

Independence caveat for H11: the second oracle is a separate implementation from the written definition and shares no code
with `fuzz.py`, but it is written by the same research team. The strongest version has a person who has not read the fuzzer
implement it from `docs/ORACLE_SPEC.md` alone. If that is done, record the implementer here.

## 4. Choices still to be fixed (addenda, each committed and tagged BEFORE the data is touched)

| Addendum | Fixes | Committed before |
|---|---|---|
| A2 | Oracle specification text; which trace fields the independent oracle may read | any H11 run |
| A3 | OFAC window (dates), programs and entity types included, mapping of entries to fuzz participants, tick mapping, delta-file source and checksum | any H12/H13 run |
| A4 | Transaction data source, chain, window, filters, epoch ratios, bootstrap size | any H14 run |
| A5 | Bridge(s), window, latency definition (event timestamps used), tick-to-seconds mapping | any H15 run |

Each addendum records the date, the git commit and, for external data, the source URL, download date and SHA-256 of the
file used. Data are never filtered after seeing results.

## 4a. Addendum A2: oracle specification and H11 (committed before any run on seeds 40,000-40,599)

**Provenance of the specification and the second oracle.** `docs/ORACLE_SPEC.md` and the second oracle
(`oracle_independent.py`) were produced within the research effort after the fuzzer had been written, and the specification
was written with knowledge of `fuzz.py`. The implementation is therefore *separate code written from a stated definition*,
not independent of the research team, and the two conventions in spec section 5 were identified by reading the fuzzer.
How the software and documentation were produced, including the use of AI tools, is stated in `docs/DISCLOSURE.md`.

**What was learned on exploratory seeds (0-399 only, spent), disclosed because it shaped this addendum.**
1. On seeds 0-59, 480 traces: 259 violations compared, 0 disagreements between the oracles.
2. Four planted faults in the fuzzer's oracle (ignore revocation, age from the latest reason, age off by one, one participant
   never judged ineligible) were each detected (33, 23, 142 and 53 disagreements on 450 traces). This is a software test
   (`tests/test_oracle_independent.py`) and shows the comparison can fail.
3. Baseline build, seeds 0-399, 108 violations: measuring the lag at the action tick instead of the end of the step moves
   17 violations (16%) from beyond-lag to within-lag; changing the age origin moves none. The hardened cells contain too
   few violations (4 over 1,600 traces) to say anything about convention sensitivity. The fuzzer's convention is therefore
   conservative: it can over-report UNEXPLAINED, not hide one.

**H11 is refined into two parts** (the original wording of section 3 is kept above for the record):

| ID | Criterion (fixed now) |
|---|---|
| H11a | Under the fuzzer's conventions (END, EARLIEST_ACTIVE), on all 8 cells of H1-H4/H1b x 600 traces (seeds 40,000-40,599): the independent oracle reports the same set of `(step, chain, participant)` violations, the same age for each, and the same within/beyond-lag class. **0 disagreements** and at least one violation compared in the baseline cell = CONFIRMED; any disagreement = REFUTED (all are reported with the trace seed); no baseline violations = INCONCLUSIVE. |
| H11b | (robustness of the lag convention) Under all four convention pairs of spec section 5: (i) measuring at the action tick never turns a within-lag violation into a beyond-lag one; (ii) the H1 cells (hardened, adversary none/minority/feed/feeds2) still show **0 unexplained** violations. Both true = CONFIRMED. Counts of flips are reported in full. |

Attribution to an adversary capability (`kind = adversary`) depends on the fuzzer's internal state and is **not** re-derived
by the oracle; H11 does not test it. The oracle reads the exogenous events (sanction, delist, revoke) from the fuzzer's own
action text, so H11 checks the oracle's eligibility, age and violation logic, not whether an event was applied to the
system correctly. If H11b shows flips, the paper reports both counts, keeps the conservative convention as primary and
does not change the frozen fuzzer.

Frozen at this addendum: `oracle_independent.py`, `fuzz_observed.py`, `hypotheses_v2.py`, `ORACLE_SPEC.md` and
`tests/test_oracle_independent.py` are added to `docs/FREEZE.json`.

**Human-independent implementation (recommended, not yet done).** Give `docs/ORACLE_SPEC.md` (only) to a colleague who has
not read `fuzz.py` and ask for a third implementation; run it through `oi.compare`. Record the implementer and date here:
_______________.

## 4b. Addenda A3-A5: real-trace experiments (committed before any real data is run)

The code for these experiments is `traces/ofac.py`, `fuzz_replay.py`, `traces/timing.py`, `traces/bridge.py` and
`hypotheses_real.py`, frozen by this commit. The compliance layer stays simulated ("real traces, simulated compliance
layer"). The runner refuses to start unless `docs/data/datasets.json` has no `TODO`, tracked files are committed and the
freeze is intact; a `--force` run is flagged in the output.

**A3. OFAC replay (H12, H12b, H12c, H13, H16).**
* Source: OFAC's "Archive of changes to the SDN list", text files `sdnnew19.txt`-`sdnnew23.txt`
  (https://ofac.treasury.gov/specially-designated-nationals-list-sdn-list/archive-of-changes-to-the-sdn-list). Window
  2019-01-01 to 2023-12-31. The files are hashed (SHA-256) at run time. PDF-only years (2024-) are not used.
* Parsing: the layout was checked on a verbatim excerpt of `sdnnew22.txt` (`tests/fixtures/ofac_real_excerpt_2022.txt`); the
  other years are checked by the parser's diagnostics (`ofac-parse` prints unrecognised headers and over-long entries). Parser
  corrections made before any H12 run are allowed and committed; none after.
* Events: every "added" and "removed" entry (individuals, entities, vessels, aircraft; alias rows count as entries). "Changed"
  entries only rename an identity. Identity is a heuristic primary-name key (`entry_key`); this is a stated limitation.
* Pool: entries whose first in-window event is an add and that are later removed at least once. Each trace samples 3 entries
  (seeded by the trace seed) and binds them to the accredited participants `u, a1, a2`; `z` stays permanently sanctioned.
* Schedule: the real order of the bound entries' add/remove events is replayed as the fuzzer's own sanction/delist actions.
  Real time gaps are not preserved. Two variants, both required: `spread` (events evenly spaced from step 2) and `burst`
  (consecutive steps from step 2). Events beyond step 35 are dropped.
* Cells: baseline/none, hardened/none, hardened/quorum, hardened/quorum+censor, hardened/issuer, each in both variants; 600
  traces x 40 steps; seeds 50,000-50,599. Revocations stay synthetic (no real revocation data).

| ID | Criterion (both variants must satisfy it) |
|---|---|
| H12 | hardened/none: 0 UNEXPLAINED, 0 adversary-attributed, 0 crashes or trail failures; at least one real event applied. |
| H12b | baseline/none: > 0 violations in each variant (otherwise INCONCLUSIVE, the replay is vacuous). |
| H12c | the independent oracle (H11) agrees with the fuzzer's oracle on every replay violation: 0 disagreements. |
| H13a-c | the criteria of H2, H3 and H4 hold under replay. |
| H16 | at least one entry is removed and later re-added in the window; else INCONCLUSIVE (not a pass). |

**A4. Real transaction timing (H14).** One on-chain activity series with at least 1,000 timestamps over at least 90 days,
declared in `datasets.json` (source, chain, contract or filter, window). Gaps are rescaled to a mean of 10 ticks. Circular
block resampling (block 300, 40 resamples, seed 2026); epoch ratios 1, 2, 3, 5, 8, 10, 20; reaction delay mean 2 ticks. The
synthetic sweep is run beside it. Criterion as in section 3. The series' burstiness (coefficient of variation) is reported.

**A5. Bridge latency (H15, descriptive).** One bridge route, at least 100 completed transfers, source and destination
timestamps declared in `datasets.json`. Reported: median, 95th and 99th percentile, share above 60 s, 300 s and 3,600 s;
negative latencies are dropped and counted. No tick mapping is imposed.

**Data rules.** Aggregate statistics only; no attempt to identify any person or address. Respect each source's terms.

## 4c. Official-run procedure and replication (committed before any real-data run)

Because the authors work without a local development environment, the **official run is executed by a GitHub Actions
workflow** (`.github/workflows/rwa-threatlab-official-run.yml`) from the tag `v1.3-prereg-real`, on a clean GitHub-hosted runner:

1. check out the tag; install; run the full test suite and `scripts/freeze.py check` (the run aborts if either fails);
2. download `sdnnew19.txt`-`sdnnew23.txt` from treasury.gov (a file already committed in `docs/data/raw/` is used as is);
   record SHA-256 of every file and the UTC retrieval time;
3. parse with `python -m rwa_threatlab ofac-parse` (the run aborts on any unrecognised header or an empty result);
4. run `python -m rwa_threatlab real --only <sections> --out docs/results/real`, which itself refuses to run if tracked
   files are uncommitted, the freeze is broken or a dataset is undeclared;
5. publish outputs, the raw files and an evidence folder (run URL, commit, hashes, parse log) to a new branch
   `official-run-<run id>`, never to main, and as a workflow artifact.

**Independent replication.** The same command is re-run in a second, separate environment (a separate environment used within the research effort)
from the committed raw files and the same tag, and `real.json` is compared field by field excluding the provenance fields
(Python build, CI run link, timestamps). Agreement or any difference is reported. The replication does not count as a
second sample (the computation is deterministic); it checks that the result does not depend on the machine.

**Stages.** The OFAC section (H12, H12b, H12c, H13, H16) needs no manual data and is run first. H14 and H15 need CSV exports
the authors take from public explorers; their datasets are declared and committed (new tag) before their own run.

**Limits of this record.** A git tag can be moved or deleted by the repository owner. The defence is an independent
registration of this document (for example an OSF registration made before the run, or an archived release) and the Actions
run log, which the owner cannot edit. The replication environment is used within the research effort, so it is not an
independent third-party replication; a third party re-running the workflow on the tag is the strongest check.

## 5. Reporting commitments

* All outcomes are reported, including REFUTED and INCONCLUSIVE ones, side by side with the synthetic results.
* Real-trace results are labelled "real traces, simulated compliance layer", never "live system".
* Parameters are not tuned to improve a result. Sweeps use the pre-stated ratios.
* Aggregate statistics only; no attempt is made to identify any real person or address (see `DATA.md`).

## 6. Deviation log

| Date | Change | Reason | Frozen files touched | Seed range consumed |
|---|---|---|---|---|
| (pre-run) | `traces/timing.py`, `traces/bridge.py`, `hypotheses_real.py`: CSV column names configurable via `datasets.json`; naive timestamps read as UTC; provenance records raw-file hashes and the CI run link; official-run workflow added | needed to run without a local environment and to accept explorer exports with their own headers; made before any real data were run | traces/timing.py, traces/bridge.py, hypotheses_real.py, tests/test_real_traces.py | none |
| (A3-A5) | real-trace code and design fixed before any real data is run | the OFAC archive format was inspected (only a verbatim excerpt of 2022) while designing the parser | none (additive files only) | none |
| (A2) | H11 refined into H11a/H11b before any run on its reserved seeds | the paper's definition leaves two conventions open (spec section 5); exploratory seeds showed they matter | none (additive files only) | none |
| (v1.1) | `hypotheses.py` H10 uses 20,000 trials instead of 5,000 | the paper reports 72% from 20,000 trials; the code printed 71% | hypotheses.py, docs/results | none (H10 is descriptive and uses its own seed 2026) |

Earlier deviations (C1-C3) are in `FINDINGS.md` section B.

## 7. Run log

| Hypothesis | Seeds | Commit before run | Outcome |
|---|---|---|---|
| H11a | 40,000-40,599, 8 cells | `75d9073` (addendum A2 and freeze) | **CONFIRMED**: 2,824 violations compared (baseline 186; hardened none 5, minority 1, feed 1, feeds2 1, quorum 1,070, quorum+censor 1,181, issuer 379), 0 disagreements |
| H11b | same | same | **CONFIRMED**: measuring at the action tick moves 31 of 2,824 violations from beyond-lag to within-lag and none the other way; the H1 cells show 0 unexplained under all four conventions |

Notes. (1) The first invocation of `python -m rwa_threatlab h11` printed these results and then crashed while writing the
output files, because of a variable-name clash in `__main__.py` (command-line glue, not part of the frozen instrument). The
glue was fixed and the command re-run only to save the files; the computation is deterministic and the numbers were identical.
No hypothesis, parameter or seed was changed. (2) H11 checks the oracle's own logic (see addendum A2 for what it cannot check).
Results: `docs/results/h11.json`, `docs/results/h11.md`.
