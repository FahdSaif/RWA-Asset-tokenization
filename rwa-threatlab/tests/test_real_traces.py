"""Tests for the real-trace tooling. Fixtures are FORMAT fixtures: an invented file imitating OFAC's layout and a short
verbatim excerpt of the real 2022 change file. No real-data result is produced or asserted here."""
import json
import random
from pathlib import Path

import pytest

from rwa_threatlab import fuzz_replay, hypotheses_real as hr
from rwa_threatlab.config import Config
from rwa_threatlab.traces import bridge, ofac, timing

FIX = Path(__file__).parent / "fixtures"
W = ("2021-01-01", "2021-12-31")


def _fixture():
    return ofac.parse_text((FIX / "ofac_format_fixture.txt").read_text())


def test_parser_on_verbatim_excerpt_of_the_real_2022_file():
    r = ofac.parse_text((FIX / "ofac_real_excerpt_2022.txt").read_text())
    got = [(e.date, e.action, e.key) for e in r["events"]]
    assert got == [("2022-01-05", "add", "ALTERNATIVNA TELEVIZIJA D.O.O. BANJA LUKA"), ("2022-01-05", "add", "ATV"),
                   ("2022-01-10", "add", "BARAHONA CASTRO, ROSA ADELINA"), ("2022-01-10", "add", "BARAHONA DE RIVAS, ROSA ADELINA"),
                   ("2022-01-10", "add", "CALDERON VINDELL, RAMON HUMBERTO"), ("2022-01-31", "remove", "OMAN PRIDE CRUDE OIL TANKER")]
    assert r["diag"]["unrecognised_headers"] == [] and r["diag"]["long_entries"] == 0
    assert r["diag"]["headers"] == {"change": 2, "add": 2, "remove": 1, "resulting": 1}


def test_parser_on_invented_fixture_handles_wrapped_tags_renames_and_relisting():
    r = _fixture()
    assert len(r["events"]) == 13 and r["renames"] == [("2021-03-15", "ZORLAND, QUENTIN", "ZORLAND, QUENTIN ALEXANDER")]
    assert any(e.programs == "TESTPROG-B|TESTPROG-C" for e in r["events"])            # tag wrapped over two lines
    h = ofac.build_histories(r["events"], r["renames"], *W)
    assert h["ZORLAND, QUENTIN ALEXANDER"] == ["add", "remove"]                          # rename joins the two names
    assert set(ofac.relisted(h)) == {"BELMONT TRADING LLC", "NIGHTINGALE, PERCIVAL"}
    assert "RAVEN HOLDINGS" not in ofac.volatile_pool(h) and len(ofac.volatile_pool(h)) == 5


def test_events_csv_round_trip(tmp_path):
    r = _fixture()
    p = tmp_path / "e.csv"
    ofac.write_events_csv(p, r["events"], r["renames"])
    ev, rn = ofac.load_events_csv(p)
    assert ev == r["events"] and rn == r["renames"]


def test_schedule_keeps_real_order_and_bounds():
    r = _fixture()
    dated = ofac.dated_histories(r["events"], r["renames"], *W)
    pool = ofac.volatile_pool(ofac.build_histories(r["events"], r["renames"], *W))
    ent = ofac.sample_entries(pool, 7)
    for variant in ("spread", "burst"):
        s = ofac.make_schedule(ent, dated, variant, 40)
        assert s and min(s) >= 2 and max(s) < 39
        assert list(s) == sorted(s)
        assert len(set(s)) == len(s)
    b = ofac.make_schedule(ent, dated, "burst", 40)
    assert list(b) == list(range(2, 2 + len(b)))
    with pytest.raises(ValueError):
        ofac.sample_entries(["only", "two"][:2], 1)


def test_replay_applies_scripted_events_with_the_frozen_fuzzers_own_actions():
    sched = {2: ("sanction", "a1"), 5: ("delist", "a1"), 8: ("delist", "u")}      # last one is invalid (u not listed) -> skipped
    run = fuzz_replay.replay_trace(Config.hardened(), "none", 123, sched, 20)
    acts = run.result.actions
    assert acts[2] == "sanction(a1)" and acts[5] == "delist(a1)" and acts[8] == "delist(skip)"
    assert (run.applied, run.skipped) == (2, 1)
    assert all(not a.startswith(("sanction(", "delist(")) or i in sched for i, a in enumerate(acts) if "(skip)" not in a)
    assert "z" in run.sanctioned_since and "a1" not in run.sanctioned_since     # z fixed, a1 delisted again


def test_replay_campaign_is_sensitive_and_oracles_agree():
    r = _fixture()
    base = fuzz_replay.replay_campaign(Config.baseline(), "none", r["events"], r["renames"], W, "burst", 1000, 40)
    hard = fuzz_replay.replay_campaign(Config.hardened(), "none", r["events"], r["renames"], W, "burst", 1000, 40)
    assert sum(base["violations"].values()) > 0 and base["oracle_compared"] > 0
    assert hard["violations"]["UNEXPLAINED"] == 0 and hard["crashes"] == 0
    assert base["oracle_disagreements"] == hard["oracle_disagreements"] == 0
    assert base["events_applied"] == base["events_scheduled"] > 0


def test_timing_loader_sweep_and_h14_rule(tmp_path):
    rnd = random.Random(1)
    t, rows = 1_700_000_000.0, ["timestamp"]
    for _ in range(2000):
        t += rnd.lognormvariate(3, 1.2)
        rows.append(f"{t:.3f}")
    p = tmp_path / "t.csv"
    p.write_text("\n".join(rows))
    gaps = timing.gaps_in_ticks(timing.load_timestamps(p))
    assert 8 <= sum(gaps) / len(gaps) <= 12                                    # rescaled to ~10 ticks
    sw = timing.real_sweep(gaps, boot=6)
    assert [r["events_per_epoch"] for r in sw] == list(timing.RATIOS) and sw[0]["mean"] > sw[-1]["mean"]
    assert timing.evaluate_h14(sw)[0] in ("CONFIRMED", "REFUTED")
    with pytest.raises(ValueError):
        timing.gaps_in_ticks([float(i) for i in range(100)])
    iso = tmp_path / "iso.csv"
    iso.write_text("timestamp\n2024-01-01T00:00:00Z\n2024-01-01T00:00:10+00:00\n")
    assert timing.load_timestamps(iso) == [1704067200.0, 1704067210.0]


def test_bridge_loader_and_summary(tmp_path):
    rows = ["src_timestamp,dst_timestamp"] + [f"{1000 + i},{1000 + i + 30 + (i % 50)}" for i in range(200)] + ["500,400"]
    p = tmp_path / "b.csv"
    p.write_text("\n".join(rows))
    lat, dropped = bridge.load_latencies(p)
    s = bridge.summarise(lat, dropped)
    assert s["n"] == 200 and s["dropped_negative"] == 1 and 30 <= s["median_s"] <= 80 and s["share_over"]["3600"] == 0
    with pytest.raises(ValueError):
        bridge.summarise(lat[:10])


def test_guards_refuse_undeclared_data_and_pipeline_runs_on_fixtures(tmp_path):
    template = json.loads((Path(hr.ROOT) / "docs/data/datasets.json").read_text())
    with pytest.raises(hr.GuardError):
        hr.check_declarations(template, ("ofac", "timing", "bridge"))
    r = _fixture()
    ofac.write_events_csv(tmp_path / "e.csv", r["events"], r["renames"])
    rnd, t = random.Random(2), 0.0
    (tmp_path / "t.csv").write_text("timestamp\n" + "\n".join(f"{(t := t + rnd.lognormvariate(3, 1)):.2f}" for _ in range(1500)))
    (tmp_path / "b.csv").write_text("latency_seconds\n" + "\n".join(str(30 + i % 90) for i in range(150)))
    ds = {"ofac": dict(events_csv="e.csv", window_start=W[0], window_end=W[1]), "timing": dict(csv="t.csv"), "bridge": dict(csv="b.csv")}
    res = hr.run_real(root=tmp_path, guard=False, datasets=ds, traces=12, steps=40)
    assert set(res) >= {"provenance", "ofac", "timing", "bridge", "label"} and res["label"].startswith("real traces")
    assert res["ofac"]["status"]["H12"][0] in ("CONFIRMED", "REFUTED") and res["ofac"]["H16"][0] == "CONFIRMED"
    assert res["bridge"]["status"][0] == "DESCRIPTIVE" and "H12c" in res["ofac"]["status"]
    assert "H12" in hr.markdown(res)


def test_configurable_columns_naive_times_are_utc_and_raw_hashes_recorded(tmp_path):
    p = tmp_path / "t.csv"
    p.write_text("Txhash,UnixTimestamp,DateTime (UTC)\nx,1704067200,2024-01-01 00:00:00\ny,1704067210,2024-01-01 00:00:10\n")
    assert timing.load_timestamps(p, "UnixTimestamp") == [1704067200.0, 1704067210.0]
    assert timing.load_timestamps(p, "DateTime (UTC)") == [1704067200.0, 1704067210.0]      # naive = UTC
    b = tmp_path / "b.csv"
    b.write_text("sent,received\n" + "\n".join(f"{i},{i + 5}" for i in range(120)))
    lat, _ = bridge.load_latencies(b, "sent", "received")
    assert set(lat) == {5.0}
    with pytest.raises(ValueError):
        bridge.load_latencies(b)
    r = _fixture()
    ofac.write_events_csv(tmp_path / "e.csv", r["events"], r["renames"])
    (tmp_path / "raw").mkdir()
    (tmp_path / "raw" / "sdnnew21.txt").write_text("x")
    ds = {"ofac": dict(events_csv="e.csv", window_start=W[0], window_end=W[1], raw_dir="raw")}
    res = hr.run_real(root=tmp_path, sections=("ofac",), guard=False, datasets=ds, traces=6, steps=40)
    assert list(res["provenance"]["raw_sources"]) == ["sdnnew21.txt"]


def test_compare_runs_ignores_machine_fields_and_catches_result_changes():
    import importlib.util
    spec = importlib.util.spec_from_file_location("cmp", Path(hr.ROOT) / "scripts" / "compare_runs.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    a = {"provenance": {"python": "3.12", "git_commit": "a", "freeze_info": "x"}, "ofac": {"H12": ["CONFIRMED", "e"]}}
    b = {"provenance": {"python": "3.10", "git_commit": "b", "freeze_info": "x"}, "ofac": {"H12": ["CONFIRMED", "e"]}}
    assert m.diff(a, b) == []
    b["ofac"]["H12"][0] = "REFUTED"
    assert m.diff(a, b) == ["ofac/H12[0]: 'CONFIRMED' vs 'REFUTED'"]
    b["ofac"]["H12"][0], b["provenance"]["freeze_info"] = "CONFIRMED", "y"
    assert m.diff(a, b) == ["provenance/freeze_info: 'x' vs 'y'"]
