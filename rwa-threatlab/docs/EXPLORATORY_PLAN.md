# Exploratory real-data analyses: plan fixed before analysis (version 1, 8 November 2026)

**Status.** Three descriptive analyses of real Ethereum data that complement the pre-registered experiments (H1-H16). They are **exploratory** and are **not part of the OSF registration** (https://osf.io/64atb). This plan is committed and tagged (`v1.6-exploratory-plan`) **before** any of them is analysed; whatever they show is reported, and deviations are logged below. Code: `src/rwa_threatlab/exploratory/`; runner workflow: `.github/workflows/exploratory-run.yml`; results: `docs/results/exploratory/<name>/` (one folder per analysis, never overwritten).

**What was known before this plan (disclosure).** (i) The USDY transfer pages used for A were downloaded for H14; their *values* were not examined. (ii) A count of Ethereum-format addresses in the OFAC files (141 distinct addresses added 2019-2023, clustered on a few listing dates, 53 on 2022-11-08 and 38 on 2022-08-08) was made to judge the feasibility of B. (iii) Nothing for C has been fetched.

## A. Anonymity sets of real transfers under value bucketing and batching (supports D1, M9)

*Question.* In real token traffic, how large are the sets of transactions that an observer cannot tell apart once amounts are bucketed and submissions are batched into time epochs?

*Data.* The 10,000 USDY transfer events of the H14 download (`docs/data/exploratory/usdy_events.csv`, built without filtering from the raw pages whose SHA-256 digests are in `docs/data/timing_summary.json`).

*Method.* For each event, k = the number of **distinct transactions** with an event in the same cell of (time epoch, value bucket). Epochs are on a fixed grid of unix time: 1 min, 10 min, 1 h, 6 h, 1 day, whole window. Value bucket: the exact decimal value, or a relative width of 1%, 5%, 10% or 25% (bucket index = floor(ln v / ln(1+r))); zero values share one bucket. Report for every cell: the share of events with k = 1 (unique), the median k, and the shares with k >= 5 and k >= 20. Summary: for each epoch, the first bucket width in the grid order at which fewer than 5% of events are unique.

*Pre-stated reading rules (descriptive, no test).* A1: with exact values and a 1-hour epoch, at least 50% of events are unique (the amount alone fingerprints). A2: with 10% buckets and a 1-day epoch, fewer than 10% of events are unique. If A2 fails, bucketing and batching at this traffic volume do not give small anonymity sets, which would be consistent with H6 (batching helps only with enough concurrent traffic).

*Limits.* This measures the potential for linkage, not actual deanonymisation; one token and one 131-day window; multi-leg transactions are collapsed by counting transactions.

## B. Delay between OFAC listing and on-chain blacklisting (supports B2, C2, E1: real rule-activation windows)

*Question.* How long after OFAC first lists an Ethereum-format address do the two largest stablecoin issuers, Circle (USDC) and Tether (USDT), blacklist it on-chain?

*Data.* (1) OFAC: every 0x-format address in "added" entries of the five change files 2019-2023 (already in `docs/data/raw`), with the date of first listing. (2) Ethereum mainnet logs through the Etherscan API: USDC `0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48`, event `Blacklisted(address)` (topic0 `0xffa4e6181777692565cf28528fc88fd1516ea86b56da075235fa575af6a4b855`); USDT `0xdAC17F958D2ee523a2206206994597C13D831ec7`, event `AddedBlackList(address)` (topic0 `0x42e160154868087d6bfdc0ca23d96a1c1cfa32f1b72ba9ba27b69b98a0d819dc`); from block 6,900,000 (about December 2018) to the latest block at retrieval. The address is read from topic 1 if present, otherwise from the last 20 bytes of the data field. Only events for OFAC addresses are committed.

*Method.* For each (issuer, address) the first blacklist event is used; the delay in days is the UTC date of that event minus the OFAC listing date. Addresses never blacklisted by the retrieval date are censored. Report per issuer and for "either": the number blacklisted and its share, the median, quartiles and 90th percentile, the shares within 1, 7 and 30 days, and the share blacklisted before the OFAC date; and a per-listing-date table with the median of the per-date medians (to show the clustering).

*Pre-stated reading rules (descriptive, no test).* B1 (supports a window of days): among addresses blacklisted by either issuer, at least 80% within 7 days and a median of at most 7 days. B2 (contrary): a median above 30 days, or fewer than 50% of the OFAC addresses blacklisted at all by the retrieval date. Anything in between is reported as mixed.

*Limits.* Listings cluster on few dates, so the effective sample is the number of listing dates, not the number of addresses; delays have date resolution only; an issuer's blacklist is a proxy for an enforcement-rule update, not a protocol-level rule change; 0x addresses can belong to other EVM chains.

## C. Census of privileged control in real tokenised-asset contracts (supports F1, F2, Tables 10 and 12)

*Question.* In real tokenised-asset tokens on Ethereum, who can upgrade, freeze, pause or force-move tokens, and how is that control protected?

*Sample (fixed before any fetch).* The first 25 token contracts in the order Etherscan lists them under its "Real World Assets" label (top to bottom, as displayed), with no exclusions. The list of addresses is committed as `docs/data/exploratory/census_tokens.txt` before any data are fetched.

*Observations per contract.* Whether the source is verified; proxy or not and the implementation address; the EIP-1967 admin slot; `owner()` where present; for each controlling address: externally owned account or contract, Safe-style multisig (`getThreshold()`, `getOwners()`), timelock (`getMinDelay()`); function names in the ABI matched against fixed lists (pause, freeze/blacklist, forced transfer/recovery, mint/burn, upgrade).

*Report.* Counts and shares only: upgradeable or not; control type (none, single EOA, multisig m-of-n, timelock with delay, other contract, unknown); presence of each privileged function category.

*Limits.* At most 25 tokens; the label is curated by Etherscan; control exercised through role-based access (not readable with a single call) is reported as unknown; no inference about the intent or risk of any named token is drawn.

## Reporting commitments

All results are reported, whatever they show, in a clearly labelled exploratory subsection. Real-data results are labelled "real traces, simulated compliance layer" where the compliance layer is simulated and "measurement" where it is not. Raw API responses contain public addresses and are held by the authors; their digests are recorded. A change to this plan after a result is seen is a logged deviation.

## Deviation log

(none yet)
