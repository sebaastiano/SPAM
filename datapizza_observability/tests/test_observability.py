"""Tests for VectorSpaceModule, TrajectoryTracker, and SnapshotStore."""

import asyncio
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


# ═══════════════════════════════════════════
# VectorSpaceModule
# ═══════════════════════════════════════════

class TestVectorSpaceModule:

    def _make_features(self, n_entities=5, n_dims=8):
        return {f"e_{i}": np.random.rand(n_dims).tolist() for i in range(n_entities)}

    def test_basic_pca_projection(self):
        mod = VectorSpaceModule(n_components=2, method="pca")
        features = self._make_features()
        result = mod.run({"features": features})

        assert "projections" in result
        assert len(result["projections"]) == 5
        for eid, proj in result["projections"].items():
            assert "coordinates" in proj
            assert len(proj["coordinates"]) == 2
            assert "raw_features" in proj

    def test_variance_explained(self):
        mod = VectorSpaceModule(n_components=2, method="pca")
        result = mod.run({"features": self._make_features()})

        ve = result["variance_explained"]
        assert len(ve) == 2
        assert all(0 <= v <= 1 for v in ve)
        # Variance explained should sum to <= 1
        assert sum(ve) <= 1.0 + 1e-6

    def test_3d_projection(self):
        mod = VectorSpaceModule(n_components=3, method="pca")
        result = mod.run({"features": self._make_features()})

        for proj in result["projections"].values():
            assert len(proj["coordinates"]) == 3

    def test_centroid_co_projection(self):
        centroids = {
            "zone_a": [0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2],
            "zone_b": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8],
        }
        mod = VectorSpaceModule(n_components=2, centroids=centroids)
        result = mod.run({"features": self._make_features()})

        assert "centroid_projections" in result
        assert "zone_a" in result["centroid_projections"]
        assert "zone_b" in result["centroid_projections"]
        assert len(result["centroid_projections"]["zone_a"]) == 2

    def test_empty_features(self):
        mod = VectorSpaceModule()
        result = mod.run({"features": {}})
        assert result["projections"] == {}

    def test_normalization_disabled(self):
        mod = VectorSpaceModule(normalize=False)
        result = mod.run({"features": self._make_features()})
        assert len(result["projections"]) == 5

    def test_project_single(self):
        mod = VectorSpaceModule(n_components=2, method="pca")
        features = self._make_features()
        mod.run({"features": features})

        # Project a new vector using stored basis
        new_vec = np.random.rand(8).tolist()
        coords = mod.project_single(new_vec)
        assert len(coords) == 2

    def test_project_single_before_fit_raises(self):
        mod = VectorSpaceModule()
        with pytest.raises(RuntimeError):
            mod.project_single([0.1] * 8)

    @pytest.mark.asyncio
    async def test_async_run(self):
        mod = VectorSpaceModule(n_components=2)
        result = await mod.a_run({"features": self._make_features()})
        assert len(result["projections"]) == 5

    def test_metadata_passthrough(self):
        mod = VectorSpaceModule()
        features = {"e_0": [0.5] * 4}
        metadata = {"e_0": {"team": "alpha"}}
        result = mod.run({"features": features, "metadata": metadata})
        assert result["projections"]["e_0"]["metadata"]["team"] == "alpha"


# ═══════════════════════════════════════════
# TrajectoryTracker
# ═══════════════════════════════════════════

class TestTrajectoryTracker:

    def _make_features(self, n_entities=3, n_dims=6):
        return {f"e_{i}": np.random.rand(n_dims).tolist() for i in range(n_entities)}

    def test_single_step_is_new(self):
        tracker = TrajectoryTracker(window=5)
        result = tracker.run({"features": self._make_features(), "step": 0})

        for traj in result["trajectories"].values():
            assert traj["classification"] == "new"
            assert traj["window_size"] == 1

    def test_multi_step_trajectory(self):
        tracker = TrajectoryTracker(window=5)
        for step in range(5):
            result = tracker.run({"features": self._make_features(), "step": step})

        for traj in result["trajectories"].values():
            assert traj["window_size"] == 5
            assert traj["classification"] != "new"
            assert "direction" in traj
            assert "momentum" in traj
            assert "drift" in traj
            assert "stability" in traj
            assert "trend" in traj

    def test_stable_entity(self):
        tracker = TrajectoryTracker(window=5, momentum_threshold=0.1, drift_threshold=0.1)
        # Feed identical features each step
        fixed = {"agent": [0.5, 0.5, 0.5, 0.5]}
        for step in range(5):
            result = tracker.run({"features": fixed, "step": step})

        traj = result["trajectories"]["agent"]
        assert traj["momentum"] < 0.01
        assert traj["drift"] < 0.01
        assert traj["classification"] == "stable"

    def test_drifting_entity(self):
        tracker = TrajectoryTracker(window=5, momentum_threshold=0.001, drift_threshold=0.01)
        for step in range(5):
            features = {"agent": [0.1 * step, 0.1 * step, 0.5, 0.5]}
            result = tracker.run({"features": features, "step": step})

        traj = result["trajectories"]["agent"]
        assert traj["drift"] > 0.01

    def test_window_enforcement(self):
        tracker = TrajectoryTracker(window=3)
        for step in range(10):
            tracker.run({"features": {"a": [float(step)]}, "step": step})

        history = tracker.get_history("a")
        assert len(history) == 3
        assert history[-1].step == 9

    def test_centroid_distance(self):
        centroids = {"zone_a": [1.0, 1.0]}
        tracker = TrajectoryTracker(window=3, centroids=centroids)
        for step in range(3):
            tracker.run({"features": {"e": [0.0, 0.0]}, "step": step})

        traj = tracker.get_trajectory("e")
        assert traj is not None
        assert traj.reference_distance is not None
        assert traj.reference_distance == pytest.approx(np.sqrt(2), abs=0.01)

    def test_get_all_entities(self):
        tracker = TrajectoryTracker()
        tracker.run({"features": {"a": [1.0], "b": [2.0]}, "step": 0})
        assert set(tracker.get_all_entities()) == {"a", "b"}

    def test_clear(self):
        tracker = TrajectoryTracker()
        tracker.run({"features": {"a": [1.0]}, "step": 0})
        tracker.clear("a")
        assert tracker.get_all_entities() == []

    def test_clear_all(self):
        tracker = TrajectoryTracker()
        tracker.run({"features": {"a": [1.0], "b": [2.0]}, "step": 0})
        tracker.clear()
        assert tracker.get_all_entities() == []

    @pytest.mark.asyncio
    async def test_async_run(self):
        tracker = TrajectoryTracker()
        result = await tracker.a_run({"features": self._make_features(), "step": 0})
        assert len(result["trajectories"]) == 3


# ═══════════════════════════════════════════
# SnapshotStore
# ═══════════════════════════════════════════

class TestSnapshotStore:

    @pytest.fixture
    def tmp_path(self):
        p = Path(tempfile.mkdtemp())
        yield p
        shutil.rmtree(p, ignore_errors=True)

    def test_json_save_and_load(self, tmp_path):
        store = SnapshotStore(path=tmp_path, backend="json", session_id="test")

        store.run({
            "features": {"a": [0.1, 0.2], "b": [0.3, 0.4]},
            "step": 0,
        })
        store.run({
            "features": {"a": [0.5, 0.6], "b": [0.7, 0.8]},
            "step": 1,
        })

        assert store.total_snapshots == 2

        snap = store.get_snapshot(0)
        assert snap is not None
        assert "a" in snap.entities
        assert snap.entities["a"].features == [0.1, 0.2]

    def test_sqlite_save_and_load(self, tmp_path):
        store = SnapshotStore(path=tmp_path, backend="sqlite", session_id="test")

        store.run({
            "features": {"a": [0.1, 0.2]},
            "step": 0,
        })

        assert store.total_snapshots == 1
        snap = store.get_snapshot(0)
        assert snap is not None
        assert snap.entities["a"].features == [0.1, 0.2]
        store.close()

    def test_get_latest(self, tmp_path):
        store = SnapshotStore(path=tmp_path, backend="json", session_id="test")

        for i in range(5):
            store.run({"features": {"a": [float(i)]}, "step": i})

        latest = store.get_latest(2)
        assert len(latest) == 2
        assert latest[-1].step == 4

    def test_get_range(self, tmp_path):
        store = SnapshotStore(path=tmp_path, backend="json", session_id="test")

        for i in range(10):
            store.run({"features": {"a": [float(i)]}, "step": i})

        ranged = store.get_range(3, 6)
        assert len(ranged) == 4
        assert ranged[0].step == 3
        assert ranged[-1].step == 6

    def test_entity_history(self, tmp_path):
        store = SnapshotStore(path=tmp_path, backend="json", session_id="test")

        for i in range(5):
            store.run({"features": {"a": [float(i)], "b": [float(i * 2)]}, "step": i})

        history = store.get_entity_history("a", last_n=3)
        assert len(history) == 3
        assert history[-1]["features"] == [4.0]

    def test_projection_and_trajectory_merge(self, tmp_path):
        store = SnapshotStore(path=tmp_path, backend="json", session_id="test")

        store.run({
            "projections": {
                "a": {"coordinates": [1.0, 2.0], "raw_features": [0.1, 0.2, 0.3]},
            },
            "trajectories": {
                "a": {"classification": "drifting", "momentum": 0.15, "drift": 0.8, "stability": 0.4},
            },
            "step": 0,
        })

        snap = store.get_snapshot(0)
        a = snap.entities["a"]
        assert a.coordinates == [1.0, 2.0]
        assert a.trajectory_class == "drifting"
        assert a.momentum == 0.15

    def test_auto_flush_disabled(self, tmp_path):
        store = SnapshotStore(path=tmp_path, backend="json", session_id="test", auto_flush=False)

        store.run({"features": {"a": [1.0]}, "step": 0})
        store.run({"features": {"a": [2.0]}, "step": 1})

        # Nothing flushed yet
        assert store._backend.step_count == 0

        store.flush()
        assert store._backend.step_count == 2

    @pytest.mark.asyncio
    async def test_async_run(self, tmp_path):
        store = SnapshotStore(path=tmp_path, backend="json", session_id="test")
        result = await store.a_run({"features": {"a": [1.0]}, "step": 0})
        assert result["step"] == 0
        assert result["total_snapshots"] == 1


# ═══════════════════════════════════════════
# Integration: full pipeline flow
# ═══════════════════════════════════════════

class TestFullPipeline:
    """Test all three components wired together."""

    @pytest.fixture
    def tmp_path(self):
        p = Path(tempfile.mkdtemp())
        yield p
        shutil.rmtree(p, ignore_errors=True)

    def test_end_to_end(self, tmp_path):
        # Setup
        centroids = {"premium": [0.9, 0.8, 0.7, 0.6], "budget": [0.2, 0.3, 0.4, 0.5]}
        projector = VectorSpaceModule(n_components=2, centroids=centroids)
        tracker = TrajectoryTracker(window=5, centroids=centroids)
        store = SnapshotStore(path=tmp_path, backend="json", session_id="e2e")

        # Simulate 5 steps
        for step in range(5):
            features = {
                "agent_a": np.random.rand(4).tolist(),
                "agent_b": np.random.rand(4).tolist(),
            }

            proj_result = projector.run({"features": features})
            traj_result = tracker.run({"features": features, "step": step})
            store_result = store.run({
                "projections": proj_result["projections"],
                "trajectories": traj_result["trajectories"],
                "centroid_projections": proj_result["centroid_projections"],
                "features": features,
                "step": step,
            })

        # Verify final state
        assert store.total_snapshots == 5

        latest = store.get_latest(1)[0]
        assert "agent_a" in latest.entities
        assert latest.entities["agent_a"].coordinates is not None
        assert latest.entities["agent_a"].trajectory_class is not None

        # Verify centroid projections persisted
        assert "premium" in latest.centroid_projections
        assert "budget" in latest.centroid_projections
