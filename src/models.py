"""
Core data models for the SPAM! agent.

All dataclasses and type definitions used across the system.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

import numpy as np


# ── Competitor Intelligence ──────────────────────────────────────


@dataclass
class CompetitorTurnState:
    """Complete reconstructed state of a competitor for one turn."""

    restaurant_id: int
    turn_id: int
    name: str

    # Direct observables (GET /restaurants)
    balance: float = 0.0
    balance_delta: float = 0.0
    inventory: dict[str, int] = field(default_factory=dict)
    menu: dict[str, float] = field(default_factory=dict)  # dish_name → price
    reputation: float = 100.0
    reputation_delta: float = 0.0
    is_open: bool = False
    kitchen_load: int = 0

    # Derived from bid_history
    bids: list[dict] = field(default_factory=list)
    total_bid_spend: float = 0.0
    bid_ingredients: set[str] = field(default_factory=set)
    bid_win_rate: float = 0.0
    avg_bid_price: float = 0.0

    # Derived from market/entries
    market_buys: list[dict] = field(default_factory=list)
    market_sells: list[dict] = field(default_factory=list)
    market_net_spend: float = 0.0

    # Derived from inventory diffs
    ingredients_consumed: dict[str, int] = field(default_factory=dict)
    ingredients_acquired: dict[str, int] = field(default_factory=dict)

    # Inferred
    inferred_recipes_cooked: list[str] = field(default_factory=list)
    inferred_revenue: float = 0.0
    inferred_clients_served: int = 0
    inferred_strategy: str = "UNCLASSIFIED"


@dataclass
class CompetitorPrediction:
    """Predicted state of a competitor for next turn."""

    restaurant_id: int
    predicted_balance: float = 0.0
    predicted_bid_ingredients: set[str] = field(default_factory=set)
    predicted_bid_spend: float = 0.0
    predicted_menu_changes: list[str] = field(default_factory=list)
    predicted_strategy: str = "UNCLASSIFIED"
    predicted_feature_vector: np.ndarray = field(
        default_factory=lambda: np.zeros(14)
    )
    threat_level: float = 0.0
    opportunity_level: float = 0.0

    # Actionable intelligence
    vulnerable_ingredients: list[str] = field(default_factory=list)
    bid_denial_cost: float = 0.0
    menu_overlap: float = 0.0


# ── Game State ───────────────────────────────────────────────────


@dataclass
class GameState:
    """Current state of our restaurant."""

    turn_id: int = 0
    phase: str = "stopped"
    balance: float = 7500.0
    inventory: dict[str, int] = field(default_factory=dict)
    reputation: float = 100.0
    menu: list[dict] = field(default_factory=list)  # [{name, price}]
    clients_served: int = 0
    revenue_this_turn: float = 0.0
    total_clients_served: int = 0
    is_open: bool = False


@dataclass
class ClientProfile:
    """Profile of a single client interaction."""

    archetype: str
    order_text: str
    matched_dish: str | None = None
    served: bool = False
    revenue: float = 0.0
    intolerance_triggered: bool = False
    prep_time_ms: int = 0
    turn_id: int = 0
    timestamp: str = ""
    client_id: str = ""


@dataclass
class ArchetypeStats:
    """Aggregate statistics for a client archetype."""

    total_served: int = 0
    total_failed: int = 0
    total_revenue: float = 0.0
    intolerance_count: int = 0
    common_intolerances: list[str] = field(default_factory=list)
    preferred_dishes: list[str] = field(default_factory=list)

    @property
    def avg_revenue_per_serve(self) -> float:
        return self.total_revenue / max(self.total_served, 1)

    @property
    def intolerance_rate(self) -> float:
        total = self.total_served + self.total_failed
        return self.intolerance_count / max(total, 1)

    def update(self, profile: ClientProfile) -> None:
        if profile.served:
            self.total_served += 1
            self.total_revenue += profile.revenue
        else:
            self.total_failed += 1
        if profile.intolerance_triggered:
            self.intolerance_count += 1
        if profile.matched_dish and profile.served:
            if profile.matched_dish not in self.preferred_dishes:
                self.preferred_dishes.append(profile.matched_dish)


# ── Decision Engine ──────────────────────────────────────────────


@dataclass
class ZoneDecision:
    """Output of zone-specific ILP solver."""

    zone: str
    bids: list[dict] = field(default_factory=list)  # [{ingredient, bid, quantity}]
    menu: list[dict] = field(default_factory=list)  # [{name, price}]
    prices: dict[str, float] = field(default_factory=dict)
    expected_revenue: float = 0.0
    expected_cost: float = 0.0


# ── Tracker ──────────────────────────────────────────────────────


@dataclass
class TrackerSnapshot:
    """Complete snapshot from tracker at a single point in time."""

    restaurants: dict[int, dict] = field(default_factory=dict)
    change_logs: dict[int, list] = field(default_factory=dict)
    bid_history: list[dict] = field(default_factory=list)
    market_entries: list[dict] = field(default_factory=list)
    own_meals: list[dict] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)


# ── Deception ────────────────────────────────────────────────────


@dataclass
class DeceptionAction:
    """A planned deception action against a competitor."""

    target_rid: int
    arm: str
    target_name: str = ""
    target_strategy: str = ""
    priority: float = 0.0
    desired_effect: str = ""
    message_hint: str = ""


# ── Recipe helpers ───────────────────────────────────────────────


@dataclass
class Recipe:
    """A recipe from the game server."""

    name: str
    preparation_time_ms: int
    ingredients: dict[str, int]  # ingredient_name → quantity
    prestige: float

    @property
    def prep_time_s(self) -> float:
        return self.preparation_time_ms / 1000.0

    @property
    def ingredient_count(self) -> int:
        return len(self.ingredients)
