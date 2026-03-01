"""
agent_introspection.py — Agent querying its own vector space position.

Demonstrates:
    1. Running a feature pipeline to track agent positions
    2. Giving an agent VectorSpaceViewer tools for self-introspection
    3. The agent reasons about WHERE it is and WHO is nearby

This is the key differentiator: agents gain spatial self-awareness
in their behavioral decision space.

Run::

    export OPENAI_API_KEY=...
    pip install datapizza-ai-observability-vectorspace
    python agent_introspection.py
"""

import asyncio
import os

import numpy as np

# datapizza framework
from datapizza.agents import Agent
from datapizza.clients.openai import OpenAIClient

# observability
from datapizza.modules.observability import (
    VectorSpaceModule,
    TrajectoryTracker,
    SnapshotStore,
)
from datapizza.tools.vectorspace import VectorSpaceViewer


# ── Feature labels for the behavioral space ──

FEATURE_LABELS = [
    "aggressiveness",   # bidding strategy intensity
    "price_premium",    # how much above market average
    "quality_focus",    # investment in quality
    "volume_seeking",   # preference for high-volume orders
    "risk_tolerance",   # willingness to make risky bids
    "adaptability",     # speed of strategy changes
]

# ── Zone centroids: ideal profiles for strategic positions ──

ZONE_CENTROIDS = {
    "aggressive_premium": [0.9, 0.8, 0.9, 0.3, 0.7, 0.5],
    "budget_volume":      [0.3, 0.2, 0.4, 0.9, 0.6, 0.7],
    "balanced_moderate":  [0.5, 0.5, 0.6, 0.5, 0.4, 0.5],
    "niche_specialist":   [0.6, 0.7, 0.8, 0.2, 0.3, 0.3],
}


def simulate_feature_data(step: int) -> dict[str, list[float]]:
    """Simulate feature vectors for 4 competitors + our agent."""
    np.random.seed(42 + step)
    entities = {}

    # Our agent — starts moderate, drifts toward premium
    base = np.array([0.5, 0.5, 0.6, 0.5, 0.4, 0.5])
    drift = np.array([0.03, 0.02, 0.03, -0.01, 0.01, 0.0]) * step
    entities["our_agent"] = np.clip(base + drift + np.random.randn(6) * 0.03, 0, 1).tolist()

    # Competitor A — aggressive
    base_a = np.array([0.8, 0.7, 0.8, 0.4, 0.6, 0.4])
    entities["competitor_A"] = np.clip(base_a + np.random.randn(6) * 0.05, 0, 1).tolist()

    # Competitor B — budget seeker
    base_b = np.array([0.3, 0.2, 0.3, 0.8, 0.5, 0.6])
    entities["competitor_B"] = np.clip(base_b + np.random.randn(6) * 0.04, 0, 1).tolist()

    # Competitor C — oscillating
    osc = 0.15 * np.sin(step * np.pi / 2)
    base_c = np.array([0.5, 0.5, 0.5, 0.5, 0.5, 0.5])
    entities["competitor_C"] = np.clip(base_c + osc + np.random.randn(6) * 0.04, 0, 1).tolist()

    return entities


async def main():
    # ── Step 1: Build observability components ──
    projector = VectorSpaceModule(
        n_components=2,
        method="pca",
        centroids=ZONE_CENTROIDS,
        feature_labels=FEATURE_LABELS,
    )
    tracker = TrajectoryTracker(
        window=5,
        centroids=ZONE_CENTROIDS,
        feature_labels=FEATURE_LABELS,
    )
    store = SnapshotStore(
        path="./introspection_data",
        backend="json",
        session_id="introspection_demo",
    )

    # ── Step 2: Feed several steps of data ──
    print("Simulating 6 steps of competitive data...\n")
    for step in range(6):
        features = simulate_feature_data(step)

        # Run through pipeline components manually
        # (In production, these would be wired via DagPipeline)
        proj_result = projector.run({"features": features})
        traj_result = tracker.run({"features": features, "step": step})
        store.run({
            "projections": proj_result.get("projections", {}),
            "trajectories": traj_result.get("trajectories", {}),
            "centroid_projections": proj_result.get("centroid_projections", {}),
            "features": features,
            "step": step,
        })

    print(f"Stored {store.total_snapshots} snapshots\n")

    # ── Step 3: Create VectorSpaceViewer with all data sources ──
    viewer = VectorSpaceViewer(
        snapshot_store=store,
        tracker=tracker,
        projector=projector,
        centroids=ZONE_CENTROIDS,
        feature_labels=FEATURE_LABELS,
    )

    # ── Step 4: Create an agent with vector space tools ──
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        print("No OPENAI_API_KEY set — showing tool outputs directly instead.\n")

        # Demo: call tools directly to show what the agent would see
        print("=== get_position('our_agent') ===")
        print(viewer.get_position("our_agent"))
        print()

        print("=== nearest_neighbors('our_agent', k=3) ===")
        print(viewer.nearest_neighbors("our_agent", k=3))
        print()

        print("=== distance_to_centroids('our_agent') ===")
        print(viewer.distance_to_centroids("our_agent"))
        print()

        print("=== trajectory_summary('our_agent') ===")
        print(viewer.trajectory_summary("our_agent"))
        print()

        print("=== space_overview() ===")
        print(viewer.space_overview())
        print()

        print("=== entity_history('our_agent', last_n=3) ===")
        print(viewer.entity_history("our_agent", last_n=3))

    else:
        client = OpenAIClient(api_key=api_key, model="gpt-4.1")

        agent = Agent(
            name="strategic_observer",
            client=client,
            system_prompt=(
                "You are a strategic intelligence agent for a competitive restaurant game. "
                "You have tools to introspect your position in a behavioral vector space "
                "where each dimension represents a strategic attribute. "
                "Use these tools to analyze your competitive position and provide "
                "actionable strategic recommendations."
            ),
            tools=viewer.get_tools(),
            max_steps=10,
        )

        # Let the agent reason about its position
        response = await agent.a_run(
            "Analyze my current competitive position (I am 'our_agent'). "
            "Where am I in the vector space? Who are my nearest competitors? "
            "Which strategic zone am I closest to? What's my trajectory — "
            "am I moving in a good direction? Give me a concise strategic briefing."
        )

        print("=== Agent Strategic Briefing ===")
        print(response.text)

    store.close()


if __name__ == "__main__":
    asyncio.run(main())
