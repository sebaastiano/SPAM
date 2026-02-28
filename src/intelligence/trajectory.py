"""
SPAM! — Advanced Trajectory Predictor
========================================
Multi-level trajectory prediction powered by tracker observables.

Level 1: Feature-space trajectory (embedding momentum)
Level 2: Observable-field prediction (concrete balance/inventory/bid forecasts)
Level 3: Behavioral pattern detection (strategy switches)
"""

import logging
from dataclasses import dataclass, field

import numpy as np

from src.intelligence.competitor_state import CompetitorTurnState

logger = logging.getLogger("spam.intelligence.trajectory")


@dataclass
class CompetitorPrediction:
    """Predicted state of a competitor for next turn."""
    restaurant_id: int = 0
    predicted_balance: float = 0.0
    predicted_bid_ingredients: set = field(default_factory=set)
    predicted_bid_spend: float = 0.0
    predicted_menu_changes: list = field(default_factory=list)
    predicted_strategy: str = "UNCLASSIFIED"
    predicted_feature_vector: np.ndarray = field(default_factory=lambda: np.zeros(14))
    threat_level: float = 0.0
    opportunity_level: float = 0.0
    vulnerable_ingredients: list = field(default_factory=list)
    bid_denial_cost: float = 0.0
    menu_overlap: float = 0.0


class AdvancedTrajectoryPredictor:
    """
    Multi-level trajectory prediction.

    Level 1: Feature-space momentum (where in strategic space)
    Level 2: Observable-field prediction (balance, bids, menu)
    Level 3: Behavioral pattern detection (strategy switches)
    """

    def __init__(self, recipe_db: dict = None, momentum_factor: float = 0.7):
        self.momentum_factor = momentum_factor
        self.recipe_db = recipe_db or {}
        self.feature_history: dict[int, list[np.ndarray]] = {}
        self.state_history: dict[int, list[CompetitorTurnState]] = {}

    def update(self, rid: int, state: CompetitorTurnState, features: np.ndarray):
        self.feature_history.setdefault(rid, []).append(features.copy())
        self.state_history.setdefault(rid, []).append(state)

    def predict(self, rid: int) -> CompetitorPrediction:
        states = self.state_history.get(rid, [])
        features = self.feature_history.get(rid, [])
        if not states:
            return CompetitorPrediction(restaurant_id=rid)

        current = states[-1]

        # Level 1: Feature-space momentum
        predicted_features = self._predict_features(features)

        # Level 2: Observable field predictions
        predicted_balance = self._predict_balance(states)
        predicted_bids = self._predict_bid_targets(states)
        predicted_bid_spend = self._predict_bid_spend(states)
        predicted_menu = self._predict_menu_changes(states)

        # Level 3: Behavioral pattern detection
        strategy = self._detect_strategy_trend(states)
        threat = self._compute_threat_level(states, predicted_bids)
        opportunity = self._compute_opportunity_level(states)

        # Actionable intelligence
        vulnerable = self._find_vulnerable_ingredients(states)
        denial_cost = self._estimate_denial_cost(states, vulnerable)

        return CompetitorPrediction(
            restaurant_id=rid,
            predicted_balance=predicted_balance,
            predicted_bid_ingredients=predicted_bids,
            predicted_bid_spend=predicted_bid_spend,
            predicted_menu_changes=predicted_menu,
            predicted_strategy=strategy,
            predicted_feature_vector=predicted_features,
            threat_level=threat,
            opportunity_level=opportunity,
            vulnerable_ingredients=vulnerable,
            bid_denial_cost=denial_cost,
        )

    # ── Level 1: Feature-space momentum ──

    def _predict_features(self, features: list[np.ndarray]) -> np.ndarray:
        if len(features) < 2:
            return features[-1] if features else np.zeros(14)
        velocity = features[-1] - features[-2]
        if len(features) >= 3:
            prev_v = features[-2] - features[-3]
            velocity = self.momentum_factor * velocity + (1 - self.momentum_factor) * prev_v
        return features[-1] + velocity

    # ── Level 2: Observable field predictions ──

    def _predict_balance(self, states: list[CompetitorTurnState]) -> float:
        if len(states) < 2:
            return states[-1].balance
        deltas = [s.balance_delta for s in states[-5:]]
        weights = [0.5 ** (len(deltas) - 1 - i) for i in range(len(deltas))]
        predicted_delta = np.average(deltas, weights=weights)
        return states[-1].balance + predicted_delta

    def _predict_bid_targets(self, states: list[CompetitorTurnState]) -> set[str]:
        if not states:
            return set()

        # Frequency: bid on in last 3 turns
        recent_bids: dict[str, int] = {}
        for s in states[-3:]:
            for ing in s.bid_ingredients:
                recent_bids[ing] = recent_bids.get(ing, 0) + 1

        # Consistent: bid on 2+ of last 3 turns
        consistent = {ing for ing, count in recent_bids.items() if count >= 2}

        # Menu-driven: ingredients needed for current menu
        menu_needed = set()
        for dish_name in states[-1].menu:
            recipe = self.recipe_db.get(dish_name, {})
            for ing in recipe.get("ingredients", {}):
                if states[-1].inventory.get(ing, 0) == 0:
                    menu_needed.add(ing)

        return consistent | menu_needed

    def _predict_bid_spend(self, states: list[CompetitorTurnState]) -> float:
        if len(states) < 2:
            return states[-1].total_bid_spend
        spends = [s.total_bid_spend for s in states[-3:]]
        return float(np.mean(spends) * 1.05)

    def _predict_menu_changes(self, states: list[CompetitorTurnState]) -> list[str]:
        if len(states) < 2:
            return []
        curr = set(states[-1].menu.keys())
        prev = set(states[-2].menu.keys())
        if states[-1].inferred_strategy == "REACTIVE_CHASER":
            return list(curr - prev)
        return []

    # ── Level 3: Behavioral pattern detection ──

    def _detect_strategy_trend(self, states: list[CompetitorTurnState]) -> str:
        if len(states) < 3:
            return states[-1].inferred_strategy

        recent = [s.inferred_strategy for s in states[-3:]]
        if len(set(recent)) == 1:
            return recent[0]
        if recent[-1] != recent[-2]:
            return f"TRANSITIONING→{recent[-1]}"
        return recent[-1]

    def _compute_threat_level(
        self, states: list[CompetitorTurnState], predicted_bids: set[str]
    ) -> float:
        current = states[-1]
        threat = 0.0

        # Balance advantage
        if current.balance > 7000:
            threat += 0.2
        elif current.balance > 5000:
            threat += 0.1

        # Bid competition
        threat += 0.3 if len(predicted_bids) > 5 else 0.1

        # Reputation
        if current.reputation > 90:
            threat += 0.1

        # Menu overlap (placeholder)
        threat += 0.1

        return min(1.0, threat)

    def _compute_opportunity_level(self, states: list[CompetitorTurnState]) -> float:
        current = states[-1]
        opportunity = 0.0

        if len(states) >= 2 and states[-1].balance_delta < -200:
            opportunity += 0.3
        if current.balance < 4000:
            opportunity += 0.2
        if current.reputation < 80:
            opportunity += 0.2
        if current.inferred_strategy == "REACTIVE_CHASER":
            opportunity += 0.3

        return min(1.0, opportunity)

    def _find_vulnerable_ingredients(self, states: list[CompetitorTurnState]) -> list[str]:
        if not states:
            return []
        ingredient_bids: dict[str, list[float]] = {}
        for s in states[-3:]:
            for b in s.bids:
                ing = b.get("ingredient", "")
                ingredient_bids.setdefault(ing, []).append(b.get("bid", 0))

        return [
            ing
            for ing, prices in ingredient_bids.items()
            if len(prices) >= 2 and np.mean(prices) < 100
        ]

    def _estimate_denial_cost(
        self, states: list[CompetitorTurnState], vulnerable: list[str]
    ) -> float:
        total = 0.0
        if states:
            for b in states[-1].bids:
                if b.get("ingredient") in vulnerable:
                    total += (b.get("bid", 0) + 1) * b.get("quantity", 1)
        return total

    # ── Aggregate methods ──

    def competitors_approaching_zone(
        self, zone_center: np.ndarray, threshold: float
    ) -> list[int]:
        approaching = []
        for rid, features in self.feature_history.items():
            if len(features) < 2:
                continue
            predicted = self._predict_features(features)
            current_dist = np.linalg.norm(features[-1] - zone_center)
            predicted_dist = np.linalg.norm(predicted - zone_center)
            if predicted_dist < current_dist and predicted_dist < threshold:
                approaching.append(rid)
        return approaching

    def get_ingredient_demand_forecast(self) -> dict[str, float]:
        """Predict aggregate demand for each ingredient next turn."""
        demand: dict[str, float] = {}
        for rid in self.state_history:
            predicted_bids = self._predict_bid_targets(self.state_history[rid])
            for ing in predicted_bids:
                recent_qty = 0
                for s in self.state_history[rid][-2:]:
                    for b in s.bids:
                        if b.get("ingredient") == ing:
                            recent_qty = max(recent_qty, b.get("quantity", 1))
                demand[ing] = demand.get(ing, 0) + max(recent_qty, 1)
        return demand

    def generate_per_competitor_briefing(self) -> dict[int, dict]:
        """Generate a tactical briefing for each competitor."""
        briefings = {}
        for rid in self.state_history:
            prediction = self.predict(rid)
            states = self.state_history[rid]
            current = states[-1]

            briefings[rid] = {
                "name": current.name,
                "strategy": prediction.predicted_strategy,
                "threat_level": prediction.threat_level,
                "opportunity_level": prediction.opportunity_level,
                "balance": current.balance,
                "balance_trend": "rising" if current.balance_delta > 0 else "falling",
                "top_bid_ingredients": list(prediction.predicted_bid_ingredients)[:5],
                "predicted_bid_spend": prediction.predicted_bid_spend,
                "vulnerable_ingredients": prediction.vulnerable_ingredients,
                "bid_denial_cost": prediction.bid_denial_cost,
                "menu_price_avg": (
                    float(np.mean(list(current.menu.values())))
                    if current.menu
                    else 0
                ),
                "menu_size": len(current.menu),
                "reputation": current.reputation,
                "recommended_action": self._recommend_action(prediction, current),
                # Connection-based activity: if present in /restaurants, they're
                # connected to the server and likely competing.  This is MORE
                # reliable than menu_size (which is 0 during speaking phase).
                "is_connected": True,
            }
        return briefings

    def _recommend_action(
        self, prediction: CompetitorPrediction, state: CompetitorTurnState
    ) -> str:
        if prediction.threat_level > 0.7:
            if prediction.bid_denial_cost < 200:
                return (
                    f"BID_DENY: outbid on "
                    f"{prediction.vulnerable_ingredients[:2]} "
                    f"(cost≈{prediction.bid_denial_cost:.0f})"
                )
            return "ZONE_AVOID: too expensive to deny, consider zone switch"
        if prediction.opportunity_level > 0.6:
            if state.inferred_strategy == "REACTIVE_CHASER":
                return "DECEIVE: send misleading menu/ingredient signal"
            if state.inferred_strategy == "DECLINING":
                return "ALLIANCE: offer cheap ingredient trade"
        return "MONITOR: no immediate action needed"
