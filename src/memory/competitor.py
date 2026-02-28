"""
SPAM! — Competitor Memory
==========================
Multi-entity tracking memory for competitor state, features, and history.
"""

import logging
from dataclasses import dataclass, field
import numpy as np

logger = logging.getLogger("spam.memory.competitor")

FEATURE_DIM = 14


@dataclass
class EntityProfile:
    """Profile for a single tracked competitor."""
    entity_id: int
    name: str = ""
    cluster: str = "unclassified"
    credibility: float = 0.5
    feature_history: list = field(default_factory=list)  # list[np.ndarray]
    balance_history: list = field(default_factory=list)
    reputation_history: list = field(default_factory=list)
    menu_history: list = field(default_factory=list)
    bid_history: list = field(default_factory=list)
    inventory_history: list = field(default_factory=list)
    strategy_history: list = field(default_factory=list)

    def add_features(self, features: np.ndarray):
        self.feature_history.append(features.copy())

    def predict_next(self, momentum: float = 0.7) -> np.ndarray:
        """Predict next position in feature space using momentum."""
        if len(self.feature_history) < 2:
            return self.feature_history[-1] if self.feature_history else np.zeros(FEATURE_DIM)
        velocity = self.feature_history[-1] - self.feature_history[-2]
        if len(self.feature_history) >= 3:
            prev_v = self.feature_history[-2] - self.feature_history[-3]
            velocity = momentum * velocity + (1 - momentum) * prev_v
        return self.feature_history[-1] + velocity


class CompetitorMemory:
    """
    Multi-entity tracking memory for all competitors.

    Each competitor is tracked across turns with:
    - 14-dim behavioral feature vectors
    - Cluster classification
    - Full state history (balance, reputation, menu, bids, inventory)
    - Predicted trajectory
    """

    def __init__(self, feature_dim: int = FEATURE_DIM):
        self.feature_dim = feature_dim
        self.entities: dict[int, EntityProfile] = {}

    def update_entity(
        self,
        entity_id: int,
        features: np.ndarray | None = None,
        name: str = "",
        balance: float | None = None,
        reputation: float | None = None,
        menu: dict | None = None,
        bids: list | None = None,
        inventory: dict | None = None,
        strategy: str | None = None,
    ):
        """Update a competitor's profile with new data."""
        if entity_id not in self.entities:
            self.entities[entity_id] = EntityProfile(entity_id=entity_id, name=name)

        entity = self.entities[entity_id]
        if name:
            entity.name = name
        if features is not None:
            entity.add_features(features)
        if balance is not None:
            entity.balance_history.append(balance)
        if reputation is not None:
            entity.reputation_history.append(reputation)
        if menu is not None:
            entity.menu_history.append(menu)
        if bids is not None:
            entity.bid_history.append(bids)
        if inventory is not None:
            entity.inventory_history.append(inventory)
        if strategy is not None:
            entity.strategy_history.append(strategy)
            entity.cluster = strategy

    def classify_entity(self, entity_id: int, cluster: str):
        if entity_id in self.entities:
            self.entities[entity_id].cluster = cluster

    def predict_trajectory(self, entity_id: int, momentum: float = 0.7) -> np.ndarray:
        """Predict next feature vector for a competitor."""
        if entity_id not in self.entities:
            return np.zeros(self.feature_dim)
        return self.entities[entity_id].predict_next(momentum)

    def get_entities_in_cluster(self, cluster: str) -> list[int]:
        return [eid for eid, e in self.entities.items() if e.cluster == cluster]

    def get_approaching_entities(self, target: np.ndarray, threshold: float) -> list[int]:
        """Which competitors are moving toward a target position in feature space?"""
        approaching = []
        for eid, entity in self.entities.items():
            if len(entity.feature_history) < 2:
                continue
            current_dist = np.linalg.norm(entity.feature_history[-1] - target)
            predicted = entity.predict_next()
            predicted_dist = np.linalg.norm(predicted - target)
            if predicted_dist < current_dist and predicted_dist < threshold:
                approaching.append(eid)
        return approaching

    def get_all_current_features(self) -> dict[int, np.ndarray]:
        """Get the latest feature vector for each competitor."""
        result = {}
        for eid, entity in self.entities.items():
            if entity.feature_history:
                result[eid] = entity.feature_history[-1]
        return result

    def get_entity(self, entity_id: int) -> EntityProfile | None:
        return self.entities.get(entity_id)

    def all_entity_ids(self) -> list[int]:
        return list(self.entities.keys())

    def reset(self):
        """Clear all competitor data (game_reset)."""
        self.entities.clear()
