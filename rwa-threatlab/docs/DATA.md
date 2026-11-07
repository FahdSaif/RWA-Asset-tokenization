# Data statement (datasheet)

**All data in this repository is synthetic.** No real participant, credential, transaction, sanction list or regulatory
record is used, and nothing here claims to be calibrated to a production system. The generators are designed to be
*plausible and falsifiable*, not to impersonate real data.

| Where | What is generated | Process and parameters | Why this form |
|---|---|---|---|
| Scenario worlds | 3-6 named participants, credentials, sanction lists, oracle feeds | hand-written fixtures (`scenarios/base.py`) | each attack-tree leaf needs a precise, inspectable setup |
| D1 timing linkage | off-chain event times and on-chain submission times | heavy-tailed inter-event gaps (log-normal, sigma = 1, mean 10 or 50 ticks); exponential reaction delay (mean 2); batching epochs of 100 ticks | real activity is bursty, not evenly spaced; heavy tails make collisions that lower attacker accuracy |
| D2 anonymity sets | 400 participants over 8 jurisdictions | Zipf weights (s = 1.0): a few jurisdictions hold most investors | real investor bases are concentrated, so worst-case anonymity sets are far smaller than the mean |
| D3 issuer linkage | issuance times and presentation delays | Poisson issuance (mean gap 3 ticks); exponential presentation delay (mean 1 or 60 ticks) | memoryless delays are a neutral baseline |
| Fuzzer | 6 participants, 3 oracle feeds, 5-member quorum (threshold 3), random action sequences of 40 steps | seeds recorded in `docs/FINDINGS.md` | exercises interleavings a hand-written scenario would not |

**Parameter choice.** Values were chosen to be reasonable, not fitted. Because of that, no single number should be quoted
as a real-world rate. The robust claims are the *shapes and boundaries* (for example, batching helps only above a few events per
epoch; see the sweeps in `docs/results/hypotheses.json`). Each D-row result is reported over 40 seeds with a 95 % interval.

**Using real data.** The privacy attackers accept real traces:

```python
from rwa_threatlab.scenarios.privacy import load_event_pairs_csv, linkage_from_pairs
pairs = load_event_pairs_csv("traces.csv")        # header: event_tick,submit_tick
print(linkage_from_pairs(pairs))
```

Suitable real sources include exchange-withdrawal timestamps paired with on-chain submission times, or issuer logs paired
with presentation times, subject to the data owner's terms and applicable data-protection law. Sanction-list structure can be
checked against published government lists. If you run real data, report it as a separate, labelled experiment; do not mix it
with the synthetic results.

**Personal data.** None. Participant names are labels (`u`, `x`, `z`, `p17`).

## Real traces (journal extension)

Pre-registered in `docs/PREREGISTRATION.md` (addenda A3-A5) and run with `docs/REAL_DATA_RUNBOOK.md`. Real data enter in three
places only; the compliance layer stays simulated.

| Experiment | Real input | What is used | What stays synthetic |
|---|---|---|---|
| H12-H13, H16 | OFAC `sdnnew19.txt`-`sdnnew23.txt` (public US Government text) | order and add/remove/re-add structure of real list entries | time gaps (compressed), revocations, participants, credentials |
| H14 | one on-chain activity series (declared in `datasets.json`) | inter-arrival shape (burstiness), rescaled to mean 10 ticks | reaction delay, batching rule, the off-chain event pairing |
| H15 | one bridge route (declared) | latency distribution (descriptive) | nothing is simulated |

No personal data are used or inferred; entries are keyed by name only to track add/remove history, and only aggregate counts
are reported. Check each source's terms before redistributing a dataset. Test fixtures (`tests/fixtures/`) are format
fixtures: one is invented, one is a short verbatim excerpt of the 2022 OFAC change file; neither produces a reported result.
