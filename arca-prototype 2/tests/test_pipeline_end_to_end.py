from arca.pipeline.end_to_end_demo import run_demo


def test_full_pipeline_accepts_a_compliant_transaction():
    outcome = run_demo(verbose=False)
    result = outcome["result"]
    assert result.accepted is True
    assert result.rejection_reasons == []


def test_full_pipeline_audit_log_is_tamper_evident():
    outcome = run_demo(verbose=False)
    audit_log = outcome["env"]["audit_log"]
    assert audit_log.verify_integrity() is True
    assert len(audit_log) > 10  # every stage across all 4 layers logged something

    # tamper directly and confirm detection
    audit_log._entries[5].payload["injected"] = "tampered"
    assert audit_log.verify_integrity() is False
