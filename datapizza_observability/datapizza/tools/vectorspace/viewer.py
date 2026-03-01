"""
VectorSpaceViewer — Agent-queryable vector space introspection tools.

Provides a set of tools that ``datapizza`` agents can use to:
    - Query their own position in behavioral feature space
    - Find nearest neighbors (similar entities)
    - Measure distance to strategic zone centroids
    - Inspect trajectory metrics (momentum, drift, stability)
    - Retrieve historical position data

Designed for agent self-awareness: an agent can reason about *where*
it is in the decision landscape relative to competitors and zones.

Usage with Agent::

    from datapizza.agents import Agent
    from datapizza.clients.openai import OpenAIClient
    from datapizza.tools.vectorspace import VectorSpaceViewer

    viewer = VectorSpaceViewer(snapshot_store=store, tracker=tracker)

    agent = Agent(
        name="strategic_agent",
        client=OpenAIClient(api_key="...", model="gpt-4.1"),
        tools=[
            viewer.get_position,
            viewer.nearest_neighbors,
            viewer.distance_to_centroids,
            viewer.trajectory_summary,
            viewer.entity_history,
            viewer.space_overview,
        ],
    )

    response = agent.run("Where am I relative to the premium zone?")
"""

from __future__ import annotations

import json
import logging
from typing import Any

import numpy as np

logger = logging.getLogger("datapizza.tools.vectorspace.viewer")


class VectorSpaceViewer:
    """
    Collection of agent-queryable tools for vector space introspection.

    Each public method is a standalone tool that can be passed to a
    ``datapizza.agents.Agent`` via its ``tools`` parameter.

    Parameters
    ----------
    snapshot_store : SnapshotStore | None
        A SnapshotStore instance for historical queries.
        If None, only live queries via tracker/projector are available.
    tracker : TrajectoryTracker | None
        A TrajectoryTracker instance for trajectory queries.
    projector : VectorSpaceModule | None
        A VectorSpaceModule for projecting new vectors.
    centroids : dict[str, list[float]] | None
        Named reference centroids in feature space.
    feature_labels : list[str] | None
        Human-readable names for each feature dimension.
    """

    def __init__(
        self,
        snapshot_store=None,
        tracker=None,
        projector=None,
        centroids: dict[str, list[float]] | None = None,
        feature_labels: list[str] | None = None,
    ):
        self.store = snapshot_store
        self.tracker = tracker
        self.projector = projector
        self.centroids = centroids or {}
        self.feature_labels = feature_labels or []

    # ── Tool: get_position ──

    def get_position(self, entity_id: str) -> str:
        """
        Get the current position of an entity in the vector space.

        Returns the entity's raw feature vector, projected coordinates (if available),
        and per-feature values with human-readable labels. Use this to understand
        where a specific entity (agent, competitor, restaurant) currently sits
        in the behavioral decision space.

        Args:
            entity_id: The unique identifier of the entity to query.

        Returns:
            A JSON string with the entity's position data, including features,
            coordinates, and labeled feature values.
        """
        result = {"entity_id": entity_id}

        # Try snapshot store first (latest data)
        if self.store:
            latest = self.store.get_latest(1)
            if latest:
                snap = latest[0]
                if entity_id in snap.entities:
                    es = snap.entities[entity_id]
                    result["features"] = es.features
                    result["coordinates"] = es.coordinates
                    result["step"] = snap.step
                    if self.feature_labels and es.features:
                        result["labeled_features"] = {
                            label: round(val, 4)
                            for label, val in zip(self.feature_labels, es.features)
                        }
                    return json.dumps(result)

        # Fallback: try tracker
        if self.tracker:
            history = self.tracker.get_history(entity_id)
            if history:
                latest_point = history[-1]
                result["features"] = latest_point.features
                result["step"] = latest_point.step
                if self.feature_labels:
                    result["labeled_features"] = {
                        label: round(val, 4)
                        for label, val in zip(self.feature_labels, latest_point.features)
                    }
                # Project if possible
                if self.projector:
                    try:
                        coords = self.projector.project_single(latest_point.features)
                        result["coordinates"] = coords
                    except RuntimeError:
                        pass
                return json.dumps(result)

        result["error"] = f"Entity '{entity_id}' not found in any data source"
        return json.dumps(result)

    # ── Tool: nearest_neighbors ──

    def nearest_neighbors(self, entity_id: str, k: int = 5) -> str:
        """
        Find the K nearest entities to a given entity in feature space.

        Computes Euclidean distances between the target entity and all other
        entities using their raw feature vectors. Useful for identifying
        competitors with similar behavioral patterns or finding clusters.

        Args:
            entity_id: The entity to find neighbors for.
            k: Number of nearest neighbors to return (default: 5).

        Returns:
            A JSON string with a ranked list of neighbors, each including
            entity_id, distance, and shared feature comparison.
        """
        # Get all current entity vectors
        all_vectors = self._get_all_current_vectors()
        if entity_id not in all_vectors:
            return json.dumps({"error": f"Entity '{entity_id}' not found"})

        target = np.array(all_vectors[entity_id], dtype=np.float64)
        distances = []

        for eid, fv in all_vectors.items():
            if eid == entity_id:
                continue
            vec = np.array(fv, dtype=np.float64)
            dist = float(np.linalg.norm(target - vec))
            distances.append({"entity_id": eid, "distance": round(dist, 4)})

        distances.sort(key=lambda x: x["distance"])
        neighbors = distances[:k]

        # Add feature comparison for top neighbors
        if self.feature_labels:
            for n in neighbors:
                n_vec = np.array(all_vectors[n["entity_id"]], dtype=np.float64)
                diff = target - n_vec
                n["feature_differences"] = {
                    label: round(float(d), 4)
                    for label, d in zip(self.feature_labels, diff)
                }

        return json.dumps({
            "entity_id": entity_id,
            "neighbors": neighbors,
            "total_entities": len(all_vectors),
        })

    # ── Tool: distance_to_centroids ──

    def distance_to_centroids(self, entity_id: str) -> str:
        """
        Measure the distance from an entity to all named zone centroids.

        Returns Euclidean distances to each centroid (zone reference point)
        in the raw feature space. Lower distance means the entity's behavior
        is closer to that zone's ideal profile. Useful for strategic
        positioning decisions.

        Args:
            entity_id: The entity to measure distances for.

        Returns:
            A JSON string with distances to each centroid, sorted by
            proximity, including the nearest zone name.
        """
        if not self.centroids:
            return json.dumps({"error": "No centroids configured"})

        all_vectors = self._get_all_current_vectors()
        if entity_id not in all_vectors:
            return json.dumps({"error": f"Entity '{entity_id}' not found"})

        target = np.array(all_vectors[entity_id], dtype=np.float64)
        distances = []

        for cid, cv in self.centroids.items():
            c_vec = np.array(cv, dtype=np.float64)
            dist = float(np.linalg.norm(target - c_vec))
            distances.append({
                "centroid": cid,
                "distance": round(dist, 4),
            })

            # Feature gap analysis
            if self.feature_labels:
                gap = c_vec - target
                distances[-1]["feature_gaps"] = {
                    label: round(float(g), 4)
                    for label, g in zip(self.feature_labels, gap)
                }

        distances.sort(key=lambda x: x["distance"])

        return json.dumps({
            "entity_id": entity_id,
            "nearest_zone": distances[0]["centroid"] if distances else None,
            "centroid_distances": distances,
        })

    # ── Tool: trajectory_summary ──

    def trajectory_summary(self, entity_id: str) -> str:
        """
        Get a summary of an entity's recent trajectory in feature space.

        Returns trajectory metrics: movement direction, momentum (speed of change),
        drift (total distance from starting position), stability (behavioral
        consistency), and classification (stable/drifting/oscillating/etc).

        Args:
            entity_id: The entity to get trajectory data for.

        Returns:
            A JSON string with trajectory metrics and a human-readable
            interpretation of the entity's behavioral pattern.
        """
        if not self.tracker:
            return json.dumps({"error": "No trajectory tracker configured"})

        traj = self.tracker.get_trajectory(entity_id)
        if traj is None:
            return json.dumps({"error": f"No trajectory data for '{entity_id}'"})

        result = traj.to_dict()

        # Add human-readable interpretation
        interp = self._interpret_trajectory(traj)
        result["interpretation"] = interp

        # Add labeled direction if feature labels available
        if self.feature_labels and traj.direction:
            sorted_dims = sorted(
                enumerate(traj.direction),
                key=lambda x: abs(x[1]),
                reverse=True,
            )
            result["dominant_movement"] = [
                {
                    "feature": self.feature_labels[i] if i < len(self.feature_labels) else f"dim_{i}",
                    "direction_weight": round(w, 4),
                }
                for i, w in sorted_dims[:5]
            ]

        return json.dumps(result)

    # ── Tool: entity_history ──

    def entity_history(self, entity_id: str, last_n: int = 10) -> str:
        """
        Get the historical positions of an entity over recent steps.

        Returns a time series of the entity's feature vectors, projected
        coordinates, and trajectory classifications across the last N steps.
        Useful for understanding behavioral evolution over time.

        Args:
            entity_id: The entity to get history for.
            last_n: Number of recent steps to return (default: 10).

        Returns:
            A JSON string with a time series of position data.
        """
        if self.store:
            history = self.store.get_entity_history(entity_id, last_n=last_n)
            if history:
                return json.dumps({
                    "entity_id": entity_id,
                    "history": history,
                    "steps": len(history),
                })

        # Fallback to tracker history
        if self.tracker:
            points = self.tracker.get_history(entity_id)
            if points:
                recent = points[-last_n:]
                history = [
                    {"step": p.step, "features": p.features}
                    for p in recent
                ]
                return json.dumps({
                    "entity_id": entity_id,
                    "history": history,
                    "steps": len(history),
                })

        return json.dumps({"error": f"No history for '{entity_id}'"})

    # ── Tool: space_overview ──

    def space_overview(self) -> str:
        """
        Get a high-level overview of the entire vector space.

        Returns a summary of all tracked entities, their positions, trajectory
        classifications, and the overall state of the decision landscape.
        Useful for getting a quick picture of the competitive environment.

        Returns:
            A JSON string with entity count, per-entity summaries,
            centroid info, and aggregate statistics.
        """
        all_vectors = self._get_all_current_vectors()
        if not all_vectors:
            return json.dumps({"error": "No entities in the vector space"})

        entities_summary = []
        for eid, fv in all_vectors.items():
            entry = {"entity_id": eid}

            # Trajectory info
            if self.tracker:
                traj = self.tracker.get_trajectory(eid)
                if traj:
                    entry["classification"] = traj.classification
                    entry["momentum"] = round(traj.momentum, 4)
                    entry["stability"] = round(traj.stability, 4)
                    entry["drift"] = round(traj.drift, 4)

            # Nearest centroid
            if self.centroids:
                min_dist = float("inf")
                nearest = None
                target = np.array(fv, dtype=np.float64)
                for cid, cv in self.centroids.items():
                    dist = float(np.linalg.norm(target - np.array(cv, dtype=np.float64)))
                    if dist < min_dist:
                        min_dist = dist
                        nearest = cid
                entry["nearest_zone"] = nearest
                entry["zone_distance"] = round(min_dist, 4)

            entities_summary.append(entry)

        # Aggregate stats
        if self.tracker:
            classifications = {}
            for es in entities_summary:
                cls = es.get("classification", "unknown")
                classifications[cls] = classifications.get(cls, 0) + 1
        else:
            classifications = {}

        return json.dumps({
            "total_entities": len(all_vectors),
            "entities": entities_summary,
            "centroids": list(self.centroids.keys()),
            "trajectory_distribution": classifications,
        })

    # ── Internal helpers ──

    def _get_all_current_vectors(self) -> dict[str, list[float]]:
        """Get current feature vectors for all known entities."""
        vectors = {}

        # From snapshot store
        if self.store:
            latest = self.store.get_latest(1)
            if latest:
                for eid, es in latest[0].entities.items():
                    if es.features:
                        vectors[eid] = es.features

        # From tracker (if store didn't have data)
        if not vectors and self.tracker:
            for eid in self.tracker.get_all_entities():
                history = self.tracker.get_history(eid)
                if history:
                    vectors[eid] = history[-1].features

        return vectors

    def _interpret_trajectory(self, traj) -> str:
        """Generate a human-readable interpretation of a trajectory."""
        cls = traj.classification

        interpretations = {
            "stable": (
                f"Entity is behaviorally stable (momentum={traj.momentum:.3f}, "
                f"drift={traj.drift:.3f}). Minimal change in recent steps."
            ),
            "drifting": (
                f"Entity is drifting away from its starting behavior (drift={traj.drift:.3f}). "
                f"This suggests a strategic shift or environmental adaptation."
            ),
            "oscillating": (
                f"Entity is oscillating between strategies (stability={traj.stability:.3f}). "
                f"Behavior is inconsistent — possible experimentation or instability."
            ),
            "accelerating": (
                f"Entity is accelerating — behavioral changes are getting larger each step "
                f"(momentum={traj.momentum:.3f}). Possible aggressive pivot."
            ),
            "converging": (
                f"Entity is converging — behavioral changes are getting smaller "
                f"(momentum={traj.momentum:.3f}). Settling into a strategy."
            ),
            "new": "Entity was just observed — no trajectory data yet.",
            "active": (
                f"Entity is actively changing (momentum={traj.momentum:.3f}, "
                f"drift={traj.drift:.3f}) but without a clear directional pattern."
            ),
        }

        return interpretations.get(cls, f"Unknown classification: {cls}")

    # ── Convenience: list all tool methods ──

    def get_tools(self) -> list:
        """Return all tool methods as a list for Agent(tools=[...])."""
        return [
            self.get_position,
            self.nearest_neighbors,
            self.distance_to_centroids,
            self.trajectory_summary,
            self.entity_history,
            self.space_overview,
        ]
