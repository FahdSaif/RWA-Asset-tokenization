from arca.layer3_runtime.audit_log import HashChainLedger


def test_empty_ledger_integrity():
    ledger = HashChainLedger()
    assert ledger.verify_integrity() is True
    assert len(ledger) == 0


def test_append_and_chain_linkage():
    ledger = HashChainLedger()
    e1 = ledger.append("test.event", {"n": 1})
    e2 = ledger.append("test.event", {"n": 2})
    assert e2.prev_hash == e1.entry_hash
    assert ledger.verify_integrity() is True


def test_tamper_with_payload_breaks_integrity():
    ledger = HashChainLedger()
    ledger.append("test.event", {"n": 1})
    ledger.append("test.event", {"n": 2})
    ledger._entries[0].payload["n"] = 999  # simulate a tamper
    assert ledger.verify_integrity() is False


def test_tamper_with_hash_directly_breaks_integrity():
    ledger = HashChainLedger()
    ledger.append("test.event", {"n": 1})
    ledger._entries[0].entry_hash = "0" * 64
    assert ledger.verify_integrity() is False


def test_query_by_event_type():
    ledger = HashChainLedger()
    ledger.append("type_a", {})
    ledger.append("type_b", {})
    ledger.append("type_a", {})
    assert len(ledger.query("type_a")) == 2
    assert len(ledger.query("type_b")) == 1
    assert len(ledger.query()) == 3
