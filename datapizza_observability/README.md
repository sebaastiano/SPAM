# datapizza-ai-observability-vectorspace

**Agent decision-making observability through latent space trajectories.**

A `datapizza-ai` kernel extension that provides real-time observability into _how agents think_ — not just what they output, but where they are in a behavioral decision space and how their strategy evolves over time.

---

## The Problem

Current AI agent frameworks treat agents as black boxes. You see inputs and outputs, maybe some token-level tracing, but you have **zero visibility** into the agent's _behavioral state_ — the latent space where its decisions actually live.

When an agent starts losing in a competitive environment, you can't answer:

- **Where** is it positioned relative to competitors?
- **Why** is it drifting toward a losing strategy?
- Is it **converging** on an optimal position or **oscillating** between bad ones?
- Which **behavioral dimensions** are driving the change?

## The Idea

Every entity observed through a pipeline can be described by an N-dimensional feature vector — a point in behavioral space. By tracking these vectors over time, we can:

1. **Project** them into 2D/3D for visualization (PCA, t-SNE, UMAP)
2. **Track trajectories** — direction, momentum, drift, stability
3. **Classify patterns** — stable, drifting, oscillating, accelerating, converging
4. **Give agents self-awareness** — tools to query their own position and reason about strategy

This turns agent observability from "read the logs" into **spatial intelligence**.

---

## Architecture

```
Your Pipeline
    │
    ├─ Feature Extraction ──► VectorSpaceModule ──► 2D/3D projections
    │                              │
    │                              ├──► SnapshotStore ──► persistent history
    │                              │
    ├─ Feature Extraction ──► TrajectoryTracker ──► trajectory metrics
    │                              │
    │                              ├──► SnapshotStore
    │
    └─ Agent ──► VectorSpaceViewer (tools) ──► spatial self-awareness
                      │
                      └──► VectorSpaceDashboard ──► real-time web UI
```

### Components

| Component              | Type              | Description                                                                                          |
| ---------------------- | ----------------- | ---------------------------------------------------------------------------------------------------- |
| `VectorSpaceModule`    | PipelineComponent | Dimensionality reduction (PCA/t-SNE/UMAP) with centroid co-projection                                |
| `TrajectoryTracker`    | PipelineComponent | Per-entity trajectory tracking with momentum, drift, stability, trend                                |
| `SnapshotStore`        | PipelineComponent | Persistent time-series storage (JSON or SQLite backends)                                             |
| `VectorSpaceViewer`    | Agent Tools       | 6 tools for agent self-introspection (position, neighbors, centroids, trajectory, history, overview) |
| `VectorSpaceDashboard` | Web UI            | Real-time interactive scatter plot with trajectory trails and entity cards                           |

---

## Installation

```bash
pip install datapizza-ai-observability-vectorspace

# With web dashboard
pip install datapizza-ai-observability-vectorspace[dashboard]

# With UMAP support
pip install datapizza-ai-observability-vectorspace[all]
```

## Quick Start

### 1. Pipeline Integration

```python
from datapizza.pipeline.dag_pipeline import DagPipeline
from datapizza.modules.observability import (
    VectorSpaceModule,
    TrajectoryTracker,
    SnapshotStore,
)

pipeline = DagPipeline()

# Your existing feature extraction
pipeline.add_module("features", your_feature_extractor)

# Add observability
pipeline.add_module("vectorspace", VectorSpaceModule(
    n_components=2,
    method="pca",
    centroids={"zone_a": [...], "zone_b": [...]},
))
pipeline.add_module("trajectory", TrajectoryTracker(window=5))
pipeline.add_module("store", SnapshotStore(path="./data", backend="json"))

# Wire it up
pipeline.connect("features", "vectorspace", target_key="features")
pipeline.connect("features", "trajectory", target_key="features")
pipeline.connect("vectorspace", "store", target_key="projections")
pipeline.connect("trajectory", "store", target_key="trajectories")

# Run
result = await pipeline.a_run({"step": 0})
```

### 2. Agent Self-Introspection

```python
from datapizza.agents import Agent
from datapizza.clients.openai import OpenAIClient
from datapizza.tools.vectorspace import VectorSpaceViewer

viewer = VectorSpaceViewer(
    snapshot_store=store,
    tracker=tracker,
    centroids=zone_centroids,
    feature_labels=["aggressiveness", "quality", "price", ...],
)

agent = Agent(
    name="strategic_agent",
    client=OpenAIClient(api_key="...", model="gpt-4.1"),
    tools=viewer.get_tools(),
)

# Agent can now ask: "Where am I? Who's nearby? Am I drifting?"
response = await agent.a_run(
    "Analyze my competitive position and recommend strategic adjustments."
)
```

### 3. Real-Time Dashboard

```python
from datapizza.tools.vectorspace import VectorSpaceDashboard

dashboard = VectorSpaceDashboard(
    snapshot_store=store,
    tracker=tracker,
    projector=projector,
)

# Launch in background (non-blocking)
url = dashboard.launch_background(port=5050)
# → http://127.0.0.1:5050
```

---

## Modules Reference

### VectorSpaceModule

Dimensionality reduction PipelineComponent. Takes N-dimensional feature vectors and projects them into 2D or 3D.

```python
VectorSpaceModule(
    n_components=2,        # Target dimensions (2 or 3)
    method="pca",          # "pca" | "tsne" | "umap"
    centroids={...},       # Named reference points (zone ideals)
    feature_labels=[...],  # Human-readable feature names
    normalize=True,        # Min-max normalize before projection
)
```

**Input:** `{"features": {"entity_id": [f1, f2, ..., fn]}}`  
**Output:** `{"projections": {"entity_id": {"coordinates": [x, y], ...}}, "variance_explained": [...]}`

### TrajectoryTracker

Per-entity trajectory tracking with sliding window.

```python
TrajectoryTracker(
    window=10,                 # Steps to keep per entity
    centroids={...},           # Reference points for distance
    momentum_threshold=0.05,   # Below = "stable"
    drift_threshold=0.1,       # Below = not significantly moved
)
```

**Output metrics per entity:**

- `direction` — Unit vector of movement in feature space
- `momentum` — Speed of recent changes (0 = static)
- `drift` — Distance from starting position (total behavioral shift)
- `stability` — Inverse variance (0 = chaotic, 1 = stable)
- `trend` — Per-feature linear slope
- `classification` — `"stable"` | `"drifting"` | `"oscillating"` | `"accelerating"` | `"converging"`

### SnapshotStore

Persistent time-series backend. Accepts outputs from both VectorSpaceModule and TrajectoryTracker.

```python
SnapshotStore(
    path="./data",         # Storage directory
    backend="json",        # "json" (JSONL) or "sqlite"
    session_id="run_1",    # Groups runs together
    auto_flush=True,       # Write immediately on each run()
)
```

**Query API:**

```python
store.get_latest(n=1)                       # Last N snapshots
store.get_range(start=0, end=10)            # Step range
store.get_entity_history("entity_id")       # Time series for one entity
store.total_snapshots                       # Count
```

### VectorSpaceViewer (Agent Tools)

6 tools for agent self-introspection:

| Tool                                   | Description                                                  |
| -------------------------------------- | ------------------------------------------------------------ |
| `get_position(entity_id)`              | Current position + labeled feature values                    |
| `nearest_neighbors(entity_id, k=5)`    | K nearest entities with feature diffs                        |
| `distance_to_centroids(entity_id)`     | Distance to all zone centroids with gap analysis             |
| `trajectory_summary(entity_id)`        | Trajectory metrics + human-readable interpretation           |
| `entity_history(entity_id, last_n=10)` | Historical positions over recent steps                       |
| `space_overview()`                     | Full landscape: all entities, classifications, distributions |

---

## Origin

This package was derived from the vector space intelligence system built for **Team SPAM!'s** entry in the **Hackapizza** competitive multi-agent hackathon. The core insight:

> Agents making decisions in complex environments create implicit trajectories through a behavioral feature space. By making this space _observable_, agents gain a form of spatial self-awareness — they can reason about WHERE they are, not just WHAT to do.

The original system tracked 14-dimensional behavioral feature vectors for competing restaurants across 6 strategic zones, enabling:

- Real-time PCA projection to a 2D scatter plot
- Trajectory-based competitor strategy inference
- Agent self-assessment of competitive positioning
- Profit-maximizing bid optimization informed by vector gap analysis

This package generalizes that system into a framework-native `datapizza-ai` extension that works with any pipeline producing entity feature vectors.

---

## Roadmap

- [ ] 3D visualization (Three.js)
- [ ] Cluster detection (DBSCAN/HDBSCAN)
- [ ] Anomaly detection for behavioral outliers
- [ ] Integration with `datapizza` ContextTracing (OpenTelemetry spans)
- [ ] Streaming support (SSE/WebSocket for dashboard)
- [ ] Multi-session comparison views
- [ ] Export to Weights & Biases / MLflow

---

## License

MIT

## Authors

Team SPAM! — Hackapizza 2025
