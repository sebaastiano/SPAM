"""
main.py — SPAM! Agent entry point.

Initializes all subsystems, wires SSE events to the event bus,
and runs the phase-based game loop.
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys
from typing import Any

import aiohttp

from src.config import (
    BASE_URL,
    HEADERS,
    REGOLO_API_KEY,
    REGOLO_BASE_URL,
    SSE_HEADERS,
    SSE_URL,
    TEAM_ID,
    PRIMARY_MODEL,
    FAST_MODEL,
)
from src.decision.pricing import compute_menu_price
from src.decision.subagent_router import SubagentRouter
from src.diplomacy.agent import DiplomacyAgent
from src.diplomacy.deception_bandit import DeceptionBandit
from src.diplomacy.firewall import GroundTruthFirewall
from src.diplomacy.pseudo_gan import PseudoGAN
from src.event_bus import ReactiveEventBus
from src.intelligence.pipeline import IntelligencePipeline
from src.intelligence.tracker_bridge import TrackerBridge
from src.memory.client_profile import ClientProfileMemory, IntoleranceDetector
from src.memory.competitor import CompetitorMemory
from src.memory.event_log import EventLog
from src.memory.game_state import GameStateMemory
from src.memory.message_log import MessageMemory
from src.models import Recipe
from src.phase_router import PhaseRouter
from src.serving.pipeline import ServingPipeline

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)-28s | %(levelname)-5s | %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("main")


# ═══════════════════════════════════════════════════════════════════
#  Global state — instantiated once in ``main()``
# ═══════════════════════════════════════════════════════════════════

recipe_db: dict[str, Recipe] = {}
session: aiohttp.ClientSession | None = None

# Subsystem singletons (set in main)
event_log: EventLog
game_memory: GameStateMemory
competitor_memory: CompetitorMemory
client_memory: ClientProfileMemory
message_memory: MessageMemory
intolerance: IntoleranceDetector

tracker_bridge: TrackerBridge
intel_pipeline: IntelligencePipeline
router: SubagentRouter
serving: ServingPipeline
diplomacy: DiplomacyAgent
phase_router: PhaseRouter
event_bus: ReactiveEventBus


# ═══════════════════════════════════════════════════════════════════
#  Bootstrap helpers
# ═══════════════════════════════════════════════════════════════════


async def fetch_recipes(sess: aiohttp.ClientSession) -> dict[str, Recipe]:
    """GET /recipes → dict[name, Recipe]."""
    url = f"{BASE_URL}/recipes"
    async with sess.get(url, headers=HEADERS) as resp:
        resp.raise_for_status()
        raw = await resp.json()

    db: dict[str, Recipe] = {}
    for r in raw:
        name = r.get("name", "")
        db[name] = Recipe(
            name=name,
            preparation_time_ms=r.get("preparationTimeMs", 0),
            ingredients=r.get("ingredients", {}),
            prestige=r.get("prestige", 0),
        )
    log.info("Loaded %d recipes from server", len(db))
    return db


async def fetch_own_state(sess: aiohttp.ClientSession) -> dict:
    """GET /restaurant/17 → raw JSON dict."""
    url = f"{BASE_URL}/restaurant/{TEAM_ID}"
    async with sess.get(url, headers=HEADERS) as resp:
        resp.raise_for_status()
        return await resp.json()


async def mcp_call(
    sess: aiohttp.ClientSession,
    tool_name: str,
    arguments: dict,
) -> dict:
    """Execute an MCP JSON-RPC tool call."""
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {"name": tool_name, "arguments": arguments},
    }
    async with sess.post(
        f"{BASE_URL}/mcp", json=payload, headers=HEADERS
    ) as resp:
        result = await resp.json()
    is_error = result.get("result", {}).get("isError", False)
    content = (
        result.get("result", {}).get("content", [{}])[0].get("text", "")
    )
    if is_error:
        log.warning("MCP %s error: %s", tool_name, content)
    else:
        log.info("MCP %s OK: %s", tool_name, content[:120])
    return result


# ═══════════════════════════════════════════════════════════════════
#  Phase handlers
# ═══════════════════════════════════════════════════════════════════


async def on_speaking(data: dict[str, Any]) -> None:
    """Phase: speaking — intelligence + set menu + diplomacy."""
    global recipe_db, session
    assert session is not None

    game_memory.set_phase("speaking")
    log.info("── SPEAKING (turn %d) ──", game_memory.current.turn_id)

    # 1. Run intelligence pipeline
    intel = await intel_pipeline.run(game_memory.current.turn_id)
    briefings = intel["briefings"]
    clusters = intel["clusters"]
    demand_forecast = intel["demand_forecast"]

    # 2. Select zone
    zone = router.select(game_memory.current, clusters, briefings)

    # 3. Generate ILP plan
    decision = router.plan(
        game_memory.current, recipe_db, demand_forecast, briefings
    )

    # 4. Set menu (save_menu MCP)
    if decision.menu:
        await mcp_call(session, "save_menu", {"items": decision.menu})
        game_memory.current.menu = decision.menu
        log.info("Menu set: %d items", len(decision.menu))

    # 5. Diplomacy
    if phase_router.can_send_message():
        try:
            await diplomacy.run_speaking_phase(
                briefings, session, game_memory.current.turn_id
            )
        except Exception as exc:
            log.warning("Diplomacy error: %s", exc)


async def on_closed_bid(data: dict[str, Any]) -> None:
    """Phase: closed_bid — submit bids."""
    global session
    assert session is not None

    game_memory.set_phase("closed_bid")
    log.info("── CLOSED_BID (turn %d) ──", game_memory.current.turn_id)

    # Use latest decision from speaking phase
    decision = router.last_decision
    if decision and decision.bids:
        await mcp_call(session, "closed_bid", {"bids": decision.bids})
        log.info("Bids submitted: %d items, est. cost %.0f",
                 len(decision.bids),
                 sum(b["bid"] * b["quantity"] for b in decision.bids))
    else:
        log.warning("No bids to submit — no ILP decision available")


async def on_waiting(data: dict[str, Any]) -> None:
    """Phase: waiting — refresh inventory, adjust menu, open restaurant."""
    global session, recipe_db
    assert session is not None

    game_memory.set_phase("waiting")
    log.info("── WAITING (turn %d) ──", game_memory.current.turn_id)

    # 1. Fetch fresh state (post-bid inventory is now accurate)
    own = await fetch_own_state(session)
    game_memory.update_from_server(own)
    log.info(
        "Post-bid state: balance=%.0f, inventory=%s",
        game_memory.current.balance,
        game_memory.current.inventory,
    )

    # 2. Re-evaluate menu against actual inventory
    available_dishes = []
    for item in game_memory.current.menu:
        dish_name = item.get("name", "")
        recipe = recipe_db.get(dish_name)
        if not recipe:
            continue
        # Check we have all ingredients
        can_cook = all(
            game_memory.current.inventory.get(ing, 0) >= qty
            for ing, qty in recipe.ingredients.items()
        )
        if can_cook:
            available_dishes.append(item)

    if available_dishes != game_memory.current.menu:
        log.info(
            "Menu trimmed: %d → %d dishes (inventory check)",
            len(game_memory.current.menu),
            len(available_dishes),
        )
        if available_dishes:
            await mcp_call(session, "save_menu", {"items": available_dishes})
            game_memory.current.menu = available_dishes
        else:
            log.warning("No dishes can be cooked with current inventory!")

    # 3. Pre-compute serving lookup
    await serving.start_phase(
        game_memory.current.turn_id, game_memory.current.menu
    )

    # 4. Open the restaurant
    await mcp_call(
        session, "update_restaurant_is_open", {"is_open": True}
    )
    game_memory.current.is_open = True


async def on_serving(data: dict[str, Any]) -> None:
    """Phase: serving — handled reactively via client_spawned events."""
    game_memory.set_phase("serving")
    log.info("── SERVING (turn %d) ──", game_memory.current.turn_id)
    # Actual serving is handled by on_client_spawned / on_preparation_complete


async def on_stopped(data: dict[str, Any]) -> None:
    """Phase: stopped — end-of-turn snapshot, memory updates."""
    global session
    assert session is not None

    game_memory.set_phase("stopped")
    log.info("── STOPPED (turn %d) ──", game_memory.current.turn_id)

    # 1. Close serving pipeline
    await serving.end_phase()

    # 2. Fetch final state (GET only — no MCP allowed)
    try:
        own = await fetch_own_state(session)
        game_memory.update_from_server(own)
    except Exception as exc:
        log.warning("Failed to fetch final state: %s", exc)

    # 3. Snapshot + zero inventory (expires each turn)
    game_memory.end_turn_snapshot()

    # 4. Log summary
    last = game_memory.last_turn()
    if last:
        log.info(
            "Turn %d summary: balance=%.0f, rep=%.1f, clients=%d, revenue=%.0f",
            last.turn_id, last.balance, last.reputation,
            last.clients_served, last.revenue_this_turn,
        )

    # 5. Persist event log
    event_log.log({
        "type": "turn_end",
        "turn_id": game_memory.current.turn_id,
        "balance": game_memory.current.balance,
        "reputation": game_memory.current.reputation,
    })


# ═══════════════════════════════════════════════════════════════════
#  SSE event handlers
# ═══════════════════════════════════════════════════════════════════


async def on_game_started(data: dict[str, Any]) -> None:
    """game_started — initialize / re-initialize."""
    global recipe_db, session
    assert session is not None

    log.info("=== GAME STARTED ===")
    game_memory.reset()
    game_memory.set_turn(1)

    # Fetch recipes if not cached
    if not recipe_db:
        recipe_db = await fetch_recipes(session)
        intel_pipeline.set_recipe_db(recipe_db)

    # Initial state pull
    own = await fetch_own_state(session)
    game_memory.update_from_server(own)
    log.info(
        "Initial state: balance=%.0f, reputation=%.1f",
        game_memory.current.balance,
        game_memory.current.reputation,
    )

    event_log.log({"type": "game_started"})


async def on_game_phase_changed(data: dict[str, Any]) -> None:
    """game_phase_changed — delegate to PhaseRouter."""
    phase = data.get("phase", "unknown")

    # Update turn counter on transition to speaking (new turn)
    if phase == "speaking":
        current_turn = game_memory.current.turn_id
        game_memory.set_turn(current_turn + 1 if current_turn > 0 else 1)

    event_log.log({"type": "phase_changed", "phase": phase})
    await phase_router.handle_phase_change(data)


async def on_client_spawned(data: dict[str, Any]) -> None:
    """client_spawned — route to serving pipeline."""
    if not phase_router.is_serving():
        log.warning("client_spawned outside serving phase — ignoring")
        return

    event_log.log({"type": "client_spawned", "data": data})
    await serving.handle_client_spawned(data)


async def on_preparation_complete(data: dict[str, Any]) -> None:
    """preparation_complete — route to serving pipeline."""
    if not phase_router.is_serving():
        log.warning("preparation_complete outside serving — ignoring")
        return

    event_log.log({"type": "preparation_complete", "data": data})
    await serving.handle_preparation_complete(data)


async def on_new_message(data: dict[str, Any]) -> None:
    """new_message — process through diplomacy firewall."""
    event_log.log({"type": "new_message", "data": data})
    await diplomacy.handle_incoming(data)


async def on_message(data: dict[str, Any]) -> None:
    """message (broadcast) — log market broadcasts."""
    event_log.log({"type": "broadcast_message", "data": data})
    message_memory.record_broadcast(data)


async def on_game_reset(data: dict[str, Any]) -> None:
    """game_reset — clear turn-scoped state, preserve cross-turn memory."""
    log.info("=== GAME RESET ===")
    game_memory.reset()
    event_log.log({"type": "game_reset"})
    # Don't call any MCP — wait for next game_started


async def on_heartbeat(data: dict[str, Any]) -> None:
    """heartbeat — just confirm connection is alive."""
    pass  # no-op; logged by middleware if needed


# ═══════════════════════════════════════════════════════════════════
#  Event bus middleware
# ═══════════════════════════════════════════════════════════════════


async def logging_middleware(
    event_type: str, data: dict[str, Any]
) -> dict[str, Any] | None:
    """Logs every SSE event (lightweight)."""
    if event_type != "heartbeat":
        log.debug("SSE event: %s — %s", event_type, json.dumps(data)[:200])
    return data


# ═══════════════════════════════════════════════════════════════════
#  LLM client factory (optional — for PseudoGAN)
# ═══════════════════════════════════════════════════════════════════


def _build_llm_clients() -> tuple[Any, Any] | tuple[None, None]:
    """Try to build datapizza OpenAILikeClient instances.

    Returns (generator_client, discriminator_client) or (None, None)
    if the API key is missing or the import fails.
    """
    if not REGOLO_API_KEY:
        log.warning("REGOLO_API_KEY not set — PseudoGAN disabled")
        return None, None

    try:
        from datapizza.clients.openai_like import OpenAILikeClient

        gen = OpenAILikeClient(
            base_url=REGOLO_BASE_URL,
            api_key=REGOLO_API_KEY,
            model=PRIMARY_MODEL,
        )
        disc = OpenAILikeClient(
            base_url=REGOLO_BASE_URL,
            api_key=REGOLO_API_KEY,
            model=FAST_MODEL,
        )
        log.info("LLM clients created (generator=%s, discriminator=%s)",
                 PRIMARY_MODEL, FAST_MODEL)
        return gen, disc
    except Exception as exc:
        log.warning("Failed to create LLM clients: %s", exc)
        return None, None


# ═══════════════════════════════════════════════════════════════════
#  Main
# ═══════════════════════════════════════════════════════════════════


async def main() -> None:
    global recipe_db, session
    global event_log, game_memory, competitor_memory
    global client_memory, message_memory, intolerance
    global tracker_bridge, intel_pipeline, router
    global serving, diplomacy, phase_router, event_bus

    log.info("Starting SPAM! agent (Team %d)", TEAM_ID)

    # ── 1. Memory layer ──────────────────────────────────────────
    event_log = EventLog()
    game_memory = GameStateMemory()
    competitor_memory = CompetitorMemory()
    client_memory = ClientProfileMemory()
    message_memory = MessageMemory()
    intolerance = IntoleranceDetector()

    # ── 2. Intelligence layer ────────────────────────────────────
    tracker_bridge = TrackerBridge()
    intel_pipeline = IntelligencePipeline(
        bridge=tracker_bridge,
        competitor_memory=competitor_memory,
    )

    # ── 3. Decision engine ───────────────────────────────────────
    router = SubagentRouter()

    # ── 4. Serving pipeline (recipes set later after fetch) ──────
    serving = ServingPipeline(
        recipes={},  # populated on game_started
        intolerance=intolerance,
        client_memory=client_memory,
    )

    # ── 5. Diplomacy ─────────────────────────────────────────────
    bandit = DeceptionBandit()
    firewall = GroundTruthFirewall()

    gen_client, disc_client = _build_llm_clients()
    pseudo_gan = PseudoGAN(gen_client, disc_client) if gen_client else None

    diplomacy = DiplomacyAgent(
        bandit=bandit,
        pseudo_gan=pseudo_gan,
        firewall=firewall,
        message_memory=message_memory,
    )

    # ── 6. Phase router ──────────────────────────────────────────
    phase_router = PhaseRouter()
    phase_router.register("speaking", on_speaking)
    phase_router.register("closed_bid", on_closed_bid)
    phase_router.register("waiting", on_waiting)
    phase_router.register("serving", on_serving)
    phase_router.register("stopped", on_stopped)

    # ── 7. Event bus ─────────────────────────────────────────────
    event_bus = ReactiveEventBus()

    # Middleware
    event_bus.use(logging_middleware)

    # Register SSE handlers (includes new_message — template bug fix)
    event_bus.on("game_started", on_game_started)
    event_bus.on("game_phase_changed", on_game_phase_changed)
    event_bus.on("client_spawned", on_client_spawned, priority=0)
    event_bus.on("preparation_complete", on_preparation_complete, priority=0)
    event_bus.on("message", on_message)
    event_bus.on("new_message", on_new_message)      # ← template fix
    event_bus.on("heartbeat", on_heartbeat, priority=10)
    event_bus.on("game_reset", on_game_reset)

    # ── 8. Shared HTTP session ───────────────────────────────────
    session = aiohttp.ClientSession()

    # ── 9. Pre-fetch recipes ─────────────────────────────────────
    try:
        recipe_db = await fetch_recipes(session)
        intel_pipeline.set_recipe_db(recipe_db)
        serving.recipes = recipe_db
        log.info("Pre-loaded %d recipes", len(recipe_db))
    except Exception as exc:
        log.warning("Could not pre-fetch recipes: %s", exc)

    # ── 10. Connect SSE (blocks forever) ─────────────────────────
    log.info("Connecting to SSE at %s …", SSE_URL)
    try:
        await event_bus.connect_sse(SSE_URL, SSE_HEADERS)
    except KeyboardInterrupt:
        log.info("Shutting down (Ctrl-C)")
    finally:
        if session and not session.closed:
            await session.close()
        await tracker_bridge.close()
        log.info("Cleanup complete — goodbye")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
