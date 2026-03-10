"""SPAM! — Zone Selector
=======================
Embedding-aware zone selection per turn.

Scores each zone by:
  revenue_potential × 0.25 + inventory_fit × 0.20
  − competitor_penalty × 0.15 + reputation_bonus × 0.05
  + gap_score × 0.20 − trajectory_penalty × 0.10
  + demand_viability × 0.05

The *gap_score* uses the 14-dim feature vectors of every competitor to
find which zone's centroid is furthest from the crowd — the unoccupied
region described in vectorization_strategy.md.

The *trajectory_penalty* uses AdvancedTrajectoryPredictor to detect
competitors whose predicted next-turn position is moving toward a
zone — penalising zones that will become crowded BEFORE it happens.

The *demand_viability* checks whether the ingredients our zone needs
are in high aggregate demand from competitors (via demand_forecast).
Zones whose recipes need contested ingredients score lower.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import numpy as np

from src.config import (
    ZONES,
    ZONE_PRESTIGE_RANGE,
    ZONE_MENU_SIZE,
    ZONE_TARGET_ARCHETYPES,
    ARCHETYPE_CEILINGS,
)

if TYPE_CHECKING:
    from src.intelligence.trajectory import AdvancedTrajectoryPredictor

logger = logging.getLogger("spam.decision.zone_selector")

# ── Zone archetype centroids in 14-dim feature space ──
# These are *ideal* feature profiles for each zone, used to compute
# the gap between competitor positions and a zone.  Values are
# heuristic anchors (same ordering as feature_extractor.py).
#
# Feature indices:
#  0: bid_aggressiveness,  1: bid_concentration,  2: bid_consistency,
#  3: bid_volume,          4: price_positioning,  5: menu_stability,
#  6: specialization_depth, 7: market_activity,   8: buy_sell_ratio,
#  9: balance_growth_rate, 10: reputation_rate,   11: prestige_targeting,
# 12: recipe_complexity,   13: menu_size

_ZONE_CENTROIDS: dict[str, np.ndarray] = {
    "DIVERSIFIED":        np.array([0.15, 0.3, 0.6, 6, 0.9, 0.7, 0.06, 0.3, 1.0, 200, 2, 0.50, 0.5, 16.0]),
    "PREMIUM_MONOPOLIST": np.array([0.30, 0.7, 0.7, 3, 1.8, 0.8, 0.20, 0.1, 0.5, 300, 3, 0.90, 0.8,  5.0]),
    "BUDGET_OPPORTUNIST": np.array([0.10, 0.3, 0.5, 5, 0.5, 0.6, 0.08, 0.2, 1.0, 100, 1, 0.30, 0.3, 14.0]),
    "NICHE_SPECIALIST":   np.array([0.20, 0.8, 0.8, 3, 1.2, 0.9, 0.12, 0.1, 0.5, 150, 2, 0.70, 0.6,  8.0]),
    "SPEED_CONTENDER":    np.array([0.15, 0.4, 0.6, 5, 0.8, 0.7, 0.07, 0.2, 1.0, 150, 2, 0.50, 0.4, 14.0]),
    "MARKET_ARBITRAGEUR": np.array([0.05, 0.2, 0.3, 2, 0.6, 0.4, 0.30, 0.8, 0.3,  50, 0, 0.40, 0.3,  3.0]),
}

# Gaussian widths per feature (controls how sensitive gap is per dimension)
_FEATURE_SCALES = np.array([0.3, 0.4, 0.4, 5, 1.0, 0.4, 0.15, 0.5, 1.0, 300, 3, 0.4, 0.4, 10.0])


# ─────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────

def count_active_competitors(
    competitor_briefings: dict[int, dict],
    all_states: dict | None = None,
) -> int:
    """
    Canonical competitor-activity count used across the codebase.

    A competitor is *active* when it is connected AND has either a
    non-empty menu or an open restaurant.  Falls back to raw
    ``all_states`` when briefings undercount (e.g. during speaking
    phase before menus are published).
    """
    # Primary: count from briefings
    active = sum(
        1 for b in competitor_briefings.values()
        if b.get("is_connected", b.get("is_active", False))
        and (b.get("menu_size", 0) > 0 or b.get("is_connected", False))
    )

    # Fallback: if briefings show 0, cross-check raw state data
    if active == 0 and all_states:
        for rid, rdata in all_states.items():
            if hasattr(rdata, "menu"):
                if rdata.menu:
                    active += 1
            elif isinstance(rdata, dict):
                menu = rdata.get("menu")
                if isinstance(menu, dict) and menu.get("items"):
                    active += 1
                elif isinstance(menu, list) and menu:
                    active += 1
                elif rdata.get("isOpen", False):
                    active += 1
        if active > 0:
            logger.warning(
                "Briefings show 0 active competitors but all_states shows %d! "
                "Using raw count to avoid monopoly assumption.", active
            )

    return active


def select_zone(
    balance: float,
    inventory: dict[str, int],
    reputation: float,
    recipes: list[dict],
    competitor_clusters: dict[int, str],
    competitor_briefings: dict[int, dict],
    all_states: dict | None = None,
    # ── NEW: vector-space inputs ──
    embeddings: dict[int, np.ndarray] | None = None,
    features: dict[int, np.ndarray] | None = None,
    demand_forecast: dict[str, float] | None = None,
    trajectory_predictor: "AdvancedTrajectoryPredictor | None" = None,
) -> str:
    """
    Select the optimal zone for this turn.

    INTELLIGENCE-DRIVEN ZONE SELECTION:
    - When no active competitors: pick DIVERSIFIED (widest customer coverage)
    - When competitors exist: score zones by revenue, fit, competition,
      reputation, **embedding gap**, **trajectory preemption**, and
      **demand viability**.
    """
    active_competitors = count_active_competitors(
        competitor_briefings, all_states,
    )

    # MONOPOLY EXPLOITATION: no active competition → DIVERSIFIED
    if active_competitors == 0:
        logger.info(
            "No active competitors detected — selecting DIVERSIFIED "
            "for maximum customer coverage (no competition to worry about)"
        )
        return "DIVERSIFIED"

    zone_scores: dict[str, float] = {}

    for zone in ZONES:
        # 1. Revenue potential
        revenue_potential = _estimate_zone_revenue(zone, reputation, balance)

        # 2. Inventory fit
        inventory_fit = _calculate_inventory_alignment(zone, inventory, recipes)

        # 3. Competitor penalty (strategy + price overlap)
        competitor_penalty = _count_competitors_in_zone(
            zone, competitor_clusters, competitor_briefings
        )

        # 4. Reputation bonus
        reputation_bonus = _reputation_alignment(zone, reputation)

        # 5. Monopoly bonus
        monopoly_bonus = 0.0
        if active_competitors <= 2:
            if zone == "DIVERSIFIED":
                monopoly_bonus = 0.35 * (1 - active_competitors / 5)
            elif zone == "PREMIUM_MONOPOLIST":
                monopoly_bonus = 0.2 * (1 - active_competitors / 5)
            elif zone == "NICHE_SPECIALIST":
                monopoly_bonus = 0.1 * (1 - active_competitors / 5)

        # 6. Diversity bonus
        diversity_bonus = 0.15 if zone == "DIVERSIFIED" else 0.0

        # ── NEW SIGNALS ──

        # 7. Embedding gap score: how far is the zone centroid from the
        #    nearest competitor in feature space?  Higher = less contested.
        gap_score = _compute_gap_score(zone, features)

        # 8. Trajectory penalty: how many competitors are *moving toward*
        #    this zone's centroid next turn?  Higher = avoid.
        traj_penalty = _compute_trajectory_penalty(
            zone, trajectory_predictor
        )

        # 9. Demand viability: are the ingredients this zone's recipes
        #    need heavily contested?  Lower = good.
        demand_viability = _compute_demand_viability(
            zone, recipes, demand_forecast
        )

        score = (
            revenue_potential  * 0.25
            + inventory_fit    * 0.20
            - competitor_penalty * 0.15
            + reputation_bonus * 0.05
            + monopoly_bonus
            + diversity_bonus
            + gap_score        * 0.20
            - traj_penalty     * 0.10
            + demand_viability * 0.05
        )

        zone_scores[zone] = score
        logger.debug(
            f"Zone {zone}: rev={revenue_potential:.2f} inv={inventory_fit:.2f} "
            f"comp={competitor_penalty:.2f} rep={reputation_bonus:.2f} "
            f"mono={monopoly_bonus:.2f} div={diversity_bonus:.2f} "
            f"gap={gap_score:.2f} traj={traj_penalty:.2f} "
            f"dem={demand_viability:.2f} → {score:.2f}"
        )

    best_zone = max(zone_scores, key=zone_scores.get)
    logger.info(
        f"Selected zone: {best_zone} "
        f"(score={zone_scores[best_zone]:.2f}, "
        f"active_competitors={active_competitors})"
    )

    return best_zone


# ─────────────────────────────────────────────────────────────────
# Original scoring helpers (unchanged)
# ─────────────────────────────────────────────────────────────────

def _estimate_zone_revenue(zone: str, reputation: float, balance: float) -> float:
    """Estimate revenue potential for a zone."""
    target_archetypes = ZONE_TARGET_ARCHETYPES.get(zone, [])
    if not target_archetypes:
        return 0.3  # minimal for zones without defined targets

    total_ceiling = sum(
        ARCHETYPE_CEILINGS.get(arch, 100) for arch in target_archetypes
    )
    avg_ceiling = total_ceiling / len(target_archetypes)

    rep_factor = min(1.0, reputation / 100)
    budget_factor = min(1.0, balance / 5000)

    if zone == "DIVERSIFIED":
        volume_bonus = 1.3
        return (avg_ceiling / 600) * rep_factor * budget_factor * volume_bonus

    return (avg_ceiling / 600) * rep_factor * budget_factor


def _calculate_inventory_alignment(
    zone: str, inventory: dict[str, int], recipes: list[dict]
) -> float:
    """How well does our inventory match this zone's recipe pool?"""
    prestige_min, prestige_max = ZONE_PRESTIGE_RANGE.get(zone, (0, 100))

    eligible = [
        r for r in recipes
        if prestige_min <= r.get("prestige", 50) <= prestige_max
    ]

    if not eligible:
        return 0.0

    cookable = 0
    for recipe in eligible:
        ingredients = recipe.get("ingredients", {})
        if all(inventory.get(ing, 0) >= qty for ing, qty in ingredients.items()):
            cookable += 1

    partial_scores = []
    for recipe in eligible[:10]:
        ingredients = recipe.get("ingredients", {})
        total = sum(ingredients.values())
        have = sum(
            min(inventory.get(ing, 0), qty) for ing, qty in ingredients.items()
        )
        partial_scores.append(have / max(total, 1))

    full_score = cookable / max(len(eligible), 1)
    partial_score = np.mean(partial_scores) if partial_scores else 0

    return full_score * 0.6 + partial_score * 0.4


def _count_competitors_in_zone(
    zone: str,
    competitor_clusters: dict[int, str],
    competitor_briefings: dict[int, dict],
) -> float:
    """Count how many competitors are in or approaching this zone."""
    zone_to_strategies = {
        "DIVERSIFIED": set(),
        "PREMIUM_MONOPOLIST": {"PREMIUM_MONOPOLIST", "STABLE_SPECIALIST"},
        "BUDGET_OPPORTUNIST": {"BUDGET_OPPORTUNIST"},
        "NICHE_SPECIALIST": {"STABLE_SPECIALIST"},
        "SPEED_CONTENDER": set(),
        "MARKET_ARBITRAGEUR": {"MARKET_ARBITRAGEUR"},
    }

    target_strategies = zone_to_strategies.get(zone, set())
    if not target_strategies:
        return 0.1

    count = 0
    for rid, brief in competitor_briefings.items():
        strategy = brief.get("strategy", "")
        if strategy in target_strategies:
            count += 1
        if brief.get("menu_size", 0) > 0:
            avg_price = brief.get("menu_price_avg", 0)
            if zone == "PREMIUM_MONOPOLIST" and avg_price > 150:
                count += 0.5
            elif zone == "BUDGET_OPPORTUNIST" and avg_price < 80:
                count += 0.5

    return count / max(len(competitor_briefings), 1)


def _reputation_alignment(zone: str, reputation: float) -> float:
    """Does our reputation support this zone's target archetypes?"""
    if zone == "PREMIUM_MONOPOLIST":
        return min(1.0, reputation / 100)
    elif zone == "DIVERSIFIED":
        return min(1.0, 0.6 + reputation / 200)
    elif zone == "BUDGET_OPPORTUNIST":
        return 0.7
    elif zone == "SPEED_CONTENDER":
        return 0.6
    else:
        return min(1.0, (reputation + 20) / 100)


# ─────────────────────────────────────────────────────────────────
# NEW: Embedding / trajectory / demand components
# ─────────────────────────────────────────────────────────────────

def _compute_gap_score(
    zone: str,
    features: dict[int, np.ndarray] | None,
) -> float:
    """
    Measure how *unoccupied* this zone's centroid is in feature space.

    For every competitor whose 14-dim feature vector is known, compute
    the scaled Euclidean distance to the zone centroid.  The gap score
    is the *minimum* distance across competitors, normalised to [0, 1].
    A high gap score means no competitor is close to this zone's ideal
    position — exactly the "unoccupied region" from vectorization_strategy.md.
    """
    if not features:
        return 0.5  # neutral when we have no embedding data

    centroid = _ZONE_CENTROIDS.get(zone)
    if centroid is None:
        return 0.5

    min_dist = float("inf")
    for rid, feat in features.items():
        if feat is None or len(feat) != len(centroid):
            continue
        diff = (feat - centroid) / _FEATURE_SCALES
        dist = float(np.linalg.norm(diff))
        if dist < min_dist:
            min_dist = dist

    if min_dist == float("inf"):
        return 0.5

    # Sigmoid-style mapping: dist 0→0, dist ~3→0.85, dist >5→~1.0
    gap = 1.0 - np.exp(-0.3 * min_dist)
    return float(np.clip(gap, 0.0, 1.0))


def _compute_trajectory_penalty(
    zone: str,
    trajectory_predictor: "AdvancedTrajectoryPredictor | None",
) -> float:
    """
    Penalty for zones that competitors are *moving toward*.

    Uses the trajectory predictor's ``competitors_approaching_zone``
    which checks whether a competitor's predicted next-turn feature
    vector is closer to the zone centroid than its current one.
    """
    if trajectory_predictor is None:
        return 0.0

    centroid = _ZONE_CENTROIDS.get(zone)
    if centroid is None:
        return 0.0

    try:
        approaching = trajectory_predictor.competitors_approaching_zone(
            zone_center=centroid,
            threshold=4.0,
        )
    except Exception:
        return 0.0

    # Scale: 0 approaching → 0, 3+ approaching → ~1.0
    return min(1.0, len(approaching) / 3.0)


def _compute_demand_viability(
    zone: str,
    recipes: list[dict],
    demand_forecast: dict[str, float] | None,
) -> float:
    """
    Score how *uncontested* the ingredients for this zone's recipes are.

    Zones whose eligible recipes need many ingredients that competitors
    are also bidding on (high demand_forecast) get a LOWER score.
    Zones whose ingredients are mostly uncontested get a HIGHER score.
    """
    if not demand_forecast:
        return 0.5  # neutral

    prestige_min, prestige_max = ZONE_PRESTIGE_RANGE.get(zone, (0, 100))
    eligible = [
        r for r in recipes
        if prestige_min <= r.get("prestige", 50) <= prestige_max
    ]
    if not eligible:
        return 0.0

    recipe_scores = []
    for recipe in eligible[:15]:
        ings = recipe.get("ingredients", {})
        if not ings:
            continue
        total_demand = sum(demand_forecast.get(ing, 0) for ing in ings)
        avg_demand = total_demand / len(ings)
        recipe_scores.append(np.exp(-0.3 * avg_demand))

    if not recipe_scores:
        return 0.5

    return float(np.mean(recipe_scores))
