"""
basic_pipeline.py — Minimal DagPipeline with vector space observability.

Demonstrates:
    1. Extracting feature vectors for a set of entities
    2. Projecting them into 2D using VectorSpaceModule (PCA)
    3. Tracking trajectories across multiple pipeline steps
    4. Persisting snapshots with SnapshotStore

Run::

    pip install datapizza-ai-observability-vectorspace
    python basic_pipeline.py
"""

import asyncio
import random

import numpy as np

# datapizza pipeline
from datapizza.pipeline.dag_pipeline import DagPipeline

# observability components
from datapizza.modules.observability import (
    VectorSpaceModule,
    TrajectoryTracker,
    SnapshotStore,
)


# ── Mock feature extractor ──
# In a real system, this would be your feature extraction logic
# (e.g., extracting behavioral signals from agent actions)

class MockFeatureExtractor:
    """Simulates 8-dimensional behavioral features for 5 entities."""

    def __init__(self):
        # Each entity starts at a random position
        self.positions = {
            f"agent_{i}": np.random.rand(8) for i in range(5)
        }
        self.step = 0

    def run(self, data=None, **kwargs):
        """Evolve positions with random drift + some structure."""
        self.step += 1
        features = {}

        for eid, pos in self.positions.items():
            # Add gaussian noise (behavioral change per step)
            drift = np.random.randn(8) * 0.05

            # agent_0 drifts toward high values (aggressive strategy)
            if eid == "agent_0":
                drift += 0.02

            # agent_3 oscillates
            if eid == "agent_3":
                drift *= (-1) ** self.step

            pos = np.clip(pos + drift, 0, 1)
            self.positions[eid] = pos
            features[eid] = pos.tolist()

        return {"features": features}

    async def a_run(self, data=None, **kwargs):
        return self.run(data, **kwargs)


# ── Define zone centroids ──
# These represent "ideal behavioral profiles" for strategic zones

ZONE_CENTROIDS = {
    "premium": [0.9, 0.8, 0.7, 0.6, 0.8, 0.9, 0.7, 0.5],
    "budget":  [0.2, 0.3, 0.8, 0.9, 0.3, 0.2, 0.4, 0.7],
    "niche":   [0.5, 0.5, 0.5, 0.5, 0.9, 0.8, 0.9, 0.3],
}

FEATURE_LABELS = [
    "price_level", "quality_score", "volume_capacity",
    "cost_efficiency", "brand_strength", "innovation",
    "specialization", "flexibility",
]


async def main():
    # ── Build the pipeline ──
    pipeline = DagPipeline()

    extractor = MockFeatureExtractor()
    vectorspace = VectorSpaceModule(
        n_components=2,
        method="pca",
        centroids=ZONE_CENTROIDS,
        feature_labels=FEATURE_LABELS,
        normalize=True,
    )
    tracker = TrajectoryTracker(
        window=5,
        feature_labels=FEATURE_LABELS,
        centroids=ZONE_CENTROIDS,
    )
    store = SnapshotStore(
        path="./example_data",
        backend="json",
        session_id="basic_demo",
    )

    # Register modules
    pipeline.add_module("features", extractor)
    pipeline.add_module("vectorspace", vectorspace)
    pipeline.add_module("trajectory", tracker)
    pipeline.add_module("store", store)

    # Wire connections
    pipeline.connect("features", "vectorspace", target_key="features")
    pipeline.connect("features", "trajectory", target_key="features")
    pipeline.connect("vectorspace", "store", target_key="projections")
    pipeline.connect("trajectory", "store", target_key="trajectories")

    # ── Run for 10 steps ──
    print("Running 10 pipeline steps...\n")

    for step in range(10):
        result = await pipeline.a_run({"step": step})

        # Extract key metrics from the store output
        store_out = result.get("store", {})
        snapshot = store_out.get("snapshot", {})
        entities = snapshot.get("entities", {})

        print(f"Step {step}: {len(entities)} entities tracked")

        for eid, es in entities.items():
            traj_class = es.get("trajectory_class", "—")
            momentum = es.get("momentum")
            coords = es.get("coordinates")
            m_str = f"  momentum={momentum:.3f}" if momentum is not None else ""
            c_str = f"  pos=({coords[0]:.2f}, {coords[1]:.2f})" if coords else ""
            print(f"  {eid}: {traj_class}{m_str}{c_str}")
        print()

    # ── Query stored data ──
    print("=== Historical Query ===")
    history = store.get_entity_history("agent_0", last_n=5)
    print(f"agent_0 last 5 steps:")
    for h in history:
        print(f"  step {h['step']}: class={h.get('trajectory_class', '—')}, "
              f"momentum={h.get('momentum', '—')}")

    print(f"\nTotal snapshots stored: {store.total_snapshots}")
    store.close()


if __name__ == "__main__":
    asyncio.run(main())
