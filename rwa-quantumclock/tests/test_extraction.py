"""Tests for data collection (with a fake Etherscan) and its interpretation."""
import datetime as dt
import hashlib
import json

import pytest

from qamp.extraction import (Observer, decode_address_array, decode_string, facts_from_raw, word_to_address,
                             word_to_int)
from qamp.keccak import _sha3_256, keccak256, selector, topic
from qamp.observed import (bytecode_labels, calendars_from_events, capacity_from_events, change_days, issuer_groups,
                           selectors_from_bytecode, topology_from_raw)

TOKEN = "0x" + "99" * 20
IMPL = "0x" + "98" * 20
SAFE = "0x" + "22" * 20
O1, O2, O3 = "0x" + "aa" * 20, "0x" + "bb" * 20, "0x" + "cc" * 20
MINTER = "0x" + "ee" * 20


def w(x: str) -> str:
    return x[2:].rjust(64, "0")


def arr(addrs):
    return "0x" + hex(32)[2:].rjust(64, "0") + hex(len(addrs))[2:].rjust(64, "0") + "".join(w(a) for a in addrs)


def enc_string(s: str) -> str:
    b = s.encode().hex()
    return "0x" + hex(32)[2:].rjust(64, "0") + hex(len(s))[2:].rjust(64, "0") + b.ljust(64, "0")


def code_with(*sigs) -> str:
    """Fake contract code with the given functions, plus a hidden lookalike that must be ignored."""
    body = "".join("63" + selector(s)[2:] + "14" for s in sigs)
    hidden = "7f" + ("63" + selector("isValidSignature(bytes32,bytes)")[2:]).ljust(64, "0")
    return "0x" + body + hidden + "00"


ABI = json.dumps([{"type": "function", "name": n} for n in ("transfer", "permit", "grantRole", "hasRole", "MINTER_ROLE", "getRoleMember")])
TS = {1: 1_700_000_000, 2: 1_715_000_000, 3: 1_731_000_000}      # 2023-11, 2024-05, 2024-11


def fake_etherscan(url: str):
    q = dict(p.split("=", 1) for p in url.split("?", 1)[1].split("&"))
    chain = int(q.get("chainid", 1))
    act, to = q.get("action"), (q.get("address") or q.get("to") or "").lower()
    data = q.get("data", "")
    if chain != 1:
        if chain == 10 and act == "eth_getCode":
            return dict(result="0x6080")
        if chain == 10 and act == "eth_call" and data == selector("symbol()"):
            return dict(result=enc_string("TOK"))
        if chain == 10 and act == "eth_call" and data == selector("totalSupply()"):
            return dict(result="0x" + w(hex(300)))
        if chain == 56:
            return dict(status="0", message="NOTOK", result="Free API access is not supported for this chain")
        if act == "eth_getCode":
            return dict(result="0x")
        return dict(error=dict(message="execution reverted"))
    if act == "getsourcecode":
        if to == TOKEN:
            return dict(status="1", result=[dict(ContractName="Proxy", SourceCode="contract P {}", ABI="[]", Proxy="1", Implementation=IMPL)])
        return dict(status="1", result=[dict(ContractName="Tok", SourceCode="contract Tok {}", ABI=ABI, Proxy="0", Implementation="")])
    if act == "eth_getStorageAt":
        return dict(result="0x" + w(SAFE)) if q.get("position", "").endswith("6103") and to == TOKEN else dict(result="0x" + "0" * 64)
    if act == "eth_getCode":
        if to == TOKEN:
            return dict(result=code_with("upgradeTo(address)"))
        if to == IMPL:
            return dict(result=code_with("permit(address,address,uint256,uint256,uint8,bytes32,bytes32)", "grantRole(bytes32,address)"))
        return dict(result="0x6080" if to == SAFE else "0x")
    if act == "eth_getTransactionCount":
        return dict(result={O1: "0x5", O2: "0x0", O3: "0x9", MINTER: "0x2"}.get(to, "0x1"))
    if act == "getLogs":
        t0 = q.get("topic0")
        if to == SAFE and t0 in (topic("AddedOwner(address)"), topic("RemovedOwner(address)")):
            k = 1 if t0 == topic("AddedOwner(address)") else 2
            return dict(status="1", result=[dict(blockNumber=hex(100 + k), timeStamp=hex(TS[k]), transactionHash=f"0x{k}", topics=[t0], data="0x"),
                                            dict(blockNumber=hex(300), timeStamp=hex(TS[3]), transactionHash="0x3", topics=[t0], data="0x")])
        return dict(status="0", message="No records found", result=[])
    if act == "eth_call":
        if to == TOKEN and data == selector("totalSupply()"):
            return dict(result="0x" + w(hex(700)))
        if to == TOKEN and data == selector("symbol()"):
            return dict(result=enc_string("TOK"))
        if to == TOKEN and data == selector("MINTER_ROLE()"):
            return dict(result="0x" + "12" * 32)
        if to == TOKEN and data == selector("getRoleMemberCount(bytes32)") + "12" * 32:
            return dict(result="0x" + w("0x1"))
        if to == TOKEN and data.startswith(selector("getRoleMember(bytes32,uint256)")):
            return dict(result="0x" + w(MINTER))
        if to == SAFE and data == selector("getThreshold()"):
            return dict(result="0x" + w("0x2"))
        if to == SAFE and data == selector("getOwners()"):
            return dict(result=arr([O1, O2, O3]))
        return dict(error=dict(message="execution reverted"))
    return dict(result=None)


@pytest.fixture(scope="module")
def observed_raw():
    import qamp.extraction as ex
    old = ex.time.sleep
    ex.time.sleep = lambda s: None
    try:
        ob = Observer(fake_etherscan, key="SECRETKEY")
        rec = ob.observe_token(TOKEN, other_chains={10: "optimism", 56: "bnb", 137: "polygon"})
    finally:
        ex.time.sleep = old
    return dict(tokens=[rec], retrieved_at_utc="2026-12-01T00:00:00Z", block=1)


# --- keccak and decoders

def test_keccak_vectors():
    assert keccak256(b"").hex() == "c5d2460186f7233c927e7db2dcc703c0e500b653ca82273b7bfad8045d85a470"
    assert selector("transfer(address,uint256)") == "0xa9059cbb"
    assert topic("Transfer(address,address,uint256)") == "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
    for n in (0, 1, 135, 136, 137, 300):                 # long inputs, checked against hashlib
        m = bytes(range(256))[: n % 256] * (1 + n // 256)
        assert _sha3_256(m) == hashlib.sha3_256(m).digest()


def test_decoders():
    assert word_to_address("0x" + w(SAFE)) == SAFE and word_to_address("0x" + "0" * 64) is None
    assert word_to_int("0x2") == 2
    assert decode_address_array(arr([O1, O2])) == [O1, O2]
    assert decode_string(enc_string("USDY")) == "USDY"
    assert decode_string("0x" + "4d4b520000".ljust(64, "0")) == "MKR"


# --- observer

def test_observer_record(observed_raw):
    rec = observed_raw["tokens"][0]
    assert rec["is_proxy"] and rec["implementation"] == IMPL and rec["admin_slot"] == SAFE
    assert "MINTER_ROLE" in rec["abi_functions"] and rec["roles"]["MINTER_ROLE"]["members"] == [MINTER]
    flat = rec["controllers"]
    assert flat[SAFE]["threshold"] == 2 and flat[SAFE]["owners"] == [O1, O2, O3] and flat[SAFE]["n_owners"] == 3
    assert flat[O2]["is_contract"] is False and flat[O2]["nonce"] == 0
    assert len([e for e in rec["events"] if e["address"] == SAFE]) == 4
    assert rec["chains"][10]["code"] is True and rec["chains"][10]["symbol"] == "TOK"
    assert rec["chains"][137]["code"] is False
    assert rec["chains"][56]["code"] is None and any("[56]" in e for e in rec["errors"])
    assert "SECRETKEY" not in json.dumps(rec)


def test_facts_from_raw(observed_raw):
    f = facts_from_raw(observed_raw)
    assert f[SAFE]["key_exposed"] is True          # 2 of 3 signers exposed, threshold 2
    assert f[O2]["key_exposed"] is False and f[MINTER]["key_exposed"] is True


# --- classification

def test_selectors_skip_push_data():
    code = code_with("permit(address,address,uint256,uint256,uint8,bytes32,bytes32)")
    s = selectors_from_bytecode(code)
    assert selector("permit(address,address,uint256,uint256,uint8,bytes32,bytes32)") in s
    assert selector("isValidSignature(bytes32,bytes)") not in s      # hidden inside other data


def test_bytecode_labels(observed_raw):
    rows = {r["surface"]: r for r in bytecode_labels(observed_raw)}
    assert rows["eip2612_permit"]["present"] == 1 and rows["access_control_roles"]["present"] == 1
    assert rows["upgradeable_proxy"]["present"] == 1 and "eip1967-slot" in rows["upgradeable_proxy"]["evidence"]
    assert rows["erc2771_forwarder"]["present"] == 0 and rows["erc1271_contract_signature"]["present"] == 0


def test_calendars_and_capacity():
    from qamp.model import Anchor, Deployment
    d = lambda s: dt.date.fromisoformat(s)  # noqa: E731
    days = {"a": [d("2024-01-10"), d("2025-01-12"), d("2026-01-15")], "b": [d("2026-02-01")], "c": [d("2026-01-20")]}
    cal = calendars_from_events(days)
    assert set(cal) == {"a"} and cal["a"].period == 4 and cal["a"].phase == (( 2026 - 2027) * 4) % 4
    lb = calendars_from_events({"b": [d("2023-01-01")]}, policy="lower_bound", window_end=d("2026-11-01"))
    assert lb["b"].period == 8
    dep = Deployment(tokens=[], anchors=[Anchor("a", "x", "eoa", issuer_group="G"), Anchor("c", "x", "eoa", issuer_group="G"),
                                         Anchor("b", "x", "eoa", issuer_group="H")])
    cap = capacity_from_events(days, dep)
    assert cap["G"] == 2 and cap["H"] == 1           # a and c changed in the same quarter


def test_change_days_and_loader(observed_raw, tmp_path):
    from qamp.data import load_census
    toks = tmp_path / "tokens.txt"
    toks.write_text(f"{TOKEN} 1 Test Token (TOK) 1,000,000\n")
    q1 = tmp_path / "q1.json"
    q1.write_text(json.dumps(observed_raw))
    dep = load_census(tokens_path=toks, q1_raw_path=q1)
    assert dep.source.startswith("extraction notebook") and len(dep.tokens) == 1
    ids = {a.anchor_id for a in dep.anchors}
    assert f"ctrl:{SAFE}" in ids and f"ctrl:{MINTER}" in ids and f"role_holder:{TOKEN}" not in ids
    safe = dep.anchor(f"ctrl:{SAFE}")
    assert safe.controller_type == "multisig" and safe.n_keys == 2
    days = change_days(observed_raw, dep)
    assert len(days[f"ctrl:{SAFE}"]) == 3
    assert safe.calendar.source.startswith("observed") and safe.calendar.period == 2   # about every 6 months
    assert dep.group_capacity
    topo = dep.observed_topology
    assert set(topo[f"ctrl:{SAFE}"]) == {"ethereum", "optimism"}
    assert abs(topo[f"ctrl:{SAFE}"]["ethereum"] - 0.7) < 1e-9


def test_issuer_groups_ignore_zero_address():
    zero = "0x" + "0" * 40
    raw = [dict(address="0x1", owner=zero, name="A"), dict(address="0x2", owner=zero, name="B"),
           dict(address="0x3", owner=SAFE, name="C"), dict(address="0x4", admin_slot=SAFE, name="D")]
    g = issuer_groups(raw, lambda r: r["name"])
    assert g["0x1"] != g["0x2"] and g["0x3"] == g["0x4"]


def test_topology_requires_matching_symbol(observed_raw):
    from qamp.model import Anchor, Deployment, Token
    raw = json.loads(json.dumps(observed_raw))
    raw["tokens"][0]["chains"]["10"] = dict(chain="optimism", code=True, symbol="OTHER", total_supply=5)
    raw["tokens"][0]["chains"].pop(10, None)
    dep = Deployment(tokens=[Token(TOKEN, 1, "T", "TOK", 1e6)], anchors=[Anchor("x", "owner_admin", "eoa", tokens=[TOKEN])])
    assert topology_from_raw(raw, dep) == {}


def test_issuer_groups_use_role_members_and_top_rank_name():
    """Tokens sharing a role member are one issuer, named after the largest token."""
    from qamp.observed import issuer_groups
    m = "0x" + "ab" * 20
    toks = [dict(address="0x" + "01" * 20, roles={"R": {"members": [m]}}, name="iShares"),
            dict(address="0x" + "02" * 20, roles={"R": {"members": [m]}}, name="Ondo"),
            dict(address="0x" + "03" * 20, owner="0x" + "0" * 40, name="Other")]
    g = issuer_groups(toks, lambda t: t["name"], rank={toks[0]["address"]: 5, toks[1]["address"]: 1})
    assert g[toks[0]["address"]] == g[toks[1]["address"]] == "Ondo"
    assert g[toks[2]["address"]] == "Other"   # the zero address joins nothing


def test_q1b_targets_and_merge():
    """Only tokens with a fixed role getter are targets; merging adds roles and keeps the Q1 records unchanged."""
    from qamp.extraction import merge_role_getters, q1b_targets
    h = "0x" + "cd" * 20
    raw = dict(tokens=[dict(address="0x" + "01" * 20, abi_functions=["minter", "transfer"], roles={}, controllers={}, events=[]),
                       dict(address="0x" + "02" * 20, abi_functions=["transfer"], roles={}, controllers={}, events=[])])
    assert q1b_targets(raw) == ["0x" + "01" * 20]
    q1b = dict(tokens=[dict(address="0x" + "01" * 20, getters={"minter": h}, controllers={h: {"is_contract": False, "nonce": 3}},
                            events=[dict(address="0x" + "01" * 20, event="NewMinter(address)", ts=1700000000)])])
    m = merge_role_getters(raw, q1b)
    assert m["tokens"][0]["roles"]["minter()"]["members"] == [h]
    assert h in m["tokens"][0]["controllers"]
    assert raw["tokens"][0]["roles"] == {}            # original untouched


def test_q1b_selectors():
    from qamp.keccak import selector
    assert selector("minter()") == "0x07546172"
    assert selector("pauser()") == "0x9fd0506d"
