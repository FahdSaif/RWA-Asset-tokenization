"""
Layer 1 — Behavioural Anomaly Detection Agent (paper Sec. V-C,
"Behavioural Anomaly Detection Agent").

Monitors the on-chain transaction *graph* (participants as nodes,
transactions as directed edges) for structural patterns associated with
layering and structuring: unusually high fan-out/fan-in (a "hub" moving
funds through many counterparties), short cyclic paths (funds returning
close to their origin — a classic layering red flag), and statistical
outliers across graph-derived features via IsolationForest, an
unsupervised method appropriate here because, unlike the Risk Scoring
Agent, this agent is explicitly meant to catch patterns that were not
anticipated at model-design time rather than fit to a labeled dataset.

Detections are severity-classified and issued as CRRs; the Transaction
Validation Module (Layer 3) can act on this immediately, per the
paper's "triggering heightened validation requirements for subsequent
transactions from flagged participants."
"""
from __future__ import annotations

from typing import Dict, List

import networkx as nx
import numpy as np
from sklearn.ensemble import IsolationForest

from arca.layer1_intelligence.crr import ComplianceRecommendationRecord, issue_crr
from arca.layer2_identity.did_registry import DIDKeyPair


class TransactionGraph:
    """Thin wrapper around a networkx.MultiDiGraph of DID -> DID transfers."""

    def __init__(self):
        self.graph = nx.MultiDiGraph()

    def add_transaction(self, sender_did: str, receiver_did: str, amount: float, timestamp: float) -> None:
        self.graph.add_edge(sender_did, receiver_did, amount=amount, timestamp=timestamp)

    def node_features(self, did: str) -> Dict[str, float]:
        g = self.graph
        if did not in g:
            return {
                "out_degree": 0, "in_degree": 0, "unique_out_neighbors": 0, "unique_in_neighbors": 0,
                "total_sent": 0.0, "total_received": 0.0, "reciprocity": 0.0, "shortest_cycle_len": 0.0,
            }
        out_edges = list(g.out_edges(did, data=True))
        in_edges = list(g.in_edges(did, data=True))
        out_neighbors = {v for _, v, _ in out_edges}
        in_neighbors = {u for u, _, _ in in_edges}
        reciprocal = out_neighbors & in_neighbors

        cycle_len = 0.0
        try:
            for target in list(out_neighbors)[:5]:  # bounded, for tractability on a demo graph
                if nx.has_path(g, target, did):
                    length = nx.shortest_path_length(g, target, did)
                    if cycle_len == 0.0 or length + 1 < cycle_len:
                        cycle_len = length + 1
        except nx.NetworkXNoPath:
            pass

        return {
            "out_degree": float(len(out_edges)),
            "in_degree": float(len(in_edges)),
            "unique_out_neighbors": float(len(out_neighbors)),
            "unique_in_neighbors": float(len(in_neighbors)),
            "total_sent": float(sum(d["amount"] for _, _, d in out_edges)),
            "total_received": float(sum(d["amount"] for _, _, d in in_edges)),
            "reciprocity": float(len(reciprocal)),
            "shortest_cycle_len": cycle_len,
        }

    def all_participants(self) -> List[str]:
        return list(self.graph.nodes)


GRAPH_FEATURES = [
    "out_degree", "in_degree", "unique_out_neighbors", "unique_in_neighbors",
    "total_sent", "total_received", "reciprocity", "shortest_cycle_len",
]


class BehaviouralAnomalyDetectionAgent:
    def __init__(self, keypair: DIDKeyPair, contamination: float = 0.08, random_state: int = 42):
        self.keypair = keypair
        self.contamination = contamination
        self.random_state = random_state
        self._model: IsolationForest | None = None

    def fit(self, graph: TransactionGraph) -> None:
        """Fits the outlier model over the current participant population.
        In production this is refreshed on a rolling window, not fit once
        — kept simple here for a self-contained demo."""
        participants = graph.all_participants()
        X = np.array([[graph.node_features(p)[f] for f in GRAPH_FEATURES] for p in participants])
        self._model = IsolationForest(contamination=self.contamination, random_state=self.random_state)
        self._model.fit(X)

    def evaluate(self, context_id: str, did: str, graph: TransactionGraph) -> ComplianceRecommendationRecord:
        if self._model is None:
            raise RuntimeError("call fit(graph) before evaluate()")

        features = graph.node_features(did)
        X = np.array([[features[f] for f in GRAPH_FEATURES]])
        anomaly_score = float(-self._model.score_samples(X)[0])  # higher = more anomalous
        is_outlier = bool(self._model.predict(X)[0] == -1)

        if anomaly_score > 0.65:
            severity = "high"
        elif anomaly_score > 0.55:
            severity = "medium"
        else:
            severity = "low"

        reasoning = [f"Graph-based anomaly score: {anomaly_score:.3f} (severity={severity})."]
        if features["shortest_cycle_len"] and features["shortest_cycle_len"] <= 3:
            reasoning.append(
                f"Short return path detected (length {features['shortest_cycle_len']:.0f}): "
                "funds sent by this participant return to it within a small number of hops, "
                "a pattern associated with layering."
            )
        if features["unique_out_neighbors"] >= 5 and features["out_degree"] / max(features["unique_out_neighbors"], 1) < 1.5:
            reasoning.append(
                f"High fan-out to {features['unique_out_neighbors']:.0f} distinct counterparties "
                "with low repeat-interaction rate, consistent with fund dispersal / structuring."
            )
        if is_outlier:
            reasoning.append("Flagged as a statistical outlier relative to the current participant population.")

        return issue_crr(
            self.keypair,
            determination_type="anomaly",
            context_id=context_id,
            outcome=is_outlier and severity in ("medium", "high"),
            reasoning_trace=reasoning,
            inputs={"did": did, **features},
            subject_did=did,
        )
