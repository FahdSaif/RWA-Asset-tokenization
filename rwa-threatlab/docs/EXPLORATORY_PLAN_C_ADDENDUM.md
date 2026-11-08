# Addendum to the exploratory plan, section C (census of privileged control): rules fixed before any data are fetched

Status: written on 8 November 2026, after experiments A and B were complete and **before any census data were fetched**. It makes section C of `docs/EXPLORATORY_PLAN.md` exact. Exploratory; not part of the OSF registration. Tag: `v1.6-census-plan`.

## 1. Sample

The 25 contracts in `docs/data/exploratory/census_tokens.txt`: the first 25 rows, in the order displayed, of Etherscan's "Real World Assets" token label page (841 records, sorted by market cap descending, seen on 2026-11-08). No exclusions, no replacements. A contract that cannot be read is kept and reported as unreadable.

## 2. What is observed (Etherscan API V2, Ethereum mainnet, latest block at retrieval)

For each contract: (a) `getsourcecode`: whether the source is verified, the contract name, Etherscan's proxy flag and implementation address, and the ABI; for a proxy the ABI of the implementation is read as well and the function names of both are merged; (b) storage slot reads (`eth_getStorageAt`) of the EIP-1967 admin slot `0xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103` and implementation slot `0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc`; (c) calls (`eth_call`) to `owner()` `0x8da5cb5b` and `defaultAdmin()` `0x84ef8ffc`; (d) for every address found in (b) or (c), and for the owner of such a contract (one further hop, at most): `eth_getCode` (empty means externally owned account), `getThreshold()` `0xe75235b8`, `getOwners()` `0xa0e67e2b` (the length of the returned array), `getMinDelay()` `0xf27a0c92` and `owner()`.

## 3. Classification rules (applied by `src/rwa_threatlab/exploratory/census.py`, not by hand)

*Controller type of an address:* zero address: `none`; no code: `eoa`; code and `getThreshold()` answers: `multisig` (with threshold and number of owners when readable); else `getMinDelay()` answers: `timelock` (with the delay); else, if it answers `owner()` and one hop remains, the type of that owner is reported with the note "via contract"; otherwise `other_contract`. An address whose observations are missing is `unknown`.

*Upgrade control:* not a proxy (Etherscan flag false and implementation slot empty): `no proxy detected`. Proxy and EIP-1967 admin slot non-zero: the controller type of the admin. Proxy and admin slot empty: `not readable` (for example UUPS, where the authority sits in implementation logic).

*Owner control:* the controller type of `owner()` if the contract answers it, else of `defaultAdmin()`, else `no owner() or defaultAdmin()`.

*Privileged-function categories* (case-insensitive match on function names of the merged ABI; presence only, not who may call them): pause: `pause`; freeze or blacklist: `freeze`, `frozen`, `blacklist`, `blocklist`, `denylist`, `sanction`; forced transfer or recovery: `forcedtransfer`, `forcetransfer`, `clawback`, `seize`, `confiscate`, `recoveryaddress`, `recoveraddress`, `forceburn`; mint or burn by name: names starting with `mint` or `burn`; upgrade: `upgradeto`, `setimplementation`.

## 4. Report

Counts and shares only: verified source; proxy; control type of upgrade control among proxies; control type of owner control; presence of each category; number of contracts with any error or unreadable item. A per-token table is published with the contract names exactly as returned.

## 5. Limits

At most 25 tokens, selected by a curated label ranked by market cap; control exercised through role-based access control cannot be read with these calls and is reported as `not readable` or `no owner() or defaultAdmin()`; a function name shows that a capability exists in the code, not that anyone can use it or has used it; no conclusion about the intent or the risk of any named token is drawn, and a single snapshot is taken.
