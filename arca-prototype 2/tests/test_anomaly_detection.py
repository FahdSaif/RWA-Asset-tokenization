from arca.layer1_intelligence.anomaly_detection_agent import (
    BehaviouralAnomalyDetectionAgent,
    TransactionGraph,
)
from arca.layer2_identity.did_registry import generate_did


def test_layering_hub_flagged_normal_not_flagged():
    parties = [generate_did() for _ in range(15)]
    g = TransactionGraph()

    for i in range(10):
        a, b = parties[i % 15].did, parties[(i + 1) % 15].did
        g.add_transaction(a, b, amount=500 + i * 10, timestamp=i)

    hub = parties[0].did
    for j in range(2, 12):
        g.add_transaction(hub, parties[j].did, amount=2000, timestamp=100 + j)
    g.add_transaction(parties[3].did, parties[4].did, amount=1900, timestamp=150)
    g.add_transaction(parties[4].did, hub, amount=1850, timestamp=160)  # short cycle back

    agent = BehaviouralAnomalyDetectionAgent(generate_did())
    agent.fit(g)

    hub_crr = agent.evaluate("CTX-hub", hub, g)
    normal_crr = agent.evaluate("CTX-normal", parties[7].did, g)

    assert hub_crr.outcome is True
    assert normal_crr.outcome is False


def test_unknown_participant_returns_zero_features_not_error():
    g = TransactionGraph()
    g.add_transaction("did:key:a", "did:key:b", 100, 0)
    agent = BehaviouralAnomalyDetectionAgent(generate_did())
    agent.fit(g)
    result = agent.evaluate("CTX", "did:key:unseen", g)
    assert result.outcome is False
