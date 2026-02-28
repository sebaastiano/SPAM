"""
Pricing logic — computes per-dish menu prices.
"""

from __future__ import annotations

from src.config import ARCHETYPE_CEILINGS, ZONE_PRICE_FACTORS
from src.models import GameState


def compute_menu_price(
    dish_prestige: float,
    zone: str,
    game_state: GameState,
    target_archetype: str = "Famiglie Orbitali",
) -> int:
    """Compute a single menu item's price.

    Price = ceiling × reputation_mult × zone_factor, clamped.
    """
    ceiling = ARCHETYPE_CEILINGS.get(target_archetype, 120)
    rep_mult = 1.0 + (game_state.reputation - 50) / 200
    zone_factor = ZONE_PRICE_FACTORS.get(zone, 0.7)
    prestige_mult = dish_prestige / 70.0

    price = int(ceiling * rep_mult * zone_factor * prestige_mult)
    return max(10, min(price, ceiling))  # clamp to [10, ceiling]
