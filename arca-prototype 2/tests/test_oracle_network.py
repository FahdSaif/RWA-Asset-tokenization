from arca.layer2_identity.did_registry import generate_did
from arca.layer3_runtime.audit_log import HashChainLedger
from arca.layer4_governance.oracle_network import RegulatoryOracleNetwork, submit_report


def _setup(quorum=2):
    audit = HashChainLedger()
    providers = [generate_did() for _ in range(4)]
    authorized = {p.did for p in providers[:3]}
    net = RegulatoryOracleNetwork(audit_log=audit, authorized_providers=authorized, consensus_quorum=quorum)
    return audit, providers, net


def test_consensus_reached_with_quorum_agreement():
    audit, providers, net = _setup(quorum=2)
    reports = [
        submit_report(providers[0], "risk:SY", "prohibited"),
        submit_report(providers[1], "risk:SY", "prohibited"),
        submit_report(providers[2], "risk:SY", "high"),
    ]
    assert net.ingest("risk:SY", reports) == "prohibited"


def test_unauthorized_provider_report_is_ignored():
    audit, providers, net = _setup(quorum=2)
    reports = [
        submit_report(providers[0], "risk:SY", "prohibited"),
        submit_report(providers[3], "risk:SY", "prohibited"),  # unauthorized (idx 3)
    ]
    # Only 1 authorized report -> below quorum, despite 2 total reports agreeing
    assert net.ingest("risk:SY", reports) is None


def test_no_consensus_on_full_disagreement():
    audit, providers, net = _setup(quorum=2)
    reports = [
        submit_report(providers[0], "risk:XX", "low"),
        submit_report(providers[1], "risk:XX", "high"),
        submit_report(providers[2], "risk:XX", "prohibited"),
    ]
    assert net.ingest("risk:XX", reports) is None


def test_forged_signature_report_is_rejected():
    audit, providers, net = _setup(quorum=2)
    good = submit_report(providers[0], "risk:XX", "low")
    forged = submit_report(providers[1], "risk:XX", "low")
    forged.signature = providers[2].sign(b"wrong payload")  # corrupt the signature
    assert net.ingest("risk:XX", [good, forged]) is None  # only 1 valid report


def test_duplicate_reports_from_same_provider_only_count_once():
    audit, providers, net = _setup(quorum=2)
    r1 = submit_report(providers[0], "risk:XX", "low")
    r2 = submit_report(providers[0], "risk:XX", "low")  # same provider reports twice
    assert net.ingest("risk:XX", [r1, r2]) is None  # still only 1 distinct provider
