"""
SPAM! — Tracker Bridge
=======================
Bridge between tracker.py sidecar (localhost:5555) and the agent's
intelligence pipeline.

tracker.py runs independently, polling the game server every 5s.
This bridge queries tracker's local API at decision points.
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field

import httpx

from src.config import TRACKER_BASE_URL, TEAM_ID

logger = logging.getLogger("spam.intelligence.tracker_bridge")


@dataclass
class TrackerSnapshot:
    """Complete snapshot from tracker at a single point in time."""
    restaurants: dict = field(default_factory=dict)       # rid → flattened restaurant data
    change_logs: dict = field(default_factory=dict)       # rid → list of changes
    bid_history: list = field(default_factory=list)       # all bids across all teams
    market_entries: list = field(default_factory=list)     # all market BUY/SELL entries
    own_meals: list = field(default_factory=list)          # our completed meals
    timestamp: float = 0.0


class TrackerBridge:
    """
    Bridge between tracker.py sidecar and the intelligence pipeline.

    tracker.py already polls GET /restaurants every 5s — no need to duplicate.
    This bridge queries tracker's pre-computed diffs at decision points only.
    """

    def __init__(self, base_url: str = TRACKER_BASE_URL, own_id: int = TEAM_ID):
        self.base_url = base_url
        self.own_id = own_id
        self._client: httpx.AsyncClient | None = None
        self._last_snapshot: TrackerSnapshot | None = None

    async def _ensure_client(self):
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url, timeout=5.0
            )

    async def snapshot(self) -> TrackerSnapshot:
        """
        Pull a complete snapshot from tracker.
        Called once at the start of each decision cycle.
        """
        await self._ensure_client()

        # Parallel fetch from all tracker endpoints
        restaurants, bids, market, meals = await asyncio.gather(
            self._fetch_all_restaurants(),
            self._fetch_bid_history(),
            self._fetch_market_entries(),
            self._fetch_own_meals(),
        )

        # Fetch change logs for all known restaurants
        change_logs = {}
        if restaurants:
            tasks = {
                rid: self._fetch_change_log(rid) for rid in restaurants.keys()
            }
            results = await asyncio.gather(*tasks.values())
            for rid, log in zip(tasks.keys(), results):
                change_logs[rid] = log

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

    async def _fetch_all_restaurants(self) -> dict[int, dict]:
        try:
            resp = await self._client.get("/api/all_restaurants")
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, list):
                return {r.get("id", i): r for i, r in enumerate(data)}
            if isinstance(data, dict):
                # JSON keys are strings — convert to int for consistency
                return {int(k): v for k, v in data.items()}
            return {}
        except Exception as e:
            logger.warning(f"Failed to fetch restaurants from tracker: {e}")
            return {}

    async def _fetch_change_log(self, rid: int) -> list[dict]:
        try:
            resp = await self._client.get(f"/api/restaurant/{rid}")
            resp.raise_for_status()
            data = resp.json()
            return data.get("change_log", []) if isinstance(data, dict) else []
        except Exception:
            return []

    async def _fetch_bid_history(self) -> list[dict]:
        try:
            resp = await self._client.get("/api/bid_history")
            resp.raise_for_status()
            data = resp.json()
            return data if isinstance(data, list) else []
        except Exception as e:
            logger.warning(f"Failed to fetch bid history: {e}")
            return []

    async def _fetch_market_entries(self) -> list[dict]:
        try:
            resp = await self._client.get("/api/market")
            resp.raise_for_status()
            data = resp.json()
            return data if isinstance(data, list) else []
        except Exception as e:
            logger.warning(f"Failed to fetch market entries: {e}")
            return []

    async def _fetch_own_meals(self) -> list[dict]:
        try:
            resp = await self._client.get("/api/meals")
            resp.raise_for_status()
            data = resp.json()
            return data if isinstance(data, list) else []
        except Exception as e:
            logger.warning(f"Failed to fetch meals: {e}")
            return []

    def delta_since_last(self, rid: int) -> dict:
        """Compare current snapshot vs previous for a specific restaurant."""
        if not self._last_snapshot or rid not in self._last_snapshot.change_logs:
            return {}
        return {
            entry.get("field", ""): {"old": entry.get("old"), "new": entry.get("new")}
            for entry in self._last_snapshot.change_logs.get(rid, [])
        }

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()
