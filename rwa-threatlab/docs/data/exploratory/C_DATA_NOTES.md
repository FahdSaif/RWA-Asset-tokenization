# Experiment C data: provenance and verification (written before the analysis was run)

Plan: `docs/EXPLORATORY_PLAN.md` section C and `docs/EXPLORATORY_PLAN_C_ADDENDUM.md` (tag `v1.6-census-plan`, commit 7af15fa). Fetched with `docs/data/exploratory/C_fetch_census.ipynb` (Google Colab) on 2026-11-08 (09:45 UTC) from the Etherscan API V2, at the latest block at that time, for the 25 contracts of `census_tokens.txt`.

Files: `census_raw.json` (the raw observations of the 25 contracts: source verification, ABI function names, proxy slots, `owner()` and `defaultAdmin()` answers, and the controller observations), and `census_summary.json` (counts, retrieval time and the SHA-256 digest of the raw file). The classification of the observations is done only by `src/rwa_threatlab/exploratory/census.py`, on GitHub, from the committed data.

## Verification performed (no classification or result was computed)

* the digest in the summary matches `census_raw.json`; no API key appears in any file;
* the 25 contracts are exactly the contracts of `census_tokens.txt`, in the same order; every record has all fields; every address is a well-formed 20-byte hex string;
* no read error was recorded for any contract (calls to functions that a contract does not have are expected to revert and are not counted as errors).

## Limits

A single snapshot at the retrieval time; function names show that a capability exists in the code, not who may use it; control through role-based access control cannot be read with these calls.
