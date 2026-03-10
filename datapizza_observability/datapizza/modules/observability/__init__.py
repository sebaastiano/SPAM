"""
datapizza.modules.observability
================================
Agent decision-making observability through latent space trajectories.

This module provides PipelineComponents that plug into any DagPipeline
to extract, project, and track behavioral feature vectors — enabling
real-time visualization and introspection of how agents (or any entities
observed through a pipeline) move through a decision space over time.

Components:
    VectorSpaceModule   — PCA/t-SNE/UMAP projection of feature vectors
    TrajectoryTracker   — Multi-step trajectory tracking with momentum
    SnapshotStore       — Persistent time-series store for vector snapshots

Quick start::

    from datapizza.pipeline.dag_pipeline import DagPipeline
    from datapizza.modules.observability import VectorSpaceModule, TrajectoryTracker

    pipeline = DagPipeline()
    pipeline.add_module("features", your_feature_extractor)
    pipeline.add_module("vectorspace", VectorSpaceModule(n_components=2))
    pipeline.add_module("trajectory", TrajectoryTracker(window=5))
    pipeline.connect("features", "vectorspace", target_key="features")
    pipeline.connect("features", "trajectory", target_key="features")
"""

from datapizza.modules.observability.vector_space import VectorSpaceModule
from datapizza.modules.observability.trajectory_tracker import TrajectoryTracker
from datapizza.modules.observability.snapshot_store import SnapshotStore

__all__ = ["VectorSpaceModule", "TrajectoryTracker", "SnapshotStore"]
