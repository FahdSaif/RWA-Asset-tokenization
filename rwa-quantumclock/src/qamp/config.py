"""Settings. Each run records the values it used."""
from __future__ import annotations

from pathlib import Path

START_YEAR = 2027              # quarter 0 is 2027 Q1
HORIZON_QUARTERS = 56          # count losses up to 2040 Q4
PLAN_LAST_QUARTER = 35         # last quarter a migration can start (2035 Q4)

QAMP_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = QAMP_ROOT.parent
THREATLAB = REPO_ROOT / "rwa-threatlab"
CENSUS_RAW = THREATLAB / "docs" / "data" / "exploratory" / "census_raw.json"
CENSUS_TOKENS = THREATLAB / "docs" / "data" / "exploratory" / "census_tokens.txt"
KB_DIR = QAMP_ROOT / "kb"
DATA_DIR = QAMP_ROOT / "data"
RESULTS_DIR = QAMP_ROOT / "results"

# Development seeds are for trying things out. Held-out seeds are only for the pre-registered run.
DEV_SEED_BASE = 0
HELD_OUT_SEED_BASE = 50_000


def quarter_label(q: int) -> str:
    return f"{START_YEAR + q // 4} Q{q % 4 + 1}"


def year_end_quarter(year: int) -> int:
    """Index of the last quarter of a year (2030 -> 2030 Q4)."""
    return (year - START_YEAR) * 4 + 3
