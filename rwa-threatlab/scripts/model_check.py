"""Thin wrapper kept for the name used in the paper's appendix: python scripts/model_check.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from rwa_threatlab import modelcheck  # noqa: E402

if __name__ == "__main__":
    modelcheck.run(verbose=True)
