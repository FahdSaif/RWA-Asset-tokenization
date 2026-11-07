# Specification of the oracle of truth (for the independent implementation, H11)

This document is the only input an independent implementer needs. It restates the definition in the paper (Section 4.6:
"an oracle of truth tracks who is legally eligible at every tick; any participant whose balance rises while ineligible is a
violation, classified as documented-lag ... ") precisely enough to implement. It does not describe the fuzzer's code.
Where the paper's sentence is ambiguous, the ambiguity is named (section 5) and BOTH readings are specified.

## 1. Fixture (scenario data, not code)

* Participants: `u, x, z, a1, a2, k1`. The account `treasury` is the issuer's own account and is never evaluated.
* Accredited investors: `u, z, a1, a2`. Not accredited: `x, k1`. Accreditation never changes.
* Chains: `O` and `D` (two instances of the architecture).
* At the start `z` is on the sanctions list, and the regulator never removes it.
* Documented lag window: `L_DOC = 6` ticks.
* "Before the run" is tick `-1000`: a listing or non-accreditation that holds at the start began at tick `-1000`.

## 2. Input: the step log

One record per step, in order: `step` (0-based), `tick_before`, `tick_after`, `action` (text), `before` and `after`
(balance of every `(chain, participant)` pair, read from the ledger before the action and after the step's clock advance).
At most one action happens per step. The action text may be one of:

| Text | Meaning | Effect on eligibility |
|---|---|---|
| `sanction(n)` | regulator lists participant `n` | `n` is listed from `tick_before` |
| `delist(n)` | regulator removes `n` from the list | `n` is not listed from `tick_before` |
| `revoke(n)` | issuer revokes `n`'s credential, permanently | `n` is revoked from `tick_before` |
| anything else, including `...(skip)` | no effect on eligibility | none |

## 3. Definitions

* `n` is **eligible** at a moment iff accredited, not currently listed, and not currently revoked. Otherwise **ineligible**.
* A **violation** is a triple `(step, chain, n)` such that `n` is a named participant, the balance of `(chain, n)` is
  larger in `after` than in `before`, and `n` is ineligible. Events of a step apply before its balance check.
* The **age** of an ineligibility at a measurement tick `T` is `T - since(n)` (section 5 defines `since` and `T`).
* A violation is **within lag** iff `0 <= age <= L_DOC`, else **beyond lag**.

## 4. Output

For every violation: `step, chain, n, age, within_lag`.

## 5. Named ambiguities (the paper does not say; both readings are implemented)

| | Reading A | Reading B |
|---|---|---|
| **Measurement tick `T`** | `END`: the step's `tick_after` | `ACTION`: the step's `tick_before`, the tick at which the balance changed |
| **Origin `since(n)`** | `EARLIEST_ACTIVE`: the earliest start among the reasons that currently hold (non-accreditation, listing, revocation) | `CONTINUOUS`: the start of the present uninterrupted ineligibility, i.e. the tick at which `n` last changed from eligible to ineligible |

The fuzzer's code uses (END, EARLIEST_ACTIVE). The author of this specification identified that by reading the code; this is
disclosed in `PREREGISTRATION.md` addendum A2. (ACTION, CONTINUOUS) is the reading the paper's wording suggests most directly.
