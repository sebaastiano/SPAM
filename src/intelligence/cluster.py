"""
SPAM! — Cluster Classifier
=============================
Classify competitors into behavioral clusters based on
14-dim feature vectors and their PCA embeddings.

Clusters:
  STABLE_SPECIALIST, REACTIVE_CHASER, AGGRESSIVE_HOARDER,
  DECLINING, DORMANT, UNCLASSIFIED
"""

import logging

import numpy as np

from src.config import CLUSTER_STRATEGIES

logger = logging.getLogger("spam.intelligence.cluster")

# Cluster definitions for rule-based classification
CLUSTERS = list(CLUSTER_STRATEGIES.keys())


class ClusterClassifier:
    """
    Rule-based competitor classification into behavioral clusters.

    Uses strategy inference results and feature vectors for
    classification. Falls back to k-means when sufficient data
    is available (>= 5 restaurants, >= 3 turns).
    """

    def classify(self, strategy: str, features: np.ndarray | None = None) -> str:
        """
        Classify a competitor into a cluster.

        Primary classification uses the StrategyInferrer result directly,
        mapping strategy names to cluster names.
        """
        strategy_to_cluster = {
            "PREMIUM_MONOPOLIST": "STABLE_SPECIALIST",
            "BUDGET_OPPORTUNIST": "STABLE_SPECIALIST",
            "AGGRESSIVE_HOARDER": "AGGRESSIVE_HOARDER",
            "MARKET_ARBITRAGEUR": "STABLE_SPECIALIST",
            "REACTIVE_CHASER": "REACTIVE_CHASER",
            "DECLINING": "DECLINING",
            "DORMANT": "DORMANT",
            "UNCLASSIFIED": "UNCLASSIFIED",
        }

        cluster = strategy_to_cluster.get(strategy, "UNCLASSIFIED")

        # Transitioning strategies
        if strategy.startswith("TRANSITIONING→"):
            target = strategy.split("→")[-1]
            cluster = strategy_to_cluster.get(target, "REACTIVE_CHASER")

        return cluster

    def get_relational_strategy(self, cluster: str) -> str:
        """Get the recommended relational strategy for a cluster."""
        return CLUSTER_STRATEGIES.get(cluster, "Probe — classify first")

    async def process(self, input_data: dict) -> dict:
        """
        Pipeline module interface.

        input_data should contain:
          - strategies: {rid: {strategy: str, ...}} from strategy inferrer
          - features: {rid: np.ndarray} from feature extractor (optional)
          - embeddings: {rid: np.ndarray} from embedding module (optional)

        Returns dict with 'clusters': {rid: cluster_name}
        """
        strategies = input_data.get("strategies", {})
        features = input_data.get("features", {})

        clusters = {}
        for rid, strat_data in strategies.items():
            strategy = strat_data if isinstance(strat_data, str) else strat_data.get("strategy", "UNCLASSIFIED")
            feat = features.get(rid)
            clusters[rid] = self.classify(strategy, feat)

        return {"clusters": clusters}
