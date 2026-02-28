"""
SPAM! — Reactive Event Bus
===========================
Event-driven agent activation layer connecting SSE streams to handlers.
Typed routing with priority and middleware support.
"""

import asyncio
import json
import logging
from typing import Any, Awaitable, Callable

import aiohttp

from src.config import SSE_URL, HEADERS, API_KEY, TEAM_ID, BASE_URL

logger = logging.getLogger("spam.event_bus")

Middleware = Callable[[str, dict], Awaitable[dict | None]]


class EventHandler:
    """Typed event handler with priority and filtering."""

    def __init__(
        self,
        event_type: str,
        handler: Callable[[dict], Awaitable[None]],
        priority: int = 0,
        filter_fn: Callable[[dict], bool] | None = None,
    ):
        self.event_type = event_type
        self.handler = handler
        self.priority = priority
        self.filter_fn = filter_fn


class ReactiveEventBus:
    """
    Event-driven agent activation layer.

    Extends the framework pattern to support push-based SSE architectures.
    Dispatches events through middleware chain then to prioritised handlers.

    Usage:
        bus = ReactiveEventBus()
        bus.on("client_spawned", handle_client, priority=0)
        bus.on("new_message", handle_message, priority=1)
        bus.on("game_phase_changed", phase_router, priority=0)

        # Connect to SSE stream
        await bus.connect_sse()
    """

    def __init__(self):
        self.handlers: dict[str, list[EventHandler]] = {}
        self.middleware: list[Middleware] = []
        self._connected = False

    def on(
        self,
        event_type: str,
        handler: Callable[[dict], Awaitable[None]],
        priority: int = 0,
        filter_fn: Callable[[dict], bool] | None = None,
    ):
        """Register a handler for an event type."""
        if event_type not in self.handlers:
            self.handlers[event_type] = []
        self.handlers[event_type].append(
            EventHandler(event_type, handler, priority, filter_fn)
        )
        # Sort by priority (lower = higher priority)
        self.handlers[event_type].sort(key=lambda h: h.priority)

    def use(self, middleware: Middleware):
        """Add middleware (e.g., GroundTruthFirewall, EventLog)."""
        self.middleware.append(middleware)

    async def emit(self, event_type: str, data: dict):
        """Dispatch an event through middleware then to handlers."""
        # Run through middleware chain
        for mw in self.middleware:
            result = await mw(event_type, data)
            if result is None:
                return  # middleware blocked the event
            data = result

        # Dispatch to registered handlers
        for handler in self.handlers.get(event_type, []):
            if handler.filter_fn and not handler.filter_fn(data):
                continue
            try:
                await handler.handler(data)
            except Exception as e:
                logger.error(f"Handler error for {event_type}: {e}", exc_info=True)

    async def connect_sse(self, retry_delay: float = 2.0):
        """
        Connect to the game's SSE stream and dispatch events.

        Handles:
          409 — connection already active (wait and retry)
          401/403/404 — fatal errors
          Network errors — reconnect with backoff
        """
        url = f"{BASE_URL}/events/{TEAM_ID}"
        headers = {
            "Accept": "text/event-stream",
            "x-api-key": API_KEY,
        }

        while True:
            try:
                timeout = aiohttp.ClientTimeout(
                    total=None, sock_connect=15, sock_read=None
                )
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    logger.info(f"Connecting to SSE at {url}")
                    async with session.get(url, headers=headers) as resp:
                        if resp.status == 409:
                            logger.warning("SSE 409 — another connection active, retrying...")
                            await asyncio.sleep(retry_delay)
                            continue
                        if resp.status in (401, 403, 404):
                            logger.error(f"SSE fatal error: HTTP {resp.status}")
                            resp.raise_for_status()

                        logger.info("SSE connection established")
                        self._connected = True

                        async for line in resp.content:
                            await self._handle_line(line)

            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                logger.warning(f"SSE disconnected: {e} — reconnecting in {retry_delay}s")
                self._connected = False
                await asyncio.sleep(retry_delay)
                continue
            except Exception as e:
                logger.error(f"SSE unexpected error: {e}", exc_info=True)
                self._connected = False
                await asyncio.sleep(retry_delay)
                continue

            break  # clean exit

    async def _handle_line(self, raw_line: bytes):
        """Parse a single SSE line and dispatch."""
        if not raw_line:
            return

        line = raw_line.decode("utf-8", errors="ignore").strip()
        if not line:
            return

        # Standard SSE data format: data: ...
        if line.startswith("data:"):
            payload = line[5:].strip()
            if payload == "connected":
                logger.info("SSE connected acknowledgement")
                return
            line = payload

        try:
            event_json = json.loads(line)
        except json.JSONDecodeError:
            logger.debug(f"SSE raw: {line}")
            return

        event_type = event_json.get("type", "unknown")
        event_data = event_json.get("data", {})
        if not isinstance(event_data, dict):
            event_data = {"value": event_data}

        await self.emit(event_type, event_data)

    @property
    def is_connected(self) -> bool:
        return self._connected
