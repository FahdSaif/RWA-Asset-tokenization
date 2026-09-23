import pathlib

from arca.layer1_intelligence.crr import verify_crr
from arca.layer1_intelligence.risk_scoring_agent import TransactionRiskScoringAgent, train_model
from arca.layer2_identity.did_registry import generate_did

DATA_DIR = pathlib.Path(__file__).resolve().parents[1] / "data"


def test_model_beats_random_baseline():
    metrics = train_model()
    # A random/no-signal model has ROC-AUC ~0.5; require the trained model
    # to show genuine, substantial separation on held-out data.
    assert metrics["roc_auc"] > 0.75, f"ROC-AUC too low: {metrics['roc_auc']}"


def test_agent_scores_and_signs_a_crr():
    agent = TransactionRiskScoringAgent(generate_did())
    features = {
        "amount": 5000.0, "jurisdiction_tier": 0, "tx_velocity_24h": 1,
        "unique_counterparties_7d": 1, "account_age_days": 500, "cross_border": 0,
        "is_new_counterparty": 0, "hour_of_day": 10, "structuring_proximity": 0.0, "is_round_number": 0.0,
    }
    crr = agent.score("TX-1", features)
    assert 0.0 <= crr.outcome <= 1.0
    assert verify_crr(crr) is True
    assert len(crr.reasoning_trace) >= 2


def test_high_risk_pattern_scores_higher_than_low_risk_pattern():
    agent = TransactionRiskScoringAgent(generate_did())
    low_risk = {
        "amount": 3000.0, "jurisdiction_tier": 0, "tx_velocity_24h": 1,
        "unique_counterparties_7d": 1, "account_age_days": 900, "cross_border": 0,
        "is_new_counterparty": 0, "hour_of_day": 13, "structuring_proximity": 0.0, "is_round_number": 0.0,
    }
    high_risk = {
        "amount": 9500.0, "jurisdiction_tier": 2, "tx_velocity_24h": 8,
        "unique_counterparties_7d": 6, "account_age_days": 5, "cross_border": 1,
        "is_new_counterparty": 1, "hour_of_day": 3, "structuring_proximity": 0.9, "is_round_number": 1.0,
    }
    crr_low = agent.score("TX-low", low_risk)
    crr_high = agent.score("TX-high", high_risk)
    assert crr_high.outcome > crr_low.outcome
