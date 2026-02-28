"""
SPAM! — Serving Pipeline
==========================
Zero-LLM hot path for serving clients.

Flow: client_spawned → order match → intolerance check → resolve client_id
      → prepare_dish → (preparation_complete) → serve_dish

Design principle: NO LLM calls in the common case.
Total latency target: <100ms before prepare_dish call.
"""

import asyncio
import logging

import aiohttp

from src.config import BASE_URL, HEADERS, TEAM_ID
from src.memory.client_profile import (
    ClientProfile,
    GlobalClientLibrary,
    IntoleranceDetector,
)
from src.serving.order_matcher import OrderMatcher
from src.serving.priority_queue import ClientPriorityQueue, classify_archetype

logger = logging.getLogger("spam.serving.pipeline")


class ServingPipeline:
    """
    Hot path: SSE event → dish match → prepare → serve
    Total latency target: <100ms before prepare_dish call.

    Uses NO LLM calls for the common case. Only for genuinely
    ambiguous orders (Tier 3 fallback, <5% of cases).
    """

    def __init__(
        self,
        recipes: dict[str, dict],
        intolerance_detector: IntoleranceDetector,
        client_library: GlobalClientLibrary,
        mcp_client=None,
    ):
        """
        Args:
            recipes: dict mapping recipe_name → {ingredients: {name: qty}, prestige, prep_time, ...}
            intolerance_detector: Bayesian intolerance detector
            client_library: Global client knowledge base
            mcp_client: datapizza MCPClient for MCP calls
        """
        self.recipes = recipes
        self.intolerance_detector = intolerance_detector
        self.client_library = client_library
        self.mcp_client = mcp_client

        # Set during waiting phase
        self.menu: dict[str, dict] = {}  # dish_name → {name, price}
        self.order_matcher: OrderMatcher | None = None
        self.priority_queue = ClientPriorityQueue()

        # Serving state
        self.preparing: dict[str, str] = {}  # dish_name → client_id
        self.current_turn: int = 0
        self._session: aiohttp.ClientSession | None = None

        # Tracking
        self.served_this_turn: list[ClientProfile] = []
        self._client_orders: dict[str, dict] = {}  # order_text → client_data

    def set_menu(self, menu_items: list[dict]):
        """
        Set the current menu and rebuild the order matcher.
        Called during waiting phase before serving starts.
        """
        self.menu = {item["name"]: item for item in menu_items}
        self.order_matcher = OrderMatcher(
            menu_items,
            order_cache=self.client_library.order_to_dish_cache,
        )
        logger.info(f"Menu set with {len(menu_items)} items")

    async def start_serving(self, turn_id: int):
        """Called at the start of serving phase."""
        self.current_turn = turn_id
        self.priority_queue.clear()
        self.preparing.clear()
        self.served_this_turn.clear()
        self._client_orders.clear()
        # Create shared session (reuse across all client_id resolutions)
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        logger.info(f"Serving started for turn {turn_id}")

    async def stop_serving(self):
        """Called at end of serving phase."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None
        logger.info(
            f"Serving ended: {len(self.served_this_turn)} clients served"
        )

    async def handle_client(self, data: dict):
        """
        Called on client_spawned SSE event.

        data: {clientName: str, orderText: str}
        NOTE: client_id is NOT in client_spawned — must resolve from GET /meals
        """
        client_name = data.get("clientName", "unknown")
        order_text = data.get("orderText", "")

        logger.info(f"Client spawned: {client_name} — '{order_text}'")

        # Add to priority queue
        self.priority_queue.add_client(data)

        # Process queue (serve highest priority first)
        await self._process_queue()

    async def _process_queue(self):
        """Process the priority queue, serving clients in priority order."""
        while not self.priority_queue.is_empty():
            client_data = self.priority_queue.next_client()
            if client_data:
                await self._serve_client(client_data)

    async def _serve_client(self, client_data: dict):
        """
        Process a single client through the serving pipeline.

        Flow:
        1. Normalize order text
        2. Match to menu dish (3-tier: exact → fuzzy → LLM)
        3. Check intolerance safety
        4. Fetch client_id from GET /meals
        5. prepare_dish via MCP
        6. (preparation_complete will trigger serve_dish)
        """
        client_name = client_data.get("clientName", "unknown")
        order_text = client_data.get("orderText", "")
        archetype = client_data.get("_archetype", classify_archetype(client_name))

        # Step 1-2: Match dish
        if self.order_matcher is None:
            logger.error("Order matcher not initialized — menu not set")
            return

        dish = self.order_matcher.match(order_text)
        if dish is None:
            logger.warning(f"No dish match for '{order_text}' — skipping client")
            return

        # Step 3: Intolerance check
        recipe = self.recipes.get(dish, {})
        recipe_ings = list(recipe.get("ingredients", {}).keys())

        if not self.intolerance_detector.is_recipe_safe(archetype, recipe_ings):
            # Try to find a safe alternative
            alt_dish = self._find_safe_alternative(archetype)
            if alt_dish:
                logger.info(f"Swapped {dish} → {alt_dish} (intolerance risk for {archetype})")
                dish = alt_dish
            else:
                logger.warning(f"No safe dish for {archetype} — serving anyway (risky)")

        # Step 4: Fetch client_id
        client_id = await self._resolve_client_id(client_name, order_text)
        if client_id is None:
            logger.warning(f"Could not resolve client_id for {client_name}")
            return

        # Step 5: Prepare dish via MCP
        self.preparing[dish] = client_id
        self._client_orders[dish] = {
            "client_name": client_name,
            "order_text": order_text,
            "archetype": archetype,
            "dish": dish,
            "client_id": client_id,
        }

        await self._mcp_prepare_dish(dish)

    async def handle_preparation_complete(self, data: dict):
        """
        Called on preparation_complete SSE event.

        IMPORTANT: SSE payload field is 'dish' (not 'dish_name').
        """
        dish_name = data.get("dish")
        if not dish_name:
            logger.warning("preparation_complete without dish name")
            return

        client_id = self.preparing.pop(dish_name, None)
        if client_id:
            await self._mcp_serve_dish(dish_name, client_id)

            # Track the serve
            client_data = self._client_orders.pop(dish_name, {})
            profile = ClientProfile(
                archetype=client_data.get("archetype", "unknown"),
                order_text=client_data.get("order_text", ""),
                matched_dish=dish_name,
                served=True,
                turn_id=self.current_turn,
            )
            self.served_this_turn.append(profile)

            # Update order cache
            if client_data.get("order_text"):
                self.order_matcher.add_to_cache(client_data["order_text"], dish_name)

            logger.info(f"Served {dish_name} to client {client_id}")
        else:
            logger.warning(f"preparation_complete for unknown dish: {dish_name}")

    def _find_safe_alternative(self, archetype: str) -> str | None:
        """Find the best safe menu dish for this archetype."""
        safe_dishes = []
        for dish_name in self.menu:
            recipe = self.recipes.get(dish_name, {})
            ings = list(recipe.get("ingredients", {}).keys())
            if self.intolerance_detector.is_recipe_safe(archetype, ings):
                prestige = recipe.get("prestige", 0)
                safe_dishes.append((dish_name, prestige))

        if safe_dishes:
            # Pick highest prestige safe dish
            safe_dishes.sort(key=lambda x: x[1], reverse=True)
            return safe_dishes[0][0]
        return None

    async def _resolve_client_id(self, client_name: str, order_text: str) -> str | None:
        """
        Fetch client_id from GET /meals endpoint.

        client_spawned SSE event does NOT include client_id.
        We must query GET /meals?turn_id=<id>&restaurant_id=17
        and match by order text to find the correct client_id.
        """
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()

        url = f"{BASE_URL}/meals?turn_id={self.current_turn}&restaurant_id={TEAM_ID}"
        try:
            async with self._session.get(url, headers=HEADERS) as resp:
                if resp.status != 200:
                    logger.error(f"GET /meals returned {resp.status}")
                    return None
                meals = await resp.json()

            # Match by order text — skip already-executed meals
            for meal in meals:
                if meal.get("executed"):
                    continue
                if meal.get("orderText", "").lower() == order_text.lower():
                    cid = self._extract_client_id(meal)
                    if cid:
                        return cid

            # Fallback: match by client name
            for meal in meals:
                if meal.get("executed"):
                    continue
                if meal.get("clientName", "").lower() == client_name.lower():
                    cid = self._extract_client_id(meal)
                    if cid:
                        return cid

            # Last resort: return first unexecuted meal
            for meal in meals:
                if not meal.get("executed"):
                    cid = self._extract_client_id(meal)
                    if cid:
                        return cid

        except Exception as e:
            logger.error(f"Failed to resolve client_id: {e}")

        return None

    @staticmethod
    def _extract_client_id(meal: dict) -> str | None:
        """Extract client_id from a /meals response entry.

        The API field may be 'id', 'client_id', or 'mealId'.
        Try all known candidates and log which one matched so we can
        converge on the correct field name at runtime.
        """
        for field in ("id", "client_id", "mealId"):
            val = meal.get(field)
            if val is not None:
                logger.debug(f"client_id resolved via field '{field}' = {val}")
                return str(val)
        logger.warning(f"No client_id field found in meal keys: {list(meal.keys())}")
        return None

    async def _mcp_prepare_dish(self, dish_name: str):
        """Call prepare_dish via MCP."""
        if self.mcp_client is None:
            logger.error("MCP client not set — cannot prepare dish")
            return
        try:
            result = await self.mcp_client.call_tool(
                "prepare_dish", {"dish_name": dish_name}
            )
            logger.debug(f"prepare_dish({dish_name}): {result}")
        except Exception as e:
            logger.error(f"prepare_dish failed for {dish_name}: {e}")

    async def _mcp_serve_dish(self, dish_name: str, client_id: str):
        """Call serve_dish via MCP."""
        if self.mcp_client is None:
            logger.error("MCP client not set — cannot serve dish")
            return
        try:
            result = await self.mcp_client.call_tool(
                "serve_dish", {"dish_name": dish_name, "client_id": client_id}
            )
            logger.debug(f"serve_dish({dish_name}, {client_id}): {result}")
        except Exception as e:
            logger.error(f"serve_dish failed for {dish_name}: {e}")

    def get_turn_profiles(self) -> list[ClientProfile]:
        """Get all client profiles from this turn (for end-of-turn learning)."""
        return self.served_this_turn
