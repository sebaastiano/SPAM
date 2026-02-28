"""
SPAM! — Phase Router
=====================
Phase state machine routing SSE game_phase_changed events
to phase-specific handlers.

Phase lifecycle:
  game_started → speaking → closed_bid → waiting → serving → stopped → (next turn)

Phase restrictions (CRITICAL):
  - speaking: intelligence pipeline, diplomacy, menu setting
  - closed_bid: bid submission ONLY here; save_menu still allowed
  - waiting: fetch post-bid inventory, finalize menu, open restaurant
  - serving: prepare_dish + serve_dish ONLY; save_menu FORBIDDEN; cannot reopen
  - stopped: ALL MCP tools forbidden; GET only; inventory expires
"""

import logging
from typing import Callable, Awaitable

logger = logging.getLogger("spam.phase_router")


class PhaseRouter:
    """
    Phase state machine.

    Routes game_phase_changed SSE events to the correct phase handler.
    Enforces phase restrictions and tracks the current game phase.
    """

    VALID_PHASES = {"speaking", "closed_bid", "waiting", "serving", "stopped"}
    VALID_TRANSITIONS = {
        None: {"speaking"},
        "speaking": {"closed_bid"},
        "closed_bid": {"waiting"},
        "waiting": {"serving"},
        "serving": {"stopped"},
        "stopped": {"speaking"},  # next turn
    }

    def __init__(self):
        self.current_phase: str | None = None
        self.current_turn: int = 0
        self._handlers: dict[str, Callable[[dict], Awaitable[None]]] = {}
        self._on_turn_change: Callable[[int], Awaitable[None]] | None = None

    def register(self, phase: str, handler: Callable[[dict], Awaitable[None]]):
        """Register a handler for a specific phase."""
        if phase not in self.VALID_PHASES:
            raise ValueError(f"Unknown phase: {phase}")
        self._handlers[phase] = handler

    def on_turn_change(self, handler: Callable[[int], Awaitable[None]]):
        """Register a callback for turn changes (stopped → speaking)."""
        self._on_turn_change = handler

    async def handle_phase_change(self, data: dict):
        """
        Called by event_bus on 'game_phase_changed' events.

        data format: {"phase": "serving", "turn_id": 3, ...}
        """
        new_phase = data.get("phase", "").lower()
        turn_id = data.get("turn_id", self.current_turn)

        if new_phase not in self.VALID_PHASES:
            logger.warning(f"Unknown phase received: {new_phase}")
            return

        # Detect turn change
        if new_phase == "speaking" and self.current_phase == "stopped":
            self.current_turn = turn_id
            logger.info(f"=== TURN {self.current_turn} STARTED ===")
            if self._on_turn_change:
                await self._on_turn_change(self.current_turn)

        old_phase = self.current_phase
        self.current_phase = new_phase
        self.current_turn = turn_id

        logger.info(f"Phase: {old_phase} → {new_phase} (turn {turn_id})")

        # Dispatch to phase handler
        handler = self._handlers.get(new_phase)
        if handler:
            try:
                await handler(data)
            except Exception as e:
                logger.error(f"Phase handler error ({new_phase}): {e}", exc_info=True)
        else:
            logger.warning(f"No handler registered for phase: {new_phase}")

    async def handle_game_started(self, data: dict):
        """Called on game_started SSE event."""
        self.current_phase = None
        self.current_turn = 0
        logger.info("Game started — awaiting first phase")

    async def handle_game_reset(self, data: dict):
        """
        Called on game_reset SSE event.
        Clear turn-scoped state, preserve cross-turn memory.
        Do NOT call any MCP tools — wait for next game_started.
        """
        logger.info("Game reset — clearing turn-scoped state")
        self.current_phase = None
        self.current_turn = 0

    # ── Phase guard methods ──

    def is_serving(self) -> bool:
        return self.current_phase == "serving"

    def is_bidding(self) -> bool:
        return self.current_phase == "closed_bid"

    def is_waiting(self) -> bool:
        return self.current_phase == "waiting"

    def can_set_menu(self) -> bool:
        """save_menu allowed in speaking, closed_bid, waiting — NOT serving/stopped."""
        return self.current_phase in {"speaking", "closed_bid", "waiting"}

    def can_send_message(self) -> bool:
        """send_message allowed in speaking, closed_bid, waiting, serving — NOT stopped."""
        return self.current_phase in {"speaking", "closed_bid", "waiting", "serving"}

    def can_prepare_dish(self) -> bool:
        """prepare_dish only in serving."""
        return self.current_phase == "serving"

    def can_serve_dish(self) -> bool:
        """serve_dish only in serving."""
        return self.current_phase == "serving"

    def can_open_restaurant(self) -> bool:
        """update_restaurant_is_open(true) only in waiting (NOT serving)."""
        return self.current_phase == "waiting"

    def can_close_restaurant(self) -> bool:
        """update_restaurant_is_open(false) in waiting or serving."""
        return self.current_phase in {"waiting", "serving"}

    def can_bid(self) -> bool:
        """closed_bid only in closed_bid phase."""
        return self.current_phase == "closed_bid"

    def can_use_market(self) -> bool:
        """Market ops in speaking, closed_bid, waiting, serving."""
        return self.current_phase in {"speaking", "closed_bid", "waiting", "serving"}
