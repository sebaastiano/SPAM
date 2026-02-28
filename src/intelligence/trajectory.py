"""
Trajectory prediction — multi-level predictor using feature-space
momentum and observable-field extrapolation.
"""

from __future__ import annotations

import numpy as np

from src.models import CompetitorPrediction, CompetitorTurnState, Recipe


class AdvancedTrajectoryPredictor:
    """Multi-level trajectory predictor powered by tracker observables."""

    def __init__(
        self,
        recipe_db: dict[str, Recipe] | None = None,
        momentum_factor: float = 0.7,
    ) -> None:
        self.momentum_factor = momentum_factor
        self.recipe_db: dict[str, Recipe] = recipe_db or {}
        self.feature_history: dict[int, list[np.ndarray]] = {}
        self.state_history: dict[int, list[CompetitorTurnState]] = {}

    def set_recipe_db(self, recipes: dict[str, Recipe]) -> None:
        self.recipe_db = recipes

    # ── Public API ────────────────────────────────────────────────

    def update(
        self, rid: int, state: CompetitorTurnState, features: np.ndarray
    ) -> None:
        self.feature_history.setdefault(rid, []).append(features)
        self.state_history.setdefault(rid, []).append(state)

    def predict(self, rid: int) -> CompetitorPrediction:
        states = self.state_history.get(rid, [])
        features = self.feature_history.get(rid, [])
        if not states:
            return CompetitorPrediction(restaurant_id=rid)

        current = states[-1]
        return CompetitorPrediction(
            restaurant_id=rid,
            predicted_balance=self._predict_balance(states),
            predicted_bid_ingredients=self._predict_bid_targets(states),
            predicted_bid_spend=self._predict_bid_spend(states),
            predicted_menu_changes=self._predict_menu_changes(states),
            predicted_strategy=self._detect_strategy_trend(states),
            predicted_feature_vector=(
                self._predict_features(features) if features else np.zeros(14)
            ),
            threat_level=self._compute_threat(states),
            opportunity_level=self._compute_opportunity(states),
            vulnerable_ingredients=self._find_vulnerable(states),
            bid_denial_cost=self._estimate_denial_cost(states),
            menu_overlap=0.0,
        )

    # ── Aggregates ────────────────────────────────────────────────

    def get_ingredient_demand_forecast(self) -> dict[str, float]:
        """Predicted per-ingredient demand summed across all competitors."""
        demand: dict[str, float] = {}
        for rid, states in self.state_history.items():
            predicted = self._predict_bid_targets(states)
            for ing in predicted:
                recent_qty = 1.0
                for s in states[-2:]:
                    for b in s.bids:
                        if b.get("ingredient") == ing:
                            recent_qty = max(recent_qty, b.get("quantity", 1))
                demand[ing] = demand.get(ing, 0) + recent_qty
        return demand

    def generate_briefings(self) -> dict[int, dict]:
        """Per-competitor tactical briefing for decision & diplomacy."""
        briefings: dict[int, dict] = {}
        for rid, states in self.state_history.items():
            pred = self.predict(rid)
            cur = states[-1]
            briefings[rid] = {
                "name": cur.name,
                "strategy": pred.predicted_strategy,
                "threat_level": pred.threat_level,
                "opportunity_level": pred.opportunity_level,
                "balance": cur.balance,
                "balance_trend": "rising" if cur.balance_delta > 0 else "falling",
                "top_bid_ingredients": list(pred.predicted_bid_ingredients)[:5],
                "predicted_bid_spend": pred.predicted_bid_spend,
                "vulnerable_ingredients": pred.vulnerable_ingredients,
                "bid_denial_cost": pred.bid_denial_cost,
                "menu_price_avg": (
                    float(np.mean(list(cur.menu.values()))) if cur.menu else 0
                ),
                "menu_size": len(cur.menu),
                "reputation": cur.reputation,
                "recommended_action": self._recommend_action(pred, cur),
            }
        return briefings

    # ── Level 1: feature-space momentum ───────────────────────────

    def _predict_features(self, features: list[np.ndarray]) -> np.ndarray:
        if len(features) < 2:
            return features[-1]
        vel = features[-1] - features[-2]
        if len(features) >= 3:
            prev_vel = features[-2] - features[-3]
            vel = self.momentum_factor * vel + (1 - self.momentum_factor) * prev_vel
        return features[-1] + vel

    # ── Level 2: observable field prediction ──────────────────────

    def _predict_balance(self, states: list[CompetitorTurnState]) -> float:
        if len(states) < 2:
            return states[-1].balance
        deltas = [s.balance_delta for s in states[-5:]]
        weights = [0.5 ** (len(deltas) - 1 - i) for i in range(len(deltas))]
        return states[-1].balance + float(np.average(deltas, weights=weights))

    def _predict_bid_targets(
        self, states: list[CompetitorTurnState]
    ) -> set[str]:
        if not states:
            return set()
        freq: dict[str, int] = {}
        for s in states[-3:]:
            for ing in s.bid_ingredients:
                freq[ing] = freq.get(ing, 0) + 1
        consistent = {ing for ing, c in freq.items() if c >= 2}

        menu_needed: set[str] = set()
        for dish in states[-1].menu:
            recipe = self.recipe_db.get(dish)
            if recipe:
                for ing in recipe.ingredients:
                    if states[-1].inventory.get(ing, 0) == 0:
                        menu_needed.add(ing)
        return consistent | menu_needed

    def _predict_bid_spend(self, states: list[CompetitorTurnState]) -> float:
        if len(states) < 2:
            return states[-1].total_bid_spend
        spends = [s.total_bid_spend for s in states[-3:]]
        return float(np.mean(spends) * 1.05)

    def _predict_menu_changes(
        self, states: list[CompetitorTurnState]
    ) -> list[str]:
        if len(states) < 2:
            return []
        curr = set(states[-1].menu.keys())
        prev = set(states[-2].menu.keys())
        if states[-1].inferred_strategy == "REACTIVE_CHASER":
            return list(curr - prev)
        return []

    # ── Level 3: behavioural patterns ─────────────────────────────

    def _detect_strategy_trend(
        self, states: list[CompetitorTurnState]
    ) -> str:
        if len(states) < 3:
            return states[-1].inferred_strategy
        recent = [s.inferred_strategy for s in states[-3:]]
        if len(set(recent)) == 1:
            return recent[0]
        if recent[-1] != recent[-2]:
            return f"TRANSITIONING→{recent[-1]}"
        return recent[-1]

    def _compute_threat(self, states: list[CompetitorTurnState]) -> float:
        cur = states[-1]
        threat = 0.0
        if cur.balance > 7000:
            threat += 0.3
        elif cur.balance > 5000:
            threat += 0.15
        if cur.reputation > 90:
            threat += 0.2
        if cur.menu and len(cur.menu) >= 4:
            threat += 0.2
        return min(1.0, threat)

    def _compute_opportunity(
        self, states: list[CompetitorTurnState]
    ) -> float:
        cur = states[-1]
        opp = 0.0
        if len(states) >= 2 and cur.balance_delta < -200:
            opp += 0.3
        if cur.balance < 4000:
            opp += 0.2
        if cur.reputation < 80:
            opp += 0.2
        if cur.inferred_strategy == "REACTIVE_CHASER":
            opp += 0.3
        return min(1.0, opp)

    def _find_vulnerable(
        self, states: list[CompetitorTurnState]
    ) -> list[str]:
        bid_prices: dict[str, list[float]] = {}
        for s in states[-3:]:
            for b in s.bids:
                ing = b.get("ingredient", "")
                bid_prices.setdefault(ing, []).append(b.get("bid", 0))
        return [
            ing
            for ing, prices in bid_prices.items()
            if len(prices) >= 2 and float(np.mean(prices)) < 100
        ]

    def _estimate_denial_cost(
        self, states: list[CompetitorTurnState]
    ) -> float:
        vulnerable = self._find_vulnerable(states)
        cost = 0.0
        for b in states[-1].bids:
            if b.get("ingredient") in vulnerable:
                cost += (b.get("bid", 0) + 1) * b.get("quantity", 1)
        return cost

    @staticmethod
    def _recommend_action(
        pred: CompetitorPrediction, state: CompetitorTurnState
    ) -> str:
        if pred.threat_level > 0.7:
            if pred.bid_denial_cost < 200:
                return f"BID_DENY: {pred.vulnerable_ingredients[:2]}"
            return "ZONE_AVOID"
        if pred.opportunity_level > 0.6:
            if state.inferred_strategy == "REACTIVE_CHASER":
                return "DECEIVE"
            if state.inferred_strategy == "DECLINING":
                return "ALLIANCE"
        return "MONITOR"
