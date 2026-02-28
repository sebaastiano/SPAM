"""
SPAM! — Pricing Module
========================
Menu pricing logic based on zone, intelligence data, and competition levels.
"""

import logging

from src.config import (
    ARCHETYPE_CEILINGS,
    ZONE_PRICE_FACTORS,
    ZONE_TARGET_ARCHETYPES,
)

logger = logging.getLogger("spam.decision.pricing")


def compute_menu_prices(
    menu_items: list[dict],
    zone: str,
    reputation: float,
    competitor_avg_price: float = 120.0,
    competitor_briefings: dict[int, dict] | None = None,
) -> list[dict]:
    """
    Compute optimized prices for all menu items.

    INTELLIGENCE-DRIVEN: uses competitor data when available.
    When no competition: prices at archetype ceiling for max profit.
    """
    target_archetypes = ZONE_TARGET_ARCHETYPES.get(zone, [])
    if target_archetypes:
        primary_archetype = target_archetypes[0]
    else:
        primary_archetype = "Famiglie Orbitali"

    base_ceiling = ARCHETYPE_CEILINGS.get(primary_archetype, 120)
    rep_mult = 1.0 + (reputation - 50) / 200

    # Assess competition from intelligence — use CONNECTION STATUS
    # (is_connected) instead of menu_size, which is 0 during speaking phase.
    active_competitors = 0
    if competitor_briefings:
        active_competitors = sum(
            1 for b in competitor_briefings.values()
            if b.get("is_connected", False)
        )

    # When no competition, don't apply zone discount factor — price at ceiling
    if active_competitors == 0:
        zone_factor = 1.0  # monopoly: full ceiling price
    else:
        zone_factor = ZONE_PRICE_FACTORS.get(zone, 0.7)

    priced = []
    for item in menu_items:
        prestige = item.get("prestige", 50)
        prestige_mult = 1.0 + (prestige - 50) / 200

        price = int(base_ceiling * rep_mult * zone_factor * prestige_mult)

        # Ensure price is within reasonable bounds
        price = max(10, min(price, int(base_ceiling * 1.3)))

        priced.append({
            "name": item["name"],
            "price": price,
        })

    return priced


def adjust_prices_competitive(
    menu_items: list[dict],
    competitor_prices: list[float],
    zone: str,
    competitor_briefings: dict[int, dict] | None = None,
) -> list[dict]:
    """
    Adjust prices based on competitor pricing and intelligence data.

    When no active competitors: maintain ceiling prices (monopoly profit).
    When competitors active: strategy-specific adjustment.
    """
    # Check if there are actually active competitors — use CONNECTION
    # STATUS, not menu_size (which is 0 during speaking phase).
    active_competitors = 0
    if competitor_briefings:
        active_competitors = sum(
            1 for b in competitor_briefings.values()
            if b.get("is_connected", False)
        )

    if active_competitors == 0:
        # Monopoly — keep prices high, no undercutting needed
        logger.info("No active competitors — maintaining ceiling prices")
        return menu_items

    if not competitor_prices:
        return menu_items

    avg_competitor = sum(competitor_prices) / len(competitor_prices)

    adjusted = []
    for item in menu_items:
        price = item["price"]

        if zone == "BUDGET_OPPORTUNIST":
            # Undercut competitors
            price = min(price, int(avg_competitor * 0.85))
        elif zone == "PREMIUM_MONOPOLIST":
            # Stay premium
            price = max(price, int(avg_competitor * 1.1))

        adjusted.append({"name": item["name"], "price": max(10, price)})

    return adjusted
