"""Thin wrapper kept for the name used in the paper's appendix: python scripts/rubric.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from rwa_threatlab import risk  # noqa: E402

if __name__ == "__main__":
    print(risk.markdown_table())
    print(risk.sensitivity())
