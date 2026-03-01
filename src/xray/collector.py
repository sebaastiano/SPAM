"""
SPAM! X-Ray — Trace Collector
===============================
Non-invasive structured tracing singleton.

Collects trace events from all subsystems and broadcasts them to
connected dashboard clients via WebSocket.  If no dashboard is
connected, events are silently buffered (capped ring-buffer) with
near-zero overhead on the hot path.

Trace event types:
    phase       — Game phase transitions
    skill       — Skill execution lifecycle (start/success/fail)
    decision    — Strategic decisions with rationale
    intelligence— Competitor analysis results
    diplomacy   — Messages sent/received, deception strategy
    serving     — Client processing, order matching
    memory      — State snapshots (balance, inventory, reputation)
    event       — Raw SSE events from the game server
    span        — Timed operation spans (context manager / decorator)
"""

from __future__ import annotations

import asyncio
import functools
import json
import logging
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Callable

logger = logging.getLogger("spam.xray")

# Maximum buffered events before oldest are discarded
MAX_BUFFER = 2000


@dataclass
class TraceEvent:
    """A single structured trace event."""
    id: str
    timestamp: str
    category: str          # phase | skill | decision | intelligence | ...
    name: str              # e.g. "zone_selection", "speaking", "client_spawned"
    status: str = "info"   # info | running | success | failed | warning
    turn_id: int = 0
    phase: str = ""
    duration_ms: float | None = None
    data: dict = field(default_factory=dict)
    parent_id: str | None = None

    def to_dict(self) -> dict:
        d = asdict(self)
        # Strip None values for compact JSON
        return {k: v for k, v in d.items() if v is not None}

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), default=str)


class XRayCollector:
    """
    Singleton trace collector and broadcaster.

    Thread-safe (uses asyncio queue for cross-task communication).
    All public methods are safe to call from sync or async contexts.
    """

    def __init__(self):
        self._buffer: list[TraceEvent] = []
        self._subscribers: list[asyncio.Queue] = []
        self._loop: asyncio.AbstractEventLoop | None = None
        self._server = None
        self._current_turn: int = 0
        self._current_phase: str = ""
        self._game_state: dict[str, Any] = {}
        self._skill_states: dict[str, dict] = {}  # name → latest state
        self._competitor_states: dict[str, dict] = {}
        self._serving_stats: dict[str, Any] = {}
        self._started = False

    # ══════════════════════════════════════════════════════════════
    #  LIFECYCLE
    # ══════════════════════════════════════════════════════════════

    async def start(self, port: int = 8777):
        """Start the X-Ray dashboard server."""
        if self._started:
            return
        self._loop = asyncio.get_event_loop()
        from src.xray.server import XRayServer
        self._server = XRayServer(self, port=port)
        await self._server.start()
        self._started = True
        logger.info(f"X-Ray dashboard available at http://localhost:{port}")

    def subscribe(self) -> asyncio.Queue:
        """Register a new WebSocket subscriber. Returns a queue of TraceEvents."""
        q: asyncio.Queue = asyncio.Queue(maxsize=500)
        self._subscribers.append(q)
        return q

    def unsubscribe(self, q: asyncio.Queue):
        """Remove a subscriber."""
        if q in self._subscribers:
            self._subscribers.remove(q)

    # ══════════════════════════════════════════════════════════════
    #  CORE EMIT
    # ══════════════════════════════════════════════════════════════

    def emit(
        self,
        category: str,
        name: str,
        status: str = "info",
        data: dict | None = None,
        duration_ms: float | None = None,
        parent_id: str | None = None,
    ) -> str:
        """
        Emit a structured trace event.

        Returns the event ID for parent-child linking.
        """
        event = TraceEvent(
            id=uuid.uuid4().hex[:12],
            timestamp=datetime.now(timezone.utc).isoformat(),
            category=category,
            name=name,
            status=status,
            turn_id=self._current_turn,
            phase=self._current_phase,
            duration_ms=duration_ms,
            data=data or {},
            parent_id=parent_id,
        )

        # Buffer (ring-buffer eviction)
        self._buffer.append(event)
        if len(self._buffer) > MAX_BUFFER:
            self._buffer = self._buffer[-MAX_BUFFER:]

        # Broadcast to WebSocket subscribers
        dead: list[asyncio.Queue] = []
        for q in self._subscribers:
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                dead.append(q)
        for q in dead:
            self._subscribers.remove(q)

        return event.id

    # ══════════════════════════════════════════════════════════════
    #  HIGH-LEVEL TRACE METHODS
    # ══════════════════════════════════════════════════════════════

    def phase(self, phase_name: str, turn_id: int = 0, **extra):
        """Record a phase transition."""
        if turn_id:
            self._current_turn = turn_id
        self._current_phase = phase_name
        self.emit("phase", phase_name, status="info", data={
            "turn_id": turn_id or self._current_turn,
            **extra,
        })

    def skill(self, name: str, status: str = "running", **extra):
        """Record a skill lifecycle event."""
        self._skill_states[name] = {"status": status, **extra}
        self.emit("skill", name, status=status, data=extra)

    def decision(self, name: str, choice: str = "", reason: str = "", **extra):
        """Record a strategic decision with rationale."""
        self.emit("decision", name, status="info", data={
            "choice": choice,
            "reason": reason,
            **extra,
        })

    def intelligence(self, name: str, **data):
        """Record an intelligence analysis result."""
        self.emit("intelligence", name, data=data)

    def diplomacy(self, name: str, **data):
        """Record a diplomacy event."""
        self.emit("diplomacy", name, data=data)

    def serving(self, name: str, status: str = "info", **data):
        """Record a serving event."""
        self.emit("serving", name, status=status, data=data)

    def memory(self, name: str, **data):
        """Record a memory/state update."""
        self.emit("memory", name, data=data)

    def event(self, name: str, **data):
        """Record a raw SSE event."""
        self.emit("event", name, data=data)

    def warning(self, name: str, message: str, **data):
        """Record a warning."""
        self.emit("warning", name, status="warning", data={
            "message": message, **data,
        })

    def error(self, name: str, message: str, **data):
        """Record an error."""
        self.emit("error", name, status="failed", data={
            "message": message, **data,
        })

    # ══════════════════════════════════════════════════════════════
    #  STATE SNAPSHOTS (for dashboard panels)
    # ══════════════════════════════════════════════════════════════

    def update_game_state(
        self,
        balance: float = 0,
        inventory: dict | None = None,
        reputation: float = 0,
        menu: list | None = None,
        is_open: bool = False,
        zone: str = "",
    ):
        """Update the current game state snapshot for the dashboard."""
        self._game_state = {
            "turn_id": self._current_turn,
            "phase": self._current_phase,
            "balance": balance,
            "inventory_count": len(inventory) if inventory else 0,
            "inventory_total": sum(inventory.values()) if inventory else 0,
            "inventory": dict(list((inventory or {}).items())[:20]),  # top 20
            "reputation": reputation,
            "menu": menu or [],
            "menu_count": len(menu) if menu else 0,
            "is_open": is_open,
            "zone": zone,
        }
        self.emit("memory", "game_state", data=self._game_state)

    def update_competitors(self, briefings: dict):
        """Update competitor intelligence snapshot."""
        summary = {}
        for rid, b in briefings.items():
            summary[str(rid)] = {
                "name": b.get("name", f"Team {rid}"),
                "strategy": b.get("strategy", "UNKNOWN"),
                "threat_level": b.get("threat_level", 0),
                "is_connected": b.get("is_connected", False),
                "menu_size": b.get("menu_size", 0),
                "menu_price_avg": round(b.get("menu_price_avg", 0), 1),
                "balance": b.get("balance", 0),
                "reputation": b.get("reputation", 0),
            }
        self._competitor_states = summary
        self.emit("intelligence", "competitors", data={"competitors": summary})

    def update_serving_stats(self, **stats):
        """Update serving statistics snapshot."""
        self._serving_stats.update(stats)
        self.emit("serving", "stats", data=self._serving_stats)

    # ══════════════════════════════════════════════════════════════
    #  SPAN CONTEXT MANAGER
    # ══════════════════════════════════════════════════════════════

    @contextmanager
    def span(self, name: str, category: str = "span", **extra):
        """
        Context manager for timed operation spans.

        Usage:
            with xray.span("ilp_solver", recipes=50):
                result = solve_zone_ilp(...)
        """
        start = time.monotonic()
        span_id = self.emit(category, name, status="running", data=extra)
        try:
            yield span_id
            elapsed = (time.monotonic() - start) * 1000
            self.emit(
                category, name, status="success",
                duration_ms=round(elapsed, 1),
                data=extra,
                parent_id=span_id,
            )
        except Exception as e:
            elapsed = (time.monotonic() - start) * 1000
            self.emit(
                category, name, status="failed",
                duration_ms=round(elapsed, 1),
                data={"error": str(e), **extra},
                parent_id=span_id,
            )
            raise

    # ══════════════════════════════════════════════════════════════
    #  DECORATOR
    # ══════════════════════════════════════════════════════════════

    def traced(self, name: str | None = None, category: str = "skill"):
        """
        Decorator for tracing async functions.

        Usage:
            @xray.traced("intelligence_scan")
            async def _skill_intelligence_scan(self, ctx):
                ...
        """
        def decorator(fn: Callable):
            trace_name = name or fn.__name__

            @functools.wraps(fn)
            async def wrapper(*args, **kwargs):
                start = time.monotonic()
                span_id = self.emit(category, trace_name, status="running")
                try:
                    result = await fn(*args, **kwargs)
                    elapsed = (time.monotonic() - start) * 1000
                    # If result is a SkillResult, extract status
                    status = "success"
                    result_data = {}
                    if hasattr(result, "success"):
                        status = "success" if result.success else "failed"
                        result_data = getattr(result, "data", {}) or {}
                        if not result.success:
                            result_data["error"] = getattr(result, "error", "")
                    self.emit(
                        category, trace_name, status=status,
                        duration_ms=round(elapsed, 1),
                        data=result_data,
                        parent_id=span_id,
                    )
                    return result
                except Exception as e:
                    elapsed = (time.monotonic() - start) * 1000
                    self.emit(
                        category, trace_name, status="failed",
                        duration_ms=round(elapsed, 1),
                        data={"error": str(e)},
                        parent_id=span_id,
                    )
                    raise

            return wrapper
        return decorator

    # ══════════════════════════════════════════════════════════════
    #  SNAPSHOT (for new dashboard connections)
    # ══════════════════════════════════════════════════════════════

    def get_snapshot(self) -> dict:
        """
        Get the current full state snapshot for a newly-connected dashboard.

        Returns everything needed to render the UI immediately.
        """
        return {
            "type": "snapshot",
            "turn_id": self._current_turn,
            "phase": self._current_phase,
            "game_state": self._game_state,
            "skill_states": self._skill_states,
            "competitors": self._competitor_states,
            "serving_stats": self._serving_stats,
            "recent_events": [e.to_dict() for e in self._buffer[-100:]],
        }

    def get_history(self, limit: int = 200) -> list[dict]:
        """Get recent trace history."""
        return [e.to_dict() for e in self._buffer[-limit:]]
