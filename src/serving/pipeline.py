"""
Serving pipeline — zero-LLM hot path for the serving phase.

Flow per client:
  client_spawned → match dish → intolerance check →
  fetch client_id (GET /meals) → prepare_dish (MCP) →
  preparation_complete → serve_dish (MCP)
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

import aiohttp

from src.config import BASE_URL, HEADERS, TEAM_ID
from src.memory.client_profile import ClientProfileMemory, IntoleranceDetector
from src.models import ClientProfile, Recipe
from src.serving.order_matcher import OrderMatcher
from src.serving.priority_queue import ClientPriorityQueue, classify_archetype

log = logging.getLogger(__name__)


class ServingPipeline:
    """Hot-path serving: SSE event → dish match → prepare → serve.

    Latency target: <100 ms before ``prepare_dish`` MCP call.
    """

    def __init__(
        self,
        recipes: dict[str, Recipe],
        intolerance: IntoleranceDetector,
        client_memory: ClientProfileMemory,
    ) -> None:
        self.recipes = recipes
        self.intolerance = intolerance
        self.client_memory = client_memory
        self.matcher = OrderMatcher()
        self.queue = ClientPriorityQueue()

        # dish_name → client_id (waiting for preparation_complete)
        self.preparing: dict[str, str] = {}
        self.current_turn: int = 0

        # Shared session — created once per serving phase
        self._session: aiohttp.ClientSession | None = None
        self._mcp_url = f"{BASE_URL}/mcp"

    # ── Lifecycle ────────────────────────────────────────────────

    async def start_phase(self, turn_id: int, menu_items: list[dict]) -> None:
        """Call at beginning of serving phase."""
        self.current_turn = turn_id
        self.preparing.clear()
        self.queue.clear()
        self.matcher.build_lookup(menu_items)
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()

    async def end_phase(self) -> None:
        """Call at end of serving phase."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None

    # ── Event handlers ───────────────────────────────────────────

    async def handle_client_spawned(self, data: dict[str, Any]) -> None:
        """Called on ``client_spawned`` SSE event."""
        client_name = data.get("clientName", "unknown")
        order_text = str(data.get("orderText", ""))

        # Add to priority queue and process immediately
        self.queue.add(data)
        await self._process_next()

    async def handle_preparation_complete(self, data: dict[str, Any]) -> None:
        """Called on ``preparation_complete`` SSE event.

        IMPORTANT: payload field is ``dish`` (not ``dish_name``).
        """
        dish_name = data.get("dish")
        if not dish_name:
            log.warning("preparation_complete without dish field: %s", data)
            return

        client_id = self.preparing.pop(dish_name, None)
        if client_id:
            await self._mcp_serve_dish(dish_name, client_id)
        else:
            log.warning("No waiting client for prepared dish %s", dish_name)

    # ── Internal processing ──────────────────────────────────────

    async def _process_next(self) -> None:
        """Process the highest-priority client in queue."""
        client_data = self.queue.pop()
        if client_data is None:
            return

        client_name = client_data.get("clientName", "unknown")
        order_text = str(client_data.get("orderText", ""))
        archetype = classify_archetype(client_name)

        # 1. Match dish
        dish_name = self.matcher.match(order_text)

        # 1b. Fallback to global cache
        if dish_name is None:
            dish_name = self.client_memory.global_lib.get_cached_dish(order_text)

        if dish_name is None:
            log.info("No dish match for order '%s' from %s", order_text, client_name)
            return

        # 2. Intolerance check
        recipe = self.recipes.get(dish_name)
        if recipe:
            safe_list = self.intolerance.filter_safe_recipes(
                archetype, [recipe]
            )
            if not safe_list:
                # Try to find alternative
                alt = self._find_safe_alternative(archetype)
                if alt:
                    dish_name = alt
                    recipe = self.recipes.get(dish_name)
                else:
                    log.info(
                        "No safe dish for archetype %s — skipping",
                        archetype,
                    )
                    return

        # 3. Fetch client_id from GET /meals
        client_id = await self._resolve_client_id(client_name, order_text)
        if not client_id:
            log.warning("Could not resolve client_id for %s", client_name)
            return

        # 4. Prepare dish
        self.preparing[dish_name] = client_id
        await self._mcp_prepare_dish(dish_name)

        # Record interaction
        profile = ClientProfile(
            archetype=archetype,
            order_text=order_text,
            matched_dish=dish_name,
            client_id=client_id,
            turn_id=self.current_turn,
        )
        self.client_memory.record_interaction(profile)

    def _find_safe_alternative(self, archetype: str) -> str | None:
        """Find the best safe menu dish for this archetype."""
        menu_dishes = list(self.matcher._dishes.values())
        candidates: list[Recipe] = []
        for name in menu_dishes:
            r = self.recipes.get(name)
            if r:
                candidates.append(r)
        safe = self.intolerance.filter_safe_recipes(archetype, candidates)
        if safe:
            return max(safe, key=lambda r: r.prestige).name
        return None

    async def _resolve_client_id(
        self, client_name: str, order_text: str
    ) -> str | None:
        """Fetch ``client_id`` from ``GET /meals``.

        ``client_spawned`` SSE event does NOT include ``client_id``.
        """
        if not self._session:
            return None

        url = (
            f"{BASE_URL}/meals"
            f"?turn_id={self.current_turn}&restaurant_id={TEAM_ID}"
        )
        try:
            async with self._session.get(url, headers=HEADERS) as resp:
                meals = await resp.json()
        except Exception as exc:
            log.error("GET /meals failed: %s", exc)
            return None

        norm_order = order_text.lower().strip()
        for meal in meals:
            if meal.get("executed"):
                continue
            meal_order = str(meal.get("orderText", "")).lower().strip()
            if meal_order == norm_order:
                return str(meal.get("client_id") or meal.get("id", ""))
        return None

    # ── MCP calls ────────────────────────────────────────────────

    async def _mcp_call(self, tool_name: str, arguments: dict) -> dict:
        if not self._session:
            return {"error": "no session"}
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": arguments},
        }
        try:
            async with self._session.post(
                self._mcp_url,
                json=payload,
                headers=HEADERS,
            ) as resp:
                result = await resp.json()
                return result
        except Exception as exc:
            log.error("MCP %s failed: %s", tool_name, exc)
            return {"error": str(exc)}

    async def _mcp_prepare_dish(self, dish_name: str) -> None:
        result = await self._mcp_call(
            "prepare_dish", {"dish_name": dish_name}
        )
        log.info("prepare_dish(%s): %s", dish_name, _mcp_text(result))

    async def _mcp_serve_dish(self, dish_name: str, client_id: str) -> None:
        result = await self._mcp_call(
            "serve_dish", {"dish_name": dish_name, "client_id": client_id}
        )
        log.info("serve_dish(%s, %s): %s", dish_name, client_id, _mcp_text(result))


def _mcp_text(result: dict) -> str:
    """Extract human-readable text from MCP response."""
    try:
        return result["result"]["content"][0]["text"]
    except (KeyError, IndexError, TypeError):
        return str(result)
