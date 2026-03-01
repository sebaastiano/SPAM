"""
SPAM! — Pricing Module
========================
Menu pricing logic based on prestige tiers, zone, and competition.

VOLUME-FIRST MIXED PRICING: tiered by prestige to attract ALL customer types.
"""

import logging

from src.config import (
    ARCHETYPE_CEILINGS,
    ZONE_PRICE_FACTORS,
    ZONE_TARGET_ARCHETYPES,
    PRICE_TIERS,
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
    Compute optimized prices for all menu items using MIXED TIERED PRICING.

    VOLUME-FIRST approach:
    - Low-prestige dishes: BARGAIN prices → attract Esploratori, Famiglie
    - Mid-prestige dishes: MODERATE prices → broad appeal
    - High-prestige dishes: HIGHER prices → Astrobaroni, Saggi pay willingly
    - The result: a menu with price diversity that attracts ALL archetypes

    When no competition: modest premium (don't get greedy, volume still king)
    When competition: undercut on cheap dishes, hold on premium
    """
    zone_factor = ZONE_PRICE_FACTORS.get(zone, 0.65)
    rep_mult = 1.0 + (reputation - 50) / 300

    # Assess competition
    active_competitors = 0
    if competitor_briefings:
        active_competitors = sum(
            1 for b in competitor_briefings.values()
            if b.get("is_connected", False)
        )

    # Monopoly bonus — modest, don't scare customers
    monopoly_mult = 1.15 if active_competitors == 0 else 1.0

    # Get competitor avg for undercutting
    comp_avg = competitor_avg_price
    if competitor_briefings:
        comp_prices = [
            b.get("menu_price_avg", 0)
            for b in competitor_briefings.values()
            if b.get("menu_price_avg", 0) > 0
        ]
        if comp_prices:
            comp_avg = sum(comp_prices) / len(comp_prices)

    priced = []
    for item in menu_items:
        prestige = item.get("prestige", 50)

        # Determine base price from tier
        base_price = 60  # fallback
        for tier_name, (p_min, p_max, tier_price) in PRICE_TIERS.items():
            if p_min <= prestige <= p_max:
                base_price = tier_price
                break

        # Gentle scaling
        prestige_mult = 1.0 + (prestige - 50) / 250
        price = int(base_price * prestige_mult * rep_mult * zone_factor * monopoly_mult)

        # Competition undercutting (only when competitors exist)
        if active_competitors > 0 and comp_avg > 0:
            if prestige <= 50:
                price = min(price, int(comp_avg * 0.75))
            elif prestige <= 70:
                price = min(price, int(comp_avg * 0.90))

        # Hard bounds
        price = max(12, min(price, 250))

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
    Adjust prices based on competitor pricing.

    VOLUME-FIRST approach:
    - When no active competitors: keep prices, modest bump only
    - When competitors active: undercut on budget dishes, hold on premium
    - Never race to zero — maintain minimum viable margins
    """
    active_competitors = 0
    if competitor_briefings:
        active_competitors = sum(
            1 for b in competitor_briefings.values()
            if b.get("is_connected", False)
        )

    if active_competitors == 0:
        # No competition — keep as-is, already set by compute_menu_prices
        logger.info("No active competitors — maintaining tiered prices")
        return menu_items

    if not competitor_prices:
        return menu_items

    avg_competitor = sum(competitor_prices) / len(competitor_prices)

    adjusted = []
    for item in menu_items:
        price = item["price"]

        # Cheap dishes (≤50): undercut aggressively to win customers
        if price <= 50:
            price = min(price, int(avg_competitor * 0.75))
        # Mid dishes (51-100): slight undercut
        elif price <= 100:
            price = min(price, int(avg_competitor * 0.90))
        # Premium dishes (>100): hold firm (rich clients don't comparison-shop)

        adjusted.append({"name": item["name"], "price": max(12, price)})

    return adjusted
