"""Run the executable mediation-surface audit (the paper's Table 1) on any build."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from rwa_threatlab.__main__ import mediation_md  # noqa: E402

print(mediation_md())
