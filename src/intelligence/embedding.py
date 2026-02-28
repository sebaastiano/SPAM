"""
Embedding — PCA / UMAP for strategy-space positioning.
"""

from __future__ import annotations

import numpy as np


class EmbeddingProjector:
    """Projects 14-dim feature vectors to 2D for clustering and visualisation.

    Uses PCA by default; UMAP if scikit-learn-extra is available (optional).
    """

    def __init__(self, n_components: int = 2) -> None:
        self.n_components = n_components
        self._mean: np.ndarray | None = None
        self._components: np.ndarray | None = None

    def fit_transform(self, features: np.ndarray) -> np.ndarray:
        """``features``: shape ``(n_restaurants, 14)``.
        Returns shape ``(n_restaurants, n_components)``."""
        if features.shape[0] < 2:
            return features[:, : self.n_components]

        self._mean = features.mean(axis=0)
        centred = features - self._mean
        # Covariance + eigen decomposition (lightweight PCA)
        cov = np.cov(centred, rowvar=False)
        eigenvalues, eigenvectors = np.linalg.eigh(cov)
        # Take top n_components eigenvectors (largest eigenvalues last)
        idx = np.argsort(eigenvalues)[::-1][: self.n_components]
        self._components = eigenvectors[:, idx]
        return centred @ self._components

    def transform(self, features: np.ndarray) -> np.ndarray:
        if self._mean is None or self._components is None:
            return features[:, : self.n_components]
        centred = features - self._mean
        return centred @ self._components
