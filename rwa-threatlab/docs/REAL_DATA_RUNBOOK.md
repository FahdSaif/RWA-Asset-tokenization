# Runbook: running the real-trace experiments (H12-H16)

**No local environment?** Use `docs/GITHUB_ONLY_GUIDE.md` (GitHub web interface + GitHub Actions). This runbook is the command-line version and also describes the data exports for H14 and H15.

Do these in order. The runner enforces the pre-registration: it refuses to run until the datasets are declared and the
tree is committed. Everything below runs on your computer; the data sources need internet access.

## 0. Check the install
```
cd rwa-threatlab
python -m pip install -e ".[dev]"
python -m pytest -q                 # all tests pass
python scripts/freeze.py check      # "frozen instrument intact"
```

## 1. OFAC change files (H12, H12b, H12c, H13, H16)
Download the five text files (public US Government data) into `docs/data/raw/`:
```
mkdir -p docs/data/raw && cd docs/data/raw
for y in 19 20 21 22 23; do curl -O https://www.treasury.gov/ofac/downloads/sdnnew$y.txt; done
cd ../../..
```
(Source page: https://ofac.treasury.gov/specially-designated-nationals-list-sdn-list/archive-of-changes-to-the-sdn-list)
Parse them into a normalised event file:
```
python -m rwa_threatlab ofac-parse --inputs docs/data/raw/sdnnew19.txt docs/data/raw/sdnnew20.txt docs/data/raw/sdnnew21.txt docs/data/raw/sdnnew22.txt docs/data/raw/sdnnew23.txt --out docs/data/ofac_events.csv
```
Read the printout. Each year should show many date blocks and entries, `headers` containing `add`, `remove` and `change`, and
**no `UNRECOGNISED HEADER` lines** and `long entries` near 0. If something is off, stop and keep the printout: parser fixes
are allowed before the run, not after (see addendum A3).

## 2. On-chain timing (H14)
Pick ONE token (or contract) with at least 1,000 transfers over at least 90 days; ideally a tokenised real-world asset.
Example with Google BigQuery's public Ethereum dataset (check the table and column names in the console first):
```sql
SELECT block_timestamp AS timestamp
FROM `bigquery-public-data.crypto_ethereum.token_transfers`
WHERE token_address = '0x...lowercase address of ONE token...'
  AND block_timestamp BETWEEN TIMESTAMP('2025-01-01') AND TIMESTAMP('2025-04-01')
ORDER BY block_timestamp
```
Export as CSV with a header line `timestamp` to `docs/data/timing.csv` (unix seconds or ISO-8601 both work). An explorer's
CSV export also works if you rename its time column to `timestamp`.

## 3. Bridge latency (H15)
One bridge route, at least 100 completed transfers. Export a CSV to `docs/data/bridge.csv` with header
`src_timestamp,dst_timestamp` (or a single `latency_seconds` column), one row per completed transfer. Use the bridge's own
explorer or API; record exactly how you obtained the rows.

## 4. Declare the datasets (this is the pre-registered record)
Edit `docs/data/datasets.json`: replace every `TODO` (source, chain, contract or filter, window, retrieved_on, ...). Do not
edit the OFAC window or file list. Then commit and tag BEFORE running:
```
git add docs/data/datasets.json docs/data/ofac_events.csv docs/data/timing.csv docs/data/bridge.csv
git commit -m "prereg: datasets declared (addenda A3-A5)"
git tag v1.3-prereg-real && git push && git push --tags
```
(Raw files in `docs/data/raw/` may be committed too. Check each source's terms before publishing a dataset.)

## 5. Run (once)
```
python -m rwa_threatlab real --out docs/results/real
```
Takes a few minutes. It prints a table of outcomes and writes `docs/results/real/real.json` and `real.md`, including file
hashes, the git commit and whether the freeze was intact. You can run one section with `--only ofac` (or `timing`, `bridge`).

## 6. After the run
```
python scripts/make_latex.py          # writes docs/latex/*.tex, including tab_real.tex
git add docs/results/real docs/latex && git commit -m "real-trace results (H12-H16)" && git tag v1.3-real-results
```
Report every outcome, including REFUTED and INCONCLUSIVE. If you find an instrument bug, do not patch silently: log it in
`docs/PREREGISTRATION.md` section 6, re-freeze with a reason, and rerun on the next reserved block (seeds 60,000+; edit
`REAL_SEED0` in `hypotheses_real.py` in the same commit and spend the block in the ledger).

## What the output means
* H12/H13 CONFIRMED: the paper's claims held when the fuzzer was driven by real sanctions histories (order and
  add/remove/re-add structure of real entries; real time gaps are not preserved).
* H12 REFUTED: a hole the synthetic stream did not expose. Inspect the `examples` in `real.json` (seed and actions).
* H16 INCONCLUSIVE: the window has no remove-then-re-add; say so in the paper.
* The compliance layer is still simulated; real data drive the events, timing and latency only.
