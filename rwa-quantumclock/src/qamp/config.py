"""Global settings. Every value used in an experiment is recorded in the run's output (see evaluate.py)."""
from __future__ import annotations

from pathlib import Path

START_YEAR = 2027              # quarter 0 = 2027 Q1
HORIZON_QUARTERS = 56          # loss accounting to 2040 Q4
PLAN_LAST_QUARTER = 35         # the last quarter in which a migration may start (2035 Q4)

QAMP_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = QAMP_ROOT.parent
THREATLAB = REPO_ROOT / "rwa-threatlab"
CENSUS_RAW = THREATLAB / "docs" / "data" / "exploratory" / "census_raw.json"
CENSUS_TOKENS = THREATLAB / "docs" / "data" / "exploratory" / "census_tokens.txt"
KB_DIR = QAMP_ROOT / "kb"
DATA_DIR = QAMP_ROOT / "data"
RESULTS_DIR = QAMP_ROOT / "results"

# Seeds. Development seeds are used freely; held-out seeds are reserved for the pre-registered run and must not be
# used before the instrument is frozen (docs/PREREGISTRATION.md).
DEV_SEED_BASE = 0
HELD_OUT_SEED_BASE = 50_000


def quarter_label(q: int) -> str:
    return f"{START_YEAR + q // 4} Q{q % 4 + 1}"


def year_end_quarter(year: int) -> int:
    """Index of the last quarter of ``year`` (e.g. 2030 -> quarter of 2030 Q4)."""
    return (year - START_YEAR) * 4 + 3
