"""
multi_agent_observation.py — Observing multiple agents competing in real time.

Demonstrates:
    1. Simulating a multi-agent competitive environment
    2. Using the full observability pipeline to track all agents
    3. Launching the web dashboard for real-time visualization
    4. Each agent having different behavioral strategies

Run::

    pip install datapizza-ai-observability-vectorspace[dashboard]
    python multi_agent_observation.py

Then open http://127.0.0.1:5050 in your browser.
"""

import asyncio
import time

import numpy as np

# datapizza pipeline
from datapizza.pipeline.dag_pipeline import DagPipeline

# observability components
from datapizza.modules.observability import (
    VectorSpaceModule,
    TrajectoryTracker,
    SnapshotStore,
)
from datapizza.tools.vectorspace import VectorSpaceDashboard


# ── Feature space definition ──

FEATURE_LABELS = [
    "bid_aggressiveness",
    "price_premium_ratio",
    "quality_investment",
    "volume_capacity",
    "menu_diversity",
    "cost_efficiency",
    "brand_reputation",
    "risk_appetite",
    "innovation_index",
    "customer_retention",
]

N_FEATURES = len(FEATURE_LABELS)

# Zone centroids — represent ideal competitive strategies
ZONE_CENTROIDS = {
    "premium_leader":   [0.85, 0.90, 0.95, 0.30, 0.60, 0.40, 0.95, 0.50, 0.80, 0.90],
    "cost_leader":      [0.70, 0.15, 0.40, 0.90, 0.50, 0.95, 0.50, 0.60, 0.30, 0.65],
    "niche_specialist": [0.40, 0.75, 0.85, 0.20, 0.30, 0.50, 0.70, 0.30, 0.90, 0.85],
    "mass_market":      [0.55, 0.45, 0.55, 0.75, 0.80, 0.70, 0.55, 0.45, 0.45, 0.60],
}


# ── Agent behavioral strategies ──

class AgentStrategy:
    """Simulates distinct behavioral patterns for different agents."""

    def __init__(self, name: str, base: np.ndarray, style: str):
        self.name = name
        self.position = base.copy()
        self.style = style  # "steady", "aggressive", "adaptive", "chaotic"
        self.step = 0

    def evolve(self) -> list[float]:
        """Produce next feature vector based on behavioral style."""
        self.step += 1
        noise = np.random.randn(N_FEATURES) * 0.02

        if self.style == "steady":
            # Minimal change — reliable, predictable
            self.position += noise * 0.5

        elif self.style == "aggressive":
            # Drift toward premium, increasing bid aggressiveness
            drift = np.zeros(N_FEATURES)
            drift[0] = 0.015   # more aggressive bidding
            drift[1] = 0.01    # higher price premium
            drift[2] = 0.008   # invest in quality
            self.position += drift + noise

        elif self.style == "adaptive":
            # Oscillate — tries different strategies
            phase = np.sin(self.step * np.pi / 4) * 0.04
            self.position += noise + phase

        elif self.style == "chaotic":
            # Large random swings
            self.position += np.random.randn(N_FEATURES) * 0.06

        elif self.style == "converging":
            # Slowly converging toward a specific zone (cost_leader)
            target = np.array(ZONE_CENTROIDS["cost_leader"])
            direction = target - self.position
            self.position += direction * 0.08 + noise * 0.3

        self.position = np.clip(self.position, 0, 1)
        return self.position.tolist()


# ── Multi-entity feature extractor component ──

class CompetitiveEnvironment:
    """Simulates a competitive environment with multiple agents."""

    def __init__(self):
        self.agents = [
            AgentStrategy("alpha_grill", np.array([0.5]*N_FEATURES) + np.random.rand(N_FEATURES)*0.2, "aggressive"),
            AgentStrategy("bella_cucina", np.array([0.6]*N_FEATURES) + np.random.rand(N_FEATURES)*0.1, "steady"),
            AgentStrategy("cosmic_eats", np.array([0.4]*N_FEATURES) + np.random.rand(N_FEATURES)*0.2, "adaptive"),
            AgentStrategy("dynamo_diner", np.array([0.5]*N_FEATURES) + np.random.rand(N_FEATURES)*0.15, "chaotic"),
            AgentStrategy("echo_bistro", np.array([0.7]*N_FEATURES) + np.random.rand(N_FEATURES)*0.1, "converging"),
            AgentStrategy("fusion_house", np.array([0.3]*N_FEATURES) + np.random.rand(N_FEATURES)*0.3, "steady"),
        ]

    def run(self, data=None, **kwargs):
        features = {}
        for agent in self.agents:
            features[agent.name] = agent.evolve()
        return {"features": features}

    async def a_run(self, data=None, **kwargs):
        return self.run(data, **kwargs)


async def main():
    # ── Build the full pipeline ──
    pipeline = DagPipeline()

    env = CompetitiveEnvironment()
    projector = VectorSpaceModule(
        n_components=2,
        method="pca",
        centroids=ZONE_CENTROIDS,
        feature_labels=FEATURE_LABELS,
    )
    tracker = TrajectoryTracker(
        window=10,
        centroids=ZONE_CENTROIDS,
        feature_labels=FEATURE_LABELS,
    )
    store = SnapshotStore(
        path="./multi_agent_data",
        backend="json",
        session_id="multi_agent_demo",
    )

    pipeline.add_module("environment", env)
    pipeline.add_module("vectorspace", projector)
    pipeline.add_module("trajectory", tracker)
    pipeline.add_module("store", store)

    pipeline.connect("environment", "vectorspace", target_key="features")
    pipeline.connect("environment", "trajectory", target_key="features")
    pipeline.connect("vectorspace", "store", target_key="projections")
    pipeline.connect("trajectory", "store", target_key="trajectories")

    # ── Launch dashboard ──
    try:
        dashboard = VectorSpaceDashboard(
            snapshot_store=store,
            tracker=tracker,
            projector=projector,
        )
        url = dashboard.launch_background(port=5050)
        print(f"Dashboard running at {url}")
        print("Open your browser to see the vector space in real time.\n")
    except ImportError:
        print("Flask not installed — running without dashboard.")
        print("Install with: pip install datapizza-ai-observability-vectorspace[dashboard]\n")

    # ── Simulate 30 turns of competition ──
    print("Simulating 30 competitive turns (2s each)...\n")

    for step in range(30):
        result = await pipeline.a_run({"step": step})

        # Print step summary
        store_out = result.get("store", {})
        snapshot = store_out.get("snapshot", {})
        entities = snapshot.get("entities", {})

        classifications = {}
        for eid, es in entities.items():
            cls = es.get("trajectory_class", "—")
            classifications[cls] = classifications.get(cls, 0) + 1

        print(f"Turn {step:2d} | {len(entities)} agents | "
              f"patterns: {dict(classifications)}")

        # Wait 2 seconds so the dashboard can poll
        await asyncio.sleep(2)

    print("\nSimulation complete. Dashboard remains active.")
    print("Press Ctrl+C to exit.\n")

    # Keep alive for dashboard
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        store.close()
        print("Done.")


if __name__ == "__main__":
    asyncio.run(main())
