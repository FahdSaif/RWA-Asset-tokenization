# H14 data: provenance and selection (written before the H14 analysis was run)

H14 tests whether the batching boundary of H6 survives real transaction timing (`docs/PREREGISTRATION.md`, addendum A4: one on-chain activity series with at least 1,000 timestamps over at least 90 days).

## What was done, in order

1. **Token search.** Tokenised treasury and dollar-yield funds were searched on Etherscan. WisdomTree Floating Rate Treasury Fund (USFRon) was rejected because it has only 224 transfers in total (fewer than the 1,000 required). Ondo U.S. Dollar Yield (USDY) was chosen: 23,603 transfers in total, about 43 per day, a real tokenised-asset product. No other token was examined for its transfer series, and no timing analysis was run on any of them.
2. **Rule fixed in advance of the download.** All events of the latest window from the Etherscan API, reduced to one timestamp per distinct transaction hash (a swap or bridge creates several transfer events in one transaction), no other filter.
3. **First attempt (discarded).** The first run fetched 6,000 events (6 pages). They collapsed to 2,714 distinct transactions over 64.5 days, below the registered 90-day minimum, so that data set was not used. The reason was the registered minimum, not any result: no H14 analysis had been run. The window rule was then changed to "fetch whole windows of 10 pages until the registered minimum holds".
4. **Second attempt (used).** One window of 10 pages (10,000 events) gave 4,996 distinct transactions from 2026-06-29T13:22:47Z to 2026-11-08T00:46:35Z (131.47 days), retrieved 2026-11-08T01:37:48Z.
5. **Verification.** The CSV was rebuilt independently from the raw pages and is identical; all raw-page digests match `timing_summary.json`; all 10,000 events come from the USDY contract; no API key appears in any file.

## Files

* `timing.csv`: columns `timestamp` (Unix seconds, UTC) and `block`; this is the input of the analysis (`timestamp_column` in `datasets.json`).
* `timing_summary.json`: counts, window, retrieval time and SHA-256 digests of the ten raw pages and of `timing.csv`.
* `H14_fetch_usdy.ipynb`: the notebook that fetched the data (Google Colab).
* The ten raw API pages contain public addresses and are not committed; the authors hold them and their digests are recorded.

## Limits

One token, one chain, one time window; the timestamps are of transactions, not of the off-chain events that an attacker would correlate with, which remain simulated in the experiment. The series is used for its inter-arrival shape (burstiness) only.
