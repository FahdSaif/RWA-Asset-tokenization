# Findings from adversarial evaluation (read this before the results)

An adversarial stateful fuzzer (`src/rwa_threatlab/fuzz.py`) drives a full two-chain deployment with random user
actions, exogenous regulatory events (sanctions, delistings, revocations) and a chosen adversary capability set. An
*oracle of truth* tracks who is legally eligible at every tick; any participant whose balance rises while ineligible is a
violation, classified as **documented-lag** (inside the paper's stated windows), **adversary** (a capability had a
recorded harmful effect) or **UNEXPLAINED** (a hole the paper did not predict).

## A. Genuine defects found in the implementation (and in the paper's M4/M5 design)

All three were found on *exploratory* seeds 0-399 against the hardened build with **no adversary at all**.

| # | Defect | Counterexample (seed) | Root cause | Fix | Regression test |
|---|---|---|---|---|---|
| F1 | **Lost update.** A pending relaxation silently undid a newer sanction. | hardened/none, seed 26 and others | Proposals carried whole rule-set snapshots; activation overwrote whatever had changed since. | Proposals are applied as a *delta* on the current rule set (`Governance._rebase`); concurrent rule-content changes fail closed. | `test_pending_relaxation_does_not_overwrite_a_later_tightening` |
| F2 | **Fail-open expiry.** A legitimate sanction lapsed after its expiry. | hardened/none, seed 55 | "Auto-expire unless ratified" reverted to the previous snapshot, i.e. to a *less* restrictive state, in a system that is supposed to fail closed. | Expiry is a **review deadline**: a tightening consistent with the regulator's list is kept; an inconsistent one is undone. | `test_expiry_keeps_a_consistent_sanction_and_only_undoes_its_own_delta` |
| F3 | **Expiry undid a re-asserted sanction.** | hardened/none, seed 26 after F1-F2 | Consistency was judged by whole-set equality with *today's* truth, so an old proposal looked inconsistent after the truth moved on, and its undo removed a name that was currently, legitimately sanctioned. | A proposal is judged by its own delta (each name it adds must be truly sanctioned; none it removes may be), and only failing names are undone (`Governance.consistent`). | `test_expiry_never_undoes_a_name_that_is_currently_sanctioned_in_truth` |

Effect on the exploratory campaign (hardened build, no adversary): 11 unexplained violations in 300 traces before the fixes,
0 in 400 after. F2 contradicts the paper's earlier wording of M5 ("auto-expiring unless ratified"), which has been corrected.

## B. Corrections to the measuring instrument (disclosed because they were made after seeing results)

| # | Correction | Triggered by |
|---|---|---|
| C1 | Honest watchers now check before every tick, not once per step. | 5 residual unexplained violations that replay showed were a stale delisting activating in the same tick as a re-sanction. |
| C2 | A relaxation counts as *harmful* only if it removed a name the regulator sanctions, not whenever an adversary proposal activates. | H2 and H3 came out REFUTED on the first held-out seeds because harmless activations were credited as attacks. |
| C3 | Harm is judged at the moment of activation, not against later truth. | H2 and H3 still REFUTED by 2 cases; replay showed the regulator had delisted the name, then re-sanctioned it after the relaxation activated. |

Each correction was made after inspecting the replayed counterexample, but changing the method after seeing a result is a
researcher degree of freedom and should be read as such. The paper's threats-to-validity section says so.

## C. Seed ledger

| Seeds | Use |
|---|---|
| 0-399 | exploratory: finding and fixing F1-F3, debugging the fuzzer |
| 10,000-10,599 | first held-out run: spent (H2/H3 refuted by instrument error C2) |
| 20,000-20,599 | second held-out run: spent (2 cases, instrument error C3) |
| **30,000-30,599** | **final confirmation run** (the reported results, `docs/results/hypotheses.md`) |

## D. What this does and does not show

* It shows that, in this implementation, no violation occurs outside the documented lag windows unless an adversary holds a
  trust-anchor capability, **after** three defects that only adversarial search found were fixed.
* It does not show that real systems have these properties. The implementation is a simulation (see `LIMITATIONS.md`), the
  oracle of truth is the author's model of legal eligibility, and the fuzzer explores only the action space the author wrote.
* "All hypotheses confirmed" is a statement about a final, corrected instrument on fresh seeds. The earlier refutations and
  corrections are part of the evidence and are kept here on purpose.
