"""
TrackerBridge — async interface between tracker.py sidecar (localhost:5555)
and the agent's intelligence pipeline.

tracker.py already polls the game server every 5s, computes diffs, and
exposes a local REST API.  This bridge queries it at decision points.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

import aiohttp

from src.config import BASE_URL, HEADERS, TEAM_ID, TRACKER_BASE_URL
from src.models import TrackerSnapshot

log = logging.getLogger(__name__)


class TrackerBridge:
    """Async gateway to the tracker sidecar running on localhost:5555."""

    def __init__(
        self,
        base_url: str = TRACKER_BASE_URL,
        own_id: int = TEAM_ID,
        timeout: float = 5.0,
    ) -> None:
        self.base_url = base_url
        self.own_id = own_id
        self._timeout = aiohttp.ClientTimeout(total=timeout)
        self._session: aiohttp.ClientSession | None = None
        self._last_snapshot: TrackerSnapshot | None = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(timeout=self._timeout)
        return self._session

    # ── Main entry point ──────────────────────────────────────────

    async def snapshot(self) -> TrackerSnapshot:
        """Pull a complete snapshot from the tracker sidecar."""
        restaurants, bids, market, meals = await asyncio.gather(
            self._fetch_all_restaurants(),
            self._fetch_bid_history(),
            self._fetch_market_entries(),
            self._fetch_own_meals(),
        )

        change_logs: dict[int, list] = {}
        if restaurants:
            rid_list = list(restaurants.keys())
            logs = await asyncio.gather(
                *(self._fetch_change_log(rid) for rid in rid_list)
            )
            for rid, cl in zip(rid_list, logs):
                change_logs[rid] = cl

        snap = TrackerSnapshot(
            restaurants=restaurants,
            change_logs=change_logs,
            bid_history=bids,
            market_entries=market,
            own_meals=meals,
            timestamp=time.time(),
        )
        self._last_snapshot = snap
        return snap

    # ── Individual fetchers ───────────────────────────────────────

    async def _fetch_json(self, path: str) -> Any:
        session = await self._get_session()
        try:
            async with session.get(f"{self.base_url}{path}") as resp:
                resp.raise_for_status()
                return await resp.json()
        except Exception as exc:
            log.warning("TrackerBridge: %s failed: %s", path, exc)
            return None

    async def _fetch_all_restaurants(self) -> dict[int, dict]:
        data = await self._fetch_json("/api/all_restaurants")
        if isinstance(data, list):
            return {r["id"]: r for r in data if "id" in r}
        if isinstance(data, dict):
            return data
        return {}

    async def _fetch_change_log(self, rid: int) -> list[dict]:
        data = await self._fetch_json(f"/api/restaurant/{rid}")
        if isinstance(data, dict):
            return data.get("change_log", [])
        return []

    async def _fetch_bid_history(self) -> list[dict]:
        data = await self._fetch_json("/api/bid_history")
        return data if isinstance(data, list) else []

    async def _fetch_market_entries(self) -> list[dict]:
        data = await self._fetch_json("/api/market")
        return data if isinstance(data, list) else []

    async def _fetch_own_meals(self) -> list[dict]:
        data = await self._fetch_json("/api/meals")
        return data if isinstance(data, list) else []

    # ── Fallback: direct game-server polling ──────────────────────

    async def fetch_restaurants_direct(self) -> list[dict]:
        """Fallback if tracker.py is unreachable."""
        session = await self._get_session()
        try:
            async with session.get(
                f"{BASE_URL}/restaurants", headers=HEADERS
            ) as resp:
                resp.raise_for_status()
                return await resp.json()
        except Exception as exc:
            log.error("Direct restaurants fetch failed: %s", exc)
            return []

    async def fetch_own_state_direct(self) -> dict:
        """Fallback: GET /restaurant/17."""
        session = await self._get_session()
        try:
            async with session.get(
                f"{BASE_URL}/restaurant/{self.own_id}", headers=HEADERS
            ) as resp:
                resp.raise_for_status()
                return await resp.json()
        except Exception as exc:
            log.error("Direct own-state fetch failed: %s", exc)
            return {}

    # ── Lifecycle ─────────────────────────────────────────────────

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()
