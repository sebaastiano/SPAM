"""
SPAM! — Pricing Module
========================
Menu pricing logic based on zone, archetype, and reputation.
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
) -> list[dict]:
    """
    Compute optimized prices for all menu items.

    Returns menu items with updated prices.
    """
    target_archetypes = ZONE_TARGET_ARCHETYPES.get(zone, [])
    if target_archetypes:
        primary_archetype = target_archetypes[0]
    else:
        primary_archetype = "Famiglie Orbitali"

    base_ceiling = ARCHETYPE_CEILINGS.get(primary_archetype, 120)
    zone_factor = ZONE_PRICE_FACTORS.get(zone, 0.7)
    rep_mult = 1.0 + (reputation - 50) / 200

    priced = []
    for item in menu_items:
        prestige = item.get("prestige", 50)
        prestige_mult = 1.0 + (prestige - 50) / 200

        price = int(base_ceiling * rep_mult * zone_factor * prestige_mult)

        # Ensure price is within reasonable bounds
        price = max(10, min(price, int(base_ceiling * 1.2)))

        priced.append({
            "name": item["name"],
            "price": price,
        })

    return priced


def adjust_prices_competitive(
    menu_items: list[dict],
    competitor_prices: list[float],
    zone: str,
) -> list[dict]:
    """
    Adjust prices based on competitor pricing.

    For premium zones: stay near ceiling (don't undercut)
    For budget zones: undercut competitors by 10-20%
    """
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
