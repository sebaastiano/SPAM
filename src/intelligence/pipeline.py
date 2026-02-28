"""
Intelligence pipeline — wires the full data-collection → embedding →
clustering → zone-selection flow.
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np

from src.config import TEAM_ID
from src.intelligence.briefing import BriefingGenerator
from src.intelligence.cluster import classify_cluster
from src.intelligence.competitor_state import CompetitorStateBuilder
from src.intelligence.data_collector import DataCollector
from src.intelligence.embedding import EmbeddingProjector
from src.intelligence.feature_extractor import extract_feature_vector
from src.intelligence.strategy_inferrer import StrategyInferrer
from src.intelligence.tracker_bridge import TrackerBridge
from src.intelligence.trajectory import AdvancedTrajectoryPredictor
from src.memory.competitor import CompetitorMemory
from src.models import Recipe, TrackerSnapshot

log = logging.getLogger(__name__)


class IntelligencePipeline:
    """Orchestrates the full competitive-intelligence flow.

    Call ``run(turn_id)`` once per strategic decision point (start of
    speaking / waiting phase). It returns the active-zone recommendation
    and per-competitor briefings.
    """

    def __init__(
        self,
        bridge: TrackerBridge,
        competitor_memory: CompetitorMemory,
        recipe_db: dict[str, Recipe] | None = None,
    ) -> None:
        self.collector = DataCollector(bridge)
        self.state_builder = CompetitorStateBuilder(recipe_db)
        self.strategy_inferrer = StrategyInferrer()
        self.feature_extractor = extract_feature_vector  # function
        self.projector = EmbeddingProjector()
        self.trajectory = AdvancedTrajectoryPredictor(recipe_db)
        self.briefing_gen = BriefingGenerator(self.trajectory)
        self.competitor_memory = competitor_memory

    def set_recipe_db(self, recipes: dict[str, Recipe]) -> None:
        self.state_builder.set_recipe_db(recipes)
        self.trajectory.set_recipe_db(recipes)

    async def run(self, turn_id: int) -> dict[str, Any]:
        """Execute the full intelligence pipeline.

        Returns::

            {
                "briefings": {rid: {...}},
                "clusters": {rid: cluster_label},
                "demand_forecast": {ingredient: qty},
                "snapshot": TrackerSnapshot,
            }
        """
        # 1. Collect data
        snapshot: TrackerSnapshot = await self.collector.collect(turn_id)

        # 2. Build per-competitor states
        features_map: dict[int, np.ndarray] = {}
        for rid, rdata in snapshot.restaurants.items():
            if rid == TEAM_ID:
                continue
            state = self.state_builder.build(
                rid=rid,
                turn_id=turn_id,
                restaurant_data=rdata,
                bid_data=snapshot.bid_history,
                market_data=snapshot.market_entries,
            )

            # 3. Infer strategy
            history = self.state_builder.history.get(rid, [])
            inference = self.strategy_inferrer.infer(state, history)
            state.inferred_strategy = inference["strategy"]

            # 4. Extract features
            feats = self.feature_extractor(state, history)
            features_map[rid] = feats

            # 5. Update trajectory predictor
            self.trajectory.update(rid, state, feats)

            # 6. Persist to memory
            self.competitor_memory.record_state(state)
            self.competitor_memory.record_features(rid, feats)

        # 7. Embedding + clustering
        rids = list(features_map.keys())
        if rids:
            matrix = np.array([features_map[r] for r in rids])
            projected = self.projector.fit_transform(matrix)
            for i, rid in enumerate(rids):
                state = self.state_builder.history[rid][-1]
                cluster = classify_cluster(
                    projected[i], state.inferred_strategy
                )
                self.competitor_memory.set_cluster(rid, cluster)

        # 8. Briefings
        briefings = self.briefing_gen.generate()

        # 9. Demand forecast
        demand_forecast = self.trajectory.get_ingredient_demand_forecast()

        return {
            "briefings": briefings,
            "clusters": dict(self.competitor_memory.clusters),
            "demand_forecast": demand_forecast,
            "snapshot": snapshot,
        }
