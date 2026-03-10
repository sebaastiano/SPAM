"""
TrajectoryTracker — Multi-step trajectory tracking with momentum analysis.

A ``datapizza`` PipelineComponent that maintains a sliding window of
feature vectors per entity and computes trajectory metrics:
    - **Direction** — Which way the entity is moving in feature space.
    - **Momentum** — How fast and consistently it's moving.
    - **Drift** — Distance from a reference point (e.g., zone centroid).
    - **Stability** — How much the entity's behavior fluctuates.
    - **Trend** — Per-feature slopes over the window.

Integration::

    from datapizza.pipeline.dag_pipeline import DagPipeline
    from datapizza.modules.observability import TrajectoryTracker

    pipeline = DagPipeline()
    pipeline.add_module("features", my_feature_extractor)
    pipeline.add_module("trajectory", TrajectoryTracker(window=5))
    pipeline.connect("features", "trajectory", target_key="features")

    result = await pipeline.a_run({...})
    trajectories = result["trajectory"]["trajectories"]
"""

from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

import numpy as np

logger = logging.getLogger("datapizza.modules.observability.trajectory_tracker")


# ── Data types ──

@dataclass
class TrajectoryPoint:
    """A single point in an entity's trajectory."""

    step: int
    features: list[float]
    timestamp: float | None = None


@dataclass
class Trajectory:
    """
    Complete trajectory analysis for one entity.

    Attributes
    ----------
    entity_id : str
        The entity being tracked.
    direction : list[float]
        Unit vector showing the primary movement direction in feature space.
    momentum : float
        Magnitude of recent movement (0 = stationary, higher = faster change).
    drift : float
        Distance from entity's starting position (measures total behavioral shift).
    stability : float
        Inverse of variance in recent steps (0 = chaotic, 1 = very stable).
    trend : list[float]
        Per-feature linear slope over the window. Positive = increasing.
    window_size : int
        Number of steps in the current window.
    classification : str
        Human-readable trajectory label: "stable", "drifting", "oscillating",
        "accelerating", "converging".
    """

    entity_id: str
    direction: list[float]
    momentum: float
    drift: float
    stability: float
    trend: list[float]
    window_size: int
    classification: str
    reference_distance: float | None = None  # distance to nearest centroid

    def to_dict(self) -> dict:
        return {
            "entity_id": self.entity_id,
            "direction": self.direction,
            "momentum": round(self.momentum, 4),
            "drift": round(self.drift, 4),
            "stability": round(self.stability, 4),
            "trend": [round(t, 4) for t in self.trend],
            "window_size": self.window_size,
            "classification": self.classification,
            "reference_distance": round(self.reference_distance, 4) if self.reference_distance else None,
        }


# ── PipelineComponent ──

class TrajectoryTracker:
    """
    Trajectory tracking PipelineComponent for datapizza DagPipeline.

    Maintains per-entity feature histories across pipeline runs and
    computes trajectory metrics (direction, momentum, drift, stability).

    Parameters
    ----------
    window : int
        Number of recent steps to keep per entity. Default: 10.
    feature_labels : list[str] | None
        Human-readable labels for each feature dimension.
    centroids : dict[str, list[float]] | None
        Reference centroids. Each entity's ``reference_distance`` is
        computed as distance to the nearest centroid.
    momentum_threshold : float
        Below this momentum, entity is classified as "stable". Default: 0.05.
    drift_threshold : float
        Below this drift, entity hasn't moved significantly. Default: 0.1.
    """

    def __init__(
        self,
        window: int = 10,
        feature_labels: list[str] | None = None,
        centroids: dict[str, list[float] | np.ndarray] | None = None,
        momentum_threshold: float = 0.05,
        drift_threshold: float = 0.1,
    ):
        self.window = window
        self.feature_labels = feature_labels
        self.centroids = centroids or {}
        self.momentum_threshold = momentum_threshold
        self.drift_threshold = drift_threshold

        # Per-entity sliding window: {entity_id: [TrajectoryPoint, ...]}
        self._histories: dict[str, list[TrajectoryPoint]] = defaultdict(list)
        self._step_counter = 0

    # ── datapizza PipelineComponent interface ──

    def run(self, data: dict | None = None, **kwargs) -> dict:
        """
        Synchronous pipeline entry point.

        Parameters
        ----------
        data : dict
            Must contain ``"features"`` with ``{entity_id: list[float]}``.
            Optionally ``"step"`` (int) to set the step counter.

        Returns
        -------
        dict
            ``{"trajectories": {entity_id: Trajectory.to_dict()}, "step": int}``
        """
        return self._process(data or {}, **kwargs)

    async def a_run(self, data: dict | None = None, **kwargs) -> dict:
        """Async pipeline entry point."""
        return self._process(data or {}, **kwargs)

    # ── Core logic ──

    def _process(self, data: dict, **kwargs) -> dict:
        """Ingest features, update histories, compute trajectories."""
        features_raw = data.get("features", {})
        if not features_raw:
            for key, val in data.items():
                if isinstance(val, dict) and "features" in val:
                    features_raw = val["features"]
                    break

        step = data.get("step", self._step_counter)
        self._step_counter = step + 1

        # Ingest new features
        for eid, fv in features_raw.items():
            eid_str = str(eid)
            vec = fv.tolist() if hasattr(fv, "tolist") else list(fv)
            self._histories[eid_str].append(TrajectoryPoint(step=step, features=vec))

            # Enforce window size
            if len(self._histories[eid_str]) > self.window:
                self._histories[eid_str] = self._histories[eid_str][-self.window :]

        # Compute trajectories for all entities with history
        trajectories = {}
        for eid, history in self._histories.items():
            if len(history) >= 2:
                trajectories[eid] = self._compute_trajectory(eid, history).to_dict()
            else:
                trajectories[eid] = Trajectory(
                    entity_id=eid,
                    direction=[0.0] * len(history[0].features) if history else [],
                    momentum=0.0,
                    drift=0.0,
                    stability=1.0,
                    trend=[0.0] * len(history[0].features) if history else [],
                    window_size=len(history),
                    classification="new",
                ).to_dict()

        logger.info(
            f"Tracked {len(trajectories)} entities at step {step} "
            f"(window={self.window})"
        )

        return {"trajectories": trajectories, "step": step}

    def _compute_trajectory(self, eid: str, history: list[TrajectoryPoint]) -> Trajectory:
        """Compute full trajectory metrics for one entity."""
        # Stack features into matrix  (steps × features)
        X = np.array([p.features for p in history], dtype=np.float64)
        n_steps, n_dims = X.shape

        # ── Direction: average of step-to-step deltas ──
        deltas = np.diff(X, axis=0)  # (n_steps-1) × n_dims
        avg_delta = deltas.mean(axis=0)
        norm = np.linalg.norm(avg_delta)
        direction = (avg_delta / norm).tolist() if norm > 1e-8 else [0.0] * n_dims

        # ── Momentum: mean magnitude of recent deltas ──
        recent_deltas = deltas[-min(3, len(deltas)) :]
        momentum = float(np.mean(np.linalg.norm(recent_deltas, axis=1)))

        # ── Drift: distance from first to last position ──
        drift = float(np.linalg.norm(X[-1] - X[0]))

        # ── Stability: 1 / (1 + mean variance across features) ──
        variance = np.var(X, axis=0).mean()
        stability = float(1.0 / (1.0 + variance))

        # ── Trend: per-feature linear regression slope ──
        steps = np.arange(n_steps, dtype=np.float64)
        steps_centered = steps - steps.mean()
        denom = (steps_centered**2).sum()
        trend = []
        for d in range(n_dims):
            if denom > 0:
                slope = float((steps_centered * (X[:, d] - X[:, d].mean())).sum() / denom)
            else:
                slope = 0.0
            trend.append(slope)

        # ── Reference distance (to nearest centroid) ──
        ref_dist = None
        if self.centroids:
            min_dist = float("inf")
            for cid, cv in self.centroids.items():
                cv_arr = np.array(cv, dtype=np.float64)
                dist = float(np.linalg.norm(X[-1] - cv_arr))
                if dist < min_dist:
                    min_dist = dist
            ref_dist = min_dist

        # ── Classification ──
        classification = self._classify(momentum, drift, stability, deltas)

        return Trajectory(
            entity_id=eid,
            direction=direction,
            momentum=momentum,
            drift=drift,
            stability=stability,
            trend=trend,
            window_size=n_steps,
            classification=classification,
            reference_distance=ref_dist,
        )

    def _classify(
        self,
        momentum: float,
        drift: float,
        stability: float,
        deltas: np.ndarray,
    ) -> str:
        """Classify trajectory pattern."""
        if momentum < self.momentum_threshold and drift < self.drift_threshold:
            return "stable"

        # Check for oscillation: sign changes in deltas
        if deltas.shape[0] >= 3:
            sign_flips = 0
            for d in range(deltas.shape[1]):
                signs = np.sign(deltas[:, d])
                sign_flips += np.sum(signs[1:] != signs[:-1])
            avg_flips = sign_flips / (deltas.shape[1] * (deltas.shape[0] - 1))
            if avg_flips > 0.6:
                return "oscillating"

        # Check for acceleration: increasing delta magnitudes
        if deltas.shape[0] >= 3:
            magnitudes = np.linalg.norm(deltas, axis=1)
            if all(magnitudes[i + 1] > magnitudes[i] * 1.1 for i in range(len(magnitudes) - 1)):
                return "accelerating"

        # Check for convergence: decreasing delta magnitudes
        if deltas.shape[0] >= 3:
            magnitudes = np.linalg.norm(deltas, axis=1)
            if all(magnitudes[i + 1] < magnitudes[i] * 0.9 for i in range(len(magnitudes) - 1)):
                return "converging"

        if drift > self.drift_threshold:
            return "drifting"

        return "active"

    # ── Query API ──

    def get_trajectory(self, entity_id: str) -> Trajectory | None:
        """Get the latest trajectory for an entity (outside pipeline)."""
        history = self._histories.get(str(entity_id))
        if not history or len(history) < 2:
            return None
        return self._compute_trajectory(str(entity_id), history)

    def get_history(self, entity_id: str) -> list[TrajectoryPoint]:
        """Get raw feature history for an entity."""
        return list(self._histories.get(str(entity_id), []))

    def get_all_entities(self) -> list[str]:
        """List all tracked entity IDs."""
        return list(self._histories.keys())

    def clear(self, entity_id: str | None = None):
        """Clear history for one or all entities."""
        if entity_id:
            self._histories.pop(str(entity_id), None)
        else:
            self._histories.clear()
            self._step_counter = 0
