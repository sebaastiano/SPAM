"""
VectorSpaceModule — Dimensionality reduction for agent observability.

A ``datapizza`` PipelineComponent that takes N-dimensional feature vectors
and projects them into a low-dimensional space (2D or 3D) for visualization
and analysis.

Supports three projection methods:
    - **pca** (default) — Fast, deterministic, preserves global structure.
    - **tsne** — Better local clustering, slower.
    - **umap** — Best for large datasets, requires ``umap-learn``.

Integration::

    from datapizza.pipeline.dag_pipeline import DagPipeline
    from datapizza.modules.observability import VectorSpaceModule

    pipeline = DagPipeline()
    pipeline.add_module("features", my_feature_extractor)
    pipeline.add_module("vectorspace", VectorSpaceModule(n_components=2, method="pca"))
    pipeline.connect("features", "vectorspace", target_key="features")

    result = await pipeline.a_run({"features": {...}})
    projections = result["vectorspace"]["projections"]
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Literal

import numpy as np

logger = logging.getLogger("datapizza.modules.observability.vector_space")


# ── Data types ──

@dataclass
class Projection:
    """A single entity's position in the projected space."""

    entity_id: str
    coordinates: list[float]           # [x, y] or [x, y, z]
    raw_features: list[float]          # original N-dim vector
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "entity_id": self.entity_id,
            "coordinates": self.coordinates,
            "raw_features": self.raw_features,
            "metadata": self.metadata,
        }


@dataclass
class ProjectionResult:
    """Complete output of a projection step."""

    projections: dict[str, Projection]  # entity_id → Projection
    variance_explained: list[float]     # per-component (PCA only)
    method: str
    n_components: int
    centroid_projections: dict[str, list[float]] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "projections": {k: v.to_dict() for k, v in self.projections.items()},
            "variance_explained": self.variance_explained,
            "centroid_projections": self.centroid_projections,
            "method": self.method,
            "n_components": self.n_components,
        }


# ── PipelineComponent ──

class VectorSpaceModule:
    """
    Dimensionality reduction PipelineComponent for datapizza DagPipeline.

    Accepts a dict of ``{entity_id: feature_vector}`` and produces 2D/3D
    projections using PCA, t-SNE, or UMAP.

    Parameters
    ----------
    n_components : int
        Target dimensionality (2 or 3). Default: 2.
    method : str
        Projection method: ``"pca"``, ``"tsne"``, or ``"umap"``. Default: ``"pca"``.
    feature_labels : list[str] | None
        Human-readable labels for each feature dimension.
    centroids : dict[str, list[float]] | None
        Named reference points to project alongside entity vectors.
        Useful for showing "zones" or "ideal behaviors" in the space.
    normalize : bool
        Whether to normalize features to [0, 1] before projection. Default: True.
    """

    def __init__(
        self,
        n_components: int = 2,
        method: Literal["pca", "tsne", "umap"] = "pca",
        feature_labels: list[str] | None = None,
        centroids: dict[str, list[float] | np.ndarray] | None = None,
        normalize: bool = True,
    ):
        self.n_components = n_components
        self.method = method
        self.feature_labels = feature_labels
        self.centroids = centroids or {}
        self.normalize = normalize

        # Internal state for consistent projections across runs
        self._projection_basis: np.ndarray | None = None  # PCA: Vt matrix
        self._normalization_params: tuple[np.ndarray, np.ndarray] | None = None
        self._fit_count = 0

    # ── datapizza PipelineComponent interface ──

    def run(self, data: dict | None = None, **kwargs) -> dict:
        """
        Synchronous pipeline entry point.

        Parameters
        ----------
        data : dict
            Must contain a ``"features"`` key with
            ``{entity_id: list[float] | np.ndarray}``.
            Optionally ``"centroids"`` to override init centroids.
            Optionally ``"metadata"`` with ``{entity_id: dict}``.

        Returns
        -------
        dict
            ``{"projections": ..., "variance_explained": ..., ...}``
        """
        return self._process(data or {}, **kwargs)

    async def a_run(self, data: dict | None = None, **kwargs) -> dict:
        """Async pipeline entry point (delegates to sync — projection is CPU-bound)."""
        return self._process(data or {}, **kwargs)

    # ── Core logic ──

    def _process(self, data: dict, **kwargs) -> dict:
        """Process features into projections."""
        # Accept features from upstream module or direct input
        features_raw = data.get("features", {})
        if not features_raw:
            # Try data from a parent node (DagPipeline passes nested dicts)
            for key, val in data.items():
                if isinstance(val, dict) and "features" in val:
                    features_raw = val["features"]
                    break

        if not features_raw:
            logger.warning("VectorSpaceModule received no features")
            return ProjectionResult(
                projections={},
                variance_explained=[],
                method=self.method,
                n_components=self.n_components,
            ).to_dict()

        # Convert to arrays
        entity_ids = []
        vectors = []
        metadata_map = data.get("metadata", {})

        for eid, fv in features_raw.items():
            entity_ids.append(str(eid))
            vec = fv.tolist() if hasattr(fv, "tolist") else list(fv)
            vectors.append(vec)

        X = np.array(vectors, dtype=np.float64)
        n_dims = X.shape[1] if X.ndim == 2 else 0

        if n_dims == 0 or len(entity_ids) == 0:
            return ProjectionResult(
                projections={}, variance_explained=[],
                method=self.method, n_components=self.n_components,
            ).to_dict()

        # Merge centroids
        centroids = dict(self.centroids)
        if "centroids" in data:
            centroids.update(data["centroids"])

        centroid_ids = list(centroids.keys())
        centroid_vecs = []
        for cid in centroid_ids:
            cv = centroids[cid]
            centroid_vecs.append(cv.tolist() if hasattr(cv, "tolist") else list(cv))

        # Combine entity vectors + centroids for joint projection
        if centroid_vecs:
            C = np.array(centroid_vecs, dtype=np.float64)
            combined = np.vstack([X, C])
        else:
            combined = X

        # Normalize
        if self.normalize:
            combined, norm_params = self._normalize(combined)
        else:
            norm_params = None

        # Project
        projected, variance_explained = self._project(combined)

        # Split back into entities and centroids
        entity_projected = projected[: len(entity_ids)]
        centroid_projected = projected[len(entity_ids):]

        # Build results
        projections = {}
        for i, eid in enumerate(entity_ids):
            projections[eid] = Projection(
                entity_id=eid,
                coordinates=entity_projected[i].tolist(),
                raw_features=vectors[i],
                metadata=metadata_map.get(eid, {}),
            )

        centroid_results = {}
        for i, cid in enumerate(centroid_ids):
            centroid_results[cid] = centroid_projected[i].tolist()

        result = ProjectionResult(
            projections=projections,
            variance_explained=variance_explained,
            method=self.method,
            n_components=self.n_components,
            centroid_projections=centroid_results,
        )

        self._fit_count += 1
        logger.info(
            f"Projected {len(entity_ids)} entities + {len(centroid_ids)} centroids "
            f"from {n_dims}D → {self.n_components}D ({self.method})"
        )

        return result.to_dict()

    def _normalize(self, X: np.ndarray) -> tuple[np.ndarray, tuple]:
        """Min-max normalize to [0, 1]."""
        mins = X.min(axis=0)
        maxs = X.max(axis=0)
        ranges = maxs - mins
        ranges[ranges == 0] = 1.0  # avoid divide by zero
        normalized = (X - mins) / ranges
        self._normalization_params = (mins, ranges)
        return normalized, (mins, ranges)

    def _project(self, X: np.ndarray) -> tuple[np.ndarray, list[float]]:
        """Dispatch to the selected projection method."""
        if self.method == "pca":
            return self._pca(X)
        elif self.method == "tsne":
            return self._tsne(X)
        elif self.method == "umap":
            return self._umap(X)
        else:
            raise ValueError(f"Unknown projection method: {self.method}")

    def _pca(self, X: np.ndarray) -> tuple[np.ndarray, list[float]]:
        """PCA via SVD — pure numpy, no external deps."""
        centered = X - X.mean(axis=0)
        try:
            U, S, Vt = np.linalg.svd(centered, full_matrices=False)
            self._projection_basis = Vt
            projected = centered @ Vt[: self.n_components].T
            total_var = (S**2).sum()
            variance_explained = [
                float(S[i] ** 2 / total_var) if total_var > 0 else 0.0
                for i in range(min(self.n_components, len(S)))
            ]
        except np.linalg.LinAlgError:
            # Fallback: just take first n_components dimensions
            projected = centered[:, : self.n_components]
            variance_explained = [1.0 / self.n_components] * self.n_components

        return projected, variance_explained

    def _tsne(self, X: np.ndarray) -> tuple[np.ndarray, list[float]]:
        """t-SNE via sklearn (optional dependency)."""
        try:
            from sklearn.manifold import TSNE

            n_samples = X.shape[0]
            perplexity = min(30.0, max(2.0, n_samples / 3))
            tsne = TSNE(
                n_components=self.n_components,
                perplexity=perplexity,
                random_state=42,
                max_iter=500,
            )
            projected = tsne.fit_transform(X)
            return projected, []  # t-SNE doesn't have variance explained
        except ImportError:
            logger.warning("sklearn not installed — falling back to PCA")
            return self._pca(X)

    def _umap(self, X: np.ndarray) -> tuple[np.ndarray, list[float]]:
        """UMAP (optional dependency: umap-learn)."""
        try:
            import umap

            reducer = umap.UMAP(
                n_components=self.n_components,
                n_neighbors=min(15, X.shape[0] - 1),
                min_dist=0.1,
                random_state=42,
            )
            projected = reducer.fit_transform(X)
            return projected, []  # UMAP doesn't have variance explained
        except ImportError:
            logger.warning("umap-learn not installed — falling back to PCA")
            return self._pca(X)

    # ── Utility methods ──

    def get_projection_basis(self) -> np.ndarray | None:
        """Return the PCA basis (Vt matrix) if PCA was used."""
        return self._projection_basis

    def project_single(self, feature_vector: list[float] | np.ndarray) -> list[float]:
        """
        Project a single feature vector using the last-fitted basis.

        Only works after at least one ``run()`` call with PCA method.
        Useful for projecting new entities without re-fitting.
        """
        if self._projection_basis is None:
            raise RuntimeError("No projection basis — call run() first")

        vec = np.array(feature_vector, dtype=np.float64)

        if self._normalization_params:
            mins, ranges = self._normalization_params
            vec = (vec - mins) / ranges

        # Use the stored mean (approximation: use normalization center)
        projected = vec @ self._projection_basis[: self.n_components].T
        return projected.tolist()
