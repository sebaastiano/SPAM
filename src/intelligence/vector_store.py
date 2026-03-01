"""
SPAM! — Vector Store
======================
File-based store for feature vectors that bridges the intelligence
pipeline (writer) and the dashboard (reader).

Stores per-turn snapshots of 14-dim feature vectors for all competitors,
zone centroids, and our agent's position. Written as JSON so the
dashboard can read it without importing src modules.
"""

import json
import logging
import threading
from pathlib import Path
from typing import Any

logger = logging.getLogger("spam.intelligence.vector_store")

# Store location (workspace root)
_STORE_PATH = Path(__file__).parent.parent.parent / "vectorspace_data.json"
_lock = threading.Lock()

# Feature dimension labels
FEATURE_LABELS = [
    "bid_aggressiveness", "bid_concentration", "bid_consistency", "bid_volume",
    "price_positioning", "menu_stability", "specialization_depth", "market_activity",
    "buy_sell_ratio", "balance_growth_rate", "reputation_rate", "prestige_targeting",
    "recipe_complexity", "menu_size",
]


def _load() -> dict:
    """Load the store from disk."""
    try:
        if _STORE_PATH.exists():
            return json.loads(_STORE_PATH.read_text())
    except Exception as e:
        logger.warning(f"Failed to load vector store: {e}")
    return {"turns": {}, "zone_centroids": {}}


def _save(data: dict):
    """Save the store to disk."""
    try:
        _STORE_PATH.write_text(json.dumps(data, indent=2, default=str))
    except Exception as e:
        logger.warning(f"Failed to save vector store: {e}")


def save_turn_vectors(
    turn_id: int,
    feature_vectors: dict[int | str, list[float]],
    embeddings: dict[int | str, list[float]] | None = None,
    trajectories: dict[int | str, dict] | None = None,
    our_zone: str | None = None,
    our_balance: float | None = None,
    restaurant_names: dict[int | str, str] | None = None,
):
    """
    Save a snapshot of all feature vectors for this turn.

    Args:
        turn_id: Current turn number
        feature_vectors: {restaurant_id: [14 floats]} raw features
        embeddings: {restaurant_id: [N floats]} reduced embeddings (optional)
        trajectories: {restaurant_id: trajectory_info} (optional)
        our_zone: Our current zone selection
        our_balance: Our current balance
        restaurant_names: {restaurant_id: name} mapping
    """
    with _lock:
        data = _load()

        # Convert numpy arrays to lists
        vectors = {}
        for rid, fv in feature_vectors.items():
            rid_str = str(rid)
            vec = fv.tolist() if hasattr(fv, 'tolist') else list(fv)
            vectors[rid_str] = {
                "features": vec,
                "name": (restaurant_names or {}).get(rid, (restaurant_names or {}).get(int(rid) if isinstance(rid, str) else rid, f"Team {rid}")),
            }
            if embeddings and rid_str in embeddings:
                emb = embeddings[rid_str]
                vectors[rid_str]["embedding"] = emb.tolist() if hasattr(emb, 'tolist') else list(emb)
            elif embeddings and rid in embeddings:
                emb = embeddings[rid]
                vectors[rid_str]["embedding"] = emb.tolist() if hasattr(emb, 'tolist') else list(emb)
            if trajectories and (rid_str in trajectories or rid in trajectories):
                traj = trajectories.get(rid_str, trajectories.get(rid, {}))
                vectors[rid_str]["trajectory"] = traj

        turn_data = {
            "vectors": vectors,
            "our_zone": our_zone,
            "our_balance": our_balance,
            "feature_labels": FEATURE_LABELS,
        }

        data["turns"][str(turn_id)] = turn_data

        # Keep only last 20 turns to avoid unbounded growth
        turn_keys = sorted(data["turns"].keys(), key=int)
        if len(turn_keys) > 20:
            for old_key in turn_keys[:-20]:
                del data["turns"][old_key]

        _save(data)
        logger.info(f"Saved {len(vectors)} feature vectors for turn {turn_id}")


def save_zone_centroids(centroids: dict[str, list[float]]):
    """Save zone centroid definitions (called once at startup)."""
    with _lock:
        data = _load()
        data["zone_centroids"] = {
            zone: (c.tolist() if hasattr(c, 'tolist') else list(c))
            for zone, c in centroids.items()
        }
        _save(data)


def load_all() -> dict:
    """Load the full store (used by dashboard)."""
    return _load()
