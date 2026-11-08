"""Tests for experiment C (synthetic fixtures only; no real-data result is asserted)."""
import json

import pytest

from rwa_threatlab.exploratory import census, run

Z = "0x" + "0" * 40
A = lambda n: "0x" + format(n, "040x")  # noqa: E731


def rec(**kw):
    base = dict(address=A(1), rank=1, contract_name="T", source_verified=True, is_proxy=False, implementation=None, abi_functions=["transfer"],
                owner=None, default_admin=None, admin_slot=None, controllers={}, errors=[])
    base.update(kw)
    return base


def test_controller_types():
    ctl = {A(10): dict(is_contract=False),
           A(11): dict(is_contract=True, threshold=3, n_owners=5),
           A(12): dict(is_contract=True, min_delay=172800),
           A(13): dict(is_contract=True, owner=A(11)),                 # ProxyAdmin owned by a multisig
           A(14): dict(is_contract=True, owner=A(13)),                 # two contracts deep: only one hop is followed
           A(15): dict(is_contract=True), A(16): dict(is_contract=None)}
    t = lambda a: census.controller_type(a, ctl)  # noqa: E731
    assert t(A(10))["type"] == "eoa" and t(Z)["type"] == "none" and t(None)["type"] == "unknown" and t(A(99))["type"] == "unknown"
    assert t(A(11)) == dict(type="multisig", threshold=3, owners=5) and t(A(12)) == dict(type="timelock", delay_seconds=172800)
    assert t(A(13)) == dict(type="multisig", threshold=3, owners=5, via_contract=True)
    assert t(A(14)) == dict(type="other_contract", via_contract=True)          # one hop only: the second contract is not followed further
    assert t(A(15))["type"] == "other_contract" and t(A(16))["type"] == "unknown"
    assert census.label(t(A(11))) == "multisig 3-of-5" and census.label(t(A(13))) == "multisig 3-of-5 via contract" and "172800" in census.label(t(A(12)))


def test_upgrade_and_owner_control_rules():
    ctl = {A(10): dict(is_contract=False)}
    assert census.upgrade_control(rec())["type"] == "no_proxy_detected"
    assert census.upgrade_control(rec(is_proxy=True, admin_slot=Z))["type"] == "not_readable"
    assert census.upgrade_control(rec(is_proxy=True, admin_slot=None))["type"] == "not_readable"
    assert census.upgrade_control(rec(is_proxy=True, admin_slot=A(10), controllers=ctl))["type"] == "eoa"
    assert census.owner_control(rec())["type"] == "no_owner_or_default_admin"
    assert census.owner_control(rec(default_admin=A(10), controllers=ctl))["type"] == "eoa"
    assert census.owner_control(rec(owner=Z, default_admin=A(10), controllers=ctl))["type"] == "none"      # owner() has priority, even if renounced


def test_function_categories_by_name():
    c = census.categories_present(["transfer", "pause", "setAddressFrozen", "forcedTransfer", "mintTo", "upgradeToAndCall", "approve"])
    assert c == dict(pause=True, freeze_blacklist=True, forced_transfer_recovery=True, upgrade=True, mint_burn=True)
    c = census.categories_present(["transfer", "approve", "permit", "burnFrom_not_prefix_is_still_burn"])
    assert c["mint_burn"] and not c["pause"] and not c["freeze_blacklist"]
    assert not census.categories_present(["transfer", "approve"])["mint_burn"]


def test_analyse_counts_and_markdown():
    ctl = {A(10): dict(is_contract=False), A(11): dict(is_contract=True, threshold=2, n_owners=3)}
    raw = [rec(rank=1, address=A(1), is_proxy=True, admin_slot=A(11), owner=A(10), abi_functions=["pause", "upgradeTo"], controllers=ctl),
           rec(rank=2, address=A(2), source_verified=False, errors=["x"]),
           rec(rank=3, address=A(3), is_proxy=True, admin_slot=Z, abi_functions=["freeze"])]
    r = census.analyse(raw)
    assert r["n_tokens"] == 3 and r["source_verified"] == 2 and r["proxies"] == 2 and r["with_errors"] == 1
    assert r["upgrade_control_among_proxies"] == {"multisig": 1, "not_readable": 1}
    assert r["owner_control"] == {"eoa": 1, "no_owner_or_default_admin": 2}
    assert r["categories"]["pause"] == 1 and r["categories"]["freeze_blacklist"] == 1 and r["categories"]["upgrade"] == 1
    assert "multisig 2-of-3" in census.markdown(r)


def test_runner_end_to_end(tmp_path):
    d = tmp_path / "docs/data/exploratory"
    d.mkdir(parents=True)
    (d / "census_tokens.txt").write_text("# list\n" + A(1) + "  1  T\n")
    (d / "census_raw.json").write_text(json.dumps(dict(tokens=[rec()])))
    out = run.run("census", root=tmp_path, guard=False)
    assert out["result"]["n_tokens"] == 1 and out["provenance"]["files"]["census_raw"]["sha256"] and "contracts" in out["markdown"]


def test_selectors_and_slots_are_the_right_hashes():
    keccak = pytest.importorskip("Crypto.Hash.keccak")
    k = lambda s: keccak.new(digest_bits=256, data=s.encode()).digest()  # noqa: E731
    sel = lambda s: "0x" + k(s).hex()[:8]  # noqa: E731
    assert (sel("owner()"), sel("getThreshold()"), sel("getOwners()"), sel("getMinDelay()"), sel("defaultAdmin()")) == \
        ("0x8da5cb5b", "0xe75235b8", "0xa0e67e2b", "0xf27a0c92", "0x84ef8ffc")
    slot = lambda n: "0x" + format(int.from_bytes(k(n), "big") - 1, "064x")  # noqa: E731
    assert slot("eip1967.proxy.admin") == "0xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103"
    assert slot("eip1967.proxy.implementation") == "0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc"
