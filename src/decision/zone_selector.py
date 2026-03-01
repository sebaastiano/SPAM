"""
SPAM! — Zone Selector
=======================
ILP-driven zone selection per turn.

Scores each zone by:
  revenue_potential × 0.4 + inventory_fit × 0.3
  − competitor_penalty × 0.2 + reputation_bonus × 0.1
"""

import logging

import numpy as np

from src.config import (
    ZONES,
    ZONE_PRESTIGE_RANGE,
    ZONE_MENU_SIZE,
    ZONE_TARGET_ARCHETYPES,
    ARCHETYPE_CEILINGS,
)

logger = logging.getLogger("spam.decision.zone_selector")


def select_zone(
    balance: float,
    inventory: dict[str, int],
    reputation: float,
    recipes: list[dict],
    competitor_clusters: dict[int, str],
    competitor_briefings: dict[int, dict],
    all_states: dict | None = None,
) -> str:
    """
    Select the optimal zone for this turn.

    INTELLIGENCE-DRIVEN ZONE SELECTION:
    - When no active competitors: ALWAYS pick PREMIUM_MONOPOLIST
      (highest revenue per customer, no undercutting risk)
    - When competitors exist: score zones by revenue, fit, competition, reputation
    """
    # Count active competitors (with menu and/or bids)
    active_competitors = sum(
        1 for b in competitor_briefings.values()
        if b.get("is_active", True) and b.get("menu_size", 0) > 0
    )

    # FALLBACK: if briefings show 0 active but we have raw state data,
    # count competitors directly from all_states as a sanity check.
    if active_competitors == 0 and all_states:
        raw_active = 0
        for rid, rdata in all_states.items():
            # rdata can be a CompetitorTurnState or a raw dict
            if hasattr(rdata, "menu"):
                if rdata.menu:
                    raw_active += 1
            elif isinstance(rdata, dict):
                menu = rdata.get("menu")
                if isinstance(menu, dict) and menu.get("items"):
                    raw_active += 1
                elif isinstance(menu, list) and menu:
                    raw_active += 1
                elif rdata.get("isOpen", False):
                    raw_active += 1
        if raw_active > 0:
            logger.warning(
                f"Briefings show 0 active competitors but all_states shows {raw_active}! "
                f"Using raw count to avoid monopoly assumption."
            )
            active_competitors = raw_active

    # MONOPOLY EXPLOITATION: no active competition → premium zone always
    if active_competitors == 0:
        logger.info(
            f"No active competitors detected — selecting PREMIUM_MONOPOLIST "
            f"for maximum revenue per customer (monopoly exploitation)"
        )
        return "PREMIUM_MONOPOLIST"

    zone_scores: dict[str, float] = {}

    for zone in ZONES:
        # 1. Revenue potential
        revenue_potential = _estimate_zone_revenue(zone, reputation, balance)

        # 2. Inventory fit
        inventory_fit = _calculate_inventory_alignment(zone, inventory, recipes)

        # 3. Competitor penalty (scaled by actual active count)
        competitor_penalty = _count_competitors_in_zone(
            zone, competitor_clusters, competitor_briefings
        )

        # 4. Reputation bonus
        reputation_bonus = _reputation_alignment(zone, reputation)

        # 5. Monopoly bonus: fewer competitors = bigger bonus for premium zones
        monopoly_bonus = 0.0
        if active_competitors <= 2:
            if zone == "PREMIUM_MONOPOLIST":
                monopoly_bonus = 0.3 * (1 - active_competitors / 5)
            elif zone == "NICHE_SPECIALIST":
                monopoly_bonus = 0.15 * (1 - active_competitors / 5)

        score = (
            revenue_potential * 0.4
            + inventory_fit * 0.3
            - competitor_penalty * 0.2
            + reputation_bonus * 0.1
            + monopoly_bonus
        )

        zone_scores[zone] = score
        logger.debug(
            f"Zone {zone}: rev={revenue_potential:.2f} inv={inventory_fit:.2f} "
            f"comp={competitor_penalty:.2f} rep={reputation_bonus:.2f} "
            f"mono={monopoly_bonus:.2f} → {score:.2f}"
        )

    best_zone = max(zone_scores, key=zone_scores.get)
    logger.info(
        f"Selected zone: {best_zone} "
        f"(score={zone_scores[best_zone]:.2f}, "
        f"active_competitors={active_competitors})"
    )

    return best_zone


def _estimate_zone_revenue(zone: str, reputation: float, balance: float) -> float:
    """Estimate revenue potential for a zone."""
    target_archetypes = ZONE_TARGET_ARCHETYPES.get(zone, [])
    if not target_archetypes:
        return 0.3  # minimal for zones without defined targets

    # Sum of archetype ceilings × expected fill rate
    total_ceiling = sum(
        ARCHETYPE_CEILINGS.get(arch, 100) for arch in target_archetypes
    )
    avg_ceiling = total_ceiling / len(target_archetypes)

    # Reputation affects which archetypes visit
    rep_factor = min(1.0, reputation / 100)

    # Budget constraint
    budget_factor = min(1.0, balance / 5000)

    return (avg_ceiling / 600) * rep_factor * budget_factor


def _calculate_inventory_alignment(
    zone: str, inventory: dict[str, int], recipes: list[dict]
) -> float:
    """How well does our inventory match this zone's recipe pool?"""
    prestige_min, prestige_max = ZONE_PRESTIGE_RANGE.get(zone, (0, 100))

    eligible = [
        r
        for r in recipes
        if prestige_min <= r.get("prestige", 50) <= prestige_max
    ]

    if not eligible:
        return 0.0

    # How many eligible recipes can we fully cook?
    cookable = 0
    for recipe in eligible:
        ingredients = recipe.get("ingredients", {})
        if all(inventory.get(ing, 0) >= qty for ing, qty in ingredients.items()):
            cookable += 1

    # Also consider partial coverage
    partial_scores = []
    for recipe in eligible[:10]:  # check top 10
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
    # Map zone targets to approximate competitor strategies
    zone_to_strategies = {
        "PREMIUM_MONOPOLIST": {"PREMIUM_MONOPOLIST", "STABLE_SPECIALIST"},
        "BUDGET_OPPORTUNIST": {"BUDGET_OPPORTUNIST"},
        "NICHE_SPECIALIST": {"STABLE_SPECIALIST"},
        "SPEED_CONTENDER": set(),  # universal
        "MARKET_ARBITRAGEUR": {"MARKET_ARBITRAGEUR"},
    }

    target_strategies = zone_to_strategies.get(zone, set())
    if not target_strategies:
        return 0.1  # universal zones have minimal penalty

    count = 0
    for rid, brief in competitor_briefings.items():
        strategy = brief.get("strategy", "")
        if strategy in target_strategies:
            count += 1
        # Also check menu overlap
        if brief.get("menu_size", 0) > 0:
            avg_price = brief.get("menu_price_avg", 0)
            if zone == "PREMIUM_MONOPOLIST" and avg_price > 150:
                count += 0.5
            elif zone == "BUDGET_OPPORTUNIST" and avg_price < 80:
                count += 0.5

    return count / max(len(competitor_briefings), 1)


def _reputation_alignment(zone: str, reputation: float) -> float:
    """Does our reputation support this zone's target archetypes?"""
    prestige_min, _ = ZONE_PRESTIGE_RANGE.get(zone, (0, 100))

    if zone == "PREMIUM_MONOPOLIST":
        # Need high reputation for premium clients
        return min(1.0, reputation / 100)
    elif zone == "BUDGET_OPPORTUNIST":
        # Budget works at any reputation
        return 0.7
    elif zone == "SPEED_CONTENDER":
        return 0.6
    else:
        return min(1.0, (reputation + 20) / 100)
