"""
Data collector — gathers raw game data, either via TrackerBridge or
direct server polling as fallback.
"""

from __future__ import annotations

import logging
from typing import Any

import aiohttp

from src.config import BASE_URL, HEADERS, TEAM_ID
from src.intelligence.tracker_bridge import TrackerBridge
from src.models import TrackerSnapshot

log = logging.getLogger(__name__)


class DataCollector:
    """Fetches game data from either the tracker sidecar or the
    game server directly.  Returns a ``TrackerSnapshot``."""

    def __init__(self, bridge: TrackerBridge) -> None:
        self.bridge = bridge

    async def collect(self, turn_id: int = 0) -> TrackerSnapshot:
        """Attempt tracker first, fall back to direct."""
        try:
            snap = await self.bridge.snapshot()
            if snap.restaurants:
                return snap
        except Exception as exc:
            log.warning("Tracker unreachable, falling back to direct: %s", exc)

        return await self._collect_direct(turn_id)

    async def _collect_direct(self, turn_id: int) -> TrackerSnapshot:
        import time

        timeout = aiohttp.ClientTimeout(total=10)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            restaurants: dict[int, dict] = {}
            bids: list[dict] = []
            market: list[dict] = []
            meals: list[dict] = []

            try:
                async with session.get(
                    f"{BASE_URL}/restaurants", headers=HEADERS
                ) as r:
                    data = await r.json()
                    restaurants = {
                        rest["id"]: rest for rest in data if "id" in rest
                    }
            except Exception:
                pass

            try:
                async with session.get(
                    f"{BASE_URL}/bid_history",
                    headers=HEADERS,
                    params={"turn_id": turn_id},
                ) as r:
                    bids = await r.json()
            except Exception:
                pass

            try:
                async with session.get(
                    f"{BASE_URL}/market/entries", headers=HEADERS
                ) as r:
                    market = await r.json()
            except Exception:
                pass

            try:
                async with session.get(
                    f"{BASE_URL}/meals",
                    headers=HEADERS,
                    params={
                        "turn_id": turn_id,
                        "restaurant_id": TEAM_ID,
                    },
                ) as r:
                    meals = await r.json()
            except Exception:
                pass

            return TrackerSnapshot(
                restaurants=restaurants,
                bid_history=bids,
                market_entries=market,
                own_meals=meals,
                timestamp=time.time(),
            )
