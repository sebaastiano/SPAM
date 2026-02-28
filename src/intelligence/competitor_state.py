"""
SPAM! — Competitor State Builder
==================================
Builds CompetitorTurnState from tracker observables.
"""

import logging
from dataclasses import dataclass, field

logger = logging.getLogger("spam.intelligence.competitor_state")


@dataclass
class CompetitorTurnState:
    """Complete reconstructed state of a competitor for one turn."""
    restaurant_id: int = 0
    turn_id: int = 0
    name: str = ""

    # Direct observables (from GET /restaurants)
    balance: float = 0.0
    balance_delta: float = 0.0
    inventory: dict = field(default_factory=dict)
    menu: dict = field(default_factory=dict)  # dish_name → price
    reputation: float = 100.0
    reputation_delta: float = 0.0
    is_open: bool = False
    kitchen_load: int = 0

    # Derived from bid_history
    bids: list = field(default_factory=list)
    total_bid_spend: float = 0.0
    bid_ingredients: set = field(default_factory=set)
    bid_win_rate: float = 0.0
    avg_bid_price: float = 0.0

    # Derived from market/entries
    market_buys: list = field(default_factory=list)
    market_sells: list = field(default_factory=list)
    market_net_spend: float = 0.0

    # Derived from inventory diffs
    ingredients_consumed: dict = field(default_factory=dict)
    ingredients_acquired: dict = field(default_factory=dict)

    # Inferred
    inferred_recipes_cooked: list = field(default_factory=list)
    inferred_revenue: float = 0.0
    inferred_clients_served: int = 0
    inferred_strategy: str = "unclassified"


class CompetitorStateBuilder:
    """
    Builds CompetitorTurnState from tracker observables.

    Data sources:
     - GET /restaurants (via tracker polling)
     - GET /bid_history (post-auction)
     - GET /market/entries (real-time)
     - Tracker diff log (intra-turn changes)
    """

    def __init__(self, recipe_db: dict[str, dict] | None = None):
        self.recipe_db = recipe_db or {}
        self.history: dict[int, list[CompetitorTurnState]] = {}  # rid → turns

    def build_turn_state(
        self,
        rid: int,
        turn_id: int,
        restaurant_data: dict,
        bid_data: list[dict],
        market_data: list[dict],
        prev_state: CompetitorTurnState | None = None,
    ) -> CompetitorTurnState:
        """Build a complete CompetitorTurnState from raw data."""

        balance = restaurant_data.get("balance", 0)
        inventory = restaurant_data.get("inventory", {})
        if isinstance(inventory, list):
            inventory = {}
        reputation = restaurant_data.get("reputation", 100)

        prev_balance = prev_state.balance if prev_state else balance
        prev_reputation = prev_state.reputation if prev_state else reputation
        prev_inventory = prev_state.inventory if prev_state else {}

        # Reconstruct inventory movements
        ingredients_consumed = {}
        ingredients_acquired = {}
        for ing, old_qty in prev_inventory.items():
            new_qty = inventory.get(ing, 0)
            if new_qty < old_qty:
                ingredients_consumed[ing] = old_qty - new_qty
            elif new_qty > old_qty:
                ingredients_acquired[ing] = new_qty - old_qty
        for ing, new_qty in inventory.items():
            if ing not in prev_inventory and new_qty > 0:
                ingredients_acquired[ing] = new_qty

        # Infer recipes cooked
        inferred_recipes = self._match_consumed_to_recipes(ingredients_consumed)

        # Bid analysis
        team_bids = [b for b in bid_data if b.get("restaurant_id") == rid]
        won_bids = [b for b in team_bids if b.get("status") == "completed"]
        total_bid_spend = sum(
            b.get("bid", 0) * b.get("quantity", 0) for b in won_bids
        )

        # Market analysis
        team_buys = [
            e for e in market_data
            if e.get("side") == "BUY" and e.get("buyer_id") == rid
        ]
        team_sells = [
            e for e in market_data
            if e.get("side") == "SELL" and e.get("seller_id") == rid
        ]
        market_net = (
            sum(e.get("price", 0) * e.get("quantity", 0) for e in team_buys)
            - sum(e.get("price", 0) * e.get("quantity", 0) for e in team_sells)
        )

        # Revenue inference
        inferred_revenue = (balance - prev_balance) + total_bid_spend + market_net

        state = CompetitorTurnState(
            restaurant_id=rid,
            turn_id=turn_id,
            name=restaurant_data.get("name", f"team {rid}"),
            balance=balance,
            balance_delta=balance - prev_balance,
            inventory=inventory,
            menu=self._extract_menu(restaurant_data),
            reputation=reputation,
            reputation_delta=reputation - prev_reputation,
            is_open=restaurant_data.get("isOpen", False),
            kitchen_load=self._extract_kitchen_count(restaurant_data),
            bids=team_bids,
            total_bid_spend=total_bid_spend,
            bid_ingredients=set(b.get("ingredient", "") for b in team_bids),
            bid_win_rate=len(won_bids) / max(len(team_bids), 1),
            avg_bid_price=total_bid_spend / max(
                sum(b.get("quantity", 0) for b in won_bids), 1
            ),
            market_buys=team_buys,
            market_sells=team_sells,
            market_net_spend=market_net,
            ingredients_consumed=ingredients_consumed,
            ingredients_acquired=ingredients_acquired,
            inferred_recipes_cooked=inferred_recipes,
            inferred_revenue=inferred_revenue,
            inferred_clients_served=max(0, int(inferred_revenue / 100)),
            inferred_strategy="unclassified",
        )

        self.history.setdefault(rid, []).append(state)
        return state

    def get_prev_state(self, rid: int) -> CompetitorTurnState | None:
        history = self.history.get(rid, [])
        return history[-1] if history else None

    def _match_consumed_to_recipes(self, consumed: dict[str, int]) -> list[str]:
        """Match consumed ingredients to possible recipes (greedy)."""
        if not consumed or not self.recipe_db:
            return []

        candidates = []
        remaining = dict(consumed)

        sorted_recipes = sorted(
            self.recipe_db.items(),
            key=lambda r: len(r[1].get("ingredients", {})),
            reverse=True,
        )

        for recipe_name, recipe in sorted_recipes:
            ingredients = recipe.get("ingredients", {})
            if all(
                remaining.get(ing, 0) >= qty for ing, qty in ingredients.items()
            ):
                candidates.append(recipe_name)
                for ing, qty in ingredients.items():
                    remaining[ing] = remaining.get(ing, 0) - qty

        return candidates

    def _extract_menu(self, r: dict) -> dict[str, float]:
        raw_menu = r.get("menu") or {}
        if isinstance(raw_menu, dict):
            items = raw_menu.get("items") or []
        elif isinstance(raw_menu, list):
            items = raw_menu
        else:
            items = []
        return {
            item.get("name", ""): item.get("price", 0)
            for item in items
            if isinstance(item, dict)
        }

    def _extract_kitchen_count(self, r: dict) -> int:
        k = r.get("kitchen") or []
        return len(k) if isinstance(k, (list, dict)) else 0
