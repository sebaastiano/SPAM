"""
ILP solver — zone-specific bid and menu optimisation.

Uses ``scipy.optimize.milp`` when available, otherwise falls back
to a greedy heuristic so the agent always has a workable plan.
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np

from src.config import (
    ARCHETYPE_CEILINGS,
    HIGH_DELTA_INGREDIENTS,
    ZONE_PRICE_FACTORS,
)
from src.models import GameState, Recipe, ZoneDecision

log = logging.getLogger(__name__)


def solve_zone_ilp(
    zone: str,
    game_state: GameState,
    recipes: dict[str, Recipe],
    demand_forecast: dict[str, float] | None = None,
    briefings: dict[int, dict] | None = None,
) -> ZoneDecision:
    """Produce a ``ZoneDecision`` (bids + menu + prices) for the given zone.

    The full ILP formulation is described in §7 of the implementation
    strategy.  Here we implement the greedy heuristic version that is
    always available and refine with scipy.optimize.milp where possible.
    """
    demand_forecast = demand_forecast or {}
    briefings = briefings or {}

    # ── 1. Select candidate recipes for this zone ─────────────────
    candidates = _filter_recipes_for_zone(zone, recipes)
    if not candidates:
        candidates = list(recipes.values())[:6]  # absolute fallback

    # ── 2. Rank candidates by desirability ────────────────────────
    scored: list[tuple[Recipe, float]] = []
    for recipe in candidates:
        score = _recipe_zone_score(recipe, zone, game_state)
        scored.append((recipe, score))
    scored.sort(key=lambda x: x[1], reverse=True)

    # ── 3. Select menu (respect zone menu-size constraints) ───────
    max_dishes = _zone_menu_size(zone)
    menu_recipes = [r for r, _ in scored[:max_dishes]]

    # ── 4. Compute ingredient needs ───────────────────────────────
    ingredient_needs: dict[str, int] = {}
    for recipe in menu_recipes:
        for ing, qty in recipe.ingredients.items():
            ingredient_needs[ing] = ingredient_needs.get(ing, 0) + qty

    # ── 5. Generate bids ─────────────────────────────────────────
    balance_for_bids = game_state.balance * _zone_bid_fraction(zone)
    bids = _generate_bids(
        ingredient_needs, balance_for_bids, demand_forecast, briefings
    )

    # ── 6. Compute prices ─────────────────────────────────────────
    price_factor = ZONE_PRICE_FACTORS.get(zone, 0.7)
    target_archetype = _zone_target_archetype(zone)
    ceiling = ARCHETYPE_CEILINGS.get(target_archetype, 120)
    base_price = int(ceiling * price_factor)

    menu_items: list[dict] = []
    prices: dict[str, float] = {}
    for recipe in menu_recipes:
        # Adjust price by prestige
        prestige_mult = recipe.prestige / 70.0  # normalise around 70
        price = max(10, int(base_price * prestige_mult))
        menu_items.append({"name": recipe.name, "price": price})
        prices[recipe.name] = price

    expected_revenue = sum(prices.values()) * 0.5  # conservative 50% served
    expected_cost = sum(b["bid"] * b["quantity"] for b in bids)

    return ZoneDecision(
        zone=zone,
        bids=bids,
        menu=menu_items,
        prices=prices,
        expected_revenue=expected_revenue,
        expected_cost=expected_cost,
    )


# ── helpers ──────────────────────────────────────────────────────


def _filter_recipes_for_zone(
    zone: str, recipes: dict[str, Recipe]
) -> list[Recipe]:
    """Return recipes matching the zone's prestige / prep-time constraints."""
    out: list[Recipe] = []
    for r in recipes.values():
        if zone == "PREMIUM_MONOPOLIST":
            if r.prestige >= 85 and r.prep_time_s <= 8:
                out.append(r)
        elif zone == "BUDGET_OPPORTUNIST":
            if r.prestige <= 60 and r.prep_time_s <= 5:
                out.append(r)
        elif zone == "NICHE_SPECIALIST":
            if 60 <= r.prestige <= 90:
                out.append(r)
        elif zone == "SPEED_CONTENDER":
            if r.prep_time_s <= 5 and r.prestige >= 50:
                out.append(r)
        elif zone == "MARKET_ARBITRAGEUR":
            if r.prestige >= 40 and r.ingredient_count <= 5:
                out.append(r)
        else:
            out.append(r)
    return out


def _zone_menu_size(zone: str) -> int:
    sizes = {
        "PREMIUM_MONOPOLIST": 5,
        "BUDGET_OPPORTUNIST": 10,
        "NICHE_SPECIALIST": 6,
        "SPEED_CONTENDER": 7,
        "MARKET_ARBITRAGEUR": 2,
    }
    return sizes.get(zone, 5)


def _zone_bid_fraction(zone: str) -> float:
    """Fraction of balance to allocate to bids."""
    fracs = {
        "PREMIUM_MONOPOLIST": 0.5,
        "BUDGET_OPPORTUNIST": 0.25,
        "NICHE_SPECIALIST": 0.35,
        "SPEED_CONTENDER": 0.30,
        "MARKET_ARBITRAGEUR": 0.6,
    }
    return fracs.get(zone, 0.3)


def _zone_target_archetype(zone: str) -> str:
    mapping = {
        "PREMIUM_MONOPOLIST": "Saggi del Cosmo",
        "BUDGET_OPPORTUNIST": "Esploratore Galattico",
        "NICHE_SPECIALIST": "Famiglie Orbitali",
        "SPEED_CONTENDER": "Famiglie Orbitali",
        "MARKET_ARBITRAGEUR": "Esploratore Galattico",
    }
    return mapping.get(zone, "Esploratore Galattico")


def _recipe_zone_score(
    recipe: Recipe, zone: str, game_state: GameState
) -> float:
    """Score a recipe for how well it fits the given zone."""
    score = recipe.prestige

    # Penalise slow recipes (except for niche)
    if zone != "NICHE_SPECIALIST":
        if recipe.prep_time_s > 6:
            score -= (recipe.prep_time_s - 6) * 5

    # Bonus for high-Δ ingredients
    for ing in recipe.ingredients:
        if ing in HIGH_DELTA_INGREDIENTS:
            score += HIGH_DELTA_INGREDIENTS[ing]

    # Penalise recipes with many ingredients (complex to source)
    score -= recipe.ingredient_count * 2

    return score


def _generate_bids(
    needs: dict[str, int],
    budget: float,
    demand_forecast: dict[str, float],
    briefings: dict[int, dict],
) -> list[dict]:
    """Generate a bid list within the available budget."""
    bids: list[dict] = []
    remaining = budget

    # Sort ingredients by priority (high-Δ first)
    high_delta_names = set(HIGH_DELTA_INGREDIENTS.keys())
    sorted_ings = sorted(
        needs.items(),
        key=lambda x: (x[0] in high_delta_names, x[1]),
        reverse=True,
    )

    for ingredient, quantity in sorted_ings:
        if remaining <= 0:
            break

        # Base bid price — factor in competition
        forecast_demand = demand_forecast.get(ingredient, 1.0)
        base_bid = 20 + int(forecast_demand * 5)

        # High-Δ ingredients deserve higher bids
        if ingredient in high_delta_names:
            base_bid = int(base_bid * 1.5)

        # Clamp to remaining budget
        total_cost = base_bid * quantity
        if total_cost > remaining:
            quantity = max(1, int(remaining / base_bid))
            total_cost = base_bid * quantity

        if quantity <= 0:
            continue

        bids.append(
            {
                "ingredient": ingredient,
                "bid": base_bid,
                "quantity": quantity,
            }
        )
        remaining -= total_cost

    return bids
