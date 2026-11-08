"""Tests for the exploratory analyses (synthetic fixtures only; no real-data result is asserted)."""
import csv
import json
from decimal import Decimal

from rwa_threatlab.exploratory import kanon, latency, ofac_addresses, run

OFAC_TXT = """preamble

01/05/21:

The following [CYBER2] entries have been added to OFAC SDN List:

ALPHA, Aaa (individual) Digital Currency Address - ETH 0x1111111111111111111111111111111111111111; Digital Currency Address - USDT 0x2222222222222222222222222222222222222222 [CYBER2].

02/10/21:

The following [CYBER2] entries have been removed:

ALPHA, Aaa (individual) Digital Currency Address - ETH 0x1111111111111111111111111111111111111111 [CYBER2].

03/15/21:

The following [CYBER2] entries have been added to OFAC SDN List:

ALPHA, Aaa (individual) Digital Currency Address - ETH 0x1111111111111111111111111111111111111111; Digital Currency Address - ETH 0xABCDEFabcdefABCDEFabcdefABCDEFabcdefABCD [CYBER2].
"""


def test_ofac_extraction_first_listing_wins_and_removed_paragraphs_are_ignored(tmp_path):
    got = ofac_addresses.extract_text(OFAC_TXT)
    assert got["0x1111111111111111111111111111111111111111"] == "2021-01-05"        # first listing, not the re-listing
    assert got["0x2222222222222222222222222222222222222222"] == "2021-01-05"
    assert got["0xabcdefabcdefabcdefabcdefabcdefabcdefabcd"] == "2021-03-15"        # lower-cased
    (tmp_path / "sdnnew21.txt").write_text(OFAC_TXT)
    assert ofac_addresses.extract(tmp_path) == dict(sorted(got.items(), key=lambda kv: (kv[1], kv[0])))


def ev(ts, tx, v):
    return dict(timestamp=ts, tx=tx, value=Decimal(v))


def test_kanon_counts_distinct_transactions_not_events():
    # two legs of ONE transaction with the same value must not inflate the anonymity set
    events = [ev(1000, "a", "5"), ev(1010, "a", "5"), ev(1020, "b", "7")]
    s = kanon.cell_stats(events, 3600, 0.0)
    assert s["unique"] == 1.0 and s["median_k"] == 1          # a (both legs) has k=1, b has k=1
    events2 = [ev(1000, "a", "5"), ev(1010, "b", "5"), ev(1020, "c", "7")]
    s2 = kanon.cell_stats(events2, 3600, 0.0)
    assert round(s2["unique"], 3) == round(1 / 3, 3)           # a and b share a cell (k=2); c is unique


def test_kanon_buckets_and_epochs_merge_cells():
    events = [ev(0, "a", "100"), ev(10, "b", "104"), ev(7200, "c", "100")]
    assert kanon.cell_stats(events, 3600, 0.0)["unique"] == 1.0           # exact values differ
    assert kanon.cell_stats(events, 3600, 0.10)["unique"] == 1 / 3        # 100 and 104 share a 10% bucket in epoch 0; c is in another epoch
    assert kanon.cell_stats(events, None, 0.10)["unique"] == 0.0          # whole window: all three share a bucket (k=3)... 
    assert kanon.cell_stats([ev(0, "z", "0"), ev(5, "y", "0")], 60, 0.1)["unique"] == 0.0   # zero-value events share a bucket


def test_kanon_analyse_shape():
    events = [ev(i * 30, f"t{i}", str(1 + i % 5)) for i in range(200)]
    r = kanon.analyse(events)
    assert r["n_events"] == 200 and set(r["grid"]) == set(kanon.EPOCHS) and set(r["grid"]["1 hour"]) == set(kanon.BUCKETS)
    assert "Share of events that are unique" in kanon.markdown(r)


def test_latency_delays_censoring_and_clusters():
    ofac = {"0xaa": "2022-08-08", "0xbb": "2022-08-08", "0xcc": "2022-11-08", "0xdd": "2022-11-08"}
    day = lambda y, m, d: int(__import__("datetime").datetime(y, m, d, 12, tzinfo=__import__("datetime").timezone.utc).timestamp())  # noqa: E731
    events = [dict(token="USDC", address="0xaa", timestamp=day(2022, 8, 8)),           # same day: 0
              dict(token="USDC", address="0xaa", timestamp=day(2022, 9, 1)),           # later event ignored (first wins)
              dict(token="USDT", address="0xbb", timestamp=day(2022, 8, 20)),          # 12 days
              dict(token="USDC", address="0xcc", timestamp=day(2022, 11, 7)),          # -1: before OFAC
              dict(token="USDC", address="0xzz", timestamp=day(2022, 8, 8))]           # not an OFAC address: ignored
    r = latency.analyse(ofac, events, "2026-11-08")
    assert r["USDC"]["blacklisted"] == 2 and r["USDT"]["blacklisted"] == 1 and r["either"]["blacklisted"] == 3
    assert r["USDC"]["share_blacklisted"] == 0.5 and r["either"]["share_blacklisted"] == 0.75   # 0xdd never blacklisted (censored)
    assert r["either"]["median_days"] == 0 and r["either"]["before_listing"] == 1 / 3 and r["either"]["within_7d"] == 2 / 3
    assert r["by_listing_date"]["2022-08-08"]["median_days"] == 6.0 and r["dates_with_any_blacklisting"] == 2
    assert "OFAC listing dates: 2" in latency.markdown(r)


def test_runner_end_to_end_on_fixtures(tmp_path):
    d = tmp_path / "docs/data/exploratory"
    d.mkdir(parents=True)
    with open(d / "usdy_events.csv", "w", newline="") as f:
        w = csv.writer(f); w.writerow(["timestamp", "block", "tx_hash", "value"])
        for i in range(50): w.writerow([1000 + i * 40, 1 + i, f"0x{i}", f"{1 + i % 4}.5"])
    out = run.run("kanon", root=tmp_path, guard=False)
    assert out["result"]["n_events"] == 50 and out["provenance"]["files"]["events"]["sha256"]
    raw = tmp_path / "docs/data/raw"; raw.mkdir(parents=True); (raw / "sdnnew21.txt").write_text(OFAC_TXT)
    with open(d / "blacklist_events_ofac_subset.csv", "w", newline="") as f:
        w = csv.writer(f); w.writerow(["token", "address", "timestamp", "block", "tx_hash"])
        w.writerow(["USDC", "0x1111111111111111111111111111111111111111", 1610000000, 1, "0xh"])
    (d / "blacklist_summary.json").write_text(json.dumps(dict(retrieved_utc="2026-11-08T02:00:00Z")))
    out = run.run("latency", root=tmp_path, guard=False)
    assert out["result"]["ofac_addresses"] == 3 and out["result"]["USDC"]["blacklisted"] == 1 and "sdnnew21.txt" in out["provenance"]["ofac_raw_sources"]
