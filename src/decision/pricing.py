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

    PROFIT-MAXIMISATION: price as HIGH as each archetype will tolerate.
    - Astrobarone / Saggi del Cosmo don't care about price → MAX prices!
    - Famiglie Orbitali are price-conscious → moderate-high
    - Esploratori want cheap → keep accessible but still profitable
    - When no competition: full monopoly pricing (no discounts at all)
    """
    target_archetypes = ZONE_TARGET_ARCHETYPES.get(zone, [])
    if target_archetypes:
        primary_archetype = target_archetypes[0]
    else:
        primary_archetype = "Famiglie Orbitali"

    base_ceiling = ARCHETYPE_CEILINGS.get(primary_archetype, 150)
    rep_mult = 1.0 + (reputation - 50) / 150

    # Assess competition from intelligence
    active_competitors = 0
    if competitor_briefings:
        active_competitors = sum(
            1 for b in competitor_briefings.values()
            if b.get("is_connected", False)
        )

    # When no competition, don't apply zone discount — monopoly pricing
    if active_competitors == 0:
        zone_factor = 1.0  # monopoly: full ceiling price
        # For premium archetypes in monopoly, push even higher
        if primary_archetype in ("Astrobarone", "Saggi del Cosmo"):
            zone_factor = 1.15
    else:
        zone_factor = ZONE_PRICE_FACTORS.get(zone, 0.75)

    priced = []
    for item in menu_items:
        prestige = item.get("prestige", 50)
        prestige_mult = 1.0 + (prestige - 50) / 100  # stronger prestige effect

        price = int(base_ceiling * rep_mult * zone_factor * prestige_mult)

        # Generous price bounds — let the rich pay!
        price = max(15, min(price, int(base_ceiling * 2.0)))

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

    PROFIT-FIRST approach:
    - When no active competitors: maintain ceiling prices (monopoly profit).
    - When competitors active: stay above them for premium, mild undercut for budget.
    - NEVER race to the bottom — our profit margin is sacred.
    """
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
            # Only undercut slightly — never destroy our own margins
            price = min(price, int(avg_competitor * 0.92))
        elif zone == "PREMIUM_MONOPOLIST":
            # Stay well ABOVE competitors — premium brand
            price = max(price, int(avg_competitor * 1.20))

        adjusted.append({"name": item["name"], "price": max(15, price)})

    return adjusted
