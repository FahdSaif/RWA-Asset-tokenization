# Experiment B data: provenance and verification (written before the analysis was run)

Plan: docs/EXPLORATORY_PLAN.md, section B (tag v1.6-exploratory-plan, commit 93629f8). Fetched with docs/data/exploratory/B_fetch_blacklist_events.ipynb (Google Colab) on 2026-11-08 (02:47 UTC) from the Etherscan API V2, from block 6,900,000 to the latest block.

* USDC `Blacklisted(address)`: 949 events in total (2020-06-16 to 2026-11-06); USDT `AddedBlackList(address)`: 3,206 events in total (2018-12-28 to 2026-11-06).
* The 141 OFAC addresses of the plan (extracted by the repository code from the tagged OFAC files) all appear at both issuers; one address has two events at each issuer (the first event is used, as planned).
* `blacklist_events_ofac_subset.csv` (284 rows) contains only the events for OFAC addresses. The full raw logs (public addresses, 949 and 3,206 events) are held by the authors; their SHA-256 digests are in `blacklist_summary.json`.

## Verification performed (no delay or any other result was computed)

* every digest in the summary matches its file; no API key appears in any file;
* the subset CSV is identical to an independent rebuild from the raw logs and the tagged OFAC addresses;
* all decoded addresses are valid 20-byte hex strings; blocks and timestamps are non-decreasing; there is no duplicate (transaction, address) pair; USDC indexes the address, USDT carries it in the data field, and both decode to the same 141 OFAC addresses.

## Limits

One snapshot (retrieval date above). Blacklist events show what the issuers did, not why. The logs were fetched once.
