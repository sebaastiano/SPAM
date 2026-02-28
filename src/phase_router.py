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

Mid-turn entry:
  When we connect mid-turn (first phase != speaking from None), the router
  detects this and injects is_mid_turn_entry=True + skipped_phases into the
  event data so phase handlers can run catch-up logic.

Phase timing:
  Tracks phase start times and maintains rolling averages for phase
  duration estimation (used for countdown logging).
"""

import logging
import time
from typing import Callable, Awaitable

logger = logging.getLogger("spam.phase_router")

# Phase ordering for skipped-phase computation
PHASE_ORDER = ["speaking", "closed_bid", "waiting", "serving", "stopped"]

# Default phase duration estimates (seconds) — updated from observations
DEFAULT_PHASE_DURATIONS = {
    "speaking": 90.0,
    "closed_bid": 45.0,
    "waiting": 45.0,
    "serving": 150.0,
    "stopped": 30.0,
}


class PhaseRouter:
    """
    Phase state machine with mid-turn detection and timing.

    Routes game_phase_changed SSE events to the correct phase handler.
    Enforces phase restrictions and tracks the current game phase.
    Detects mid-turn entry and injects catch-up metadata.
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

        # ── Mid-turn detection ──
        self._first_phase_received = False
        self._is_mid_turn_entry = False
        self._skipped_phases: list[str] = []
        self._turn_has_seen_speaking = False

        # ── Phase timing ──
        self.phase_start_time: float = 0.0
        self.phase_durations: dict[str, list[float]] = {
            p: [] for p in self.VALID_PHASES
        }
        self.estimated_durations: dict[str, float] = dict(DEFAULT_PHASE_DURATIONS)

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

        Detects mid-turn entry and injects metadata into the data dict
        before dispatching to the phase handler.

        data format: {"phase": "serving", "turn_id": 3, ...}
        """
        new_phase = data.get("phase", "").lower()
        turn_id = data.get("turn_id", self.current_turn)

        if new_phase not in self.VALID_PHASES:
            logger.warning(f"Unknown phase received: {new_phase}")
            return

        # ── Record previous phase duration ──
        now = time.time()
        old_phase = self.current_phase
        if old_phase and self.phase_start_time > 0:
            elapsed = now - self.phase_start_time
            self.phase_durations[old_phase].append(elapsed)
            # Rolling average (last 10 observations)
            recent = self.phase_durations[old_phase][-10:]
            self.estimated_durations[old_phase] = sum(recent) / len(recent)
            logger.debug(
                f"Phase '{old_phase}' lasted {elapsed:.1f}s "
                f"(avg now {self.estimated_durations[old_phase]:.1f}s)"
            )

        # ── Mid-turn detection ──
        is_mid_turn = False
        skipped = []

        if not self._first_phase_received:
            self._first_phase_received = True
            if new_phase != "speaking":
                # We joined mid-turn — compute what we missed
                is_mid_turn = True
                if new_phase in PHASE_ORDER:
                    idx = PHASE_ORDER.index(new_phase)
                    skipped = PHASE_ORDER[:idx]
                self._is_mid_turn_entry = True
                self._skipped_phases = skipped
                logger.warning(
                    f"⚠ MID-TURN ENTRY detected! "
                    f"Joining at phase '{new_phase}' (turn {turn_id}). "
                    f"Skipped phases: {skipped}"
                )
            else:
                self._turn_has_seen_speaking = True
                logger.info("Normal turn entry at speaking phase")

        # ── Detect turn change (stopped → speaking) ──
        if new_phase == "speaking" and old_phase == "stopped":
            self.current_turn = turn_id
            self._turn_has_seen_speaking = True
            self._is_mid_turn_entry = False
            self._skipped_phases = []
            logger.info(f"=== TURN {self.current_turn} STARTED ===")
            if self._on_turn_change:
                await self._on_turn_change(self.current_turn)

        # ── Update state ──
        self.current_phase = new_phase
        self.current_turn = turn_id
        self.phase_start_time = now

        logger.info(f"Phase: {old_phase} → {new_phase} (turn {turn_id})")

        # ── Inject mid-turn metadata into data dict ──
        enriched_data = dict(data)
        enriched_data["turn_id"] = turn_id
        enriched_data["is_mid_turn_entry"] = is_mid_turn
        enriched_data["skipped_phases"] = skipped
        enriched_data["phase_start_time"] = now

        # ── Dispatch to phase handler ──
        handler = self._handlers.get(new_phase)
        if handler:
            try:
                await handler(enriched_data)
            except Exception as e:
                logger.error(f"Phase handler error ({new_phase}): {e}", exc_info=True)
        else:
            logger.warning(f"No handler registered for phase: {new_phase}")

    async def handle_game_started(self, data: dict):
        """Called on game_started SSE event."""
        self.current_phase = None
        self.current_turn = 0
        self._first_phase_received = False
        self._is_mid_turn_entry = False
        self._skipped_phases = []
        self._turn_has_seen_speaking = False
        logger.info("Game started — awaiting first phase")

    async def handle_game_reset(self, data: dict):
        """
        Called on game_reset SSE event.
        Clear turn-scoped state, preserve cross-turn memory (incl. timing).
        Do NOT call any MCP tools — wait for next game_started.
        """
        logger.info("Game reset — clearing turn-scoped state")
        self.current_phase = None
        self.current_turn = 0
        self._first_phase_received = False
        self._is_mid_turn_entry = False
        self._skipped_phases = []
        self._turn_has_seen_speaking = False
        # Keep: phase_durations, estimated_durations (cross-turn learning)

    # ── Timing helpers ──

    @property
    def elapsed_in_phase(self) -> float:
        """Seconds elapsed since current phase started."""
        if self.phase_start_time <= 0:
            return 0.0
        return time.time() - self.phase_start_time

    @property
    def estimated_remaining(self) -> float:
        """Estimated seconds remaining in current phase."""
        if not self.current_phase:
            return 0.0
        est_total = self.estimated_durations.get(self.current_phase, 60.0)
        remaining = est_total - self.elapsed_in_phase
        return max(0.0, remaining)

    @property
    def estimated_phase_end(self) -> float:
        """Estimated epoch time when current phase will end."""
        return self.phase_start_time + self.estimated_durations.get(
            self.current_phase or "speaking", 60.0
        )

    @property
    def is_mid_turn(self) -> bool:
        """Whether we entered this turn mid-way."""
        return self._is_mid_turn_entry

    @property
    def skipped_phases(self) -> list[str]:
        """Phases we skipped due to mid-turn entry."""
        return self._skipped_phases

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
        """update_restaurant_is_open(true) in speaking, closed_bid, waiting — NOT serving."""
        return self.current_phase in {"speaking", "closed_bid", "waiting"}

    def can_close_restaurant(self) -> bool:
        """update_restaurant_is_open(false) in waiting or serving."""
        return self.current_phase in {"waiting", "serving"}

    def can_bid(self) -> bool:
        """closed_bid only in closed_bid phase."""
        return self.current_phase == "closed_bid"

    def can_use_market(self) -> bool:
        """Market ops in speaking, closed_bid, waiting, serving."""
        return self.current_phase in {"speaking", "closed_bid", "waiting", "serving"}
