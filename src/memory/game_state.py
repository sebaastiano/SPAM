"""
Game state memory — tracks our restaurant state across turns.
"""

from __future__ import annotations

from typing import Any

from src.models import GameState


class GameStateMemory:
    """Per-turn snapshot of our restaurant's state.

    Maintains the current live state and a history of previous turns
    for trend analysis (balance trajectory, reputation growth, etc.).
    """

    def __init__(self) -> None:
        self.current = GameState()
        self.history: list[GameState] = []

    # ── Mutations ─────────────────────────────────────────────────

    def update_from_server(self, data: dict[str, Any]) -> None:
        """Update current state from GET /restaurant/17 response."""
        self.current.balance = data.get("balance", self.current.balance)
        self.current.inventory = data.get("inventory", self.current.inventory)
        self.current.reputation = data.get("reputation", self.current.reputation)
        self.current.is_open = data.get("isOpen", self.current.is_open)

        raw_menu = data.get("menu")
        if raw_menu:
            if isinstance(raw_menu, dict):
                items = raw_menu.get("items", [])
            elif isinstance(raw_menu, list):
                items = raw_menu
            else:
                items = []
            self.current.menu = [
                {"name": it.get("name"), "price": it.get("price")}
                for it in items
                if isinstance(it, dict)
            ]

    def set_phase(self, phase: str) -> None:
        self.current.phase = phase

    def set_turn(self, turn_id: int) -> None:
        self.current.turn_id = turn_id

    def record_serve(self, revenue: float) -> None:
        self.current.clients_served += 1
        self.current.total_clients_served += 1
        self.current.revenue_this_turn += revenue

    def end_turn_snapshot(self) -> None:
        """Archive current state and prepare for next turn."""
        import copy

        self.history.append(copy.deepcopy(self.current))
        # Inventory expires each turn
        self.current.inventory = {}
        self.current.clients_served = 0
        self.current.revenue_this_turn = 0.0

    # ── Queries ───────────────────────────────────────────────────

    def balance_trend(self, window: int = 5) -> list[float]:
        return [s.balance for s in self.history[-window:]]

    def reputation_trend(self, window: int = 5) -> list[float]:
        return [s.reputation for s in self.history[-window:]]

    def last_turn(self) -> GameState | None:
        return self.history[-1] if self.history else None

    # ── Reset ─────────────────────────────────────────────────────

    def reset(self) -> None:
        """Called on game_reset — wipe turn-scoped state, keep history for debug."""
        self.current = GameState()
