"""
SPAM! — Intelligence Pipeline
================================
DagPipeline wiring for the full competitive intelligence flow.

Flow (per implementation_strategy.md §6.7):
  DataCollector → StateBuilder → FeatureExtractor → StrategyInferrer
  → Embedding → Trajectory → Cluster → BriefingGenerator

Uses datapizza-ai DagPipeline for module orchestration.
"""

import logging

import numpy as np

from datapizza.core.models import PipelineComponent
from datapizza.pipeline import DagPipeline

from src.intelligence.tracker_bridge import TrackerBridge
from src.intelligence.data_collector import DataCollectorModule
from src.intelligence.competitor_state import CompetitorStateBuilder, CompetitorTurnState
from src.intelligence.strategy_inferrer import StrategyInferrer
from src.intelligence.feature_extractor import extract_feature_vector, set_recipe_db
from src.intelligence.embedding import EmbeddingModule
from src.intelligence.trajectory import AdvancedTrajectoryPredictor
from src.intelligence.briefing import BriefingGeneratorModule
from src.intelligence.cluster import ClusterClassifier
from src.memory.competitor import CompetitorMemory
from src.config import TEAM_ID

logger = logging.getLogger("spam.intelligence.pipeline")


# ── PipelineComponent wrappers for DagPipeline integration ──


class DataCollectorComponent(PipelineComponent):
    """Collects raw game data via TrackerBridge or direct API polling."""

    def __init__(self, collector: DataCollectorModule):
        super().__init__()
        self._collector = collector

    def _run(self, turn_id: int = 0) -> dict:
        import asyncio
        return asyncio.get_event_loop().run_until_complete(
            self._collector.process({"turn_id": turn_id})
        )

    async def _a_run(self, turn_id: int = 0) -> dict:
        result = await self._collector.process({"turn_id": turn_id})
        result["turn_id"] = turn_id
        return result


class StateBuilderComponent(PipelineComponent):
    """Builds CompetitorTurnState for all competitors from raw data."""

    def __init__(self, builder: CompetitorStateBuilder, team_id: int = TEAM_ID):
        super().__init__()
        self._builder = builder
        self._team_id = team_id

    def _run(self, raw_data: dict = None) -> dict:
        if not raw_data:
            return {"all_states": {}, "global_avg_price": 120.0}

        restaurants = raw_data.get("all_restaurants", {})
        bids = raw_data.get("bids", [])
        market = raw_data.get("market_entries", [])
        turn_id = raw_data.get("turn_id", 0)

        # Compute global average price for feature normalization
        all_prices = []
        for rid, rdata in restaurants.items():
            rid_int = int(rid) if isinstance(rid, str) else rid
            if rid_int == self._team_id:
                continue
            menu = rdata.get("menu", {})
            items = (
                menu.get("items", [])
                if isinstance(menu, dict)
                else (menu if isinstance(menu, list) else [])
            )
            for item in items:
                if isinstance(item, dict) and "price" in item:
                    all_prices.append(item["price"])
        global_avg_price = (
            float(sum(all_prices) / max(len(all_prices), 1))
            if all_prices
            else 120.0
        )

        all_states: dict[int, CompetitorTurnState] = {}
        for rid, rdata in restaurants.items():
            rid_int = int(rid) if isinstance(rid, str) else rid
            if rid_int == self._team_id:
                continue
            prev_state = self._builder.get_prev_state(rid_int)
            state = self._builder.build_turn_state(
                rid=rid_int,
                turn_id=turn_id,
                restaurant_data=rdata,
                bid_data=bids,
                market_data=market,
                prev_state=prev_state,
            )
            all_states[rid_int] = state

        return {
            "all_states": all_states,
            "global_avg_price": global_avg_price,
        }

    async def _a_run(self, raw_data: dict = None) -> dict:
        return self._run(raw_data)


class FeatureExtractorComponent(PipelineComponent):
    """Extracts 14-dim behavioral feature vectors for all competitors."""

    def __init__(self, extractor_fn, builder: CompetitorStateBuilder):
        super().__init__()
        self._extract = extractor_fn
        self._builder = builder

    def _run(self, states_data: dict = None) -> dict:
        if not states_data:
            return {"features": {}, "all_states": {}}
        all_states = states_data.get("all_states", {})
        global_avg_price = states_data.get("global_avg_price", 120.0)

        features: dict[int, np.ndarray] = {}
        for rid, state in all_states.items():
            history = self._builder.history.get(rid, [])
            features[rid] = self._extract(state, history, global_avg_price)

        return {"features": features, "all_states": all_states}

    async def _a_run(self, states_data: dict = None) -> dict:
        return self._run(states_data)


class StrategyInferrerComponent(PipelineComponent):
    """Infers strategy hypothesis for all competitors."""

    def __init__(self, inferrer: StrategyInferrer, builder: CompetitorStateBuilder):
        super().__init__()
        self._inferrer = inferrer
        self._builder = builder

    def _run(self, states_data: dict = None) -> dict:
        if not states_data:
            return {"strategies": {}}
        all_states = states_data.get("all_states", {})

        strategies: dict[int, dict] = {}
        for rid, state in all_states.items():
            history = self._builder.history.get(rid, [])
            strat = self._inferrer.infer(state, history)
            strategies[rid] = strat
            state.inferred_strategy = strat["strategy"]

        return {"strategies": strategies}

    async def _a_run(self, states_data: dict = None) -> dict:
        return self._run(states_data)


class EmbeddingComponent(PipelineComponent):
    """Computes PCA/UMAP embeddings from feature vectors."""

    def __init__(self, embedding_module: EmbeddingModule):
        super().__init__()
        self._embedding = embedding_module

    def _run(self, features_data: dict = None) -> dict:
        return {"embeddings": {}}

    async def _a_run(self, features_data: dict = None) -> dict:
        if not features_data:
            return {"embeddings": {}}
        features = features_data.get("features", {})
        if features:
            result = await self._embedding.process({"features": features})
            return {"embeddings": result.get("embeddings", {})}
        return {"embeddings": {}}


class TrajectoryComponent(PipelineComponent):
    """Multi-level trajectory prediction for all competitors."""

    def __init__(self, predictor: AdvancedTrajectoryPredictor):
        super().__init__()
        self._predictor = predictor

    def _run(
        self,
        features_data: dict = None,
        strategies_data: dict = None,
    ) -> dict:
        if not features_data:
            return {"predictions": {}, "demand_forecast": {}}

        features = features_data.get("features", {})
        all_states = features_data.get("all_states", {})

        for rid, feat in features.items():
            state = all_states.get(rid)
            if state:
                self._predictor.update(rid, state, feat)

        return {
            "predictions": self._predictor.generate_per_competitor_briefing(),
            "demand_forecast": self._predictor.get_ingredient_demand_forecast(),
        }

    async def _a_run(
        self,
        features_data: dict = None,
        strategies_data: dict = None,
    ) -> dict:
        return self._run(features_data, strategies_data)


class ClusterComponent(PipelineComponent):
    """Classifies competitors into behavioral clusters."""

    def __init__(self, classifier: ClusterClassifier):
        super().__init__()
        self._classifier = classifier

    def _run(
        self,
        strategies_data: dict = None,
        features_data: dict = None,
    ) -> dict:
        if not strategies_data:
            return {"clusters": {}}

        strategies = strategies_data.get("strategies", {})
        features = (features_data or {}).get("features", {})

        clusters: dict[int, str] = {}
        for rid, strat in strategies.items():
            clusters[rid] = self._classifier.classify(
                strat.get("strategy", "UNCLASSIFIED"),
                features.get(rid),
            )

        return {"clusters": clusters}

    async def _a_run(
        self,
        strategies_data: dict = None,
        features_data: dict = None,
    ) -> dict:
        return self._run(strategies_data, features_data)


class BriefingGeneratorComponent(PipelineComponent):
    """Generates per-competitor tactical briefings enriched with cluster data."""

    def __init__(self, classifier: ClusterClassifier):
        super().__init__()
        self._classifier = classifier

    def _run(
        self,
        trajectory_data: dict = None,
        clusters_data: dict = None,
    ) -> dict:
        if not trajectory_data:
            return {"briefings": {}, "demand_forecast": {}}

        briefings = dict(trajectory_data.get("predictions", {}))
        demand_forecast = trajectory_data.get("demand_forecast", {})
        clusters = (clusters_data or {}).get("clusters", {})

        for rid in briefings:
            briefings[rid]["cluster"] = clusters.get(rid, "UNCLASSIFIED")
            briefings[rid]["relational_strategy"] = (
                self._classifier.get_relational_strategy(
                    clusters.get(rid, "UNCLASSIFIED")
                )
            )

        return {"briefings": briefings, "demand_forecast": demand_forecast}

    async def _a_run(
        self,
        trajectory_data: dict = None,
        clusters_data: dict = None,
    ) -> dict:
        return self._run(trajectory_data, clusters_data)


# ── Main pipeline class ──


class IntelligencePipeline:
    """
    Full competitive intelligence pipeline using datapizza-ai DagPipeline.

    Module graph (per implementation_strategy.md §6.7):
      data_collector → state_builder → feature_extractor → embedding
                                     ↘ strategy_inferrer ↘
                       feature_extractor → trajectory → briefing_generator
                       strategy_inferrer → cluster   ↗

    Runs via ``await pipeline.run(turn_id)`` which delegates to DagPipeline.a_run().
    """

    def __init__(
        self,
        bridge: TrackerBridge | None = None,
        recipe_db: dict | None = None,
        competitor_memory: CompetitorMemory | None = None,
    ):
        # Core processing objects (shared across components by reference)
        self.data_collector = DataCollectorModule(bridge=bridge)
        self.state_builder = CompetitorStateBuilder(recipe_db=recipe_db or {})
        self.strategy_inferrer = StrategyInferrer()
        self.feature_extractor_fn = extract_feature_vector
        self.embedding_module = EmbeddingModule(n_components=2)
        self.trajectory_predictor = AdvancedTrajectoryPredictor(
            recipe_db=recipe_db or {}
        )
        self.cluster_classifier = ClusterClassifier()
        self.briefing_generator = BriefingGeneratorModule(
            trajectory_predictor=self.trajectory_predictor
        )
        self.competitor_memory = competitor_memory or CompetitorMemory()

        # Set recipe DB for feature extractor module
        if recipe_db:
            set_recipe_db(recipe_db)

        # ── Build DagPipeline ──
        self._dag = DagPipeline()

        # Add modules
        self._dag.add_module(
            "data_collector", DataCollectorComponent(self.data_collector)
        )
        self._dag.add_module(
            "state_builder", StateBuilderComponent(self.state_builder)
        )
        self._dag.add_module(
            "feature_extractor",
            FeatureExtractorComponent(self.feature_extractor_fn, self.state_builder),
        )
        self._dag.add_module(
            "strategy_inferrer",
            StrategyInferrerComponent(self.strategy_inferrer, self.state_builder),
        )
        self._dag.add_module(
            "embedding", EmbeddingComponent(self.embedding_module)
        )
        self._dag.add_module(
            "trajectory", TrajectoryComponent(self.trajectory_predictor)
        )
        self._dag.add_module(
            "cluster", ClusterComponent(self.cluster_classifier)
        )
        self._dag.add_module(
            "briefing_generator",
            BriefingGeneratorComponent(self.cluster_classifier),
        )

        # Wire connections (per implementation_strategy.md §6.7)
        self._dag.connect("data_collector", "state_builder", target_key="raw_data")
        self._dag.connect("state_builder", "feature_extractor", target_key="states_data")
        self._dag.connect("state_builder", "strategy_inferrer", target_key="states_data")
        self._dag.connect("feature_extractor", "embedding", target_key="features_data")
        self._dag.connect("feature_extractor", "trajectory", target_key="features_data")
        self._dag.connect("strategy_inferrer", "trajectory", target_key="strategies_data")
        self._dag.connect("strategy_inferrer", "cluster", target_key="strategies_data")
        self._dag.connect("feature_extractor", "cluster", target_key="features_data")
        self._dag.connect("trajectory", "briefing_generator", target_key="trajectory_data")
        self._dag.connect("cluster", "briefing_generator", target_key="clusters_data")

        logger.info("Intelligence DagPipeline built with 8 modules, 10 connections")

    async def run(self, turn_id: int) -> dict:
        """
        Run the full intelligence pipeline for a given turn.

        Delegates to DagPipeline.a_run(), then updates competitor memory.

        Returns:
            dict with keys: briefings, clusters, features, strategies,
            embeddings, demand_forecast, all_states, global_avg_price
        """
        logger.info(f"Running intelligence pipeline (DagPipeline) for turn {turn_id}")

        try:
            dag_result = await self._dag.a_run({
                "data_collector": {"turn_id": turn_id},
            })
        except Exception as e:
            logger.error(f"DagPipeline execution failed: {e}", exc_info=True)
            return self._empty_result()

        # Extract outputs from each module
        states_out = dag_result.get("state_builder") or {}
        features_out = dag_result.get("feature_extractor") or {}
        strategies_out = dag_result.get("strategy_inferrer") or {}
        embeddings_out = dag_result.get("embedding") or {}
        clusters_out = dag_result.get("cluster") or {}
        briefings_out = dag_result.get("briefing_generator") or {}

        all_states = states_out.get("all_states", {}) if isinstance(states_out, dict) else {}
        features = features_out.get("features", {}) if isinstance(features_out, dict) else {}
        strategies = strategies_out.get("strategies", {}) if isinstance(strategies_out, dict) else {}
        clusters = clusters_out.get("clusters", {}) if isinstance(clusters_out, dict) else {}
        briefings = briefings_out.get("briefings", {}) if isinstance(briefings_out, dict) else {}
        demand_forecast = briefings_out.get("demand_forecast", {}) if isinstance(briefings_out, dict) else {}
        global_avg_price = states_out.get("global_avg_price", 120.0) if isinstance(states_out, dict) else 120.0

        # Post-pipeline: update competitor memory
        for rid in features:
            state = all_states.get(rid)
            strat = strategies.get(rid, {})
            feat = features[rid]
            if state:
                self.competitor_memory.update_entity(
                    entity_id=rid,
                    features=feat,
                    name=state.name,
                    balance=state.balance,
                    reputation=state.reputation,
                    menu=state.menu,
                    bids=state.bids,
                    inventory=state.inventory,
                    strategy=strat.get("strategy", "UNCLASSIFIED"),
                )
            if rid in clusters:
                self.competitor_memory.classify_entity(rid, clusters[rid])

        result = {
            "briefings": briefings,
            "clusters": clusters,
            "features": features,
            "strategies": strategies,
            "embeddings": embeddings_out.get("embeddings", {}) if isinstance(embeddings_out, dict) else {},
            "demand_forecast": demand_forecast,
            "all_states": all_states,
            "global_avg_price": global_avg_price,
        }

        logger.info(
            f"Intelligence: {len(briefings)} competitors analyzed, "
            f"clusters: {dict((c, list(clusters.values()).count(c)) for c in set(clusters.values())) if clusters else {}}"
        )

        return result

    def _empty_result(self) -> dict:
        return {
            "briefings": {},
            "clusters": {},
            "features": {},
            "strategies": {},
            "embeddings": {},
            "demand_forecast": {},
            "all_states": {},
            "global_avg_price": 120.0,
        }
