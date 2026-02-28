"""
SPAM! — Main Entry Point
==========================
Wires SSE → EventBus → PhaseRouter → all subsystems.
Implements the complete game agent loop.

Usage:
    python -m src.main
"""

import asyncio
import logging
import signal
import sys

from datapizza.clients.openai.openai_client import OpenAIClient
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


class GameOrchestrator:
    """
    Central orchestrator wiring all subsystems together.

    Lifecycle:
      1. Initialise datapizza clients & MCP
      2. Connect SSE via ReactiveEventBus
      3. Route events to phase-specific handlers
      4. Each phase handler coordinates subsystems
    """

    def __init__(self):
        # ── LLM Clients ──
        self.primary_client = OpenAIClient(
            api_key=REGOLO_API_KEY,
            model=PRIMARY_MODEL,
            base_url=REGOLO_BASE_URL,
            system_prompt=(
                f"You are the AI brain of restaurant '{TEAM_NAME}' (ID {TEAM_ID}). "
                "Make optimal decisions for bidding, menu, and serving."
            ),
        )
        self.fast_client = OpenAIClient(
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

        # ── State ──
        self.recipe_db: dict[str, dict] = {}
        self._latest_intel: dict = {}
        self._running = False

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

        # Register phase handlers
        self.phase_router.register("speaking", self._phase_speaking)
        self.phase_router.register("closed_bid", self._phase_closed_bid)
        self.phase_router.register("waiting", self._phase_waiting)
        self.phase_router.register("serving", self._phase_serving)
        self.phase_router.register("stopped", self._phase_stopped)

        # Turn change callback
        self.phase_router.on_turn_change(self._on_turn_change)

    # ── Game Events ──

    async def _handle_game_started(self, data: dict):
        """Handle game_started SSE event."""
        logger.info("Game started event received")
        self.phase_router.current_phase = None
        self.phase_router.current_turn = 0

        # Reload recipes in case they changed
        self.recipe_db = await load_recipes()
        self.serving.recipes = self.recipe_db

    async def _handle_game_reset(self, data: dict):
        """Handle game_reset — clear turn-scoped state, preserve cross-turn memory."""
        logger.info("Game reset — clearing turn state")
        self.game_state.reset()
        self.serving.set_menu([])
        self.phase_router.current_phase = None
        self.phase_router.current_turn = 0
        # Keep: competitor_memory, client_library, event_log, message_log

    async def _on_turn_change(self, turn_id: int):
        """Called when a new turn starts (stopped → speaking)."""
        logger.info(f"Turn change: {turn_id}")
        self.game_state.new_turn(turn_id)

    # ── Client / Serving Events ──

    async def _handle_client_spawned(self, data: dict):
        """Handle client_spawned SSE event — only during serving phase."""
        if self.phase_router.current_phase != "serving":
            logger.warning("client_spawned outside serving phase — ignoring")
            return
        await self.serving.handle_client(data)

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

    # ── Phase Handlers ──

    async def _phase_speaking(self, data: dict):
        """
        Speaking phase:
        1. Run intelligence pipeline
        2. Set tentative menu (pre-bid)
        3. Run diplomacy

        Zone selection is deferred to waiting phase (after bids resolve,
        when we know our actual inventory).
        """
        turn_id = data.get("turn_id", self.phase_router.current_turn)
        logger.info(f"[SPEAKING] Turn {turn_id}")

        # 1. Run intelligence pipeline
        try:
            intel = await self.intelligence.run(turn_id)
            self._latest_intel = intel
            logger.info(
                f"Intelligence: {len(intel.get('briefings', {}))} briefings, "
                f"{len(intel.get('clusters', {}))} clusters"
            )
        except Exception as e:
            logger.error(f"Intelligence pipeline failed: {e}", exc_info=True)
            intel = {}
            self._latest_intel = intel

        # 2. Fetch our current state
        our_state = await load_our_restaurant()
        balance = our_state.get("balance", 10000) if our_state else 10000
        inventory = our_state.get("inventory", {}) if our_state else {}
        reputation = our_state.get("reputation", 50) if our_state else 50

        # 3. Tentative zone selection (pre-bid — will be re-evaluated in waiting)
        zone = self.subagent_router.route(
            balance=balance,
            inventory=inventory,
            reputation=reputation,
            recipes=list(self.recipe_db.values()),
            competitor_clusters=intel.get("clusters", {}),
            competitor_briefings=intel.get("briefings", {}),
        )
        logger.info(f"Tentative zone: {zone}")

        # 4. Compute tentative menu via MILP
        decision = solve_zone_ilp(
            zone=zone,
            balance=balance,
            inventory=inventory,
            recipes=list(self.recipe_db.values()),
            demand_forecast=intel.get("demand_forecast", {}),
            competitor_briefings=intel.get("briefings", {}),
            reputation=reputation,
        )

        # 5. Set tentative menu via MCP
        if decision.menu:
            try:
                result = await self.mcp_client.call_tool(
                    "save_menu",
                    {"items": decision.menu},
                )
                self.serving.set_menu(decision.menu)
                logger.info(f"Tentative menu set: {len(decision.menu)} items")
            except Exception as e:
                logger.error(f"Failed to set menu: {e}")

        # 6. Run diplomacy
        try:
            sent = await self.diplomacy.run_diplomacy_turn(
                competitor_briefings=intel.get("briefings", {}),
                competitor_states=intel.get("all_states", {}),
                turn_id=turn_id,
            )
            logger.info(f"Diplomacy: sent {len(sent)} messages")
        except Exception as e:
            logger.error(f"Diplomacy failed: {e}", exc_info=True)

    async def _phase_closed_bid(self, data: dict):
        """
        Closed bid phase:
        1. Compute optimal bids from ILP
        2. Submit bids via MCP (single call, final)
        """
        turn_id = data.get("turn_id", self.phase_router.current_turn)
        logger.info(f"[CLOSED_BID] Turn {turn_id}")

        intel = self._latest_intel

        # Get current state
        our_state = await load_our_restaurant()
        balance = our_state.get("balance", 10000) if our_state else 10000
        inventory = our_state.get("inventory", {}) if our_state else {}
        reputation = our_state.get("reputation", 50) if our_state else 50

        # Get zone from subagent router
        zone = self.subagent_router.active_zone

        # Compute bids via ILP
        decision = solve_zone_ilp(
            zone=zone,
            balance=balance,
            inventory=inventory,
            recipes=list(self.recipe_db.values()),
            demand_forecast=intel.get("demand_forecast", {}),
            competitor_briefings=intel.get("briefings", {}),
            reputation=reputation,
        )

        if decision.bids:
            try:
                result = await self.mcp_client.call_tool(
                    "closed_bid",
                    {"bids": decision.bids},
                )
                logger.info(
                    f"Bids submitted: {len(decision.bids)} items, "
                    f"total cost={decision.total_bid_cost:.0f}"
                )
            except Exception as e:
                logger.error(f"Bid submission failed: {e}")
        else:
            logger.warning("No bids computed — skipping bid phase")

    async def _phase_waiting(self, data: dict):
        """
        Waiting phase (after bids resolve):
        1. Fetch fresh post-bid inventory
        2. Re-select zone with actual inventory (ILP zone classification)
        3. Verify/rebuild menu to match actual inventory
        4. Market operations — buy missing, sell surplus
        5. Set final menu
        6. Open restaurant
        """
        turn_id = data.get("turn_id", self.phase_router.current_turn)
        logger.info(f"[WAITING] Turn {turn_id}")

        intel = self._latest_intel

        # 1. Fetch fresh inventory (post-bid)
        our_state = await load_our_restaurant()
        if our_state:
            balance = our_state.get("balance", 10000)
            inventory = our_state.get("inventory", {})
            reputation = our_state.get("reputation", 50)
            logger.info(
                f"Post-bid state: balance={balance}, "
                f"inventory_items={len(inventory)}, rep={reputation}"
            )
        else:
            balance = 10000
            inventory = {}
            reputation = 50

        # 2. Re-select zone with actual post-bid inventory
        zone = self.subagent_router.route(
            balance=balance,
            inventory=inventory,
            reputation=reputation,
            recipes=list(self.recipe_db.values()),
            competitor_clusters=intel.get("clusters", {}),
            competitor_briefings=intel.get("briefings", {}),
        )
        logger.info(f"Post-bid zone selection: {zone}")

        # 3. Verify menu items can be cooked with actual inventory
        current_menu = list(self.serving.menu.values())
        verified_menu = []

        for item in current_menu:
            recipe = self.recipe_db.get(item["name"])
            if recipe:
                can_cook = all(
                    inventory.get(ing, 0) >= qty
                    for ing, qty in recipe.get("ingredients", {}).items()
                )
                if can_cook:
                    verified_menu.append(item)
                else:
                    logger.info(f"Removing {item['name']} — insufficient ingredients")

        # If menu shrunk too much, recompute with MILP
        if len(verified_menu) < 2 and self.recipe_db:
            logger.info("Menu too small — recomputing with MILP for actual inventory")
            decision = solve_zone_ilp(
                zone=zone,
                balance=balance,
                inventory=inventory,
                recipes=list(self.recipe_db.values()),
                demand_forecast=intel.get("demand_forecast", {}),
                competitor_briefings=intel.get("briefings", {}),
                reputation=reputation,
                spending_fraction=0.0,  # no more bids in waiting
            )
            verified_menu = decision.menu

        # 4. Market operations — buy missing ingredients, sell surplus
        await self._market_operations(
            inventory=inventory,
            verified_menu=verified_menu,
            balance=balance,
        )

        # 5. Set final menu
        if verified_menu:
            try:
                result = await self.mcp_client.call_tool(
                    "save_menu",
                    {"items": verified_menu},
                )
                self.serving.set_menu(verified_menu)
                logger.info(f"Final menu: {len(verified_menu)} items")
            except Exception as e:
                logger.error(f"Failed to update menu: {e}")

        # 6. Open restaurant
        try:
            result = await self.mcp_client.call_tool(
                "update_restaurant_is_open",
                {"is_open": True},
            )
            logger.info("Restaurant opened")
        except Exception as e:
            logger.error(f"Failed to open restaurant: {e}")

        # 7. Pre-start serving pipeline
        await self.serving.start_serving(turn_id)

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
        """
        # Compute what the menu needs
        needed: dict[str, int] = {}
        for item in verified_menu:
            recipe = self.recipe_db.get(item["name"], {})
            for ing, qty in recipe.get("ingredients", {}).items():
                needed[ing] = needed.get(ing, 0) + qty

        # BUY: ingredients where inventory < needed
        for ing, need_qty in needed.items():
            have = inventory.get(ing, 0)
            deficit = need_qty - have
            if deficit > 0:
                buy_price = max(10, int(balance * 0.02))  # conservative price
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
                sell_price = max(5, int(balance * 0.01))  # low price to move
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

    async def _phase_serving(self, data: dict):
        """
        Serving phase:
        Clients are handled by SSE events → client_spawned → preparation_complete.
        This handler just logs the transition.
        """
        turn_id = data.get("turn_id", self.phase_router.current_turn)
        logger.info(f"[SERVING] Turn {turn_id} — awaiting clients")

    async def _phase_stopped(self, data: dict):
        """
        Stopped phase:
        1. Stop serving pipeline
        2. End-of-turn snapshot
        3. Update all memories
        4. Measure deception rewards
        5. Zero inventory
        6. Persist state
        """
        turn_id = data.get("turn_id", self.phase_router.current_turn)
        logger.info(f"[STOPPED] Turn {turn_id}")

        # 1. Stop serving
        await self.serving.stop_serving()

        # 2. End-of-turn snapshot
        our_state = await load_our_restaurant()
        if our_state:
            current = RestaurantState(
                turn_id=turn_id,
                phase="stopped",
                balance=our_state.get("balance", 0),
                inventory=our_state.get("inventory", {}),
                reputation=our_state.get("reputation", 0),
                menu=our_state.get("menu", []),
                clients_served=len(self.serving.served_this_turn),
                revenue_this_turn=0,
            )
            self.game_state.snapshot(current)

        # 3. Update competitor memory from intelligence
        intel = self._latest_intel
        all_features = intel.get("features", {})
        for rid, feat in all_features.items():
            self.competitor_memory.update_entity(rid, feat)
        clusters = intel.get("clusters", {})
        for rid, cluster in clusters.items():
            self.competitor_memory.classify_entity(rid, cluster)

        # 4. Measure deception rewards
        try:
            await self.diplomacy.measure_deception_rewards(
                competitor_states=intel.get("all_states", {})
            )
        except Exception as e:
            logger.warning(f"Deception reward measurement failed: {e}")

        # 5. Zero inventory (all ingredients expire at end of turn)
        self.game_state.end_turn(turn_id)

        # 6. Log turn summary
        profiles = self.serving.served_this_turn
        logger.info(
            f"Turn {turn_id} complete: "
            f"served={len(profiles)}, "
            f"balance={our_state.get('balance', '?')}, "
            f"reputation={our_state.get('reputation', '?')}"
        )


async def main():
    """Entry point."""
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
    logger.info("Shutting down...")
    orchestrator._running = False
    # Allow pending tasks to complete
    await asyncio.sleep(0.5)
    sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())
