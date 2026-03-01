"""
SPAM! — Data Collector Module
===============================
Collects game data via TrackerBridge for the intelligence pipeline.
Falls back to direct API polling if tracker is unreachable.

CRITICAL TIMING NOTE:
  During the speaking phase, the CURRENT turn's bid_history is empty
  (bids haven't happened yet) and during closed_bid they are hidden.
  We must fetch PRIOR turn bid history for feature extraction to work.
  We also accumulate bid history across turns so feature vectors have
  full historical context (bid_consistency, bid_aggressiveness, etc.).
"""

import logging
import time

import aiohttp

from src.config import BASE_URL, HEADERS, TEAM_ID
from src.http_retry import aiohttp_retry_get

logger = logging.getLogger("spam.intelligence.data_collector")


class DataCollectorModule:
    """
    Collects game data via TrackerBridge instead of direct API polling.

    Falls back to direct polling if tracker.py is unreachable.

    HISTORY ACCUMULATION:
      Bid history and market data are accumulated across turns so that
      downstream feature extraction can compute multi-turn behavioural
      signals (bid_consistency, bid_aggressiveness trend, etc.).
    """

    def __init__(self, bridge=None):
        """
        Args:
            bridge: TrackerBridge instance. If None, falls back to direct polling.
        """
        self.bridge = bridge
        # Accumulated cross-turn data
        self._bid_history_by_turn: dict[int, list] = {}   # turn → bids
        self._market_history_by_turn: dict[int, list] = {} # turn → entries
        self._meals_by_turn: dict[int, list] = {}          # turn → meals

    async def process(self, input_data: dict) -> dict:
        """
        Collect all game data for the intelligence pipeline.

        CRITICAL: Fetches PRIOR turn bid history (current turn is
        empty during speaking / hidden during closed_bid).  Merges
        with accumulated history for full multi-turn context.

        Returns dict with keys:
          all_restaurants, bids, market_entries, own_meals, change_logs,
          snapshot_time, bid_history_all, prior_turn_bids
        """
        turn_id = input_data.get("turn_id", 0)

        if self.bridge:
            try:
                snapshot = await self.bridge.snapshot()
                base_result = {
                    "all_restaurants": snapshot.restaurants,
                    "bids": snapshot.bid_history,
                    "market_entries": snapshot.market_entries,
                    "own_meals": snapshot.own_meals,
                    "change_logs": snapshot.change_logs,
                    "snapshot_time": snapshot.timestamp,
                }
            except Exception as e:
                logger.warning(f"TrackerBridge failed, falling back to direct: {e}")
                base_result = await self._direct_poll(input_data)
        else:
            base_result = await self._direct_poll(input_data)

        # ── Fetch PRIOR turn bid history (the one that actually has data) ──
        prior_bids = []
        if turn_id > 1:
            prior_bids = await self._fetch_prior_bids(turn_id)

        # ── Accumulate into cross-turn stores ──
        if prior_bids and (turn_id - 1) not in self._bid_history_by_turn:
            self._bid_history_by_turn[turn_id - 1] = prior_bids
            logger.info(f"Accumulated {len(prior_bids)} bids from turn {turn_id - 1}")

        current_bids = base_result.get("bids", [])
        if current_bids and turn_id not in self._bid_history_by_turn:
            self._bid_history_by_turn[turn_id] = current_bids

        current_market = base_result.get("market_entries", [])
        if current_market:
            self._market_history_by_turn[turn_id] = current_market

        current_meals = base_result.get("own_meals", [])
        if current_meals:
            self._meals_by_turn[turn_id] = current_meals

        # ── Merge all accumulated bids for downstream use ──
        all_bids = []
        for t_bids in self._bid_history_by_turn.values():
            all_bids.extend(t_bids)

        # Use the BEST available bids: prior turn if current is empty
        effective_bids = current_bids if current_bids else prior_bids

        base_result["bids"] = effective_bids
        base_result["bid_history_all"] = all_bids
        base_result["prior_turn_bids"] = prior_bids
        base_result["turn_id"] = turn_id

        logger.info(
            f"Data collected: {len(base_result.get('all_restaurants', {}))} restaurants, "
            f"{len(effective_bids)} effective bids (current={len(current_bids)}, "
            f"prior={len(prior_bids)}), "
            f"{len(all_bids)} total accumulated bids across "
            f"{len(self._bid_history_by_turn)} turns"
        )

        return base_result

    def feed_bid_history(self, turn_id: int, bids: list):
        """Manually feed bid history from info_gather (stopped phase)."""
        if bids and turn_id not in self._bid_history_by_turn:
            self._bid_history_by_turn[turn_id] = bids
            logger.info(f"Fed {len(bids)} bids for turn {turn_id}")

    async def _fetch_prior_bids(self, current_turn: int) -> list:
        """Fetch bid history for the PRIOR turn (turn_id - 1)."""
        prior_turn = current_turn - 1
        if prior_turn <= 0:
            return []

        # Check cache first
        if prior_turn in self._bid_history_by_turn:
            return self._bid_history_by_turn[prior_turn]

        try:
            resp = await aiohttp_retry_get(
                f"{BASE_URL}/bid_history?turn_id={prior_turn}",
                headers=HEADERS, label=f"prior_bids_t{prior_turn}",
            )
            if resp and resp.status == 200:
                bids = await resp.json()
                if bids:
                    self._bid_history_by_turn[prior_turn] = bids
                    logger.info(
                        f"Fetched {len(bids)} prior-turn bids "
                        f"(turn {prior_turn})"
                    )
                    return bids
        except Exception as e:
            logger.warning(f"Failed to fetch prior turn bids: {e}")

        return []

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
            # Fetch restaurants
            resp = await aiohttp_retry_get(
                f"{BASE_URL}/restaurants", headers=HEADERS,
                label="poll_restaurants",
            )
            if resp and resp.status == 200:
                data = await resp.json()
                if isinstance(data, list):
                    result["all_restaurants"] = {
                        r.get("id", i): r for i, r in enumerate(data)
                    }

            # Fetch bid history (current turn — may be empty)
            resp = await aiohttp_retry_get(
                f"{BASE_URL}/bid_history?turn_id={turn_id}",
                headers=HEADERS, label=f"poll_bids_t{turn_id}",
            )
            if resp and resp.status == 200:
                result["bids"] = await resp.json()

            # Fetch market entries
            resp = await aiohttp_retry_get(
                f"{BASE_URL}/market/entries", headers=HEADERS,
                label="poll_market",
            )
            if resp and resp.status == 200:
                result["market_entries"] = await resp.json()

            # Fetch our meals
            resp = await aiohttp_retry_get(
                f"{BASE_URL}/meals?turn_id={turn_id}&restaurant_id={TEAM_ID}",
                headers=HEADERS, label=f"poll_meals_t{turn_id}",
            )
            if resp and resp.status == 200:
                result["own_meals"] = await resp.json()

        except Exception as e:
            logger.error(f"Direct polling failed: {e}")

        result["snapshot_time"] = time.time()
        return result
