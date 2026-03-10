"""Tests for VectorSpaceViewer agent tools."""

import json
import shutil
import tempfile
from pathlib import Path

import numpy as np
import pytest

from datapizza.modules.observability import (
    VectorSpaceModule,
    TrajectoryTracker,
    SnapshotStore,
)
from datapizza.tools.vectorspace import VectorSpaceViewer


@pytest.fixture
def populated_system():
    """Create a fully populated observability system with 5 steps of data."""
    tmp_path = Path(tempfile.mkdtemp())

    centroids = {
        "premium": [0.9, 0.8, 0.7, 0.6],
        "budget": [0.2, 0.3, 0.4, 0.5],
    }
    feature_labels = ["price", "quality", "volume", "cost"]

    projector = VectorSpaceModule(n_components=2, centroids=centroids)
    tracker = TrajectoryTracker(window=5, centroids=centroids)
    store = SnapshotStore(path=tmp_path, backend="json", session_id="test")

    # Feed 5 steps
    for step in range(5):
        features = {
            "alpha": [0.7 + step * 0.02, 0.6, 0.5, 0.4],
            "beta": [0.3, 0.4, 0.8, 0.7],
            "gamma": [0.5, 0.5, 0.5, 0.5],
        }
        proj = projector.run({"features": features})
        traj = tracker.run({"features": features, "step": step})
        store.run({
            "projections": proj["projections"],
            "trajectories": traj["trajectories"],
            "centroid_projections": proj["centroid_projections"],
            "features": features,
            "step": step,
        })

    viewer = VectorSpaceViewer(
        snapshot_store=store,
        tracker=tracker,
        projector=projector,
        centroids=centroids,
        feature_labels=feature_labels,
    )

    yield viewer, store, tmp_path
    store.close()
    shutil.rmtree(tmp_path, ignore_errors=True)


class TestVectorSpaceViewer:

    def test_get_position(self, populated_system):
        viewer, _, _ = populated_system
        result = json.loads(viewer.get_position("alpha"))
        assert result["entity_id"] == "alpha"
        assert "features" in result
        assert "coordinates" in result

    def test_get_position_not_found(self, populated_system):
        viewer, _, _ = populated_system
        result = json.loads(viewer.get_position("nonexistent"))
        assert "error" in result

    def test_nearest_neighbors(self, populated_system):
        viewer, _, _ = populated_system
        result = json.loads(viewer.nearest_neighbors("alpha", k=2))
        assert len(result["neighbors"]) == 2
        for n in result["neighbors"]:
            assert "distance" in n

    def test_distance_to_centroids(self, populated_system):
        viewer, _, _ = populated_system
        result = json.loads(viewer.distance_to_centroids("alpha"))
        assert result["nearest_zone"] in ["premium", "budget"]
        assert len(result["centroid_distances"]) == 2

    def test_trajectory_summary(self, populated_system):
        viewer, _, _ = populated_system
        result = json.loads(viewer.trajectory_summary("alpha"))
        assert "classification" in result
        assert "momentum" in result
        assert "interpretation" in result

    def test_entity_history(self, populated_system):
        viewer, _, _ = populated_system
        result = json.loads(viewer.entity_history("alpha", last_n=3))
        assert len(result["history"]) == 3

    def test_space_overview(self, populated_system):
        viewer, _, _ = populated_system
        result = json.loads(viewer.space_overview())
        assert result["total_entities"] == 3
        assert len(result["entities"]) == 3
        assert "premium" in result["centroids"]

    def test_get_tools_returns_all(self, populated_system):
        viewer, _, _ = populated_system
        tools = viewer.get_tools()
        assert len(tools) == 6
        # All should be callable
        for t in tools:
            assert callable(t)

    def test_feature_labels_in_position(self, populated_system):
        viewer, _, _ = populated_system
        result = json.loads(viewer.get_position("alpha"))
        assert "labeled_features" in result
        assert "price" in result["labeled_features"]

    def test_feature_gaps_in_centroids(self, populated_system):
        viewer, _, _ = populated_system
        result = json.loads(viewer.distance_to_centroids("alpha"))
        for cd in result["centroid_distances"]:
            assert "feature_gaps" in cd
            assert "price" in cd["feature_gaps"]

    def test_dominant_movement_in_trajectory(self, populated_system):
        viewer, _, _ = populated_system
        result = json.loads(viewer.trajectory_summary("alpha"))
        if "dominant_movement" in result:
            for dm in result["dominant_movement"]:
                assert "feature" in dm
                assert "direction_weight" in dm
