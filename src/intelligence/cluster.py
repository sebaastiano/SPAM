"""
Cluster classifier — assigns each competitor to one of five
behavioural clusters.
"""

from __future__ import annotations

import numpy as np


# Cluster label → heuristic centre (will be refined after enough data)
# These are rough hand-tuned starting points in the 2-dim PCA space.
_CLUSTER_CENTRES: dict[str, np.ndarray] = {
    "STABLE_SPECIALIST": np.array([1.0, 0.5]),
    "REACTIVE_CHASER": np.array([-0.5, 1.0]),
    "AGGRESSIVE_HOARDER": np.array([1.5, -0.5]),
    "DECLINING": np.array([-1.0, -1.0]),
    "DORMANT": np.array([0.0, 0.0]),
}


def classify_cluster(
    embedding_2d: np.ndarray,
    inferred_strategy: str = "UNCLASSIFIED",
) -> str:
    """Classify a competitor based on 2-dim embedding + strategy hint.

    If the ``StrategyInferrer`` already produced a high-confidence label
    we prefer that; otherwise we fall back to nearest-centroid in the
    2-dim PCA space.
    """
    # Trust the strategy inferrer for strong signals
    strategy_to_cluster: dict[str, str] = {
        "PREMIUM_MONOPOLIST": "STABLE_SPECIALIST",
        "BUDGET_OPPORTUNIST": "STABLE_SPECIALIST",
        "AGGRESSIVE_HOARDER": "AGGRESSIVE_HOARDER",
        "MARKET_ARBITRAGEUR": "STABLE_SPECIALIST",
        "REACTIVE_CHASER": "REACTIVE_CHASER",
        "DECLINING": "DECLINING",
        "DORMANT": "DORMANT",
    }
    if inferred_strategy in strategy_to_cluster:
        return strategy_to_cluster[inferred_strategy]

    # Nearest centroid fallback
    best_label = "STABLE_SPECIALIST"
    best_dist = float("inf")
    for label, centre in _CLUSTER_CENTRES.items():
        dist = float(np.linalg.norm(embedding_2d - centre))
        if dist < best_dist:
            best_dist = dist
            best_label = label
    return best_label
