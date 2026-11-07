"""The workbook converter must refuse synthetic files by default and read real ones. Needs openpyxl (not a runtime dependency)."""
import importlib.util
from pathlib import Path

import pytest

openpyxl = pytest.importorskip("openpyxl")

spec = importlib.util.spec_from_file_location("x2i", Path(__file__).resolve().parent.parent / "scripts" / "xlsx_to_irr.py")
x2i = importlib.util.module_from_spec(spec)
spec.loader.exec_module(x2i)


def _wb(path, code, scores=(2, 2, 2, 1, 1, 1), banner=None):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Scoring"
    ws["B2"] = code
    if banner:
        ws["A1"] = banner
    for i, sid in enumerate(("A1/A2", "A3"), start=6):
        ws.cell(i, 1, sid)
        for j, v in enumerate(scores):
            ws.cell(i, 5 + j, v)
    wb.save(path)
    return path


def test_reads_real_workbook(tmp_path):
    code, rows, flagged = x2i.read(_wb(tmp_path / "a.xlsx", "R1"))
    assert code == "R1" and not flagged and len(rows) == 2 and rows[0]["F1"] == 2 and rows[0]["scenario"] == "A1/A2"


def test_flags_synthetic_by_banner_or_code(tmp_path):
    assert x2i.read(_wb(tmp_path / "b.xlsx", "R2", banner="SYNTHETIC EXAMPLE ONLY"))[2]
    assert x2i.read(_wb(tmp_path / "c.xlsx", "SYN-R03"))[2]


def test_rejects_out_of_range_scores_and_empty_code(tmp_path):
    with pytest.raises(ValueError):
        x2i.read(_wb(tmp_path / "d.xlsx", "R4", scores=(2, 2, 2, 1, 1, 4)))
    with pytest.raises(ValueError):
        x2i.read(_wb(tmp_path / "e.xlsx", ""))
