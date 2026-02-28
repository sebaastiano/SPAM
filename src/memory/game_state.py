"""
SPAM! — Game State Memory
==========================
Structured state memory tracking our restaurant's state across turns.
Extends datapizza Memory with typed state snapshots.
"""

import logging
from dataclasses import dataclass, field

logger = logging.getLogger("spam.memory.game_state")


@dataclass
class RestaurantState:
    """Snapshot of our restaurant state at a point in time."""
    turn_id: int = 0
    phase: str = ""
    balance: float = 10000.0
    inventory: dict = field(default_factory=dict)
    reputation: float = 100.0
    menu: list = field(default_factory=list)
    is_open: bool = False
    clients_served: int = 0
    revenue_this_turn: float = 0.0
    total_revenue: float = 0.0
    total_clients_served: int = 0


class GameStateMemory:
    """
    Structured game state memory with history and diffing.

    Stores per-turn snapshots for trend analysis and
    provides context injection for LLM agents.
    """

    def __init__(self):
        self.current = RestaurantState()
        self.history: list[RestaurantState] = []
        self.active_zone: str = "SPEED_CONTENDER"

    def update(self, **kwargs):
        """Update current state fields."""
        for key, value in kwargs.items():
            if hasattr(self.current, key):
                setattr(self.current, key, value)

    def snapshot(self, state=None):
        """Save current state as a historical snapshot.
        
        If *state* is provided it replaces ``self.current`` before snapshotting.
        """
        import copy
        if state is not None:
            self.current = state
        self.history.append(copy.deepcopy(self.current))

    def end_turn(self):
        """
        End-of-turn processing.
        
        CRITICAL: ALL inventory expires at end of turn.
        Record snapshot then zero out inventory.
        """
        self.snapshot()
        self.current.inventory = {}
        self.current.clients_served = 0
        self.current.revenue_this_turn = 0.0
        self.current.is_open = False
        logger.info(f"Turn {self.current.turn_id} ended — inventory expired")

    def new_turn(self, turn_id: int):
        """Start a new turn."""
        self.current.turn_id = turn_id
        self.current.inventory = {}  # inventory was zeroed
        logger.info(f"Turn {turn_id} started")

    def state_diff(self, n_turns_back: int = 1) -> dict:
        """What changed in the last N turns?"""
        if len(self.history) < n_turns_back + 1:
            return {}

        old = self.history[-(n_turns_back + 1)]
        new = self.history[-1]
        diff = {}

        for field_name in ["balance", "reputation", "inventory", "menu", "is_open"]:
            old_val = getattr(old, field_name)
            new_val = getattr(new, field_name)
            if old_val != new_val:
                diff[field_name] = {"old": old_val, "new": new_val}

        return diff

    def balance_trend(self, window: int = 5) -> list[float]:
        """Get balance values over the last N turns."""
        return [s.balance for s in self.history[-window:]]

    def reputation_trend(self, window: int = 5) -> list[float]:
        """Get reputation values over the last N turns."""
        return [s.reputation for s in self.history[-window:]]

    def build_llm_context(self) -> str:
        """Build a concise context string for LLM agents."""
        s = self.current
        lines = [
            f"[GAME STATE] Turn {s.turn_id} | Phase: {s.phase}",
            f"Balance: {s.balance:.0f} | Reputation: {s.reputation:.1f}",
            f"Active Zone: {self.active_zone}",
            f"Inventory: {s.inventory}",
            f"Menu items: {len(s.menu)}",
            f"Clients served (total): {s.total_clients_served}",
        ]
        if len(self.history) >= 2:
            prev = self.history[-1]
            lines.append(
                f"Last turn: balance Δ={s.balance - prev.balance:+.0f}, "
                f"reputation Δ={s.reputation - prev.reputation:+.1f}"
            )
        return "\n".join(lines)

    def reset(self):
        """Full reset (game_reset event)."""
        self.current = RestaurantState()
        # Preserve history for debugging
        logger.info("GameStateMemory reset")
