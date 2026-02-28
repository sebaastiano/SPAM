"""
SPAM! — Data Collector Module
===============================
Collects game data via TrackerBridge for the intelligence pipeline.
Falls back to direct API polling if tracker is unreachable.
"""

import logging

import aiohttp

from src.config import BASE_URL, HEADERS, TEAM_ID

logger = logging.getLogger("spam.intelligence.data_collector")


class DataCollectorModule:
    """
    Collects game data via TrackerBridge instead of direct API polling.

    Falls back to direct polling if tracker.py is unreachable.
    """

    def __init__(self, bridge=None):
        """
        Args:
            bridge: TrackerBridge instance. If None, falls back to direct polling.
        """
        self.bridge = bridge

    async def process(self, input_data: dict) -> dict:
        """
        Collect all game data for the intelligence pipeline.

        Returns dict with keys:
          all_restaurants, bids, market_entries, own_meals, change_logs, snapshot_time
        """
        if self.bridge:
            try:
                snapshot = await self.bridge.snapshot()
                return {
                    "all_restaurants": snapshot.restaurants,
                    "bids": snapshot.bid_history,
                    "market_entries": snapshot.market_entries,
                    "own_meals": snapshot.own_meals,
                    "change_logs": snapshot.change_logs,
                    "snapshot_time": snapshot.timestamp,
                }
            except Exception as e:
                logger.warning(f"TrackerBridge failed, falling back to direct: {e}")

        # Fallback: direct API polling
        return await self._direct_poll(input_data)

    async def _direct_poll(self, input_data: dict) -> dict:
        """Fallback: poll game server directly."""
        turn_id = input_data.get("turn_id", 0)
        result = {
            "all_restaurants": {},
            "bids": [],
            "market_entries": [],
            "own_meals": [],
            "change_logs": {},
            "snapshot_time": 0,
        }

        try:
            async with aiohttp.ClientSession() as session:
                # Fetch restaurants
                async with session.get(
                    f"{BASE_URL}/restaurants", headers=HEADERS
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if isinstance(data, list):
                            result["all_restaurants"] = {
                                r.get("id", i): r for i, r in enumerate(data)
                            }

                # Fetch bid history
                async with session.get(
                    f"{BASE_URL}/bid_history?turn_id={turn_id}", headers=HEADERS
                ) as resp:
                    if resp.status == 200:
                        result["bids"] = await resp.json()

                # Fetch market entries
                async with session.get(
                    f"{BASE_URL}/market/entries", headers=HEADERS
                ) as resp:
                    if resp.status == 200:
                        result["market_entries"] = await resp.json()

                # Fetch our meals
                async with session.get(
                    f"{BASE_URL}/meals?turn_id={turn_id}&restaurant_id={TEAM_ID}",
                    headers=HEADERS,
                ) as resp:
                    if resp.status == 200:
                        result["own_meals"] = await resp.json()

        except Exception as e:
            logger.error(f"Direct polling failed: {e}")

        import time
        result["snapshot_time"] = time.time()
        return result
