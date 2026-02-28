"""
SPAM! — Main Entry Point
==========================
Wires SSE → EventBus → PhaseRouter → SkillOrchestrator → all subsystems.
Implements the complete game agent loop with mid-turn entry robustness
and phase countdown logging.

Usage:
    python -m src.main
"""

import asyncio
import logging
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path

from datapizza.clients.openai_like import OpenAILikeClient
from datapizza.tools.mcp_client import MCPClient

from src.config import (
    TEAM_ID,
    TEAM_NAME,
    API_KEY,
    BASE_URL,
    REGOLO_API_KEY,
    REGOLO_BASE_URL,
    PRIMARY_MODEL,
    FAST_MODEL,
    MCP_URL,
    HEADERS,
)
from src.event_bus import ReactiveEventBus
from src.phase_router import PhaseRouter
from src.recipe_loader import load_recipes, load_our_restaurant

# Memory
from src.memory.event_log import EventLog, event_log_middleware, set_global_log
from src.memory.message_log import MessageLog
from src.memory.game_state import GameStateMemory, RestaurantState
from src.memory.competitor import CompetitorMemory
from src.memory.client_profile import (
    GlobalClientLibrary,
    ZoneClientLibrary,
    IntoleranceDetector,
)

# Serving
from src.serving.pipeline import ServingPipeline

# Intelligence
from src.intelligence.tracker_bridge import TrackerBridge
from src.intelligence.pipeline import IntelligencePipeline
from src.intelligence.feature_extractor import set_recipe_db

# Decision
from src.decision.ilp_solver import solve_zone_ilp
from src.decision.subagent_router import SubagentRouter
from src.decision.pricing import compute_menu_prices, adjust_prices_competitive

# Diplomacy
from src.diplomacy.agent import DiplomacyAgent
from src.diplomacy.firewall import GroundTruthFirewall

# Skills
from src.skills import (
    Skill,
    SkillContext,
    SkillResult,
    SkillOrchestrator,
    compute_skipped_phases,
)

# ── Logging ──
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)-30s %(levelname)-7s %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("spam_game.log", mode="a"),
    ],
)
logger = logging.getLogger("spam.main")

# ── Countdown config ──
COUNTDOWN_LOG_INTERVAL = 15.0  # seconds between countdown log lines


class GameOrchestrator:
    """
    Central orchestrator wiring all subsystems together.

    Lifecycle:
      1. Initialise datapizza clients & MCP
      2. Connect SSE via ReactiveEventBus
      3. Route events to phase-specific handlers
      4. Each phase handler coordinates subsystems via SkillOrchestrator
      5. Mid-turn entry: detect skipped phases, run catch-up skills
      6. Background countdown timer logs time remaining in each phase
    """

    def __init__(self):
        # ── LLM Clients ──
        # Use OpenAILikeClient (chat completions API), NOT OpenAIClient
        # (responses API) — Regolo.ai returns 403 on /v1/responses.
        self.primary_client = OpenAILikeClient(
            api_key=REGOLO_API_KEY,
            model=PRIMARY_MODEL,
            base_url=REGOLO_BASE_URL,
            system_prompt=(
                f"You are the AI brain of restaurant '{TEAM_NAME}' (ID {TEAM_ID}). "
                "Make optimal decisions for bidding, menu, and serving."
            ),
        )
        self.fast_client = OpenAILikeClient(
            api_key=REGOLO_API_KEY,
            model=FAST_MODEL,
            base_url=REGOLO_BASE_URL,
            system_prompt="Fast parsing and evaluation assistant.",
        )

        # ── MCP Client ──
        self.mcp_client = MCPClient(
            url=MCP_URL,
            headers={"x-api-key": API_KEY},
            timeout=30,
        )

        # ── Memory ──
        self.event_log = EventLog()
        set_global_log(self.event_log)
        self.message_log = MessageLog()
        self.game_state = GameStateMemory()
        self.competitor_memory = CompetitorMemory()
        self.client_library = GlobalClientLibrary()
        self.intolerance_detector = IntoleranceDetector()

        # ── Intelligence ──
        self.tracker_bridge = TrackerBridge()
        self.intelligence = IntelligencePipeline(
            bridge=self.tracker_bridge,
            recipe_db={},  # set after recipes loaded
            competitor_memory=self.competitor_memory,
        )

        # ── Serving ──
        self.serving = ServingPipeline(
            recipes={},  # set after recipes loaded
            intolerance_detector=self.intolerance_detector,
            client_library=self.client_library,
            mcp_client=self.mcp_client,
        )

        # ── Decision ──
        self.subagent_router = SubagentRouter()

        # ── Diplomacy ──
        self.diplomacy = DiplomacyAgent(
            mcp_client=self.mcp_client,
            message_log=self.message_log,
        )
        self.firewall = GroundTruthFirewall(self.message_log)

        # ── Event Bus ──
        self.bus = ReactiveEventBus()
        self.phase_router = PhaseRouter()

        # ── Skill Orchestrator ──
        self.skill_orchestrator = SkillOrchestrator()
        self._register_skills()

        # ── State ──
        self.recipe_db: dict[str, dict] = {}
        self._latest_intel: dict = {}
        self._running = False
        self._countdown_task: asyncio.Task | None = None
        self._discovered_turn: int | None = None  # cached turn from probe

    async def start(self):
        """Initialise and start the game agent."""
        logger.info(f"=== SPAM! (Team {TEAM_ID}) Starting ===")

        # Load MCP tools list
        try:
            mcp_tools = await self.mcp_client.a_list_tools()
            logger.info(f"MCP tools available: {[t.name for t in mcp_tools]}")
        except Exception as e:
            logger.warning(f"MCP tool list failed: {e}")
            mcp_tools = []

        # Initialise subagent router with MCP tools
        self.subagent_router.initialize(mcp_tools=mcp_tools)

        # Load recipes
        self.recipe_db = await load_recipes()
        self.serving.recipes = self.recipe_db
        self.intelligence.state_builder.recipe_db = self.recipe_db
        self.intelligence.trajectory_predictor.recipe_db = self.recipe_db
        set_recipe_db(self.recipe_db)
        logger.info(f"Loaded {len(self.recipe_db)} recipes")

        # Fetch initial state
        our_state = await load_our_restaurant()
        if our_state:
            self.game_state.snapshot(RestaurantState(
                turn_id=0,
                phase="init",
                balance=our_state.get("balance", 10000),
                inventory=our_state.get("inventory", {}),
                reputation=our_state.get("reputation", 50),
                menu=[],
                clients_served=0,
                revenue_this_turn=0,
            ))
            logger.info(
                f"Initial state: balance={our_state.get('balance')}, "
                f"reputation={our_state.get('reputation')}"
            )

        # Wire event bus
        self._wire_events()

        # Start countdown timer background task
        self._countdown_task = asyncio.create_task(self._countdown_timer())

        # Connect SSE (runs forever)
        self._running = True
        logger.info("Connecting to SSE stream...")
        await self.bus.connect_sse()

    def _wire_events(self):
        """Wire all SSE event types to handlers."""
        # Middleware
        self.bus.use(event_log_middleware)
        self.bus.use(self.firewall.middleware)

        # Phase routing
        self.bus.on("game_phase_changed", self.phase_router.handle_phase_change, priority=0)
        self.bus.on("game_started", self._handle_game_started, priority=0)
        self.bus.on("game_reset", self._handle_game_reset, priority=0)

        # Serving events
        self.bus.on("client_spawned", self._handle_client_spawned, priority=0)
        self.bus.on("preparation_complete", self._handle_preparation_complete, priority=0)

        # Message events
        self.bus.on("new_message", self._handle_new_message, priority=1)

        # Register phase handlers (all go through unified dispatcher)
        self.phase_router.register("speaking", self._phase_speaking)
        self.phase_router.register("closed_bid", self._phase_closed_bid)
        self.phase_router.register("waiting", self._phase_waiting)
        self.phase_router.register("serving", self._phase_serving)
        self.phase_router.register("stopped", self._phase_stopped)

        # Turn change callback
        self.phase_router.on_turn_change(self._on_turn_change)

    # ══════════════════════════════════════════════════════════════
    #  SKILL REGISTRATION
    # ══════════════════════════════════════════════════════════════

    def _register_skills(self):
        """Register all skills with the orchestrator."""
        so = self.skill_orchestrator

        # ── Intelligence (full) ──
        so.register(Skill(
            name="intelligence_scan",
            description="Run full intelligence pipeline (tracker, competitor clustering)",
            valid_phases={"speaking"},
            priority=5,
            execute_fn=self._skill_intelligence_scan,
        ))

        # ── Intelligence (quick — for mid-turn catch-up) ──
        so.register(Skill(
            name="quick_intelligence",
            description="Lightweight intelligence: fetch restaurant states only",
            # Valid in all phases where we can still act
            valid_phases={"speaking", "closed_bid", "waiting", "serving"},
            priority=3,
            mid_turn_applicable=True,
            execute_fn=self._skill_quick_intelligence,
        ))

        # ── Zone Selection ──
        so.register(Skill(
            name="zone_selection",
            description="Select strategic zone via subagent router",
            valid_phases={"speaking", "closed_bid", "waiting"},
            priority=8,
            execute_fn=self._skill_zone_selection,
        ))

        # ── Menu Planning ──
        so.register(Skill(
            name="menu_planning",
            description="Compute menu via ILP solver",
            valid_phases={"speaking", "closed_bid", "waiting"},
            priority=30,
            requires_skills=["zone_selection"],
            execute_fn=self._skill_menu_planning,
        ))

        # ── Menu Save ──
        so.register(Skill(
            name="menu_save",
            description="Save menu to server via MCP",
            valid_phases={"speaking", "closed_bid", "waiting"},
            priority=35,
            requires_skills=["menu_planning"],
            execute_fn=self._skill_menu_save,
        ))

        # ── Diplomacy ──
        so.register(Skill(
            name="diplomacy_send",
            description="Run diplomacy turn (messages, deception)",
            valid_phases={"speaking", "closed_bid", "waiting", "serving"},
            priority=50,
            execute_fn=self._skill_diplomacy_send,
        ))

        # ── Bid Compute + Submit ──
        so.register(Skill(
            name="bid_compute",
            description="Compute optimal bids via ILP",
            valid_phases={"closed_bid"},
            priority=10,
            requires_skills=["zone_selection"],
            execute_fn=self._skill_bid_compute,
        ))
        so.register(Skill(
            name="bid_submit",
            description="Submit bids via MCP",
            valid_phases={"closed_bid"},
            priority=15,
            requires_skills=["bid_compute"],
            execute_fn=self._skill_bid_submit,
        ))

        # ── Inventory Verify (waiting phase) ──
        so.register(Skill(
            name="inventory_verify",
            description="Verify menu against actual post-bid inventory",
            valid_phases={"waiting"},
            priority=25,
            execute_fn=self._skill_inventory_verify,
        ))

        # ── Market Operations ──
        so.register(Skill(
            name="market_ops",
            description="Buy missing / sell surplus ingredients on market",
            valid_phases={"speaking", "closed_bid", "waiting", "serving"},
            priority=40,
            execute_fn=self._skill_market_ops,
        ))

        # ── Restaurant Open ──
        so.register(Skill(
            name="restaurant_open",
            description="Open restaurant for serving",
            valid_phases={"speaking", "closed_bid", "waiting"},
            priority=45,
            execute_fn=self._skill_restaurant_open,
        ))

        # ── Serving Prep ──
        so.register(Skill(
            name="serving_prep",
            description="Pre-start serving pipeline with inventory snapshot",
            valid_phases={"waiting", "serving"},
            priority=48,
            execute_fn=self._skill_serving_prep,
        ))

        # ── Serving Readiness Check (mid-turn serving entry) ──
        so.register(Skill(
            name="serving_readiness_check",
            description="Check if we can serve: do we have a menu + inventory?",
            valid_phases={"serving"},
            priority=5,
            mid_turn_applicable=True,
            execute_fn=self._skill_serving_readiness_check,
        ))

        # ── Emergency Menu (mid-turn serving entry) ──
        so.register(Skill(
            name="emergency_menu",
            description="Set minimal menu from available inventory (emergency)",
            valid_phases={"serving"},
            priority=8,
            mid_turn_applicable=True,
            execute_fn=self._skill_emergency_menu,
        ))

        # ── Serving Monitor ──
        so.register(Skill(
            name="serving_monitor",
            description="Log serving phase start",
            valid_phases={"serving"},
            priority=50,
            execute_fn=self._skill_serving_monitor,
        ))

        # ── Close Decision ──
        so.register(Skill(
            name="close_decision",
            description="Decide whether to close restaurant (no ingredients/menu)",
            valid_phases={"serving"},
            priority=55,
            execute_fn=self._skill_close_decision,
        ))

        # ── End-of-Turn Snapshot ──
        so.register(Skill(
            name="end_turn_snapshot",
            description="Capture end-of-turn state and update memories",
            valid_phases={"stopped"},
            priority=10,
            execute_fn=self._skill_end_turn_snapshot,
        ))

        # ── Info Gather ──
        so.register(Skill(
            name="info_gather",
            description="Gather observable info (restaurants, market) for next turn",
            valid_phases={"stopped"},
            priority=20,
            execute_fn=self._skill_info_gather,
        ))

        logger.info(f"Registered {len(so.skills)} skills")

    # ══════════════════════════════════════════════════════════════
    #  SKILL CONTEXT BUILDER
    # ══════════════════════════════════════════════════════════════

    async def _discover_turn_id(self) -> int:
        """Discover the current turn_id by probing GET /meals.

        Binary-searches turn_ids: 200 = valid (within current ± 2 window),
        400 = outside window. The highest turn_id that returns 200 is the
        current turn (or current+1/+2, close enough).

        Returns discovered turn_id, or 1 as absolute last resort.
        """
        import aiohttp

        if self._discovered_turn and self._discovered_turn > 0:
            return self._discovered_turn

        logger.info("Probing server to discover current turn_id...")

        async with aiohttp.ClientSession() as session:
            # Phase 1: exponential search to find upper bound
            # Try 1, 2, 4, 8, 16, 32, 64... until we get 400
            lo, hi = 1, 1
            while hi <= 200:  # safety cap
                url = f"{BASE_URL}/meals?turn_id={hi}&restaurant_id={TEAM_ID}"
                try:
                    async with session.get(url, headers=HEADERS) as resp:
                        if resp.status == 200:
                            lo = hi
                            hi *= 2
                        else:
                            break
                except Exception:
                    break

            # Phase 2: binary search between lo and hi
            while lo < hi:
                mid = (lo + hi + 1) // 2
                url = f"{BASE_URL}/meals?turn_id={mid}&restaurant_id={TEAM_ID}"
                try:
                    async with session.get(url, headers=HEADERS) as resp:
                        if resp.status == 200:
                            lo = mid
                        else:
                            hi = mid - 1
                except Exception:
                    hi = mid - 1

            self._discovered_turn = lo
            logger.info(f"Discovered current turn_id={lo}")
            self.phase_router.current_turn = lo
            return lo

    async def _build_skill_context(
        self,
        data: dict,
        our_state: dict | None = None,
    ) -> SkillContext:
        """
        Build a SkillContext from current game state.

        Fetches restaurant state if not provided.
        """
        if our_state is None:
            our_state = await load_our_restaurant() or {}

        turn_id = data.get("turn_id", self.phase_router.current_turn)
        # CRITICAL: Never use turn_id=0 — it causes /meals?turn_id=0 → 400
        if not turn_id or turn_id <= 0:
            turn_id = self.phase_router.current_turn
        if not turn_id or turn_id <= 0:
            turn_id = await self._discover_turn_id()
            logger.info(f"Using discovered turn_id={turn_id}")
        phase = data.get("phase", self.phase_router.current_phase or "speaking")
        is_mid = data.get("is_mid_turn_entry", False)
        skipped = data.get("skipped_phases", [])

        balance = our_state.get("balance", 10000)
        inventory = our_state.get("inventory", {})
        reputation = our_state.get("reputation", 50)

        # Check if restaurant has a menu set
        menu_items = our_state.get("menu", [])
        menu_set = len(menu_items) > 0

        # Check if restaurant is open
        restaurant_open = our_state.get("is_open", False)

        logger.info(
            f"Context built: turn={turn_id}, phase={phase}, "
            f"balance={balance}, reputation={reputation}, "
            f"inventory={len(inventory)} types/"
            f"{sum(inventory.values()) if inventory else 0} units, "
            f"menu={len(menu_items)} items, open={restaurant_open}, "
            f"mid_turn={is_mid}"
        )

        return SkillContext(
            turn_id=turn_id,
            phase=phase,
            balance=balance,
            inventory=inventory,
            reputation=reputation,
            recipes=self.recipe_db,
            intel=self._latest_intel,
            is_mid_turn_entry=is_mid,
            skipped_phases=skipped,
            time_remaining_estimate=self.phase_router.estimated_remaining,
            our_state=our_state,
            menu_set=menu_set,
            restaurant_open=restaurant_open,
        )

    # ══════════════════════════════════════════════════════════════
    #  GAME EVENTS
    # ══════════════════════════════════════════════════════════════

    async def _handle_game_started(self, data: dict):
        """Handle game_started SSE event.

        NOTE: game_started == speaking. The server NEVER fires a separate
        'speaking' phase event, so all speaking-phase logic must run here.
        """
        logger.info("Game started event received (= speaking phase)")
        self._discovered_turn = None  # reset cache for new turn
        await self.phase_router.handle_game_started(data)
        self.skill_orchestrator.new_turn()

        # Reload recipes in case they changed
        self.recipe_db = await load_recipes()
        self.serving.recipes = self.recipe_db
        set_recipe_db(self.recipe_db)

        # game_started IS the speaking phase — run speaking logic immediately.
        # Manually advance the router so _build_skill_context sees the right state.
        turn_id = data.get("turn_id", self.phase_router.current_turn)
        if turn_id <= 0:
            turn_id = await self._discover_turn_id()
            logger.info(f"game_started had no turn_id — discovered turn_id={turn_id}")
        else:
            self._discovered_turn = turn_id  # cache the known turn
        self.phase_router.current_turn = turn_id
        self.phase_router.current_phase = "speaking"
        self.phase_router._turn_has_seen_speaking = True
        self.phase_router._first_phase_received = True
        self.phase_router.phase_start_time = time.time()

        speaking_data = dict(data)
        speaking_data["phase"] = "speaking"
        speaking_data["turn_id"] = turn_id
        speaking_data["is_mid_turn_entry"] = False
        speaking_data["skipped_phases"] = []
        logger.info(f"Dispatching speaking phase with turn_id={turn_id}")
        await self._phase_speaking(speaking_data)

    async def _handle_game_reset(self, data: dict):
        """Handle game_reset — clear turn-scoped state, preserve cross-turn memory."""
        logger.info("Game reset — clearing turn state")
        self._discovered_turn = None  # reset cache
        self.game_state.reset()
        self.serving.set_menu([])
        await self.phase_router.handle_game_reset(data)
        self.skill_orchestrator.new_turn()
        # archetype_classifier removed (poll-driven v2)
        self.phase_router.current_phase = None
        self.phase_router.current_turn = 0
        # Keep: competitor_memory, client_library, event_log, message_log

    async def _on_turn_change(self, turn_id: int):
        """Called when a new turn starts (stopped → speaking)."""
        logger.info(f"Turn change: {turn_id}")
        self.game_state.new_turn(turn_id)
        self.skill_orchestrator.new_turn()

    # ── Client / Serving Events ──

    async def _handle_client_spawned(self, data: dict):
        """Handle client_spawned SSE event — only during serving phase."""
        if self.phase_router.current_phase != "serving":
            logger.warning("client_spawned outside serving phase — ignoring")
            return
        await self.serving.handle_client_spawned(data)

    async def _handle_preparation_complete(self, data: dict):
        """Handle preparation_complete SSE event."""
        if self.phase_router.current_phase != "serving":
            return
        await self.serving.handle_preparation_complete(data)

    async def _handle_new_message(self, data: dict):
        """Handle new_message SSE event — process through diplomacy firewall."""
        processed = self.diplomacy.process_incoming_message(data)
        logger.info(
            f"Message from {processed.get('sender_name', '?')}: "
            f"'{processed.get('text', '')[:80]}' "
            f"(credibility={processed.get('sender_credibility', 0):.2f})"
        )

    # ══════════════════════════════════════════════════════════════
    #  PHASE HANDLERS (delegate to SkillOrchestrator)
    # ══════════════════════════════════════════════════════════════

    async def _phase_speaking(self, data: dict):
        """
        Speaking phase handler.

        Normal flow: intelligence → zone → menu → diplomacy
        Mid-turn: same (speaking is the earliest phase, no catch-up needed)
        """
        turn_id = data.get("turn_id", self.phase_router.current_turn)
        is_mid = data.get("is_mid_turn_entry", False)
        tag = "[SPEAKING/MID-TURN]" if is_mid else "[SPEAKING]"
        logger.info(f"{tag} Turn {turn_id}")

        ctx = await self._build_skill_context(data)
        results = await self.skill_orchestrator.execute_for_phase(ctx)
        self._log_skill_results(results)

    async def _phase_closed_bid(self, data: dict):
        """
        Closed bid phase handler.

        Normal flow: compute + submit bids
        Mid-turn: quick intel → zone → menu → bids (catch-up)
        """
        turn_id = data.get("turn_id", self.phase_router.current_turn)
        is_mid = data.get("is_mid_turn_entry", False)
        tag = "[CLOSED_BID/MID-TURN]" if is_mid else "[CLOSED_BID]"
        logger.info(f"{tag} Turn {turn_id}")

        ctx = await self._build_skill_context(data)
        results = await self.skill_orchestrator.execute_for_phase(ctx)
        self._log_skill_results(results)

    async def _phase_waiting(self, data: dict):
        """
        Waiting phase handler.

        Normal flow: verify inventory → finalize menu → market → open → prep
        Mid-turn: quick intel → zone → verify → menu → market → open → prep
        """
        turn_id = data.get("turn_id", self.phase_router.current_turn)
        is_mid = data.get("is_mid_turn_entry", False)
        tag = "[WAITING/MID-TURN]" if is_mid else "[WAITING]"
        logger.info(f"{tag} Turn {turn_id}")

        ctx = await self._build_skill_context(data)
        results = await self.skill_orchestrator.execute_for_phase(ctx)
        self._log_skill_results(results)

    async def _phase_serving(self, data: dict):
        """
        Serving phase handler.

        Normal flow: log serving start, clients handled by SSE events
        Mid-turn: check readiness → emergency menu → open → start serving
        """
        turn_id = data.get("turn_id", self.phase_router.current_turn)
        is_mid = data.get("is_mid_turn_entry", False)
        tag = "[SERVING/MID-TURN]" if is_mid else "[SERVING]"
        logger.info(f"{tag} Turn {turn_id}")

        ctx = await self._build_skill_context(data)
        results = await self.skill_orchestrator.execute_for_phase(ctx)
        self._log_skill_results(results)

    async def _phase_stopped(self, data: dict):
        """
        Stopped phase handler.

        Always: stop serving → snapshot → update memories → info gathering
        """
        turn_id = data.get("turn_id", self.phase_router.current_turn)
        is_mid = data.get("is_mid_turn_entry", False)
        tag = "[STOPPED/MID-TURN]" if is_mid else "[STOPPED]"
        logger.info(f"{tag} Turn {turn_id}")

        # Always stop serving pipeline first
        await self.serving.stop_serving()

        ctx = await self._build_skill_context(data)
        results = await self.skill_orchestrator.execute_for_phase(ctx)
        self._log_skill_results(results)

    def _log_skill_results(self, results: list[SkillResult]):
        """Log a compact summary of skill execution results."""
        if not results:
            return
        ok = sum(1 for r in results if r.success)
        fail = len(results) - ok
        names = [r.skill_name for r in results]
        logger.info(
            f"Skills executed: {ok}/{len(results)} OK "
            f"({', '.join(names)})"
        )
        for r in results:
            if not r.success:
                logger.warning(f"  FAILED: {r.skill_name} — {r.error}")

    # ══════════════════════════════════════════════════════════════
    #  SKILL IMPLEMENTATIONS
    # ══════════════════════════════════════════════════════════════

    async def _skill_intelligence_scan(self, ctx: SkillContext) -> SkillResult:
        """Full intelligence pipeline: tracker, competitor clustering, briefings."""
        try:
            intel = await self.intelligence.run(ctx.turn_id)
            self._latest_intel = intel

            # Log connection-based competition awareness
            briefings = intel.get("briefings", {})
            connected_count = sum(
                1 for b in briefings.values()
                if b.get("is_connected", False)
            )
            logger.info(
                f"Intelligence: {len(briefings)} briefings, "
                f"{connected_count} connected competitors, "
                f"{len(intel.get('clusters', {}))} clusters"
            )
            return SkillResult(
                skill_name="intelligence_scan",
                success=True,
                data={"briefings": len(intel.get("briefings", {}))},
            )
        except Exception as e:
            logger.error(f"Intelligence pipeline failed: {e}", exc_info=True)
            self._latest_intel = {}
            return SkillResult(
                skill_name="intelligence_scan", success=False, error=str(e)
            )

    async def _skill_quick_intelligence(self, ctx: SkillContext) -> SkillResult:
        """
        Lightweight intelligence for mid-turn catch-up.

        Skips tracker + heavy analysis. Just fetches restaurant states
        and builds minimal competitor context for zone selection.
        """
        try:
            import aiohttp

            # Fetch all restaurants for basic competitor awareness
            url = f"{BASE_URL}/restaurants"
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=HEADERS) as resp:
                    if resp.status == 200:
                        restaurants = await resp.json()
                    else:
                        restaurants = []

            # Build minimal intel from restaurant overview
            all_states = {}
            for r in restaurants:
                rid = r.get("id", r.get("restaurantId"))
                if rid and rid != TEAM_ID:
                    all_states[rid] = r

            # Build minimal connection-based briefings so bid/price
            # logic can detect active (connected) competitors.
            # Any restaurant visible in /restaurants is connected.
            minimal_briefings = {}
            for rid, rdata in all_states.items():
                menu_raw = rdata.get("menu") or {}
                menu_items = (
                    menu_raw.get("items", [])
                    if isinstance(menu_raw, dict)
                    else (menu_raw if isinstance(menu_raw, list) else [])
                )
                menu_prices = [
                    it.get("price", 0) for it in menu_items
                    if isinstance(it, dict)
                ]
                minimal_briefings[rid] = {
                    "name": rdata.get("name", f"team {rid}"),
                    "is_connected": True,  # present → connected
                    "menu_size": len(menu_items),
                    "menu_price_avg": (
                        sum(menu_prices) / len(menu_prices)
                        if menu_prices else 0
                    ),
                    "strategy": "UNCLASSIFIED",
                    "top_bid_ingredients": [],
                    "predicted_bid_spend": 0,
                    "balance": rdata.get("balance", 0),
                    "reputation": rdata.get("reputation", 100),
                    "threat_level": 0.5,
                }

            self._latest_intel = {
                "briefings": minimal_briefings,
                "clusters": {},
                "all_states": all_states,
                "demand_forecast": {},
                "features": {},
            }
            logger.info(
                f"Quick intelligence: {len(all_states)} competitor states fetched, "
                f"{len(minimal_briefings)} connection-based briefings generated"
            )
            return SkillResult(
                skill_name="quick_intelligence",
                success=True,
                data={"competitors_seen": len(all_states)},
            )
        except Exception as e:
            logger.warning(f"Quick intelligence failed: {e}")
            self._latest_intel = {}
            return SkillResult(
                skill_name="quick_intelligence", success=False, error=str(e)
            )

    async def _skill_zone_selection(self, ctx: SkillContext) -> SkillResult:
        """Select strategic zone via subagent router."""
        try:
            zone = self.subagent_router.route(
                balance=ctx.balance,
                inventory=ctx.inventory,
                reputation=ctx.reputation,
                recipes=list(ctx.recipes.values()),
                competitor_clusters=ctx.intel.get("clusters", {}),
                competitor_briefings=ctx.intel.get("briefings", {}),
                all_states=ctx.intel.get("all_states"),
            )
            logger.info(f"Zone selected: {zone}")
            return SkillResult(
                skill_name="zone_selection",
                success=True,
                data={"zone": zone},
            )
        except Exception as e:
            logger.error(f"Zone selection failed: {e}")
            return SkillResult(
                skill_name="zone_selection", success=False, error=str(e)
            )

    async def _skill_menu_planning(self, ctx: SkillContext) -> SkillResult:
        """Compute menu via ILP solver."""
        try:
            zone = self.subagent_router.active_zone
            spending = 0.0 if ctx.phase in ("waiting", "serving") else 0.4
            logger.info(
                f"Menu planning: zone={zone}, phase={ctx.phase}, "
                f"spending={spending}, balance={ctx.balance}, "
                f"inventory_items={len(ctx.inventory)}, "
                f"inventory_total={sum(ctx.inventory.values()) if ctx.inventory else 0}"
            )
            decision = solve_zone_ilp(
                zone=zone,
                balance=ctx.balance,
                inventory=ctx.inventory,
                recipes=list(ctx.recipes.values()),
                demand_forecast=ctx.intel.get("demand_forecast", {}),
                competitor_briefings=ctx.intel.get("briefings", {}),
                reputation=ctx.reputation,
                spending_fraction=spending,
            )

            # ── Zone fallback: if primary zone yields empty menu in
            #    waiting phase (can't bid anymore), try broader zones ──
            if not decision.menu and ctx.phase == "waiting" and ctx.inventory:
                fallback_zones = [
                    z for z in ["SPEED_CONTENDER", "BUDGET_OPPORTUNIST",
                                "NICHE_SPECIALIST", "MARKET_ARBITRAGEUR"]
                    if z != zone
                ]
                for fz in fallback_zones:
                    logger.info(f"Menu empty for {zone} — trying fallback zone {fz}")
                    decision = solve_zone_ilp(
                        zone=fz,
                        balance=ctx.balance,
                        inventory=ctx.inventory,
                        recipes=list(ctx.recipes.values()),
                        demand_forecast=ctx.intel.get("demand_forecast", {}),
                        competitor_briefings=ctx.intel.get("briefings", {}),
                        reputation=ctx.reputation,
                        spending_fraction=0.0,
                    )
                    if decision.menu:
                        logger.info(
                            f"Fallback zone {fz} produced {len(decision.menu)} items"
                        )
                        self.subagent_router.active_zone = fz
                        break

            # Store for downstream skills
            self._latest_decision = decision
            if decision.menu:
                logger.info(
                    f"Menu planned: {len(decision.menu)} items — "
                    f"{[m['name'][:40] for m in decision.menu]}"
                )
            else:
                logger.warning(
                    f"Menu planning produced EMPTY menu for zone={zone}. "
                    f"This means no eligible recipes can be cooked from current inventory."
                )
            return SkillResult(
                skill_name="menu_planning",
                success=True,
                data={"menu_size": len(decision.menu), "menu": decision.menu},
            )
        except Exception as e:
            logger.error(f"Menu planning failed: {e}", exc_info=True)
            return SkillResult(
                skill_name="menu_planning", success=False, error=str(e)
            )

    async def _skill_menu_save(self, ctx: SkillContext) -> SkillResult:
        """Save menu to server via MCP."""
        decision = getattr(self, "_latest_decision", None)
        menu_result = self.skill_orchestrator.get_result("menu_planning")

        menu = []
        if menu_result and menu_result.success:
            menu = menu_result.data.get("menu", [])
        elif decision and hasattr(decision, "menu"):
            menu = decision.menu

        if not menu:
            # Last resort: check if bid_compute produced a menu (during closed_bid)
            bid_result = self.skill_orchestrator.get_result("bid_compute")
            if bid_result and bid_result.success:
                bid_decision = getattr(self, "_latest_decision", None)
                if bid_decision and hasattr(bid_decision, "menu") and bid_decision.menu:
                    menu = bid_decision.menu
                    logger.info(
                        f"Using menu from bid_compute decision: {len(menu)} items"
                    )

        if not menu:
            logger.warning("No menu to save — planning failed or produced empty menu")
            return SkillResult(
                skill_name="menu_save", success=False,
                error="No menu to save (planning failed or empty)"
            )

        try:
            await self.mcp_client.call_tool("save_menu", {"items": menu})
            self.serving.set_menu(menu)
            logger.info(f"Menu saved: {len(menu)} items")
            return SkillResult(
                skill_name="menu_save", success=True,
                data={"menu_size": len(menu)},
            )
        except Exception as e:
            logger.error(f"Failed to save menu: {e}")
            return SkillResult(
                skill_name="menu_save", success=False, error=str(e)
            )

    async def _skill_diplomacy_send(self, ctx: SkillContext) -> SkillResult:
        """Run diplomacy turn."""
        try:
            sent = await self.diplomacy.run_diplomacy_turn(
                competitor_briefings=ctx.intel.get("briefings", {}),
                competitor_states=ctx.intel.get("all_states", {}),
                turn_id=ctx.turn_id,
            )
            logger.info(f"Diplomacy: sent {len(sent)} messages")
            return SkillResult(
                skill_name="diplomacy_send", success=True,
                data={"messages_sent": len(sent)},
            )
        except Exception as e:
            logger.error(f"Diplomacy failed: {e}", exc_info=True)
            return SkillResult(
                skill_name="diplomacy_send", success=False, error=str(e)
            )

    async def _skill_bid_compute(self, ctx: SkillContext) -> SkillResult:
        """Compute optimal bids via ILP."""
        try:
            zone = self.subagent_router.active_zone
            logger.info(
                f"Bid compute: zone={zone}, balance={ctx.balance}, "
                f"inventory={len(ctx.inventory)} types, "
                f"recipes={len(ctx.recipes)}"
            )
            decision = solve_zone_ilp(
                zone=zone,
                balance=ctx.balance,
                inventory=ctx.inventory,
                recipes=list(ctx.recipes.values()),
                demand_forecast=ctx.intel.get("demand_forecast", {}),
                competitor_briefings=ctx.intel.get("briefings", {}),
                reputation=ctx.reputation,
            )
            self._latest_decision = decision
            return SkillResult(
                skill_name="bid_compute", success=True,
                data={
                    "bids": decision.bids,
                    "total_cost": getattr(decision, "total_bid_cost", 0),
                },
            )
        except Exception as e:
            logger.error(f"Bid computation failed: {e}")
            return SkillResult(
                skill_name="bid_compute", success=False, error=str(e)
            )

    async def _skill_bid_submit(self, ctx: SkillContext) -> SkillResult:
        """Submit computed bids via MCP."""
        bid_result = self.skill_orchestrator.get_result("bid_compute")
        bids = []
        if bid_result and bid_result.success:
            bids = bid_result.data.get("bids", [])

        if not bids:
            logger.warning("No bids to submit — bid_compute produced no bids")
            return SkillResult(
                skill_name="bid_submit", success=True,
                data={"submitted": 0},
            )

        # Log each bid for debugging
        for bid in bids:
            logger.info(
                f"  Bid: {bid.get('quantity')}x {bid.get('ingredient')} "
                f"@ {bid.get('bid')} each"
            )

        try:
            await self.mcp_client.call_tool("closed_bid", {"bids": bids})
            total_cost = bid_result.data.get("total_cost", 0) if bid_result else 0
            logger.info(
                f"Bids submitted: {len(bids)} items, "
                f"total cost={total_cost:.0f}"
            )
            return SkillResult(
                skill_name="bid_submit", success=True,
                data={"submitted": len(bids)},
            )
        except Exception as e:
            logger.error(f"Bid submission failed: {e}")
            return SkillResult(
                skill_name="bid_submit", success=False, error=str(e)
            )

    async def _skill_inventory_verify(self, ctx: SkillContext) -> SkillResult:
        """Verify menu items can be cooked with actual post-bid inventory."""
        current_menu = list(self.serving.menu.values())

        # Log inventory state for debugging
        logger.info(
            f"Inventory verify: {len(ctx.inventory)} ingredient types, "
            f"{sum(ctx.inventory.values()) if ctx.inventory else 0} total units"
        )
        if ctx.inventory:
            for ing, qty in sorted(ctx.inventory.items()):
                logger.debug(f"  inventory: {qty}x {ing}")

        logger.info(f"Current menu has {len(current_menu)} items to verify")

        verified = []

        for item in current_menu:
            recipe = self.recipe_db.get(item["name"])
            if recipe:
                missing = []
                for ing, qty in recipe.get("ingredients", {}).items():
                    have = ctx.inventory.get(ing, 0)
                    if have < qty:
                        missing.append(f"{ing} (need={qty}, have={have})")
                if not missing:
                    verified.append(item)
                else:
                    logger.info(
                        f"Removing {item['name']} — insufficient ingredients: "
                        f"{', '.join(missing[:3])}{'...' if len(missing) > 3 else ''}"
                    )

        # If menu shrunk too much, flag for replanning
        if len(verified) < 2 and self.recipe_db:
            logger.warning(
                "Menu too small after verify — forcing menu replan. "
                f"Original={len(current_menu)}, verified={len(verified)}"
            )
            # Clear current menu so menu_planning picks up
            self.serving.set_menu([])
            # CRITICAL: Allow menu_planning + menu_save to re-execute
            # They may have run in a prior phase (closed_bid) but the
            # menu they produced is no longer valid.
            self.skill_orchestrator.executed_this_turn.discard("menu_planning")
            self.skill_orchestrator.executed_this_turn.discard("menu_save")
            self.skill_orchestrator.results_this_turn.pop("menu_planning", None)
            self.skill_orchestrator.results_this_turn.pop("menu_save", None)
            self._latest_decision = None  # clear stale decision
            logger.info("Cleared menu_planning/menu_save from executed — will rerun this phase")
            return SkillResult(
                skill_name="inventory_verify", success=True,
                data={"verified_count": 0, "needs_replan": True},
            )

        # Update the serving pipeline with verified menu
        if verified:
            self.serving.set_menu(verified)

        return SkillResult(
            skill_name="inventory_verify", success=True,
            data={"verified_count": len(verified), "needs_replan": False},
        )

    async def _skill_market_ops(self, ctx: SkillContext) -> SkillResult:
        """Buy missing / sell surplus ingredients."""
        try:
            current_menu = list(self.serving.menu.values())
            if not current_menu:
                logger.warning(
                    "Market ops: No menu set — skipping market operations. "
                    "Selling without a menu would dump all inventory as surplus."
                )
                return SkillResult(
                    skill_name="market_ops", success=True,
                    data={"action": "skipped_no_menu"},
                )
            await self._market_operations(
                inventory=ctx.inventory,
                verified_menu=current_menu,
                balance=ctx.balance,
            )
            return SkillResult(skill_name="market_ops", success=True)
        except Exception as e:
            logger.warning(f"Market ops failed: {e}")
            return SkillResult(
                skill_name="market_ops", success=False, error=str(e)
            )

    async def _skill_restaurant_open(self, ctx: SkillContext) -> SkillResult:
        """Open restaurant for serving."""
        # Don't open if we have no menu
        if not self.serving.menu:
            logger.warning("Not opening — no menu set")
            return SkillResult(
                skill_name="restaurant_open", success=False,
                error="No menu to serve",
            )

        try:
            await self.mcp_client.call_tool(
                "update_restaurant_is_open", {"is_open": True}
            )
            logger.info("Restaurant opened")
            return SkillResult(skill_name="restaurant_open", success=True)
        except Exception as e:
            logger.error(f"Failed to open restaurant: {e}")
            return SkillResult(
                skill_name="restaurant_open", success=False, error=str(e)
            )

    async def _skill_serving_prep(self, ctx: SkillContext) -> SkillResult:
        """Pre-start serving pipeline with inventory snapshot."""
        # Guard: don't start serving pipeline if there's no menu
        if not self.serving.menu:
            logger.warning("Serving prep skipped — no menu set")
            return SkillResult(
                skill_name="serving_prep", success=False,
                error="No menu to serve — serving pipeline not started",
            )
        try:
            await self.serving.start_serving(ctx.turn_id)
            if ctx.inventory:
                self.serving.set_inventory_snapshot(ctx.inventory)
            logger.info(
                f"Serving pipeline ready: menu={len(self.serving.menu)} items, "
                f"inventory={sum(ctx.inventory.values()) if ctx.inventory else 0} units"
            )
            return SkillResult(skill_name="serving_prep", success=True)
        except Exception as e:
            logger.error(f"Serving prep failed: {e}")
            return SkillResult(
                skill_name="serving_prep", success=False, error=str(e)
            )

    async def _skill_serving_readiness_check(self, ctx: SkillContext) -> SkillResult:
        """
        Mid-turn serving entry: check if we can serve at all.

        We may have joined mid-turn at serving phase. Check:
        - Do we have a menu? (may persist from server-side)
        - Do we have inventory?
        - Is restaurant open?
        """
        our_state = ctx.our_state
        menu_items = our_state.get("menu", [])
        inventory = ctx.inventory
        is_open = our_state.get("is_open", False)

        can_serve = bool(menu_items) and bool(inventory) and is_open

        logger.info(
            f"Serving readiness: menu={len(menu_items)}, "
            f"inventory={len(inventory)}, open={is_open} → "
            f"{'READY' if can_serve else 'NOT READY'}"
        )

        if menu_items and not self.serving.menu:
            # Server has a menu but our pipeline doesn't — sync it
            # Server may return menu as list of strings (dish names) rather
            # than list of dicts. Normalize to [{"name": ..., "price": ...}].
            normalised = []
            for item in menu_items:
                if isinstance(item, str):
                    recipe = self.recipe_db.get(item, {})
                    price = recipe.get("price", recipe.get("prestige", 15))
                    normalised.append({"name": item, "price": int(price)})
                elif isinstance(item, dict):
                    normalised.append(item)
                else:
                    logger.warning(f"Unexpected menu item type: {type(item)} — skipping")
            self.serving.set_menu(normalised)
            logger.info(f"Synced {len(normalised)} menu items from server")

        return SkillResult(
            skill_name="serving_readiness_check", success=True,
            data={
                "can_serve": can_serve,
                "has_menu": bool(menu_items),
                "has_inventory": bool(inventory),
                "is_open": is_open,
            },
        )

    async def _skill_emergency_menu(self, ctx: SkillContext) -> SkillResult:
        """
        Emergency menu: set a minimal menu from available inventory.

        Only runs during mid-turn serving entry when no menu exists.
        Cannot use save_menu during serving (server forbids it), but we
        may already have a menu from a previous turn on the server.
        """
        # Check if readiness check found we already have a menu
        readiness = self.skill_orchestrator.get_result("serving_readiness_check")
        if readiness and readiness.data.get("has_menu"):
            return SkillResult(
                skill_name="emergency_menu", success=True,
                data={"action": "menu_already_exists"},
            )

        # In serving phase, save_menu is FORBIDDEN by the server.
        # We cannot set a new menu. Log this and let close_decision handle it.
        logger.warning(
            "No menu and in serving phase — save_menu forbidden. "
            "Will close restaurant to avoid penalties."
        )
        return SkillResult(
            skill_name="emergency_menu", success=False,
            error="Cannot set menu during serving phase (server restriction)",
        )

    async def _skill_serving_monitor(self, ctx: SkillContext) -> SkillResult:
        """Log serving phase start — clients handled by SSE events."""
        logger.info(
            f"[SERVING] Turn {ctx.turn_id} — "
            f"menu={len(self.serving.menu)}, "
            f"awaiting clients"
        )
        return SkillResult(skill_name="serving_monitor", success=True)

    async def _skill_close_decision(self, ctx: SkillContext) -> SkillResult:
        """
        Decide whether to close the restaurant.

        Close if:
        - No menu and in serving (can't set one)
        - No cookable dishes remain (all ingredients exhausted)
        """
        should_close = False
        reason = ""

        if not self.serving.menu:
            should_close = True
            reason = "No menu available"

        if not should_close and not ctx.inventory:
            should_close = True
            reason = "No ingredients available"

        if should_close:
            logger.warning(f"Closing restaurant: {reason}")
            try:
                await self.mcp_client.call_tool(
                    "update_restaurant_is_open", {"is_open": False}
                )
                return SkillResult(
                    skill_name="close_decision", success=True,
                    data={"closed": True, "reason": reason},
                )
            except Exception as e:
                return SkillResult(
                    skill_name="close_decision", success=False, error=str(e)
                )

        return SkillResult(
            skill_name="close_decision", success=True,
            data={"closed": False},
        )

    async def _skill_end_turn_snapshot(self, ctx: SkillContext) -> SkillResult:
        """Capture end-of-turn state, update memories, measure deception."""
        try:
            our_state = ctx.our_state
            if our_state:
                current = RestaurantState(
                    turn_id=ctx.turn_id,
                    phase="stopped",
                    balance=our_state.get("balance", 0),
                    inventory=our_state.get("inventory", {}),
                    reputation=our_state.get("reputation", 0),
                    menu=our_state.get("menu", []),
                    clients_served=len(self.serving.served_this_turn),
                    revenue_this_turn=0,
                )
                self.game_state.snapshot(current)

            # Update competitor memory
            intel = self._latest_intel
            for rid, feat in intel.get("features", {}).items():
                self.competitor_memory.update_entity(rid, feat)
            for rid, cluster in intel.get("clusters", {}).items():
                self.competitor_memory.classify_entity(rid, cluster)

            # Measure deception rewards
            try:
                await self.diplomacy.measure_deception_rewards(
                    competitor_states=intel.get("all_states", {})
                )
            except Exception as e:
                logger.warning(f"Deception reward measurement failed: {e}")

            # Zero inventory
            self.game_state.end_turn(ctx.turn_id)

            # Log summary
            served = len(self.serving.served_this_turn)
            logger.info(
                f"Turn {ctx.turn_id} complete: "
                f"served={served}, "
                f"balance={our_state.get('balance', '?')}, "
                f"reputation={our_state.get('reputation', '?')}"
            )
            return SkillResult(
                skill_name="end_turn_snapshot", success=True,
                data={"served": served},
            )
        except Exception as e:
            logger.error(f"End-turn snapshot failed: {e}", exc_info=True)
            return SkillResult(
                skill_name="end_turn_snapshot", success=False, error=str(e)
            )

    async def _skill_info_gather(self, ctx: SkillContext) -> SkillResult:
        """Gather observable info for next turn planning."""
        try:
            import aiohttp

            # Fetch bid history for this turn
            url = f"{BASE_URL}/bid_history?turn_id={ctx.turn_id}"
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=HEADERS) as resp:
                    if resp.status == 200:
                        bid_history = await resp.json()
                        logger.info(
                            f"Bid history: {len(bid_history)} entries for turn {ctx.turn_id}"
                        )
                    else:
                        bid_history = []

            # Feed to intelligence for next turn
            if bid_history:
                self._latest_intel["bid_history"] = bid_history

            return SkillResult(
                skill_name="info_gather", success=True,
                data={"bid_history_entries": len(bid_history)},
            )
        except Exception as e:
            logger.warning(f"Info gather failed: {e}")
            return SkillResult(
                skill_name="info_gather", success=False, error=str(e)
            )

    # ══════════════════════════════════════════════════════════════
    #  MARKET OPERATIONS (shared helper)
    # ══════════════════════════════════════════════════════════════

    async def _market_operations(
        self,
        inventory: dict[str, int],
        verified_menu: list[dict],
        balance: float,
    ):
        """
        Market buy/sell operations:
        - BUY: ingredients we need for the menu but don't have enough of
        - SELL: ingredients we have surplus of (not needed by any menu recipe)

        Prices are INTELLIGENCE-DRIVEN:
        - Use competitor briefings to gauge demand
        - When no competition is detected, use minimum prices (exploit monopoly)
        - Never use wallet-based pricing
        """
        # Compute what the menu needs
        needed: dict[str, int] = {}
        for item in verified_menu:
            recipe = self.recipe_db.get(item["name"], {})
            for ing, qty in recipe.get("ingredients", {}).items():
                needed[ing] = needed.get(ing, 0) + qty

        # Assess competition level from intelligence
        intel = self._latest_intel
        briefings = intel.get("briefings", {})
        active_competitors = sum(
            1 for b in briefings.values()
            if b.get("is_active", True) and b.get("menu_size", 0) > 0
        )
        competition_level = min(1.0, active_competitors / 5.0)  # 0.0 = monopoly

        # BUY: ingredients where inventory < needed
        for ing, need_qty in needed.items():
            have = inventory.get(ing, 0)
            deficit = need_qty - have
            if deficit > 0:
                # Intelligence-driven buy price:
                # - Base: 10 (minimum viable bid)
                # - If competitors exist and want this ingredient, bid higher
                # - If no competition: bid MINIMUM to maximize profit
                base_price = 10
                if briefings:
                    from src.decision.ilp_solver import compute_bid_price
                    intel_price = compute_bid_price(
                        ing,
                        briefings,
                        intel.get("demand_forecast", {}),
                    )
                    # Scale by competition: no competition = use base, competition = use intel
                    buy_price = int(base_price + (intel_price - base_price) * competition_level)
                else:
                    buy_price = base_price

                buy_price = max(10, min(buy_price, 100))  # hard cap at 100

                try:
                    await self.mcp_client.call_tool(
                        "create_market_entry",
                        {
                            "side": "BUY",
                            "ingredient_name": ing,
                            "quantity": deficit,
                            "price": buy_price,
                        },
                    )
                    logger.info(f"Market BUY: {deficit}x {ing} @ {buy_price}")
                except Exception as e:
                    logger.warning(f"Market BUY failed for {ing}: {e}")

        # SELL: ingredients we have but no menu recipe uses
        needed_ings = set(needed.keys())
        for ing, qty in inventory.items():
            if ing not in needed_ings and qty > 0:
                # Sell at a premium — let others pay more
                sell_price = max(15, int(30 * (1 + competition_level)))
                try:
                    await self.mcp_client.call_tool(
                        "create_market_entry",
                        {
                            "side": "SELL",
                            "ingredient_name": ing,
                            "quantity": qty,
                            "price": sell_price,
                        },
                    )
                    logger.info(f"Market SELL: {qty}x {ing} @ {sell_price}")
                except Exception as e:
                    logger.warning(f"Market SELL failed for {ing}: {e}")

    # ══════════════════════════════════════════════════════════════
    #  COUNTDOWN TIMER
    # ══════════════════════════════════════════════════════════════

    async def _countdown_timer(self):
        """
        Background task that periodically logs estimated time remaining
        in the current phase and until the next turn.

        Phase duration estimates are updated from observed transitions
        (rolling average in PhaseRouter).
        """
        logger.info("Countdown timer started")
        while self._running:
            try:
                await asyncio.sleep(COUNTDOWN_LOG_INTERVAL)

                phase = self.phase_router.current_phase
                if not phase:
                    continue  # no active game

                turn = self.phase_router.current_turn
                elapsed = self.phase_router.elapsed_in_phase
                remaining = self.phase_router.estimated_remaining
                est_total = self.phase_router.estimated_durations.get(phase, 60)

                # Format times
                def fmt_time(s: float) -> str:
                    m, sec = divmod(int(s), 60)
                    return f"{m}m{sec:02d}s" if m > 0 else f"{sec}s"

                # Compute time until next turn starts
                # Sum remaining of current phase + all subsequent phases
                from src.skills import PHASE_ORDER

                if phase in PHASE_ORDER:
                    idx = PHASE_ORDER.index(phase)
                    remaining_phases = PHASE_ORDER[idx + 1:]
                    time_to_next_turn = remaining
                    for p in remaining_phases:
                        time_to_next_turn += self.phase_router.estimated_durations.get(
                            p, 60
                        )
                else:
                    time_to_next_turn = remaining

                # Build progress bar for phase
                progress = min(1.0, elapsed / max(est_total, 1))
                bar_len = 20
                filled = int(bar_len * progress)
                bar = "█" * filled + "░" * (bar_len - filled)

                logger.info(
                    f"⏱ Turn {turn} | {phase.upper()} "
                    f"[{bar}] {fmt_time(elapsed)}/{fmt_time(est_total)} "
                    f"(~{fmt_time(remaining)} left) | "
                    f"Next turn in ~{fmt_time(time_to_next_turn)}"
                )

            except asyncio.CancelledError:
                logger.info("Countdown timer stopped")
                return
            except Exception as e:
                logger.debug(f"Countdown timer error: {e}")


async def main():
    """Entry point."""
    # Start (or reuse) the tracker sidecar before anything else.
    # Blocks until tracker is ready or all retries are exhausted.
    _start_tracker()

    orchestrator = GameOrchestrator()

    # Handle graceful shutdown
    loop = asyncio.get_event_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(
            sig, lambda: asyncio.create_task(_shutdown(orchestrator))
        )

    try:
        await orchestrator.start()
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt — shutting down")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


async def _shutdown(orchestrator: GameOrchestrator):
    """Graceful shutdown."""
    global _tracker_proc
    logger.info("Shutting down...")
    orchestrator._running = False
    # Cancel countdown timer
    if orchestrator._countdown_task:
        orchestrator._countdown_task.cancel()
    # Allow pending tasks to complete
    await asyncio.sleep(0.5)
    # Terminate tracker sidecar if we launched it
    if _tracker_proc is not None and _tracker_proc.poll() is None:
        logger.info(f"Terminating tracker (pid={_tracker_proc.pid})")
        _tracker_proc.terminate()
        try:
            _tracker_proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            _tracker_proc.kill()
        _tracker_proc = None
    sys.exit(0)


# ── Tracker sidecar process (set by _start_tracker, torn down by _shutdown) ──
_tracker_proc: subprocess.Popen | None = None

# ── Tracker startup constants ──
_TRACKER_PORT = 5555
_TRACKER_RETRIES = 3          # attempts to launch a fresh tracker
_TRACKER_RETRY_DELAY = 3      # seconds between launch attempts
_TRACKER_STARTUP_TIMEOUT = 15 # seconds to wait for Flask to bind after each launch
_TRACKER_SCRIPT = (
    Path(__file__).parent.parent / "_server_changes" / "tracker.py"
)


def _is_port_open(port: int, host: str = "127.0.0.1") -> bool:
    """Return True if something is already listening on *port*."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1.0)
        return s.connect_ex((host, port)) == 0


def _wait_for_port(port: int, timeout: float) -> bool:
    """Poll until port is open or timeout expires. Returns True if open."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if _is_port_open(port):
            return True
        time.sleep(0.5)
    return False


def _start_tracker() -> bool:
    """
    Ensure the tracker sidecar is running on port 5555.

    Strategy:
      1. If port already open → someone started it manually, reuse it.
      2. Otherwise, launch _server_changes/tracker.py as a subprocess and
         wait up to _TRACKER_STARTUP_TIMEOUT seconds for Flask to bind.
      3. Retry up to _TRACKER_RETRIES times on failure.
      4. If all retries exhausted, log a prominent warning and return False
         (agent continues in degraded mode — no competitor intelligence,
         serving / bidding / menu logic all still work).

    Returns True if tracker is available, False if running without it.
    """
    global _tracker_proc

    if _is_port_open(_TRACKER_PORT):
        logger.info(
            f"Tracker already running on port {_TRACKER_PORT} — reusing existing instance"
        )
        return True

    if not _TRACKER_SCRIPT.exists():
        logger.error(f"Tracker script not found at {_TRACKER_SCRIPT} — running without tracker")
        return False

    log_path = Path("tracker.log")
    for attempt in range(1, _TRACKER_RETRIES + 1):
        logger.info(
            f"Starting tracker (attempt {attempt}/{_TRACKER_RETRIES}) — "
            f"log → {log_path.resolve()}"
        )
        try:
            log_file = open(log_path, "a")
            proc = subprocess.Popen(
                [sys.executable, str(_TRACKER_SCRIPT)],
                stdout=log_file,
                stderr=log_file,
                # New process group so Ctrl-C in the terminal doesn't
                # also kill the tracker (we handle teardown ourselves).
                start_new_session=True,
            )
            ready = _wait_for_port(_TRACKER_PORT, _TRACKER_STARTUP_TIMEOUT)
            if ready:
                _tracker_proc = proc
                logger.info(
                    f"Tracker ready on port {_TRACKER_PORT} (pid={proc.pid})"
                )
                return True

            # Flask didn't bind in time — kill and retry
            logger.warning(
                f"Tracker did not become ready within {_TRACKER_STARTUP_TIMEOUT}s "
                f"(attempt {attempt}/{_TRACKER_RETRIES})"
            )
            proc.terminate()
            proc.wait(timeout=5)

        except Exception as exc:
            logger.warning(f"Tracker launch attempt {attempt} failed: {exc}")

        if attempt < _TRACKER_RETRIES:
            logger.info(f"Retrying in {_TRACKER_RETRY_DELAY}s…")
            time.sleep(_TRACKER_RETRY_DELAY)

    logger.warning(
        "=" * 60 + "\n"
        "  TRACKER UNAVAILABLE — running in DEGRADED MODE\n"
        "  Competitor intelligence will be empty this run.\n"
        "  Serving, bidding and menu logic are unaffected.\n"
        + "=" * 60
    )
    return False


if __name__ == "__main__":
    asyncio.run(main())
