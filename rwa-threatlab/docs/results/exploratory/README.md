# Exploratory results (plan: docs/EXPLORATORY_PLAN.md, tag v1.6-exploratory-plan)

These are exploratory analyses, not part of the OSF registration. Code and data are those of tag `v1.6-exploratory-data` (commit b9d444b) for A and B, and of tag `v1.6-census-data` (commit fda11ed; rules in `docs/EXPLORATORY_PLAN_C_ADDENDUM.md`, tag `v1.6-census-plan`) for C. Each result folder is copied verbatim from the results-only branch of the official run.

| Analysis | Official run | Results branch | Independent re-run |
|---|---|---|---|
| A, `kanon` (anonymity sets of USDY transfers) | https://github.com/FahdSaif/RWA-Asset-tokenization/actions/runs/42441479233 | `exploratory-kanon-42441479233` | identical |
| B, `latency` (OFAC listing to USDC/USDT blacklisting) | https://github.com/FahdSaif/RWA-Asset-tokenization/actions/runs/42441805299 | `exploratory-latency-42441805299` | identical |
| C, `census` (privileged control in 25 tokenised-asset contracts) | https://github.com/FahdSaif/RWA-Asset-tokenization/actions/runs/42468964853 | `exploratory-census-42468964853` | identical |

## Failed runs (infrastructure only)

Two earlier runs of the workflow failed before anything was published: run #1 (42440824165) because its first step ran in a folder that did not exist before the checkout, and run #2 (42441005945) because GitHub refused to let the workflow token push a branch that contained a workflow file differing from the one on `main`. The analysis code, the data and the plan were not changed; the workflow file was corrected twice (first step runs in the repository root; results are published as a branch that contains only the results). The runs listed above were made with the corrected workflow, from the unchanged tag.

## Outcomes against the rules fixed in the plan

* **A.** A1 holds (exact values, 1-hour epoch: 75.6% of events unique, rule at least 50%). A2 does not hold (10% buckets, 1-day epoch: 34.9% unique, rule below 10%). Fewer than 5% of events are unique only when all 131 days are pooled (5% buckets).
* **B.** By the measure fixed in the plan (addresses blacklisted by either issuer) B1 holds: 100% blacklisted, median 1 day, 96% within 7 days. The issuers differ sharply: USDC median 1 day (90th percentile 2 days, 96% within 7 days); USDT median 396 days (1% within 30 days), because 140 of the 141 addresses were first blacklisted by Tether on a single day, 2023-12-09, which is also the day Tether announced a voluntary freezing policy for OFAC-listed wallets. The effective sample is therefore 17 listing dates for USDC and one policy event for USDT. The OFAC files used end in 2023, so the delay after that policy change was not measured.
* **C (counts only, as planned).** 25 contracts, all with verified source; 21 are proxies. Among the 21 proxies, upgrade control is a multisig for 10 (9 of them 2-of-3), a timelock for 1 (2 hours), and not readable for 10. Owner control (owner() or defaultAdmin()): multisig 9, none or renounced 3, single externally owned account 2, timelock 1, no owner() or defaultAdmin() 10. Function names present: pause 20, upgrade 20, freeze or blacklist 11, forced transfer or recovery 3, mint or burn 23. Eight of the contracts are of one issuer family (same contract type), so the number of independent operators is smaller than 25. Function names show that a capability exists in the code, not who may use it; control through roles is not readable with these calls.
