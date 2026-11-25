"""Threat scenarios: arrival of a cryptographically relevant quantum computer (CRQC) and execution-time deviations.

CRQC arrival
  Prior from the Global Risk Institute Quantum Threat Timeline Report 2025 (26 experts): a CRQC is 28-49% likely
  within 10 years and 51-70% likely within 15 years (the range spans the low and high interpretations of the
  answers). Per scenario we draw u ~ U(0, 1), set p10 = 0.28 + 0.21 u and p15 = 0.51 + 0.19 u (one interpretation
  for both horizons), fit a Weibull CDF through (10, p10) and (15, p15) years after the survey year, and sample an
  arrival time conditional on no CRQC before the planning start (2027). ``shift_years`` moves the distribution
  earlier (the report's experts expected covert efforts could shift the timeline by two or more years).
  This is a modelling choice; sensitivity to it is part of the evaluation.

Execution-time deviation
  As in the authors' project-governance model, the execution time of a migration is uncertain by at most one
  period: delta in {-1, 0, +1} quarters with probabilities (0.15, 0.55, 0.30) (late more likely than early).
  ASSUMPTION, recorded in every run.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from . import config

SURVEY_YEAR = 2025.0
GRI = dict(p10=(0.28, 0.49), p15=(0.51, 0.70))
DELTA_VALUES = np.array([-1, 0, 1])
DELTA_PROBS = np.array([0.15, 0.55, 0.30])


def weibull_params(p10: float, p15: float) -> tuple[float, float]:
    """Shape k and scale lam (years) of a Weibull CDF with F(10) = p10 and F(15) = p15."""
    a, b = -math.log(1 - p10), -math.log(1 - p15)
    k = math.log(b / a) / math.log(15 / 10)
    lam = 10 / a ** (1 / k)
    return k, lam


def _weibull_cdf(x: float, k: float, lam: float) -> float:
    return 0.0 if x <= 0 else 1 - math.exp(-((x / lam) ** k))


@dataclass
class ScenarioSet:
    """S scenarios: CRQC arrival quarter (float, relative to quarter 0) and execution-time deviation per anchor."""
    crqc_quarter: np.ndarray            # shape (S,)
    delta: np.ndarray                   # shape (S, n_anchors), integer quarters
    seed: int
    params: dict = field(default_factory=dict)

    def __len__(self) -> int:
        return len(self.crqc_quarter)


def sample(n: int, n_anchors: int, seed: int, shift_years: float = 0.0, delta_probs=DELTA_PROBS,
           fixed_interpretation: float | None = None) -> ScenarioSet:
    rng = np.random.default_rng(seed)
    start = config.START_YEAR - SURVEY_YEAR        # years after the survey at quarter 0
    t = np.empty(n)
    for s in range(n):
        u = rng.uniform() if fixed_interpretation is None else fixed_interpretation
        p10 = GRI["p10"][0] + (GRI["p10"][1] - GRI["p10"][0]) * u
        p15 = GRI["p15"][0] + (GRI["p15"][1] - GRI["p15"][0]) * u
        k, lam = weibull_params(p10, p15)
        # sample conditional on arrival after the planning start (inverse CDF on the truncated range)
        lo = _weibull_cdf(start + shift_years, k, lam)
        v = lo + (1 - lo) * rng.uniform()
        years_after_survey = lam * (-math.log(1 - v)) ** (1 / k) - shift_years
        t[s] = max(0.0, (years_after_survey - start) * 4)
    delta = rng.choice(DELTA_VALUES, size=(n, n_anchors), p=delta_probs)
    return ScenarioSet(crqc_quarter=t, delta=delta, seed=seed,
                       params=dict(n=n, shift_years=shift_years, gri=GRI, survey_year=SURVEY_YEAR,
                                   delta_values=DELTA_VALUES.tolist(), delta_probs=list(map(float, delta_probs)),
                                   fixed_interpretation=fixed_interpretation))


def cumulative_probability_by_year(ss: ScenarioSet, years=(2030, 2032, 2035, 2040)) -> dict:
    """Share of scenarios with a CRQC by the end of each year (a check against the survey)."""
    out = {}
    for y in years:
        q = (y - config.START_YEAR + 1) * 4
        out[y] = float(np.mean(ss.crqc_quarter < q))
    return out
