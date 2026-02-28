"""
ReactiveEventBus — typed event dispatch with priority routing and
middleware support.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Awaitable, Callable

import aiohttp

log = logging.getLogger(__name__)

Handler = Callable[[dict[str, Any]], Awaitable[None]]
Middleware = Callable[[str, dict[str, Any]], Awaitable[dict[str, Any] | None]]


class _HandlerEntry:
    __slots__ = ("handler", "priority", "filter_fn")

    def __init__(
        self,
        handler: Handler,
        priority: int = 0,
        filter_fn: Callable[[dict], bool] | None = None,
    ) -> None:
        self.handler = handler
        self.priority = priority
        self.filter_fn = filter_fn


class ReactiveEventBus:
    """Push-based event bus that bridges SSE events to async handlers.

    Usage::

        bus = ReactiveEventBus()
        bus.on("client_spawned", my_handler, priority=0)
        bus.use(logging_middleware)
        await bus.connect_sse(url, headers)
    """

    def __init__(self) -> None:
        self._handlers: dict[str, list[_HandlerEntry]] = {}
        self._middleware: list[Middleware] = []

    # ── Registration ──────────────────────────────────────────────

    def on(
        self,
        event_type: str,
        handler: Handler,
        priority: int = 0,
        filter_fn: Callable[[dict], bool] | None = None,
    ) -> None:
        entry = _HandlerEntry(handler, priority, filter_fn)
        self._handlers.setdefault(event_type, []).append(entry)
        self._handlers[event_type].sort(key=lambda e: e.priority)

    def use(self, middleware: Middleware) -> None:
        self._middleware.append(middleware)

    # ── Dispatch ──────────────────────────────────────────────────

    async def emit(self, event_type: str, data: dict[str, Any]) -> None:
        """Run middleware chain, then dispatch to registered handlers."""
        for mw in self._middleware:
            result = await mw(event_type, data)
            if result is None:
                return  # middleware blocked
            data = result

        for entry in self._handlers.get(event_type, []):
            if entry.filter_fn and not entry.filter_fn(data):
                continue
            try:
                await entry.handler(data)
            except Exception as exc:
                log.error("Handler error for %s: %s", event_type, exc, exc_info=True)

    # ── SSE Connection ────────────────────────────────────────────

    async def connect_sse(
        self,
        url: str,
        headers: dict[str, str],
        retry_delay: float = 2.0,
    ) -> None:
        """Connect to SSE stream and dispatch events.

        Handles:
          409 → wait and retry (only one SSE connection per restaurant)
          401/403/404 → fatal
          Network errors → reconnect with backoff
        """
        timeout = aiohttp.ClientTimeout(
            total=None, sock_connect=15, sock_read=None
        )

        while True:
            try:
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.get(url, headers=headers) as resp:
                        if resp.status == 409:
                            log.warning("SSE 409: another connection active, retrying in %.0fs", retry_delay)
                            await asyncio.sleep(retry_delay)
                            continue
                        if resp.status in (401, 403, 404):
                            resp.raise_for_status()

                        log.info("SSE connected to %s", url)
                        async for raw_line in resp.content:
                            await self._handle_line(raw_line)
            except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
                log.warning("SSE connection lost (%s), reconnecting…", exc)
                await asyncio.sleep(retry_delay)
                continue
            except Exception as exc:
                log.error("SSE fatal error: %s", exc, exc_info=True)
                raise
            break  # clean exit

    # ── Line parsing (from template DANGER ZONE) ──────────────────

    async def _handle_line(self, raw_line: bytes) -> None:
        if not raw_line:
            return
        line = raw_line.decode("utf-8", errors="ignore").strip()
        if not line:
            return

        if line.startswith("data:"):
            payload = line[5:].strip()
            if payload == "connected":
                log.info("SSE handshake: connected")
                return
            line = payload

        try:
            event_json = json.loads(line)
        except json.JSONDecodeError:
            log.debug("SSE raw: %s", line[:120])
            return

        event_type = event_json.get("type", "unknown")
        event_data = event_json.get("data", {})
        if not isinstance(event_data, dict):
            event_data = {"value": event_data}

        await self.emit(event_type, event_data)
