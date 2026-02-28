"""
SPAM! — Embedding Module
==========================
PCA projection of 14-dim behavioral feature vectors for
visualization and clustering.
"""

import logging

import numpy as np

logger = logging.getLogger("spam.intelligence.embedding")


class EmbeddingModule:
    """
    PCA-based dimensionality reduction for behavioral feature vectors.

    Projects 14-dim vectors to 2D/3D for visualization and to
    lower dimensions for clustering.
    """

    def __init__(self, n_components: int = 2):
        self.n_components = n_components
        self._mean: np.ndarray | None = None
        self._components: np.ndarray | None = None
        self._fitted = False

    def fit(self, feature_matrix: np.ndarray):
        """
        Fit PCA on a feature matrix (n_restaurants × 14).

        Uses simple numpy PCA (no sklearn dependency in hot path).
        """
        if feature_matrix.shape[0] < 2:
            logger.warning("Not enough data to fit PCA (need ≥ 2 samples)")
            return

        self._mean = np.mean(feature_matrix, axis=0)
        centered = feature_matrix - self._mean

        # SVD-based PCA
        _, s, Vt = np.linalg.svd(centered, full_matrices=False)
        self._components = Vt[: self.n_components]
        self._fitted = True

        # Log explained variance
        explained = (s**2) / np.sum(s**2)
        logger.debug(
            f"PCA fitted: explained variance = "
            f"{explained[:self.n_components].sum():.2%} "
            f"({self.n_components} components)"
        )

    def transform(self, features: np.ndarray) -> np.ndarray:
        """Project features to lower dimensions."""
        if not self._fitted:
            # Return first n_components if not fitted
            if features.ndim == 1:
                return features[: self.n_components]
            return features[:, : self.n_components]

        centered = features - self._mean
        if centered.ndim == 1:
            return centered @ self._components.T
        return centered @ self._components.T

    def fit_transform(self, feature_matrix: np.ndarray) -> np.ndarray:
        """Fit and transform in one step."""
        self.fit(feature_matrix)
        return self.transform(feature_matrix)

    async def process(self, input_data: dict) -> dict:
        """
        Pipeline module interface.

        input_data: {features: {rid: np.ndarray}}
        output: {embeddings: {rid: np.ndarray}, embedding_matrix: np.ndarray}
        """
        features = input_data.get("features", {})
        if not features:
            return {"embeddings": {}, "embedding_matrix": np.array([])}

        rids = list(features.keys())
        matrix = np.array([features[rid] for rid in rids])

        if matrix.shape[0] >= 2:
            projected = self.fit_transform(matrix)
        else:
            projected = matrix[:, : self.n_components] if matrix.ndim == 2 else matrix

        embeddings = {rid: projected[i] for i, rid in enumerate(rids)}

        return {
            "embeddings": embeddings,
            "embedding_matrix": projected,
            "rids": rids,
        }
