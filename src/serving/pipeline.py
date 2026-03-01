"""
SPAM! — Serving Pipeline (v2 — Poll-driven)
=============================================
Poll-driven serving: GET /meals is the single source of truth.

Flow: serving phase starts → poll /meals → for each unexecuted meal:
      match orderText → dish → intolerance check → prepare_dish
      → (preparation_complete SSE) → serve_dish(dish, client_id)

Design principle: NO LLM calls in the common case.
/meals gives us client_id directly — no SSE correlation needed.

client_spawned SSE is used ONLY as a trigger to poll /meals immediately
(reduces latency vs. fixed-interval polling).

HARDENED for reliability:
  - Ingredient accounting (prevents over-committing)
  - FIFO preparation queue per dish (handles duplicate orders)
  - MCP retry with isError checking
  - Preparation timeout watchdog
  - Overflow protection (auto-close when capacity exhausted)
  - No correlation bugs: each /meals entry is self-contained
"""

import asyncio
import collections
import logging
import time
from dataclasses import dataclass

import aiohttp

from src.config import BASE_URL, HEADERS, TEAM_ID
from src.memory.client_profile import (
    ClientProfile,
    GlobalClientLibrary,
    IntoleranceDetector,
)
from src.serving.order_matcher import OrderMatcher

logger = logging.getLogger("spam.serving.pipeline")

# ── Constants ──
MAX_MCP_RETRIES = 3
MCP_RETRY_BASE_DELAY = 0.3  # seconds
PREP_TIMEOUT_MULTIPLIER = 2.5  # prep_time * this = max wait
PREP_TIMEOUT_BUFFER = 5.0  # extra seconds on top
POLL_INTERVAL = 1.5  # seconds between /meals polls
POLL_TRIGGER_DELAY = 0.3  # seconds to wait after client_spawned before polling
HTTP_RETRY_MAX = 5        # retries for 429 / 5xx on session-based GETs
HTTP_RETRY_BASE_DELAY = 1.0
RETRYABLE_HTTP_STATUSES = {429, 500, 502, 503, 504}


@dataclass
class PendingPreparation:
    """Track a dish currently being prepared for a specific client."""
    dish_name: str
    client_id: str
    client_name: str
    order_text: str
    started_at: float
    expected_prep_time: float  # from recipe database (seconds)


@dataclass
class ServingMetrics:
    """Per-turn serving statistics for debugging and learning."""
    clients_received: int = 0
    clients_matched: int = 0
    clients_no_match: int = 0
    clients_no_ingredients: int = 0
    preparations_started: int = 0
    preparations_completed: int = 0
    preparations_timed_out: int = 0
    serves_successful: int = 0
    serves_failed: int = 0
    mcp_retries: int = 0
    mcp_errors: int = 0
    intolerance_skips: int = 0
    restaurant_closed_overflow: bool = False
    polls_performed: int = 0


class ServingPipeline:
    """
    Poll-driven serving pipeline.

    Instead of correlating client_spawned SSE events with /meals entries,
    we use /meals as the single source of truth. Each meal entry already
    contains client_id + orderText + executed status.

    client_spawned is just a trigger to poll /meals immediately.

    This eliminates:
      - Priority queue (archetype not available from clientName)
      - client_id resolution (already in /meals)
      - Race conditions (we only process what /meals shows)
      - Duplicate ID bugs (each meal has a unique client_id)
    """

    def __init__(
        self,
        recipes: dict[str, dict],
        intolerance_detector: IntoleranceDetector,
        client_library: GlobalClientLibrary,
        mcp_client=None,
        llm_client=None,
    ):
        self.recipes = recipes
        self.intolerance_detector = intolerance_detector
        self.client_library = client_library
        self.mcp_client = mcp_client
        self.llm_client = llm_client  # fast LLM for order parsing fallback

        # Set during waiting phase
        self.menu: dict[str, dict] = {}  # dish_name → {name, price}
        self.order_matcher: OrderMatcher | None = None

        # Serving state — FIFO deque per dish name
        self.preparing: dict[str, collections.deque[PendingPreparation]] = {}
        self.current_turn: int = 0
        self._session: aiohttp.ClientSession | None = None

        # Ingredient accounting — real-time tracking
        self._committed_ingredients: dict[str, int] = {}  # ing → committed qty
        self._inventory_snapshot: dict[str, int] = {}  # captured at start_serving

        # Track which meal IDs we've already started processing
        self._processed_meal_ids: set[str] = set()

        # SSE order text cache: clientName → orderText
        # /meals may not include orderText, but SSE client_spawned does
        self._sse_order_cache: dict[str, str] = {}

        # Concurrency control for polling
        self._poll_event = asyncio.Event()  # set by client_spawned to trigger immediate poll
        self._poll_task: asyncio.Task | None = None

        # Timeout watchdog
        self._timeout_task: asyncio.Task | None = None

        # Tracking
        self.served_this_turn: list[ClientProfile] = []
        self.metrics = ServingMetrics()

        # Restaurant closure
        self._is_open = True
        self._serving_active = False

    def set_menu(self, menu_items: list[dict | str]):
        """
        Set the current menu and rebuild the order matcher.
        Called during waiting phase before serving starts.

        Accepts both list[dict] (normal) and list[str] (server shorthand).
        """
        normalised = []
        for item in menu_items:
            if isinstance(item, str):
                # Server sometimes returns bare dish names
                recipe = self.recipes.get(item, {})
                price = recipe.get("price", recipe.get("prestige", 15))
                normalised.append({"name": item, "price": int(price)})
            elif isinstance(item, dict):
                normalised.append(item)
        self.menu = {item["name"]: item for item in normalised}
        self.order_matcher = OrderMatcher(
            normalised,
            recipe_db=self.recipes,
            order_cache=self.client_library.order_to_dish_cache,
            llm_client=self.llm_client,
        )
        logger.info(f"Menu set with {len(normalised)} items")

    def set_inventory_snapshot(self, inventory: dict[str, int]):
        """
        Capture the inventory at the start of serving.
        Used for real-time ingredient accounting.
        """
        self._inventory_snapshot = dict(inventory)
        self._committed_ingredients.clear()
        logger.info(f"Inventory snapshot: {sum(inventory.values())} total items")

    async def start_serving(self, turn_id: int):
        """Called at the start of serving phase.

        Validates the turn_id against the server before starting the
        polling loop.  If the SSE-provided turn_id is stale, probes
        for the correct one so /meals polling works from the first request.
        """
        if turn_id <= 0:
            logger.error(f"start_serving called with invalid turn_id={turn_id} — will probe")
        self.current_turn = turn_id
        self.preparing.clear()
        self.served_this_turn.clear()
        self._committed_ingredients.clear()
        self._processed_meal_ids.clear()
        self._sse_order_cache.clear()
        self._poll_event.clear()
        self.metrics = ServingMetrics()
        self._is_open = True
        self._serving_active = True

        # Create shared session
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()

        # ── Validate turn_id before starting the polling loop ──
        # The SSE turn_id can be stale (e.g. reports turn 1 when game is
        # actually on turn 15).  A single probe catches this early instead
        # of failing every poll for the entire serving phase.
        validated = await self._validate_turn_id(turn_id)
        if validated and validated != turn_id:
            logger.warning(
                f"start_serving: turn_id corrected {turn_id} → {validated}"
            )
            self.current_turn = validated

        # Start the polling loop
        self._poll_task = asyncio.create_task(self._meals_polling_loop())

        # Start timeout watchdog
        self._timeout_task = asyncio.create_task(self._preparation_timeout_watchdog())

        logger.info(f"Serving started for turn {turn_id} (poll-driven)")

    async def stop_serving(self):
        """Called at end of serving phase."""
        self._serving_active = False

        # Cancel polling loop
        if self._poll_task and not self._poll_task.done():
            self._poll_task.cancel()
            try:
                await self._poll_task
            except asyncio.CancelledError:
                pass

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
            f"no_ingredients={m.clients_no_ingredients} "
            f"timeouts={m.preparations_timed_out} mcp_retries={m.mcp_retries} "
            f"mcp_errors={m.mcp_errors} intolerance_skips={m.intolerance_skips} "
            f"polls={m.polls_performed}"
        )

    # ══════════════════════════════════════════════════════════════
    #  SSE EVENT HANDLERS
    # ══════════════════════════════════════════════════════════════

    async def handle_client_spawned(self, data: dict):
        """
        Called on client_spawned SSE event.

        In the poll-driven design, this just triggers an immediate /meals poll.
        The actual serving logic happens in the polling loop.
        """
        client_name = data.get("clientName", "unknown")
        order_text = data.get("orderText", "")
        logger.info(f"Client spawned: {client_name} — '{order_text}'")

        # Cache order text — /meals may not include it
        if order_text and client_name != "unknown":
            self._sse_order_cache[client_name] = order_text

        # Trigger immediate poll (with small delay for server propagation)
        await asyncio.sleep(POLL_TRIGGER_DELAY)
        self._poll_event.set()

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
                archetype="unknown",  # not available from clientName
                order_text=pending.order_text,
                matched_dish=dish_name,
                served=True,
                turn_id=self.current_turn,
            )
            self.served_this_turn.append(profile)

            # Update order cache for future matching
            if self.order_matcher and pending.order_text:
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

    # ══════════════════════════════════════════════════════════════
    #  MEALS POLLING LOOP (core of the poll-driven design)
    # ══════════════════════════════════════════════════════════════

    async def _meals_polling_loop(self):
        """
        Main serving loop: poll GET /meals, process any unexecuted meals.

        Runs continuously during the serving phase. Wakes up either:
          - When client_spawned triggers _poll_event (low latency)
          - On a fixed interval (catches anything missed)
        """
        consecutive_errors = 0
        MAX_CONSECUTIVE_ERRORS = 5  # stop hammering server after this many
        try:
            while self._serving_active:
                # Wait for either a trigger or the interval timeout
                try:
                    await asyncio.wait_for(
                        self._poll_event.wait(),
                        timeout=POLL_INTERVAL,
                    )
                except asyncio.TimeoutError:
                    pass  # interval expired — poll anyway

                self._poll_event.clear()

                if not self._serving_active or not self._is_open:
                    continue

                # Fetch current meals
                meals = await self._fetch_meals()
                if meals is None:
                    consecutive_errors += 1
                    if consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
                        logger.error(
                            f"GET /meals failed {consecutive_errors} times in a row "
                            f"(turn_id={self.current_turn}) — backing off to 10s intervals"
                        )
                        await asyncio.sleep(10)
                    continue

                consecutive_errors = 0  # reset on success
                self.metrics.polls_performed += 1

                # Process each unexecuted meal we haven't started yet
                for meal in meals:
                    if not self._serving_active or not self._is_open:
                        break

                    client_id = self._extract_client_id(meal)
                    if not client_id:
                        continue

                    # Skip already-processed or already-executed meals
                    if client_id in self._processed_meal_ids:
                        continue
                    if meal.get("executed"):
                        continue

                    # Mark as being processed BEFORE any async work
                    self._processed_meal_ids.add(client_id)
                    self.metrics.clients_received += 1

                    await self._serve_meal(meal, client_id)

        except asyncio.CancelledError:
            pass

    async def _serve_meal(self, meal: dict, client_id: str):
        """
        Process a single meal from /meals through the serving pipeline.

        Flow:
        1. Match request text to menu dish
        2. Intolerance check (best-effort without archetype)
        3. Verify ingredient availability
        4. Commit ingredients
        5. prepare_dish via MCP
        6. (preparation_complete SSE triggers serve_dish)
        """
        # /meals uses 'request' for order text (NOT 'orderText' like SSE)
        order_text = meal.get("request") or meal.get("orderText", "")
        # /meals nests client name under 'customer.name' (NOT flat 'clientName')
        customer = meal.get("customer")
        if isinstance(customer, dict):
            client_name = customer.get("name", "unknown")
        else:
            client_name = meal.get("clientName", "unknown")

        # Fallback: use SSE-cached order text if /meals didn't include it
        if not order_text and client_name in self._sse_order_cache:
            order_text = self._sse_order_cache[client_name]
            logger.info(f"Using SSE-cached orderText for {client_name}: '{order_text}'")

        # Step 0.5: Extract declared intolerances from order text
        declared_intolerances = (
            self.order_matcher.extract_intolerances(order_text)
            if self.order_matcher else self._extract_intolerances(order_text)
        )
        if declared_intolerances:
            logger.info(f"Client {client_name} declared intolerances: {declared_intolerances}")

        # Step 1: Match dish
        if self.order_matcher is None:
            logger.error("Order matcher not initialized — menu not set")
            return

        dish = self.order_matcher.match(order_text)
        if dish is None:
            logger.warning(f"No dish match for '{order_text}' — skipping {client_name}")
            self.metrics.clients_no_match += 1
            return

        self.metrics.clients_matched += 1

        # Step 2: Intolerance check — use declared intolerances from order text
        recipe = self.recipes.get(dish, {})
        recipe_ings = list(recipe.get("ingredients", {}).keys())

        # Check declared intolerances against recipe ingredients
        intolerance_conflict = False
        if declared_intolerances:
            for intolerant_ing in declared_intolerances:
                intolerant_lower = intolerant_ing.lower().strip()
                for ring in recipe_ings:
                    if intolerant_lower in ring.lower() or ring.lower() in intolerant_lower:
                        intolerance_conflict = True
                        logger.warning(
                            f"Dish {dish} contains {ring} which client is intolerant to!"
                        )
                        break
                if intolerance_conflict:
                    break

        # Also check Bayesian intolerance detector as fallback
        bayesian_unsafe = not self.intolerance_detector.is_recipe_safe("unknown", recipe_ings)

        if intolerance_conflict or bayesian_unsafe:
            alt_dish = self._find_safe_cookable_dish(declared_intolerances)
            if alt_dish and alt_dish != dish:
                logger.info(
                    f"Intolerance risk for {dish} → using safe alternative {alt_dish}"
                )
                dish = alt_dish
                recipe = self.recipes.get(dish, {})
                self.metrics.intolerance_skips += 1
            elif not alt_dish:
                # No safe alternative available — skip this customer entirely.
                # Serving a dish with known intolerance = guaranteed rejection.
                logger.warning(
                    f"Intolerance conflict for {dish} and no safe alternative — "
                    f"SKIPPING {client_name} to avoid rejection"
                )
                self.metrics.intolerance_skips += 1
                return

        # Step 3: Verify ingredient availability
        # CRITICAL: If we can't cook the matched dish, DO NOT serve a random
        # alternative. Serving the wrong dish gets REJECTED by the customer
        # and damages our reputation. It's better to skip the customer entirely
        # and preserve ingredients for customers whose orders we CAN fulfill.
        if not self._can_cook(dish):
            logger.warning(
                f"Cannot cook matched dish '{dish}' for {client_name} — "
                f"SKIPPING customer to preserve reputation. "
                f"(Serving wrong dish = rejection = reputation damage)"
            )
            self.metrics.clients_no_ingredients += 1
            # Check if we have ANY cookable dishes left
            remaining = self._cookable_menu_dishes()
            if not remaining:
                logger.warning(
                    f"No cookable dishes remaining at all — closing restaurant"
                )
                await self._close_restaurant()
            return

        # Step 4: Commit ingredients (mark as used BEFORE prepare_dish)
        self._commit_ingredients(dish)

        # Step 5: Prepare dish via MCP
        prep_time = recipe.get("preparationTimeMs", recipe.get("prep_time", 5000))
        if prep_time > 100:  # likely in milliseconds
            prep_time = prep_time / 1000.0  # convert to seconds

        pending = PendingPreparation(
            dish_name=dish,
            client_id=client_id,
            client_name=client_name,
            order_text=order_text,
            started_at=time.time(),
            expected_prep_time=prep_time,
        )

        # FIFO queue per dish name
        if dish not in self.preparing:
            self.preparing[dish] = collections.deque()
        self.preparing[dish].append(pending)

        success = await self._mcp_prepare_dish(dish)
        if success:
            self.metrics.preparations_started += 1
            logger.info(
                f"Preparing {dish} for {client_name} "
                f"(client_id={client_id}, prep≈{prep_time:.1f}s)"
            )
        else:
            # Prepare failed — rollback
            self._uncommit_ingredients(dish)
            if dish in self.preparing and self.preparing[dish]:
                self.preparing[dish].pop()
                if not self.preparing[dish]:
                    del self.preparing[dish]
            logger.error(f"prepare_dish permanently failed for {dish}")

    # ══════════════════════════════════════════════════════════════
    #  SESSION-BASED RETRY HELPER
    # ══════════════════════════════════════════════════════════════

    async def _retry_session_get(
        self, url: str, label: str = "",
        max_retries: int = HTTP_RETRY_MAX,
    ):
        """GET with exponential backoff on 429/5xx using the shared session.

        Returns (status, json_body | text_body) or (None, None) on total failure.
        For 200: returns parsed JSON.
        For other non-retryable codes: returns raw text so caller can inspect.
        """
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()

        _label = label or url.split("?")[0].split("/")[-1]

        for attempt in range(max_retries):
            try:
                async with self._session.get(url, headers=HEADERS) as resp:
                    if resp.status < 400:
                        return resp.status, await resp.json()

                    if resp.status in RETRYABLE_HTTP_STATUSES:
                        retry_after = resp.headers.get("Retry-After")
                        if retry_after:
                            try:
                                wait = min(float(retry_after), 16.0)
                            except ValueError:
                                wait = min(HTTP_RETRY_BASE_DELAY * (2 ** attempt), 16.0)
                        else:
                            wait = min(HTTP_RETRY_BASE_DELAY * (2 ** attempt), 16.0)
                        logger.warning(
                            f"HTTP {resp.status} on {_label} "
                            f"(attempt {attempt + 1}/{max_retries}) — retrying in {wait:.1f}s"
                        )
                        await asyncio.sleep(wait)
                        continue

                    # Non-retryable (400, 401, 403, 404, etc.)
                    body = await resp.text()
                    return resp.status, body

            except (aiohttp.ClientError, asyncio.TimeoutError, OSError) as e:
                wait = min(HTTP_RETRY_BASE_DELAY * (2 ** attempt), 16.0)
                if attempt < max_retries - 1:
                    logger.warning(
                        f"{_label} request error (attempt {attempt + 1}): {e} — retrying in {wait:.1f}s"
                    )
                    await asyncio.sleep(wait)
                else:
                    logger.error(f"{_label} request failed after {max_retries} attempts: {e}")

        return None, None

    # ══════════════════════════════════════════════════════════════
    #  /MEALS FETCHING
    # ══════════════════════════════════════════════════════════════

    async def _fetch_meals(self) -> list[dict] | None:
        """Fetch current meals from GET /meals.

        Retries 429/5xx via _retry_session_get.
        If the server returns 400 ("turn_id too old"), probe for the
        correct turn_id, update self.current_turn, and retry once.
        """
        if self.current_turn <= 0:
            logger.warning(f"GET /meals skipped — current_turn={self.current_turn} (not set)")
            return None

        url = f"{BASE_URL}/meals?turn_id={self.current_turn}&restaurant_id={TEAM_ID}"
        try:
            status, body = await self._retry_session_get(url, label="fetch_meals")
            if status is None:
                logger.error("GET /meals failed after all retries")
                return None

            if status == 400:
                if isinstance(body, str) and "too old" in body:
                    # turn_id is stale — probe for the correct one
                    corrected = await self._probe_correct_turn_id()
                    if corrected and corrected != self.current_turn:
                        logger.warning(
                            f"turn_id auto-corrected: {self.current_turn} → {corrected}"
                        )
                        self.current_turn = corrected
                        # Retry with corrected turn_id
                        retry_url = f"{BASE_URL}/meals?turn_id={corrected}&restaurant_id={TEAM_ID}"
                        retry_status, retry_body = await self._retry_session_get(
                            retry_url, label=f"fetch_meals_corrected_t{corrected}",
                        )
                        if retry_status == 200:
                            return retry_body
                        logger.error(
                            f"GET /meals retry returned {retry_status} "
                            f"(corrected turn_id={corrected})"
                        )
                        return None
                    else:
                        logger.error(
                            f"GET /meals returned 400 (turn_id={self.current_turn}): "
                            f"{body} — probe could not find valid turn_id"
                        )
                        return None
                else:
                    logger.error(
                        f"GET /meals returned 400 (turn_id={self.current_turn}): {body}"
                    )
                    return None

            if status != 200:
                logger.error(f"GET /meals returned {status}")
                return None

            return body  # already parsed as JSON by _retry_session_get

        except Exception as e:
            logger.error(f"GET /meals failed: {e}")
            return None

    async def _probe_correct_turn_id(self) -> int | None:
        """Probe the server to discover the correct turn_id.

        The /meals endpoint only accepts the current turn and the previous 2.
        Binary-search from our current guess upward to find the highest turn_id
        that returns 200.
        """
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()

        logger.info(f"Probing for correct turn_id (current guess: {self.current_turn})...")

        # Phase 1: exponential search upward to find a valid turn_id
        lo = max(1, self.current_turn)
        hi = lo
        found_any_valid = False
        while hi <= 200:  # safety cap
            url = f"{BASE_URL}/meals?turn_id={hi}&restaurant_id={TEAM_ID}"
            status, _ = await self._retry_session_get(
                url, label=f"probe_up_{hi}", max_retries=3,
            )
            if status == 200:
                lo = hi
                found_any_valid = True
                hi *= 2
            else:
                if not found_any_valid:
                    hi = hi + 1 if hi < 10 else hi * 2
                else:
                    break

        if not found_any_valid:
            logger.error("turn_id probe: no valid turn_id found in range 1-200")
            return None

        # Phase 2: binary search between lo and hi for the highest valid turn_id
        while lo < hi:
            mid = (lo + hi + 1) // 2
            url = f"{BASE_URL}/meals?turn_id={mid}&restaurant_id={TEAM_ID}"
            status, _ = await self._retry_session_get(
                url, label=f"probe_bs_{mid}", max_retries=3,
            )
            if status == 200:
                lo = mid
            else:
                hi = mid - 1

        logger.info(f"turn_id probe result: {lo}")
        return lo

    async def _validate_turn_id(self, turn_id: int) -> int | None:
        """Quick validation of a turn_id against the server.

        Makes a GET /meals request with retry. If it returns 200, the
        turn_id is valid. If 400, probes for the correct one.
        Returns the correct turn_id (may be the same as input).
        """
        if turn_id <= 0:
            return await self._probe_correct_turn_id()

        url = f"{BASE_URL}/meals?turn_id={turn_id}&restaurant_id={TEAM_ID}"
        status, _ = await self._retry_session_get(
            url, label=f"validate_turn_{turn_id}",
        )
        if status == 200:
            return turn_id  # valid
        if status == 400:
            logger.warning(
                f"turn_id={turn_id} rejected by server — probing for correct one"
            )
            return await self._probe_correct_turn_id()
        return turn_id  # fallback: keep the original
    @staticmethod
    def _extract_client_id(meal: dict) -> str | None:
        """
        Extract client_id from a /meals response entry.

        /meals returns: id (meal id), customerId (customer id).
        serve_dish expects the customer id (customerId), not the meal id.
        Fall back to id if customerId not present.
        """
        for field_name in ("customerId", "client_id", "id", "mealId"):
            val = meal.get(field_name)
            if val is not None:
                return str(val)
        return None

    # ══════════════════════════════════════════════════════════════
    #  INGREDIENT ACCOUNTING
    # ══════════════════════════════════════════════════════════════

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
        return [d for d in self.menu if self._can_cook(d)]

    # ══════════════════════════════════════════════════════════════
    #  SAFE ALTERNATIVES
    # ══════════════════════════════════════════════════════════════

    def _find_any_cookable_dish(self) -> str | None:
        """Find ANY menu dish we can still cook, preferring highest prestige."""
        cookable = self._cookable_menu_dishes()
        if cookable:
            return max(
                cookable,
                key=lambda d: self.recipes.get(d, {}).get("prestige", 0),
            )
        return None

    def _find_safe_cookable_dish(self, declared_intolerances: list[str]) -> str | None:
        """Find a cookable dish that avoids declared intolerances."""
        cookable = self._cookable_menu_dishes()
        if not cookable:
            return None

        safe = []
        for d in cookable:
            recipe = self.recipes.get(d, {})
            ings = list(recipe.get("ingredients", {}).keys())
            conflict = False
            for intolerant_ing in declared_intolerances:
                intolerant_lower = intolerant_ing.lower().strip()
                for ring in ings:
                    if intolerant_lower in ring.lower() or ring.lower() in intolerant_lower:
                        conflict = True
                        break
                if conflict:
                    break
            if not conflict:
                safe.append(d)

        if safe:
            return max(
                safe,
                key=lambda d: self.recipes.get(d, {}).get("prestige", 0),
            )
        # No safe dish available — do NOT serve an intolerant dish.
        # Better to skip the customer than trigger an intolerance rejection.
        logger.warning(
            f"No safe cookable dish found (avoiding intolerances: {declared_intolerances})"
        )
        return None

    @staticmethod
    def _extract_intolerances(order_text: str) -> list[str]:
        """Extract declared intolerances from order text.
        
        Examples:
          'I want to eat X. I'm intolerant to Funghi Orbitali' → ['Funghi Orbitali']
          'Vorrei Y. Sono intollerante ai Cristalli di Sale' → ['Cristalli di Sale']
        """
        import re
        intolerances = []
        patterns = [
            r"(?:i[''']?m|i\s+am)\s+intolerant\s+to\s+(.+?)(?:\.|!|$)",
            r"(?:sono)\s+intollerante\s+(?:a|al|alla|ai|alle|allo|agli)\s+(.+?)(?:\.|!|$)",
            r"intolerant\s+to\s+(.+?)(?:\.|!|$)",
            r"intollerante\s+(?:a|al|alla|ai|alle|allo|agli)\s+(.+?)(?:\.|!|$)",
        ]
        text_lower = order_text.lower()
        for pattern in patterns:
            matches = re.findall(pattern, text_lower, re.IGNORECASE)
            for m in matches:
                cleaned = m.strip().rstrip(".,!?; ")
                if cleaned:
                    intolerances.append(cleaned)
        return intolerances

    # ══════════════════════════════════════════════════════════════
    #  MCP CALLS (with retry + isError checking)
    # ══════════════════════════════════════════════════════════════

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
            if result.get("isError"):
                return True
            inner = result.get("result", {})
            if isinstance(inner, dict) and inner.get("isError"):
                return True
        if hasattr(result, "isError") and result.isError:  # type: ignore[union-attr]
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

    # ══════════════════════════════════════════════════════════════
    #  PREPARATION TIMEOUT WATCHDOG
    # ══════════════════════════════════════════════════════════════

    async def _preparation_timeout_watchdog(self):
        """
        Background task that checks for timed-out preparations.
        Runs every 2 seconds during serving phase.
        """
        try:
            while True:
                await asyncio.sleep(2.0)
                now = time.time()

                for dish_name in list(self.preparing.keys()):
                    queue = self.preparing.get(dish_name)
                    if not queue:
                        continue

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
                        self.metrics.preparations_timed_out += 1

        except asyncio.CancelledError:
            pass

    # ══════════════════════════════════════════════════════════════
    #  OVERFLOW PROTECTION
    # ══════════════════════════════════════════════════════════════

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

    # ══════════════════════════════════════════════════════════════
    #  ACCESSORS
    # ══════════════════════════════════════════════════════════════

    def get_turn_profiles(self) -> list[ClientProfile]:
        """Get all client profiles from this turn (for end-of-turn learning)."""
        return self.served_this_turn
