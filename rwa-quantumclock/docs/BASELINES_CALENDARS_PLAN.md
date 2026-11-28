# Stronger baselines and calendar robustness: plan (post-registration)

Written and committed on 2026-11-28, **before** any run.
This is a post-registration analysis. It is not part of the pre-registered study in
`docs/PREREGISTRATION.md`. The pre-registered results, including the negative ones, stay as they are.

## Why

Two facts from the frozen held-out run motivate this analysis.

1. The six list baselines do not read renewal calendars; QAMP does. QAMP planned without calendars
   ("no windows", USD 399.2m) costs about the same as greedy risk (USD 399.6m). So most of QAMP's lead
   over the best list baseline may come from calendar information, not from the optimiser.
2. Of the 28 observed calendars, 26 renew every quarter and 2 every three quarters. The other 47 are
   assumed annual. A quarterly calendar has no decision window, so the value of the windows rests mainly
   on assumed calendars.

Questions: (A) Does QAMP still beat baselines that get the same information? (B) How much does planning
over many arrival dates add, compared with planning for one date? (C) What happens when the calendars
are wrong?

## Ground rules

1. No code in `src/` changes. New baselines live in `tools/` and use the frozen functions. We record the
   `src/` and `kb/` fingerprints before and after.
2. Every new baseline gets the same information as QAMP: calendars, delay distribution, capacity,
   migration durations, rule deadlines and retention, and the same overflow rule. All plans are scored
   with the same frozen evaluation code.
3. Seeds: the held-out base (50,000), for comparison with the paper, and a fresh base (90,000) that has
   never been used, as a check against tuning. 20,000 planning and 2,000 evaluation scenarios.
4. No hypotheses about QAMP being better. Everything is reported, whatever the result.
5. Decision rule fixed now: QAMP's optimiser is said to add value over a calendar-aware heuristic only if
   the 95% interval of the paired difference lies above zero on **both** seed bases. Otherwise we report
   that, in this data, the optimiser adds no measurable value over that heuristic.

## Policies

Frozen (unchanged): QAMP (stochastic), QAMP no windows, QAMP expected, ASAP, greedy risk, Mosca.

New, all calendar-aware:

| ID | Policy | How it plans |
|----|--------|--------------|
| B1 | Calendar-aware greedy risk | Order by value at risk times attack weight. Give each anchor the latest start that still takes effect at its earliest reachable boundary even with one quarter of delay, within capacity. |
| B2 | Earliest last start first | For each anchor, find the last start that still reaches its earliest boundary with one quarter of delay. Order by that start (ties by risk), then schedule each at its latest fitting start, as in B1. |
| B3 | Greedy on QAMP's cost table | Use QAMP's own expected-cost table (calendars, 20,000 scenarios, rules). Order by risk; give each anchor its cheapest start that fits capacity and meets its deadline. Only the optimiser differs from QAMP. |
| B4 | One arrival date, mean | QAMP's MILP with the arrival distribution replaced by its mean (planning set). Delays as in QAMP. |
| B5 | One arrival date, median | As B4 with the median. |

B4 and B5 against QAMP give the value of planning over many arrival dates (the "value of the stochastic
solution" in stochastic programming). "QAMP expected" is not this test: it removes delays but keeps the
20,000 arrival dates.

## Experiments

**E1. Baselines.** All policies, both seed bases, in three settings: the main setting, all calendars every
quarter (as in the frozen `period1` run), and the tight setting (8-quarter renewals, one migration at a
time, as in the frozen `tight` run).

**E2. Wrong calendars.** Plan on the frozen calendars; score on different true calendars for the 47
assumed anchors (observed calendars unchanged). True calendars: annual with a random phase; every 2
quarters; every quarter; every 8 quarters. Phases are random, 10 draws per case (draw seed 90,100).
Held-out seeds. All policies.

**E3. Assumed period.** Set the 47 assumed calendars to 1, 2, 4 or 8 quarters for both planning and
scoring (phase = frozen phase modulo the period). Held-out seeds. All policies.

Flexible boundaries are the every-quarter case (E1, E2, E3). Partly flexible boundaries (an early change
at a fee) are not in the model and are reported as a limitation.

## What we measure

- Mean realised cost per policy, with a 95% interval.
- Paired difference of each policy minus QAMP, with a 95% interval (same scenarios).
- Expected deadline misses; share of value protected by 2030 and 2032.
- E2: the above averaged over the 10 draws, with the spread across draws.
- Code and rules unchanged (fingerprint and git).

## Outputs

- `tools/baselines_calendars.py`
- `notebooks/baselines_calendars.ipynb`, the run copy and a cropped screenshot in `notebooks/runs/`
- `results/exploratory/baselines_calendars.json` and `.md`
- A section in the supplementary file and a short subsection in the paper, both labelled
  post-registration, and the text changes the results require (including the abstract and highlights
  if a headline claim no longer holds).
