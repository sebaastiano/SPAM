"""
SPAM! — Feature Extractor
===========================
Compute 14-dim behavioral feature vector from CompetitorTurnState.
Every feature maps to a concrete field from GET /restaurants,
GET /bid_history, or GET /market/entries.
"""

import logging

import numpy as np

from src.intelligence.competitor_state import CompetitorTurnState

logger = logging.getLogger("spam.intelligence.feature_extractor")

# Module-level recipe DB reference — set by IntelligencePipeline at init
_recipe_db: dict[str, dict] = {}


def set_recipe_db(recipe_db: dict[str, dict]):
    """Set the recipe DB reference used for feature extraction."""
    global _recipe_db
    _recipe_db = recipe_db


def extract_feature_vector(
    state: CompetitorTurnState,
    history: list[CompetitorTurnState],
    global_avg_price: float = 120.0,
) -> np.ndarray:
    """
    Compute 14-dim behavioral feature vector from tracker observables.

    Features:
     0: bid_aggressiveness (spend / balance)
     1: bid_concentration (Gini coefficient of bid quantities)
     2: bid_consistency (ingredient overlap with previous turn)
     3: bid_volume (number of distinct ingredients bid on)
     4: price_positioning (avg menu price / global avg)
     5: menu_stability (Jaccard similarity with previous menu)
     6: specialization_depth (1 / menu_size)
     7: market_activity ((buys + sells) / turn_count)
     8: buy_sell_ratio (buys / (sells + 1))
     9: balance_growth_rate (balance_delta)
    10: reputation_rate (reputation_delta)
    11: prestige_targeting (avg prestige of menu dishes / 100)
    12: recipe_complexity (avg ingredient count of menu dishes / 10)
    13: menu_size (raw)
    """
    # ── Auction behavior ──
    bid_aggressiveness = state.total_bid_spend / max(state.balance, 1)
    bid_quantities = [b.get("quantity", 0) for b in state.bids]
    bid_concentration = _gini(bid_quantities) if bid_quantities else 0.0
    bid_volume = len(state.bid_ingredients)

    bid_consistency = 0.0
    if len(history) >= 1 and history[-1].bid_ingredients:
        union = state.bid_ingredients | history[-1].bid_ingredients
        intersection = state.bid_ingredients & history[-1].bid_ingredients
        bid_consistency = len(intersection) / max(len(union), 1)

    # ── Menu behavior ──
    avg_price = float(np.mean(list(state.menu.values()))) if state.menu else 0
    price_positioning = avg_price / max(global_avg_price, 1)

    menu_stability = 1.0
    if len(history) >= 1:
        prev_dishes = set(history[-1].menu.keys())
        curr_dishes = set(state.menu.keys())
        union = prev_dishes | curr_dishes
        menu_stability = len(prev_dishes & curr_dishes) / max(len(union), 1)

    specialization_depth = 1.0 / max(len(state.menu), 1)

    # ── Market behavior ──
    total_turns = max(state.turn_id, 1)
    market_activity = (len(state.market_buys) + len(state.market_sells)) / total_turns
    buy_sell_ratio = len(state.market_buys) / max(len(state.market_sells) + 1, 1)

    # ── Outcome signals ──
    balance_growth_rate = state.balance_delta
    reputation_rate = state.reputation_delta

    # ── Prestige targeting & recipe complexity (from recipe DB) ──
    prestige_targeting = 0.0
    recipe_complexity = 0.0

    if state.menu and _recipe_db:
        prestiges = []
        complexities = []
        for dish_name in state.menu:
            recipe = _recipe_db.get(dish_name)
            if recipe:
                prestiges.append(recipe.get("prestige", 50))
                complexities.append(len(recipe.get("ingredients", {})))
        if prestiges:
            prestige_targeting = float(np.mean(prestiges)) / 100.0
        if complexities:
            recipe_complexity = float(np.mean(complexities)) / 10.0

    return np.array([
        bid_aggressiveness,
        bid_concentration,
        bid_consistency,
        bid_volume,
        price_positioning,
        menu_stability,
        specialization_depth,
        market_activity,
        buy_sell_ratio,
        balance_growth_rate,
        reputation_rate,
        prestige_targeting,
        recipe_complexity,
        len(state.menu),
    ])


def _gini(values: list[float]) -> float:
    """Gini coefficient — 0=equal, 1=concentrated."""
    if not values or sum(values) == 0:
        return 0.0
    sorted_v = sorted(values)
    n = len(sorted_v)
    numerator = sum((2 * i - n - 1) * v for i, v in enumerate(sorted_v, 1))
    return numerator / (n * sum(sorted_v))
