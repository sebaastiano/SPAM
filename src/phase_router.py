"""
PhaseRouter — state machine that enforces phase-specific operation
restrictions and routes phase transitions to the appropriate handlers.

Phases (in order):
    game_started → speaking → closed_bid → waiting → serving → stopped → (next turn)

The router stores the current phase and exposes guards so other modules
can check ``can_bid()``, ``can_serve()`` etc. before making MCP calls.
"""

from __future__ import annotations

import logging
from enum import Enum
from typing import Any, Awaitable, Callable

log = logging.getLogger(__name__)

PhaseHandler = Callable[[dict[str, Any]], Awaitable[None]]


class Phase(str, Enum):
    GAME_STARTED = "game_started"
    SPEAKING = "speaking"
    CLOSED_BID = "closed_bid"
    WAITING = "waiting"
    SERVING = "serving"
    STOPPED = "stopped"
    UNKNOWN = "unknown"


# ── Allowed operations per phase ────────────────────────────────
# True = allowed, False = blocked, "close_only" = special case

_ALLOWED: dict[Phase, dict[str, bool | str]] = {
    Phase.SPEAKING: {
        "save_menu": True,
        "closed_bid": False,
        "prepare_dish": False,
        "serve_dish": False,
        "create_market_entry": True,
        "execute_transaction": True,
        "delete_market_entry": True,
        "send_message": True,
        "update_restaurant_is_open": True,
    },
    Phase.CLOSED_BID: {
        "save_menu": True,
        "closed_bid": True,
        "prepare_dish": False,
        "serve_dish": False,
        "create_market_entry": True,
        "execute_transaction": True,
        "delete_market_entry": True,
        "send_message": True,
        "update_restaurant_is_open": True,
    },
    Phase.WAITING: {
        "save_menu": True,
        "closed_bid": False,
        "prepare_dish": False,
        "serve_dish": False,
        "create_market_entry": True,
        "execute_transaction": True,
        "delete_market_entry": True,
        "send_message": True,
        "update_restaurant_is_open": True,
    },
    Phase.SERVING: {
        "save_menu": False,
        "closed_bid": False,
        "prepare_dish": True,
        "serve_dish": True,
        "create_market_entry": True,
        "execute_transaction": True,
        "delete_market_entry": True,
        "send_message": True,
        "update_restaurant_is_open": "close_only",
    },
    Phase.STOPPED: {
        "save_menu": False,
        "closed_bid": False,
        "prepare_dish": False,
        "serve_dish": False,
        "create_market_entry": False,
        "execute_transaction": False,
        "delete_market_entry": False,
        "send_message": False,
        "update_restaurant_is_open": False,
    },
}


class PhaseRouter:
    """Tracks current phase and dispatches handlers on transitions.

    Usage::

        router = PhaseRouter()
        router.register("speaking", on_speaking)
        router.register("serving", on_serving)
        await router.handle_phase_change({"phase": "speaking"})
    """

    def __init__(self) -> None:
        self._phase: Phase = Phase.UNKNOWN
        self._handlers: dict[Phase, PhaseHandler] = {}

    # ── Registration ──────────────────────────────────────────────

    def register(self, phase_name: str, handler: PhaseHandler) -> None:
        try:
            phase = Phase(phase_name)
        except ValueError:
            log.warning("Unknown phase name: %s", phase_name)
            return
        self._handlers[phase] = handler

    # ── Phase transition ──────────────────────────────────────────

    async def handle_phase_change(self, data: dict[str, Any]) -> None:
        """Called by the event bus on ``game_phase_changed``."""
        raw = data.get("phase", "unknown")
        try:
            new_phase = Phase(raw)
        except ValueError:
            log.warning("Unrecognized phase: %s", raw)
            new_phase = Phase.UNKNOWN

        old = self._phase
        self._phase = new_phase
        log.info("Phase transition: %s → %s", old.value, new_phase.value)

        handler = self._handlers.get(new_phase)
        if handler:
            try:
                await handler(data)
            except Exception as exc:
                log.error("Phase handler error (%s): %s", new_phase.value, exc, exc_info=True)

    # ── Guards ────────────────────────────────────────────────────

    @property
    def phase(self) -> Phase:
        return self._phase

    @property
    def phase_name(self) -> str:
        return self._phase.value

    def is_allowed(self, operation: str) -> bool:
        """Check whether *operation* is allowed in the current phase."""
        perms = _ALLOWED.get(self._phase, {})
        val = perms.get(operation, False)
        if val == "close_only":
            return True  # caller must ensure is_open=false
        return bool(val)

    def can_save_menu(self) -> bool:
        return self.is_allowed("save_menu")

    def can_bid(self) -> bool:
        return self.is_allowed("closed_bid")

    def can_serve(self) -> bool:
        return self.is_allowed("prepare_dish")

    def can_send_message(self) -> bool:
        return self.is_allowed("send_message")

    def can_trade(self) -> bool:
        return self.is_allowed("create_market_entry")

    def is_stopped(self) -> bool:
        return self._phase == Phase.STOPPED

    def is_serving(self) -> bool:
        return self._phase == Phase.SERVING
