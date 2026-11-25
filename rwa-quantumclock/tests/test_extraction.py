"""Offline tests of the extraction decoders and observer against simulated Etherscan answers."""
from qamp.extraction import Observer, decode_address_array, facts_from_raw, word_to_address, word_to_int

A = "0x" + "11" * 20
SAFE = "0x" + "22" * 20
O1, O2, O3 = "0x" + "aa" * 20, "0x" + "bb" * 20, "0x" + "cc" * 20
TOKEN = "0x" + "99" * 20


def w(x: str) -> str:
    return x[2:].rjust(64, "0")


def arr(addrs):
    return "0x" + hex(32)[2:].rjust(64, "0") + hex(len(addrs))[2:].rjust(64, "0") + "".join(w(a) for a in addrs)


def test_decoders():
    assert word_to_address("0x" + w(A)) == A
    assert word_to_address("0x" + "0" * 64) is None
    assert word_to_int("0x2") == 2
    assert decode_address_array(arr([O1, O2])) == [O1, O2]


def fake_etherscan(url: str):
    q = dict(p.split("=", 1) for p in url.split("?", 1)[1].split("&"))
    act, to = q.get("action"), (q.get("address") or q.get("to") or "").lower()
    data = q.get("data", "")
    if act == "getsourcecode":
        return dict(status="1", result=[dict(ContractName="Tok", SourceCode="contract Tok {}", Proxy="0", Implementation="")])
    if act == "eth_getStorageAt":
        return dict(result="0x" + "0" * 64)
    if act == "eth_getCode":
        return dict(result="0x6080" if to in (SAFE, TOKEN) else "0x")
    if act == "eth_getTransactionCount":
        return dict(result={O1: "0x5", O2: "0x0", O3: "0x9"}.get(to, "0x1"))
    if act == "eth_call":
        if to == TOKEN and data == "0x8da5cb5b":
            return dict(result="0x" + w(SAFE))
        if to == SAFE and data == "0xe75235b8":
            return dict(result="0x" + "0" * 63 + "2")
        if to == SAFE and data == "0xa0e67e2b":
            return dict(result=arr([O1, O2, O3]))
        return dict(error=dict(message="execution reverted"))
    return dict(result=None)


def test_observer_and_facts(monkeypatch):
    import qamp.extraction as ex
    monkeypatch.setattr(ex.time, "sleep", lambda s: None)
    ob = Observer(fake_etherscan, key="k")
    rec = ob.observe_token(TOKEN, role_selectors={})
    assert rec["owner"] == SAFE and rec["controllers"][SAFE]["threshold"] == 2
    assert rec["controllers"][SAFE]["owners"] == [O1, O2, O3]
    f = facts_from_raw(dict(tokens=[rec]))
    assert f[SAFE]["key_exposed"] is True        # 2 of 3 owners have sent transactions, threshold 2
    assert "apikey" not in str(rec) and "=k" not in str(rec)   # the API key is never stored


def test_role_members_replace_unobserved_anchor(tmp_path):
    import json
    from qamp.data import load_census
    usdy = "0x96f6ef951840721adbf46ac996b59e0235cb985c"
    m = "0x" + "ab" * 20
    q1 = dict(tokens=[dict(address=usdy, roles={"MINTER_ROLE": dict(role_id="0x1", count=1, members=[m])},
                           controllers={m: dict(address=m, is_contract=False, nonce=3)})])
    p = tmp_path / "q1.json"
    p.write_text(json.dumps(q1))
    facts = tmp_path / "facts.json"
    facts.write_text(json.dumps({m: dict(key_exposed=True)}))
    dep = load_census(q1_raw_path=p, facts_path=facts)
    ids = [a.anchor_id for a in dep.anchors]
    assert f"ctrl:{m}" in ids and f"role_holder:{usdy}" not in ids
    a = dep.anchor(f"ctrl:{m}")
    assert a.controller_type == "eoa" and a.key_exposed is True and a.provenance["key_exposed"] == "observed"
