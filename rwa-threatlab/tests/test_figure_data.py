"""The figure data agree with the stored results they are drawn from (H14 and Exploratory B)."""
import importlib.util
import json
from pathlib import Path
from statistics import median

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("make_figure_data", ROOT / "scripts" / "make_figure_data.py")
fd = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fd)


def test_h14_rows_match_stored_result():
    rows = fd.h14_rows()
    assert [r["events_per_epoch"] for r in rows] == [1, 2, 3, 5, 8, 10, 20]
    assert round(rows[0]["real"] * 100, 1) == 35.0 and round(rows[-1]["real"] * 100, 1) == 4.9


def test_delays_match_stored_latency_summary():
    rows = fd.delay_rows()
    res = json.loads((ROOT / "docs/results/exploratory/latency/result.json").read_text())["result"]
    assert len(rows) == res["ofac_addresses"] == 141
    for tok in ("USDC", "USDT"):
        d = [r[f"{tok}_days"] for r in rows if r[f"{tok}_days"] != ""]
        assert len(d) == res[tok]["blacklisted"]
        assert float(median(d)) == res[tok]["median_days"]
        assert sum(x <= 1 for x in d) / len(d) == res[tok]["within_1d"]
