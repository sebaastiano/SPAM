"""
Zone selector — ILP-based zone classification that picks the best
strategic zone for the current turn.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from src.config import ZONES
from src.models import GameState


def select_zone(
    game_state: GameState,
    clusters: dict[int, str],
    briefings: dict[int, dict],
    inventory: dict[str, int] | None = None,
) -> str:
    """Score each zone and return the best one.

    Scoring factors:
      * Revenue potential  (weight 0.40)
      * Inventory fit      (weight 0.30)
      * Competitor penalty  (weight −0.20)
      * Reputation bonus   (weight 0.10)
    """
    inv = inventory or game_state.inventory
    scores: dict[str, float] = {}

    for zone in ZONES:
        competitor_penalty = _competitor_density(zone, clusters, briefings)
        inv_fit = _inventory_alignment(zone, inv)
        revenue = _revenue_potential(zone, game_state, briefings)
        rep_bonus = _reputation_alignment(zone, game_state.reputation)

        scores[zone] = (
            revenue * 0.40
            + inv_fit * 0.30
            - competitor_penalty * 0.20
            + rep_bonus * 0.10
        )

    best = max(scores, key=scores.get)  # type: ignore[arg-type]
    return best


# ── scoring helpers ───────────────────────────────────────────────


_ZONE_STRATEGY_MAP: dict[str, set[str]] = {
    "PREMIUM_MONOPOLIST": {"STABLE_SPECIALIST"},
    "BUDGET_OPPORTUNIST": {"REACTIVE_CHASER"},
    "NICHE_SPECIALIST": {"STABLE_SPECIALIST"},
    "SPEED_CONTENDER": {"REACTIVE_CHASER", "AGGRESSIVE_HOARDER"},
    "MARKET_ARBITRAGEUR": {"AGGRESSIVE_HOARDER"},
}


def _competitor_density(
    zone: str, clusters: dict[int, str], briefings: dict[int, dict]
) -> float:
    """How many competitors occupy this zone's niche?"""
    target_clusters = _ZONE_STRATEGY_MAP.get(zone, set())
    count = sum(1 for c in clusters.values() if c in target_clusters)
    return float(count) / max(len(clusters), 1)


def _inventory_alignment(zone: str, inventory: dict[str, int]) -> float:
    """How well does our inventory support this zone's recipes?"""
    # Simple heuristic: total ingredient quantity as a proxy
    total = sum(inventory.values()) if inventory else 0
    if zone == "PREMIUM_MONOPOLIST":
        # Premium needs fewer but right ingredients
        return min(1.0, total / 10)
    if zone == "BUDGET_OPPORTUNIST":
        # Budget needs many ingredients
        return min(1.0, total / 20)
    return min(1.0, total / 15)


def _revenue_potential(
    zone: str, game_state: GameState, briefings: dict[int, dict]
) -> float:
    """Estimated revenue opportunity for this zone."""
    if zone == "PREMIUM_MONOPOLIST":
        return 0.9 if game_state.reputation >= 80 else 0.5
    if zone == "BUDGET_OPPORTUNIST":
        return 0.7
    if zone == "NICHE_SPECIALIST":
        return 0.6
    if zone == "SPEED_CONTENDER":
        return 0.75
    if zone == "MARKET_ARBITRAGEUR":
        return 0.4
    return 0.5


def _reputation_alignment(zone: str, reputation: float) -> float:
    """Does our reputation attract the right archetypes for this zone?"""
    if zone == "PREMIUM_MONOPOLIST":
        return min(1.0, reputation / 100)
    if zone == "BUDGET_OPPORTUNIST":
        return 0.7  # always viable
    return min(1.0, reputation / 80)
