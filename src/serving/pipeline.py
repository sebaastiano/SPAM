"""
SPAM! — Serving Pipeline
==========================
Zero-LLM hot path for serving clients.

Flow: client_spawned → order match → intolerance check → resolve client_id
      → prepare_dish → (preparation_complete) → serve_dish

Design principle: NO LLM calls in the common case.
Total latency target: <100ms before prepare_dish call.

HARDENED for reliability:
  - Ingredient accounting (prevents over-committing)
  - FIFO preparation queue per dish (handles duplicate orders)
  - MCP retry with isError checking
  - Client ID resolution with caching + retry
  - Preparation timeout watchdog
  - Overflow protection (auto-close when capacity exhausted)
  - Concurrency-safe queue processing
"""

import asyncio
import collections
import logging
import time
from dataclasses import dataclass, field

import aiohttp

from src.config import BASE_URL, HEADERS, TEAM_ID
from src.memory.client_profile import (
    ClientProfile,
    GlobalClientLibrary,
    IntoleranceDetector,
)
from src.serving.archetype_classifier import ArchetypeClassifier
from src.serving.order_matcher import OrderMatcher
from src.serving.priority_queue import ClientPriorityQueue, classify_archetype

logger = logging.getLogger("spam.serving.pipeline")

# ── Constants ──
MAX_MCP_RETRIES = 3
MCP_RETRY_BASE_DELAY = 0.3  # seconds
PREP_TIMEOUT_MULTIPLIER = 2.5  # prep_time * this = max wait
PREP_TIMEOUT_BUFFER = 5.0  # extra seconds on top
MEALS_CACHE_TTL = 2.0  # seconds before refreshing /meals cache
MIN_INGREDIENTS_FOR_OPEN = 1  # close restaurant if fewer unique dishes cookable


@dataclass
class PendingPreparation:
    """Track a dish currently being prepared for a specific client."""
    dish_name: str
    client_id: str
    client_name: str
    order_text: str
    archetype: str
    started_at: float
    expected_prep_time: float  # from recipe database (seconds)


@dataclass
class ServingMetrics:
    """Per-turn serving statistics for debugging and learning."""
    clients_received: int = 0
    clients_matched: int = 0
    clients_no_match: int = 0
    clients_no_id: int = 0
    clients_no_ingredients: int = 0
    preparations_started: int = 0
    preparations_completed: int = 0
    preparations_timed_out: int = 0
    serves_successful: int = 0
    serves_failed: int = 0
    mcp_retries: int = 0
    mcp_errors: int = 0
    intolerance_swaps: int = 0
    restaurant_closed_overflow: bool = False


class ServingPipeline:
    """
    Hot path: SSE event → dish match → prepare → serve
    Total latency target: <100ms before prepare_dish call.

    Uses NO LLM calls for the common case. Only for genuinely
    ambiguous orders (Tier 3 fallback, <5% of cases).

    HARDENED:
     - FIFO deque per dish name in self.preparing (handles duplicate orders)
     - Real-time ingredient accounting (prevents over-commitment)
     - MCP retry with exponential backoff + isError checking
     - Cached /meals resolution with TTL refresh
     - Preparation timeout watchdog task
     - Auto-close when cookable dishes exhausted
    """

    def __init__(
        self,
        recipes: dict[str, dict],
        intolerance_detector: IntoleranceDetector,
        client_library: GlobalClientLibrary,
        mcp_client=None,
        archetype_classifier: ArchetypeClassifier | None = None,
    ):
<<<<<<< HEAD
=======
        """
        Args:
            recipes: dict mapping recipe_name → {ingredients: {name: qty}, prestige, prep_time, ...}
            intolerance_detector: Bayesian intolerance detector
            client_library: Global client knowledge base
            mcp_client: datapizza MCPClient for MCP calls
            archetype_classifier: LLM-based archetype classifier (Regolo gpt-oss-120b)
        """
>>>>>>> 8393507 (added the archetipe classificator)
        self.recipes = recipes
        self.intolerance_detector = intolerance_detector
        self.client_library = client_library
        self.mcp_client = mcp_client
        self.archetype_classifier = archetype_classifier or ArchetypeClassifier()

        # Set during waiting phase
        self.menu: dict[str, dict] = {}  # dish_name → {name, price}
        self.order_matcher: OrderMatcher | None = None
        self.priority_queue = ClientPriorityQueue()

        # Serving state — FIFO deque per dish name
        self.preparing: dict[str, collections.deque[PendingPreparation]] = {}
        self.current_turn: int = 0
        self._session: aiohttp.ClientSession | None = None

        # Ingredient accounting — real-time tracking
        self._committed_ingredients: dict[str, int] = {}  # ing → committed qty
        self._inventory_snapshot: dict[str, int] = {}  # captured at start_serving

        # Client ID resolution cache
        self._meals_cache: list[dict] | None = None
        self._meals_cache_time: float = 0.0
        self._resolved_meal_ids: set[str] = set()  # already-used meal IDs

        # Concurrency control
        self._queue_lock = asyncio.Lock()
        self._processing = False

        # Timeout watchdog
        self._timeout_task: asyncio.Task | None = None

        # Tracking
        self.served_this_turn: list[ClientProfile] = []
        self._client_orders: dict[str, dict] = {}  # client_id → client_data
        self.metrics = ServingMetrics()

        # Restaurant closure
        self._is_open = True

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

    def set_inventory_snapshot(self, inventory: dict[str, int]):
        """
        Capture the inventory at the start of serving.
        Used for real-time ingredient accounting.
        """
        self._inventory_snapshot = dict(inventory)
        self._committed_ingredients.clear()
        logger.info(f"Inventory snapshot: {sum(inventory.values())} total items")

    async def start_serving(self, turn_id: int):
        """Called at the start of serving phase."""
        self.current_turn = turn_id
        self.priority_queue.clear()
        self.preparing.clear()
        self.served_this_turn.clear()
        self._client_orders.clear()
        self._committed_ingredients.clear()
        self._meals_cache = None
        self._meals_cache_time = 0.0
        self._resolved_meal_ids.clear()
        self.metrics = ServingMetrics()
        self._is_open = True

        # Create shared session
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()

        # Start timeout watchdog
        self._timeout_task = asyncio.create_task(self._preparation_timeout_watchdog())

        logger.info(f"Serving started for turn {turn_id}")

    async def stop_serving(self):
        """Called at end of serving phase."""
        # Cancel timeout watchdog
        if self._timeout_task and not self._timeout_task.done():
            self._timeout_task.cancel()
            try:
                await self._timeout_task
            except asyncio.CancelledError:
                pass

        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None

        # Log any still-pending preparations
        pending_count = sum(len(q) for q in self.preparing.values())
        if pending_count:
            logger.warning(
                f"Serving ended with {pending_count} preparations still pending"
            )

        m = self.metrics
        logger.info(
            f"Serving ended: "
            f"received={m.clients_received} matched={m.clients_matched} "
            f"prepared={m.preparations_started} served={m.serves_successful} "
            f"failed={m.serves_failed} no_match={m.clients_no_match} "
            f"no_id={m.clients_no_id} no_ingredients={m.clients_no_ingredients} "
            f"timeouts={m.preparations_timed_out} mcp_retries={m.mcp_retries} "
            f"mcp_errors={m.mcp_errors} swaps={m.intolerance_swaps}"
        )

    async def handle_client(self, data: dict):
        """
        Called on client_spawned SSE event.

        data: {clientName: str, orderText: str}
        NOTE: client_id is NOT in client_spawned — must resolve from GET /meals
        """
        self.metrics.clients_received += 1
        client_name = data.get("clientName", "unknown")
        order_text = data.get("orderText", "")

        logger.info(f"Client spawned: {client_name} — '{order_text}'")

        # Check if we're still open
        if not self._is_open:
            logger.info(f"Restaurant closed — skipping {client_name}")
            return

        # Add to priority queue
        self.priority_queue.add_client(data)

        # Process queue (with concurrency guard)
        await self._process_queue()

    async def _process_queue(self):
        """
        Process the priority queue, serving clients in priority order.
        Uses a lock to prevent re-entrant processing from concurrent
        client_spawned events.
        """
        async with self._queue_lock:
            if self._processing:
                return  # another coroutine is draining the queue
            self._processing = True

        try:
            while not self.priority_queue.is_empty():
                if not self._is_open:
                    break
                client_data = self.priority_queue.next_client()
                if client_data:
                    await self._serve_client(client_data)
        finally:
            self._processing = False

    async def _serve_client(self, client_data: dict):
        """
        Process a single client through the serving pipeline.

        Flow:
        1. Match order to menu dish (3-tier: exact → fuzzy → LLM)
        2. Check intolerance safety (swap if needed)
        3. Verify ingredient availability (accounting check)
        4. Resolve client_id from GET /meals (cached)
        5. Commit ingredients
        6. prepare_dish via MCP (with retry)
        7. (preparation_complete will trigger serve_dish)
        """
        client_name = client_data.get("clientName", "unknown")
        order_text = client_data.get("orderText", "")

        # Classify archetype from order text via LLM (Regolo gpt-oss-120b)
        # Falls back to name-based heuristic if LLM fails
        name_archetype = client_data.get("_archetype", classify_archetype(client_name))
        try:
            llm_archetype, confidence = await self.archetype_classifier.classify(
                order_text=order_text,
                client_name=client_name,
            )
            if llm_archetype != "unknown" and confidence >= 0.5:
                archetype = llm_archetype
                logger.info(
                    f"Archetype override: {name_archetype} → {llm_archetype} "
                    f"(conf={confidence:.2f}) for '{order_text[:50]}'"
                )
            else:
                archetype = name_archetype
        except Exception as exc:
            logger.warning(f"Archetype classification error, falling back: {exc}")
            archetype = name_archetype

        # Step 1: Match dish
        if self.order_matcher is None:
            logger.error("Order matcher not initialized — menu not set")
            return

        dish = self.order_matcher.match(order_text)
        if dish is None:
            logger.warning(f"No dish match for '{order_text}' — skipping client")
            self.metrics.clients_no_match += 1
            return

        self.metrics.clients_matched += 1

        # Step 2: Intolerance check
        recipe = self.recipes.get(dish, {})
        recipe_ings = list(recipe.get("ingredients", {}).keys())

        if not self.intolerance_detector.is_recipe_safe(archetype, recipe_ings):
            alt_dish = self._find_safe_alternative_with_ingredients(archetype)
            if alt_dish:
                logger.info(
                    f"Swapped {dish} → {alt_dish} "
                    f"(intolerance risk for {archetype})"
                )
                dish = alt_dish
                recipe = self.recipes.get(dish, {})
                self.metrics.intolerance_swaps += 1
            else:
                logger.warning(
                    f"No safe+available dish for {archetype} — "
                    f"serving {dish} anyway (risky)"
                )

        # Step 3: Verify ingredient availability
        if not self._can_cook(dish):
            # Try to find ANY cookable dish from the menu
            fallback = self._find_any_cookable_dish(archetype)
            if fallback:
                logger.info(
                    f"Ingredient shortage for {dish} → using {fallback}"
                )
                dish = fallback
                recipe = self.recipes.get(dish, {})
            else:
                logger.warning(
                    f"No cookable dishes remaining — "
                    f"skipping {client_name}, closing restaurant"
                )
                self.metrics.clients_no_ingredients += 1
                await self._close_restaurant()
                return

        # Step 4: Resolve client_id
        client_id = await self._resolve_client_id(client_name, order_text)
        if client_id is None:
            logger.warning(f"Could not resolve client_id for {client_name}")
            self.metrics.clients_no_id += 1
            return

        # Step 5: Commit ingredients (mark as used BEFORE prepare_dish)
        self._commit_ingredients(dish)

        # Step 6: Prepare dish via MCP (with retry)
        prep_time = recipe.get("prep_time", 5000.0)
        if prep_time > 100:  # likely in milliseconds
            prep_time = prep_time / 1000.0  # convert to seconds

        pending = PendingPreparation(
            dish_name=dish,
            client_id=client_id,
            client_name=client_name,
            order_text=order_text,
            archetype=archetype,
            started_at=time.time(),
            expected_prep_time=prep_time,
        )

        # FIFO queue per dish name
        if dish not in self.preparing:
            self.preparing[dish] = collections.deque()
        self.preparing[dish].append(pending)

        self._client_orders[client_id] = {
            "client_name": client_name,
            "order_text": order_text,
            "archetype": archetype,
            "dish": dish,
            "client_id": client_id,
        }

        success = await self._mcp_prepare_dish(dish)
        if success:
            self.metrics.preparations_started += 1
        else:
            # Prepare failed — rollback ingredients and remove from queue
            self._uncommit_ingredients(dish)
            if dish in self.preparing and self.preparing[dish]:
                self.preparing[dish].pop()  # remove the pending we just added
                if not self.preparing[dish]:
                    del self.preparing[dish]
            self._client_orders.pop(client_id, None)
            logger.error(f"prepare_dish permanently failed for {dish}")

    async def handle_preparation_complete(self, data: dict):
        """
        Called on preparation_complete SSE event.

        IMPORTANT: SSE payload field is 'dish' (not 'dish_name').

        Uses FIFO deque to correctly match duplicate dish preparations
        to their respective clients.
        """
        dish_name = data.get("dish")
        if not dish_name:
            logger.warning("preparation_complete without dish name")
            return

        self.metrics.preparations_completed += 1

        # FIFO: pop the OLDEST pending preparation for this dish
        pending_queue = self.preparing.get(dish_name)
        if not pending_queue:
            logger.warning(
                f"preparation_complete for unknown/untracked dish: {dish_name}"
            )
            return

        pending = pending_queue.popleft()
        if not pending_queue:
            del self.preparing[dish_name]

        # Serve the dish to the correct client
        success = await self._mcp_serve_dish(dish_name, pending.client_id)

        if success:
            self.metrics.serves_successful += 1

            # Track the serve
            profile = ClientProfile(
                archetype=pending.archetype,
                order_text=pending.order_text,
                matched_dish=dish_name,
                served=True,
                turn_id=self.current_turn,
            )
            self.served_this_turn.append(profile)

            # Update order cache for future matching
            if pending.order_text:
                self.order_matcher.add_to_cache(pending.order_text, dish_name)

            elapsed = time.time() - pending.started_at
            logger.info(
                f"Served {dish_name} to {pending.client_name} "
                f"(client_id={pending.client_id}, elapsed={elapsed:.1f}s)"
            )
        else:
            self.metrics.serves_failed += 1
            logger.error(
                f"serve_dish FAILED for {dish_name} / {pending.client_id}"
            )

        # Cleanup
        self._client_orders.pop(pending.client_id, None)

    # ── Ingredient Accounting ──

    def _can_cook(self, dish_name: str) -> bool:
        """Check if we have uncommitted ingredients to cook this dish."""
        recipe = self.recipes.get(dish_name, {})
        for ing, qty in recipe.get("ingredients", {}).items():
            available = (
                self._inventory_snapshot.get(ing, 0)
                - self._committed_ingredients.get(ing, 0)
            )
            if available < qty:
                return False
        return True

    def _commit_ingredients(self, dish_name: str):
        """Mark ingredients as committed (reserved for this preparation)."""
        recipe = self.recipes.get(dish_name, {})
        for ing, qty in recipe.get("ingredients", {}).items():
            self._committed_ingredients[ing] = (
                self._committed_ingredients.get(ing, 0) + qty
            )

    def _uncommit_ingredients(self, dish_name: str):
        """Release committed ingredients (preparation failed/cancelled)."""
        recipe = self.recipes.get(dish_name, {})
        for ing, qty in recipe.get("ingredients", {}).items():
            current = self._committed_ingredients.get(ing, 0)
            self._committed_ingredients[ing] = max(0, current - qty)

    def _cookable_menu_dishes(self) -> list[str]:
        """Return list of menu dishes we can still cook with uncommitted inventory."""
        cookable = []
        for dish_name in self.menu:
            if self._can_cook(dish_name):
                cookable.append(dish_name)
        return cookable

    # ── Safe Alternatives ──

    def _find_safe_alternative_with_ingredients(self, archetype: str) -> str | None:
        """Find the best safe AND cookable menu dish for this archetype."""
        safe_dishes = []
        for dish_name in self.menu:
            if not self._can_cook(dish_name):
                continue
            recipe = self.recipes.get(dish_name, {})
            ings = list(recipe.get("ingredients", {}).keys())
            if self.intolerance_detector.is_recipe_safe(archetype, ings):
                prestige = recipe.get("prestige", 0)
                safe_dishes.append((dish_name, prestige))

        if safe_dishes:
            safe_dishes.sort(key=lambda x: x[1], reverse=True)
            return safe_dishes[0][0]
        return None

    def _find_safe_alternative(self, archetype: str) -> str | None:
        """Find the best safe menu dish (ignoring ingredients)."""
        safe_dishes = []
        for dish_name in self.menu:
            recipe = self.recipes.get(dish_name, {})
            ings = list(recipe.get("ingredients", {}).keys())
            if self.intolerance_detector.is_recipe_safe(archetype, ings):
                prestige = recipe.get("prestige", 0)
                safe_dishes.append((dish_name, prestige))

        if safe_dishes:
            safe_dishes.sort(key=lambda x: x[1], reverse=True)
            return safe_dishes[0][0]
        return None

    def _find_any_cookable_dish(self, archetype: str) -> str | None:
        """Find ANY menu dish we can still cook, preferring safe ones."""
        # First try safe + cookable
        safe = self._find_safe_alternative_with_ingredients(archetype)
        if safe:
            return safe

        # Then any cookable
        cookable = self._cookable_menu_dishes()
        if cookable:
            # Pick highest prestige
            best = max(
                cookable,
                key=lambda d: self.recipes.get(d, {}).get("prestige", 0),
            )
            return best
        return None

    # ── Client ID Resolution (Cached) ──

    async def _resolve_client_id(
        self, client_name: str, order_text: str
    ) -> str | None:
        """
        Resolve client_id from GET /meals endpoint with caching.

        client_spawned SSE does NOT include client_id.
        We query GET /meals and match by order text / client name.

        Caching: refreshes at most every MEALS_CACHE_TTL seconds.
        Retry: if no match found, force-refresh cache once and retry.
        """
        # Try with current cache
        client_id = await self._try_resolve_from_meals(client_name, order_text)
        if client_id:
            return client_id

        # Force refresh and retry (meal may not have appeared yet)
        await asyncio.sleep(0.3)  # brief wait for server-side propagation
        self._meals_cache = None  # force refresh
        client_id = await self._try_resolve_from_meals(client_name, order_text)
        if client_id:
            return client_id

        # Second retry with longer wait
        await asyncio.sleep(0.7)
        self._meals_cache = None
        return await self._try_resolve_from_meals(client_name, order_text)

    async def _try_resolve_from_meals(
        self, client_name: str, order_text: str
    ) -> str | None:
        """Single attempt to resolve client_id from /meals."""
        meals = await self._get_meals_cached()
        if not meals:
            return None

        # Strategy 1: Match by order text (most reliable)
        for meal in meals:
            if meal.get("executed"):
                continue
            meal_id = self._extract_client_id(meal)
            if not meal_id or meal_id in self._resolved_meal_ids:
                continue
            if meal.get("orderText", "").lower().strip() == order_text.lower().strip():
                self._resolved_meal_ids.add(meal_id)
                return meal_id

        # Strategy 2: Match by client name
        for meal in meals:
            if meal.get("executed"):
                continue
            meal_id = self._extract_client_id(meal)
            if not meal_id or meal_id in self._resolved_meal_ids:
                continue
            if meal.get("clientName", "").lower() == client_name.lower():
                self._resolved_meal_ids.add(meal_id)
                return meal_id

        # Strategy 3: First unresolved unexecuted meal (last resort)
        for meal in meals:
            if meal.get("executed"):
                continue
            meal_id = self._extract_client_id(meal)
            if meal_id and meal_id not in self._resolved_meal_ids:
                logger.warning(
                    f"Last-resort meal match for {client_name}: "
                    f"meal_id={meal_id}"
                )
                self._resolved_meal_ids.add(meal_id)
                return meal_id

        return None

    async def _get_meals_cached(self) -> list[dict]:
        """Fetch /meals with TTL caching."""
        now = time.time()
        if (
            self._meals_cache is not None
            and (now - self._meals_cache_time) < MEALS_CACHE_TTL
        ):
            return self._meals_cache

        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()

        url = f"{BASE_URL}/meals?turn_id={self.current_turn}&restaurant_id={TEAM_ID}"
        try:
            async with self._session.get(url, headers=HEADERS) as resp:
                if resp.status != 200:
                    logger.error(f"GET /meals returned {resp.status}")
                    return self._meals_cache or []
                meals = await resp.json()
                self._meals_cache = meals
                self._meals_cache_time = now
                return meals
        except Exception as e:
            logger.error(f"GET /meals failed: {e}")
            return self._meals_cache or []

    @staticmethod
    def _extract_client_id(meal: dict) -> str | None:
        """Extract client_id from a /meals response entry."""
        for field_name in ("id", "client_id", "mealId"):
            val = meal.get(field_name)
            if val is not None:
                return str(val)
        return None

    # ── MCP Calls (with retry + isError checking) ──

    async def _mcp_prepare_dish(self, dish_name: str) -> bool:
        """Call prepare_dish via MCP with retry logic."""
        return await self._mcp_call_with_retry(
            "prepare_dish", {"dish_name": dish_name}
        )

    async def _mcp_serve_dish(self, dish_name: str, client_id: str) -> bool:
        """Call serve_dish via MCP with retry logic."""
        return await self._mcp_call_with_retry(
            "serve_dish", {"dish_name": dish_name, "client_id": client_id}
        )

    async def _mcp_call_with_retry(
        self, tool_name: str, args: dict
    ) -> bool:
        """
        MCP call with exponential backoff retry.
        Checks both exceptions AND isError in response.
        Returns True if successful, False on permanent failure.
        """
        if self.mcp_client is None:
            logger.error(f"MCP client not set — cannot call {tool_name}")
            self.metrics.mcp_errors += 1
            return False

        for attempt in range(MAX_MCP_RETRIES):
            try:
                result = await self.mcp_client.call_tool(tool_name, args)

                # Check for isError in response
                if self._is_mcp_error(result):
                    error_text = self._extract_mcp_error_text(result)
                    logger.warning(
                        f"{tool_name} returned isError=true (attempt {attempt+1}): "
                        f"{error_text}"
                    )
                    # Don't retry certain permanent errors
                    if any(
                        phrase in error_text.lower()
                        for phrase in [
                            "not found",
                            "not in menu",
                            "not on the menu",
                            "insufficient",
                            "already served",
                            "already executed",
                            "invalid",
                        ]
                    ):
                        self.metrics.mcp_errors += 1
                        return False
                    # Transient error — retry
                    if attempt < MAX_MCP_RETRIES - 1:
                        self.metrics.mcp_retries += 1
                        await asyncio.sleep(
                            MCP_RETRY_BASE_DELAY * (2 ** attempt)
                        )
                        continue
                    self.metrics.mcp_errors += 1
                    return False

                logger.debug(f"{tool_name}({args}): OK")
                return True

            except Exception as e:
                logger.warning(
                    f"{tool_name} exception (attempt {attempt+1}/{MAX_MCP_RETRIES}): {e}"
                )
                if attempt < MAX_MCP_RETRIES - 1:
                    self.metrics.mcp_retries += 1
                    await asyncio.sleep(MCP_RETRY_BASE_DELAY * (2 ** attempt))
                else:
                    self.metrics.mcp_errors += 1
                    return False

        return False

    @staticmethod
    def _is_mcp_error(result) -> bool:
        """Check if MCP response indicates an error."""
        if result is None:
            return True
        if isinstance(result, dict):
            # Direct format: {isError: true, content: [...]}
            if result.get("isError"):
                return True
            # Wrapped format: {result: {isError: true, ...}}
            inner = result.get("result", {})
            if isinstance(inner, dict) and inner.get("isError"):
                return True
        # datapizza MCPClient may return an object with .isError attribute
        if hasattr(result, "isError") and result.isError:
            return True
        return False

    @staticmethod
    def _extract_mcp_error_text(result) -> str:
        """Extract error message from MCP response."""
        if isinstance(result, dict):
            content = result.get("content") or result.get("result", {}).get("content", [])
            if isinstance(content, list) and content:
                return content[0].get("text", str(content[0]))
            return str(result)
        if hasattr(result, "content"):
            content = result.content
            if isinstance(content, list) and content:
                return getattr(content[0], "text", str(content[0]))
        return str(result)

    # ── Preparation Timeout Watchdog ──

    async def _preparation_timeout_watchdog(self):
        """
        Background task that checks for timed-out preparations.
        Runs every 2 seconds during serving phase.

        If a preparation exceeds expected_prep_time * MULTIPLIER + BUFFER,
        we assume it failed and release the resources.
        """
        try:
            while True:
                await asyncio.sleep(2.0)
                now = time.time()

                for dish_name in list(self.preparing.keys()):
                    queue = self.preparing.get(dish_name)
                    if not queue:
                        continue

                    # Check oldest (front of deque)
                    oldest = queue[0]
                    timeout = (
                        oldest.expected_prep_time * PREP_TIMEOUT_MULTIPLIER
                        + PREP_TIMEOUT_BUFFER
                    )
                    elapsed = now - oldest.started_at

                    if elapsed > timeout:
                        logger.error(
                            f"TIMEOUT: {dish_name} for {oldest.client_name} "
                            f"(elapsed={elapsed:.1f}s, timeout={timeout:.1f}s) "
                            f"— removing from queue"
                        )
                        queue.popleft()
                        if not queue:
                            del self.preparing[dish_name]

                        self._uncommit_ingredients(dish_name)
                        self._client_orders.pop(oldest.client_id, None)
                        self.metrics.preparations_timed_out += 1

        except asyncio.CancelledError:
            pass

    # ── Overflow Protection ──

    async def _close_restaurant(self):
        """Close restaurant when we can't serve any more clients."""
        if not self._is_open:
            return
        self._is_open = False
        self.metrics.restaurant_closed_overflow = True
        logger.warning("CLOSING RESTAURANT — no cookable dishes remaining")

        if self.mcp_client:
            try:
                await self.mcp_client.call_tool(
                    "update_restaurant_is_open", {"is_open": False}
                )
                logger.info("Restaurant closed via MCP")
            except Exception as e:
                logger.error(f"Failed to close restaurant: {e}")

    # ── Accessors ──

    def get_turn_profiles(self) -> list[ClientProfile]:
        """Get all client profiles from this turn (for end-of-turn learning)."""
        return self.served_this_turn
