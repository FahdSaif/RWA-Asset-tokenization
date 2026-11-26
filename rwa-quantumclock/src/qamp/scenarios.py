"""Scenarios: when a quantum computer arrives, and how late each migration runs.

Arrival: fitted to the GRI 2025 expert survey (28-49% within 10 years, 51-70% within 15),
with no arrival before 2027. `shift_years` moves it earlier.
Delay: -1, 0 or +1 quarter with chances 15%, 55%, 30% (an assumption)."""
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
    """Weibull shape and scale that match the survey at 10 and 15 years."""
    a, b = -math.log(1 - p10), -math.log(1 - p15)
    k = math.log(b / a) / math.log(15 / 10)
    lam = 10 / a ** (1 / k)
    return k, lam


def _weibull_cdf(x: float, k: float, lam: float) -> float:
    return 0.0 if x <= 0 else 1 - math.exp(-((x / lam) ** k))


@dataclass
class ScenarioSet:
    """Arrival quarter per scenario and delay per scenario and anchor."""
    crqc_quarter: np.ndarray            # one per scenario
    delta: np.ndarray                   # per scenario and anchor
    seed: int
    params: dict = field(default_factory=dict)

    def __len__(self) -> int:
        return len(self.crqc_quarter)


def sample(n: int, n_anchors: int, seed: int, shift_years: float = 0.0, delta_probs=DELTA_PROBS,
           fixed_interpretation: float | None = None) -> ScenarioSet:
    rng = np.random.default_rng(seed)
    start = config.START_YEAR - SURVEY_YEAR        # years from the survey to 2027
    t = np.empty(n)
    for s in range(n):
        u = rng.uniform() if fixed_interpretation is None else fixed_interpretation
        p10 = GRI["p10"][0] + (GRI["p10"][1] - GRI["p10"][0]) * u
        p15 = GRI["p15"][0] + (GRI["p15"][1] - GRI["p15"][0]) * u
        k, lam = weibull_params(p10, p15)
        # only arrivals after 2027
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
    """Share of scenarios with an arrival by the end of each year."""
    out = {}
    for y in years:
        q = (y - config.START_YEAR + 1) * 4
        out[y] = float(np.mean(ss.crqc_quarter < q))
    return out
