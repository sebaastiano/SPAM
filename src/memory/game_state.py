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
    # P&L tracking
    bid_cost_this_turn: float = 0.0
    market_cost_this_turn: float = 0.0
    market_income_this_turn: float = 0.0
    net_profit_this_turn: float = 0.0
    menu_size_this_turn: int = 0
    zone_this_turn: str = ""


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

    def end_turn(self, turn_id: int | None = None):
        """
        End-of-turn processing.
        
        CRITICAL: ALL inventory expires at end of turn.
        Record snapshot then zero out inventory.
        """
        if turn_id is not None:
            self.current.turn_id = turn_id
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

    def get_pnl_history(self, window: int = 10) -> list[dict]:
        """Get per-turn P&L data for the last N turns.

        Returns list of dicts with keys:
          turn_id, balance, balance_delta, bid_cost, revenue,
          net_profit, clients_served, menu_size, zone, reputation
        """
        snaps = self.history[-window:]
        pnl = []
        for i, s in enumerate(snaps):
            prev_balance = snaps[i - 1].balance if i > 0 else s.balance
            balance_delta = s.balance - prev_balance
            pnl.append({
                "turn_id": s.turn_id,
                "balance": s.balance,
                "balance_delta": balance_delta,
                "bid_cost": s.bid_cost_this_turn,
                "market_cost": s.market_cost_this_turn,
                "market_income": s.market_income_this_turn,
                "revenue": s.revenue_this_turn,
                "net_profit": s.net_profit_this_turn,
                "clients_served": s.clients_served,
                "menu_size": s.menu_size_this_turn,
                "zone": s.zone_this_turn,
                "reputation": s.reputation,
            })
        return pnl

    def get_avg_revenue_per_client(self, window: int = 5) -> float:
        """Average revenue earned per client served (last N turns)."""
        snaps = self.history[-window:]
        total_rev = sum(s.revenue_this_turn for s in snaps)
        total_clients = sum(s.clients_served for s in snaps)
        return total_rev / max(total_clients, 1)

    def get_avg_profit_per_turn(self, window: int = 5) -> float:
        """Average net profit per turn (revenue - costs)."""
        pnl = self.get_pnl_history(window)
        if not pnl:
            return 0.0
        return sum(p["balance_delta"] for p in pnl) / len(pnl)

    def get_spending_efficiency(self, window: int = 5) -> float:
        """Ratio of revenue / total spending (bids + market). >1.0 = profitable."""
        pnl = self.get_pnl_history(window)
        total_spend = sum(p["bid_cost"] + p["market_cost"] for p in pnl)
        total_rev = sum(p["balance_delta"] + p["bid_cost"] + p["market_cost"] for p in pnl)
        return total_rev / max(total_spend, 1)

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
        # P&L summary
        pnl = self.get_pnl_history(5)
        if pnl:
            avg_profit = self.get_avg_profit_per_turn(5)
            efficiency = self.get_spending_efficiency(5)
            lines.append(
                f"Avg profit/turn (last 5): {avg_profit:+.0f} | "
                f"Spending efficiency: {efficiency:.2f}x"
            )
        return "\n".join(lines)

    def reset(self):
        """Full reset (game_reset event)."""
        self.current = RestaurantState()
        # Preserve history for debugging
        logger.info("GameStateMemory reset")
