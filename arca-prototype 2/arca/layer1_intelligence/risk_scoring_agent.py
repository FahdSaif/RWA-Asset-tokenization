"""
Layer 1 — Transaction Risk Scoring Agent (paper Sec. V-C, "Transaction
Risk Scoring Agent").

Trains a real gradient-boosted classifier on the transaction feature set
described in the paper ("counterparty credential profile, on-chain
behavioural history, asset type, transaction scale, and the
jurisdictional sensitivity profile") and explains every score with real
SHAP (SHapley Additive exPlanations) feature attributions, converted
into the human-readable reasoning trace the paper requires ("satisfying
both internal audit requirements and the explainability obligations
increasingly imposed on AI systems operating in financial compliance
contexts").

See scripts/generate_synthetic_transactions.py and data/README.md for
why the training data is synthetic-but-documented rather than a public
real-world dataset.
"""
from __future__ import annotations

import pathlib
from typing import Dict, List

import joblib
import numpy as np
import pandas as pd
import shap
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.model_selection import train_test_split

from arca.layer1_intelligence.crr import ComplianceRecommendationRecord, issue_crr
from arca.layer2_identity.did_registry import DIDKeyPair

FEATURE_COLUMNS: List[str] = [
    "amount",
    "jurisdiction_tier",
    "tx_velocity_24h",
    "unique_counterparties_7d",
    "account_age_days",
    "cross_border",
    "is_new_counterparty",
    "hour_of_day",
    "structuring_proximity",
    "is_round_number",
]
LABEL_COLUMN = "is_suspicious"

_DEFAULT_DATA_PATH = pathlib.Path(__file__).resolve().parents[2] / "data" / "synthetic_transactions.csv"
_DEFAULT_MODEL_PATH = pathlib.Path(__file__).resolve().parents[2] / "data" / "risk_model.joblib"


def train_model(
    data_path: pathlib.Path = _DEFAULT_DATA_PATH,
    model_out_path: pathlib.Path = _DEFAULT_MODEL_PATH,
    random_state: int = 42,
) -> Dict[str, float]:
    df = pd.read_csv(data_path)
    X = df[FEATURE_COLUMNS]
    y = df[LABEL_COLUMN]
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.25, random_state=random_state, stratify=y
    )

    model = GradientBoostingClassifier(
        n_estimators=150, learning_rate=0.08, max_depth=3, random_state=random_state
    )
    model.fit(X_train, y_train)

    probs = model.predict_proba(X_test)[:, 1]
    metrics = {
        "roc_auc": float(roc_auc_score(y_test, probs)),
        "average_precision": float(average_precision_score(y_test, probs)),
        "n_train": len(X_train),
        "n_test": len(X_test),
        "positive_rate_test": float(y_test.mean()),
    }

    model_out_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, model_out_path)
    return metrics


class TransactionRiskScoringAgent:
    def __init__(self, keypair: DIDKeyPair, model_path: pathlib.Path = _DEFAULT_MODEL_PATH):
        self.keypair = keypair
        if not model_path.exists():
            train_model(model_out_path=model_path)
        self.model: GradientBoostingClassifier = joblib.load(model_path)
        self.explainer = shap.TreeExplainer(self.model)

    def score(self, tx_id: str, features: Dict[str, float], top_k: int = 3) -> ComplianceRecommendationRecord:
        row = pd.DataFrame([{col: features[col] for col in FEATURE_COLUMNS}])
        risk_score = float(self.model.predict_proba(row)[0, 1])

        shap_values = self.explainer.shap_values(row)
        # binary classifier: TreeExplainer returns values for class 1 directly
        # in recent SHAP versions this is already a 1D array per row.
        contributions = np.asarray(shap_values).reshape(-1)
        order = np.argsort(-np.abs(contributions))[:top_k]

        reasoning = [f"Calibrated risk score: {risk_score:.3f} (0=low risk, 1=high risk)."]
        for idx in order:
            feat = FEATURE_COLUMNS[idx]
            contribution = contributions[idx]
            direction = "increased" if contribution > 0 else "decreased"
            reasoning.append(
                f"Feature '{feat}' = {features[feat]} {direction} the risk score "
                f"by {abs(contribution):.3f} (SHAP attribution)."
            )

        return issue_crr(
            self.keypair,
            determination_type="risk_score",
            context_id=tx_id,
            outcome=risk_score,
            reasoning_trace=reasoning,
            inputs=features,
        )
