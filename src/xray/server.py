"""
SPAM! X-Ray — WebSocket Dashboard Server
==========================================
Lightweight async HTTP + WebSocket server for the explainability dashboard.
Serves the static SPA and streams real-time trace events to connected clients.

Uses only aiohttp (already in requirements.txt) — no extra dependencies.
"""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING

import aiohttp
from aiohttp import web

if TYPE_CHECKING:
    from src.xray.collector import XRayCollector

logger = logging.getLogger("spam.xray.server")

STATIC_DIR = Path(__file__).parent / "static"


class XRayServer:
    """
    Async HTTP + WebSocket server for the X-Ray dashboard.

    Endpoints:
        GET /                → Dashboard SPA (index.html)
        GET /api/snapshot    → Current state snapshot (JSON)
        GET /api/history     → Recent trace events (JSON)
        WS  /ws              → Real-time event stream
    """

    def __init__(self, collector: XRayCollector, port: int = 8777):
        self.collector = collector
        self.port = port
        self._app: web.Application | None = None
        self._runner: web.AppRunner | None = None

    async def start(self):
        """Start the HTTP server (non-blocking, runs as background task)."""
        self._app = web.Application()
        self._app.router.add_get("/", self._handle_index)
        self._app.router.add_get("/api/snapshot", self._handle_snapshot)
        self._app.router.add_get("/api/history", self._handle_history)
        self._app.router.add_get("/ws", self._handle_websocket)
        # Serve static files (CSS, JS, etc.)
        if STATIC_DIR.exists():
            self._app.router.add_static("/static/", STATIC_DIR)

        self._runner = web.AppRunner(self._app, access_log=None)
        await self._runner.setup()
        site = web.TCPSite(self._runner, "0.0.0.0", self.port)
        await site.start()
        logger.info(f"X-Ray server listening on port {self.port}")

    async def stop(self):
        """Graceful shutdown."""
        if self._runner:
            await self._runner.cleanup()

    # ── HTTP Handlers ──

    async def _handle_index(self, request: web.Request) -> web.StreamResponse:
        """Serve the dashboard SPA."""
        index_path = STATIC_DIR / "index.html"
        if not index_path.exists():
            return web.Response(
                text="X-Ray dashboard index.html not found",
                status=404,
            )
        return web.FileResponse(index_path)

    async def _handle_snapshot(self, request: web.Request) -> web.Response:
        """Return current state snapshot as JSON."""
        snapshot = self.collector.get_snapshot()
        return web.json_response(snapshot)

    async def _handle_history(self, request: web.Request) -> web.Response:
        """Return recent trace history as JSON."""
        limit = int(request.query.get("limit", "200"))
        history = self.collector.get_history(limit=limit)
        return web.json_response(history)

    # ── WebSocket Handler ──

    async def _handle_websocket(self, request: web.Request) -> web.WebSocketResponse:
        """
        WebSocket endpoint for real-time trace streaming.

        Protocol:
        1. On connect: sends full snapshot
        2. Then streams each new TraceEvent as JSON
        3. Client can send {"type": "ping"} for keepalive
        """
        ws = web.WebSocketResponse(heartbeat=30)
        await ws.prepare(request)

        logger.info("X-Ray dashboard client connected")

        # Subscribe to events
        queue = self.collector.subscribe()

        try:
            # Send initial snapshot
            snapshot = self.collector.get_snapshot()
            await ws.send_json(snapshot)

            # Stream events
            while not ws.closed:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=1.0)
                    await ws.send_str(event.to_json())
                except asyncio.TimeoutError:
                    # Check if client sent anything (ping/pong)
                    continue
                except ConnectionResetError:
                    break

        except Exception as e:
            logger.warning(f"X-Ray WebSocket error: {e}")
        finally:
            self.collector.unsubscribe(queue)
            logger.info("X-Ray dashboard client disconnected")

        return ws
