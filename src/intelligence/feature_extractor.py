"""
Feature extractor — computes 14-dim behavioral vector from
``CompetitorTurnState``.
"""

from __future__ import annotations

import numpy as np

from src.models import CompetitorTurnState


def _gini(values: list[float]) -> float:
    """Gini coefficient (0 = equal, 1 = concentrated)."""
    if not values or sum(values) == 0:
        return 0.0
    sorted_v = sorted(values)
    n = len(sorted_v)
    numerator = sum((2 * i - n - 1) * v for i, v in enumerate(sorted_v, 1))
    return float(numerator / (n * sum(sorted_v)))


def extract_feature_vector(
    state: CompetitorTurnState,
    history: list[CompetitorTurnState],
    global_avg_price: float = 120.0,
) -> np.ndarray:
    """Compute 14-dim behavioral feature vector from tracker observables."""

    # ── Auction ──────────────────────────────────────────────────
    bid_aggressiveness = state.total_bid_spend / max(state.balance, 1)
    bid_concentration = (
        _gini([b.get("quantity", 0) for b in state.bids])
        if state.bids
        else 0.0
    )
    bid_consistency = 0.0
    if len(history) >= 1 and history[-1].bid_ingredients:
        union = state.bid_ingredients | history[-1].bid_ingredients
        inter = state.bid_ingredients & history[-1].bid_ingredients
        bid_consistency = len(inter) / max(len(union), 1)
    bid_volume = float(len(state.bid_ingredients))

    # ── Menu ─────────────────────────────────────────────────────
    avg_price = float(np.mean(list(state.menu.values()))) if state.menu else 0.0
    price_positioning = avg_price / max(global_avg_price, 1)

    menu_stability = 1.0
    if history:
        prev_dishes = set(history[-1].menu.keys())
        curr_dishes = set(state.menu.keys())
        union_d = prev_dishes | curr_dishes
        menu_stability = len(prev_dishes & curr_dishes) / max(len(union_d), 1)

    specialization_depth = 1.0 / max(len(state.menu), 1)

    # ── Market ───────────────────────────────────────────────────
    total_turns = max(state.turn_id, 1)
    market_activity = (
        (len(state.market_buys) + len(state.market_sells)) / total_turns
    )
    buy_sell_ratio = len(state.market_buys) / max(
        len(state.market_sells) + 1, 1
    )

    # ── Outcome signals ──────────────────────────────────────────
    balance_growth = state.balance_delta
    reputation_rate = state.reputation_delta

    # ── Prestige / complexity (placeholder — filled when recipe DB loaded)
    prestige_targeting = 0.0
    recipe_complexity = 0.0

    return np.array(
        [
            bid_aggressiveness,
            bid_concentration,
            bid_consistency,
            bid_volume,
            price_positioning,
            menu_stability,
            specialization_depth,
            market_activity,
            buy_sell_ratio,
            balance_growth,
            reputation_rate,
            prestige_targeting,
            recipe_complexity,
            float(len(state.menu)),
        ]
    )
