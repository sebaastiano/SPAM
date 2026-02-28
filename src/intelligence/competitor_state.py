"""
CompetitorStateBuilder — constructs ``CompetitorTurnState`` from raw
tracker data (GET /restaurants, /bid_history, /market/entries, diffs).
"""

from __future__ import annotations

from typing import Any

from src.models import CompetitorTurnState, Recipe


class CompetitorStateBuilder:
    """Builds a ``CompetitorTurnState`` for each competitor from raw API data."""

    def __init__(self, recipe_db: dict[str, Recipe] | None = None) -> None:
        self.recipe_db: dict[str, Recipe] = recipe_db or {}
        self.history: dict[int, list[CompetitorTurnState]] = {}

    def set_recipe_db(self, recipes: dict[str, Recipe]) -> None:
        self.recipe_db = recipes

    def build(
        self,
        rid: int,
        turn_id: int,
        restaurant_data: dict[str, Any],
        bid_data: list[dict],
        market_data: list[dict],
    ) -> CompetitorTurnState:
        prev = self.history.get(rid, [None])[-1]  # type: ignore[arg-type]

        balance = restaurant_data.get("balance", 0.0)
        inventory = restaurant_data.get("inventory", {})
        reputation = restaurant_data.get("reputation", 100.0)

        prev_balance = prev.balance if prev else balance
        prev_reputation = prev.reputation if prev else reputation
        prev_inventory = prev.inventory if prev else {}

        # Inventory movement
        consumed, acquired = self._inventory_deltas(prev_inventory, inventory)

        # Infer recipes
        inferred_recipes = self._match_consumed(consumed)

        # Bid analysis
        team_bids = [b for b in bid_data if b.get("restaurant_id") == rid]
        won_bids = [b for b in team_bids if b.get("status") == "completed"]
        total_bid_spend = sum(
            b.get("bid", 0) * b.get("quantity", 0) for b in won_bids
        )

        # Market analysis
        buys = [
            e
            for e in market_data
            if e.get("side") == "BUY" and e.get("buyer_id") == rid
        ]
        sells = [
            e
            for e in market_data
            if e.get("side") == "SELL" and e.get("seller_id") == rid
        ]
        market_net = sum(
            e.get("price", 0) * e.get("quantity", 0) for e in buys
        ) - sum(e.get("price", 0) * e.get("quantity", 0) for e in sells)

        inferred_revenue = (balance - prev_balance) + total_bid_spend + market_net

        state = CompetitorTurnState(
            restaurant_id=rid,
            turn_id=turn_id,
            name=restaurant_data.get("name", f"team_{rid}"),
            balance=balance,
            balance_delta=balance - prev_balance,
            inventory=inventory,
            menu=self._extract_menu(restaurant_data),
            reputation=reputation,
            reputation_delta=reputation - prev_reputation,
            is_open=restaurant_data.get("isOpen", False),
            kitchen_load=self._kitchen_count(restaurant_data),
            bids=team_bids,
            total_bid_spend=total_bid_spend,
            bid_ingredients={b.get("ingredient", "") for b in team_bids},
            bid_win_rate=len(won_bids) / max(len(team_bids), 1),
            avg_bid_price=total_bid_spend
            / max(sum(b.get("quantity", 1) for b in won_bids), 1),
            market_buys=buys,
            market_sells=sells,
            market_net_spend=market_net,
            ingredients_consumed=consumed,
            ingredients_acquired=acquired,
            inferred_recipes_cooked=inferred_recipes,
            inferred_revenue=inferred_revenue,
            inferred_clients_served=max(0, int(inferred_revenue / 100)),
            inferred_strategy="UNCLASSIFIED",
        )

        self.history.setdefault(rid, []).append(state)
        return state

    # ── helpers ───────────────────────────────────────────────────

    @staticmethod
    def _inventory_deltas(
        prev: dict[str, int], curr: dict[str, int]
    ) -> tuple[dict[str, int], dict[str, int]]:
        consumed: dict[str, int] = {}
        acquired: dict[str, int] = {}
        all_keys = set(prev) | set(curr)
        for k in all_keys:
            old = prev.get(k, 0)
            new = curr.get(k, 0)
            if new < old:
                consumed[k] = old - new
            elif new > old:
                acquired[k] = new - old
        return consumed, acquired

    def _match_consumed(self, consumed: dict[str, int]) -> list[str]:
        """Greedy recipe matching against consumed ingredients."""
        candidates: list[str] = []
        remaining = dict(consumed)
        sorted_recipes = sorted(
            self.recipe_db.items(),
            key=lambda r: len(r[1].ingredients),
            reverse=True,
        )
        for name, recipe in sorted_recipes:
            if all(
                remaining.get(ing, 0) >= qty
                for ing, qty in recipe.ingredients.items()
            ):
                candidates.append(name)
                for ing, qty in recipe.ingredients.items():
                    remaining[ing] = remaining.get(ing, 0) - qty
        return candidates

    @staticmethod
    def _extract_menu(r: dict) -> dict[str, float]:
        raw = r.get("menu") or {}
        if isinstance(raw, dict):
            items = raw.get("items", [])
        elif isinstance(raw, list):
            items = raw
        else:
            items = []
        return {
            it.get("name"): it.get("price", 0)
            for it in items
            if isinstance(it, dict) and it.get("name")
        }

    @staticmethod
    def _kitchen_count(r: dict) -> int:
        k = r.get("kitchen") or []
        return len(k) if isinstance(k, (list, dict)) else 0
