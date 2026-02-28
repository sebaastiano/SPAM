"""
Competitor memory — tracks all competitors across turns with feature
vectors, cluster assignments, and state history.
"""

from __future__ import annotations

import numpy as np

from src.models import CompetitorTurnState


class CompetitorMemory:
    """Cross-turn competitor tracking with per-restaurant history,
    feature vectors, and cluster assignments."""

    def __init__(self) -> None:
        # restaurant_id → list of per-turn states
        self.state_history: dict[int, list[CompetitorTurnState]] = {}
        # restaurant_id → list of 14-dim feature vectors
        self.feature_history: dict[int, list[np.ndarray]] = {}
        # restaurant_id → current cluster label
        self.clusters: dict[int, str] = {}
        # restaurant_id → credibility score (for message trust)
        self.credibility: dict[int, float] = {}

    # ── Updates ───────────────────────────────────────────────────

    def record_state(self, state: CompetitorTurnState) -> None:
        rid = state.restaurant_id
        self.state_history.setdefault(rid, []).append(state)

    def record_features(self, rid: int, features: np.ndarray) -> None:
        self.feature_history.setdefault(rid, []).append(features)

    def set_cluster(self, rid: int, cluster: str) -> None:
        self.clusters[rid] = cluster

    def update_credibility(self, rid: int, delta: float) -> None:
        self.credibility[rid] = max(
            0.0, min(1.0, self.credibility.get(rid, 0.5) + delta)
        )

    # ── Queries ───────────────────────────────────────────────────

    def get_latest(self, rid: int) -> CompetitorTurnState | None:
        history = self.state_history.get(rid, [])
        return history[-1] if history else None

    def get_history(self, rid: int) -> list[CompetitorTurnState]:
        return self.state_history.get(rid, [])

    def get_features(self, rid: int) -> list[np.ndarray]:
        return self.feature_history.get(rid, [])

    def get_cluster(self, rid: int) -> str:
        return self.clusters.get(rid, "UNCLASSIFIED")

    def get_credibility(self, rid: int) -> float:
        return self.credibility.get(rid, 0.5)

    def all_restaurant_ids(self) -> set[int]:
        return set(self.state_history.keys())

    # ── Reset ─────────────────────────────────────────────────────

    def reset(self) -> None:
        """Preserve history for analysis, but clear clusters/credibility."""
        self.clusters.clear()
        self.credibility.clear()
