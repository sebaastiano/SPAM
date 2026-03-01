"""
SPAM! X-Ray — Non-Invasive Hooks
==================================
Instruments existing subsystems by wrapping methods at runtime.

CRITICAL: This module does NOT modify any existing source files.
All instrumentation is done via monkey-patching at import time,
using functools.wraps to preserve original signatures and behavior.

Call `install_hooks(orchestrator)` once after `GameOrchestrator.__init__`
to activate all tracing. If X-Ray is disabled, nothing happens.
"""

from __future__ import annotations

import functools
import logging
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

logger = logging.getLogger("spam.xray.hooks")


def install_hooks(orchestrator) -> None:
    """
    Install X-Ray tracing hooks on the orchestrator and its subsystems.

    Non-invasive: wraps existing methods with tracing wrappers.
    Original behavior is completely preserved.
    """
    from src.xray import xray

    logger.info("Installing X-Ray hooks...")

    _hook_phase_router(orchestrator, xray)
    _hook_skill_orchestrator(orchestrator, xray)
    _hook_event_bus(orchestrator, xray)
    _hook_serving_pipeline(orchestrator, xray)
    _hook_intelligence_pipeline(orchestrator, xray)
    _hook_diplomacy(orchestrator, xray)
    _hook_decision(orchestrator, xray)
    _hook_context_builder(orchestrator, xray)

    logger.info("X-Ray hooks installed — all subsystems instrumented")


# ══════════════════════════════════════════════════════════════
#  PHASE ROUTER HOOKS
# ══════════════════════════════════════════════════════════════

def _hook_phase_router(orchestrator, xray):
    """Trace phase transitions and timing."""
    router = orchestrator.phase_router
    original_handle = router.handle_phase_change

    @functools.wraps(original_handle)
    async def traced_handle_phase_change(data):
        phase = data.get("phase", "?")
        turn_id = data.get("turn_id", 0)
        is_mid = data.get("is_mid_turn_entry", False)

        xray.phase(phase, turn_id=turn_id, is_mid_turn_entry=is_mid)
        xray.emit("phase", phase, status="info", data={
            "turn_id": turn_id,
            "is_mid_turn_entry": is_mid,
            "skipped_phases": data.get("skipped_phases", []),
            "estimated_duration": router.estimated_durations.get(phase, 60),
        })

        result = await original_handle(data)
        return result

    router.handle_phase_change = traced_handle_phase_change

    # Hook game_started
    original_game_started = router.handle_game_started

    @functools.wraps(original_game_started)
    async def traced_game_started(data):
        turn_id = data.get("turn_id", 0)
        xray.emit("phase", "game_started", status="info", data={
            "turn_id": turn_id,
        })
        return await original_game_started(data)

    router.handle_game_started = traced_game_started


# ══════════════════════════════════════════════════════════════
#  SKILL ORCHESTRATOR HOOKS
# ══════════════════════════════════════════════════════════════

def _hook_skill_orchestrator(orchestrator, xray):
    """Trace skill execution lifecycle with timing."""
    so = orchestrator.skill_orchestrator
    original_execute = so.execute_for_phase

    @functools.wraps(original_execute)
    async def traced_execute_for_phase(ctx):
        phase = ctx.phase
        is_mid = ctx.is_mid_turn_entry

        xray.emit("skill", f"phase_dispatch_{phase}", status="running", data={
            "phase": phase,
            "is_mid_turn_entry": is_mid,
            "turn_id": ctx.turn_id,
        })

        # Wrap each skill's execute_fn with timing (once)
        for name, skill in so.skills.items():
            if not hasattr(skill, '_xray_wrapped'):
                _install_skill_trace(skill, skill.execute_fn, name, xray)
                skill._xray_wrapped = True

        results = await original_execute(ctx)

        # Summary event
        ok = sum(1 for r in results if r.success)
        fail = len(results) - ok
        xray.emit("skill", f"phase_complete_{phase}", status="success", data={
            "phase": phase,
            "total_skills": len(results),
            "succeeded": ok,
            "failed": fail,
            "skill_names": [r.skill_name for r in results],
        })

        return results

    so.execute_for_phase = traced_execute_for_phase


def _install_skill_trace(skill, original_fn, name, xray):
    """Install a tracing wrapper on a single skill's execute_fn."""
    @functools.wraps(original_fn)
    async def traced_skill_fn(ctx):
        start = time.monotonic()
        xray.skill(name, status="running", phase=ctx.phase)
        try:
            result = await original_fn(ctx)
            elapsed_ms = (time.monotonic() - start) * 1000
            status = "success" if result.success else "failed"
            result_data = dict(result.data) if result.data else {}
            if not result.success and result.error:
                result_data["error"] = result.error
            result_data["duration_ms"] = round(elapsed_ms, 1)
            xray.skill(name, status=status, **result_data)
            return result
        except Exception as e:
            elapsed_ms = (time.monotonic() - start) * 1000
            xray.skill(
                name, status="failed",
                error=str(e),
                duration_ms=round(elapsed_ms, 1),
            )
            raise

    skill.execute_fn = traced_skill_fn


# ══════════════════════════════════════════════════════════════
#  EVENT BUS HOOKS
# ══════════════════════════════════════════════════════════════

def _hook_event_bus(orchestrator, xray):
    """Trace all SSE events flowing through the event bus."""
    bus = orchestrator.bus
    original_emit = bus.emit

    @functools.wraps(original_emit)
    async def traced_emit(event_type, data):
        # Record the raw SSE event
        safe_data = {}
        if isinstance(data, dict):
            for k, v in list(data.items())[:10]:
                if isinstance(v, (str, int, float, bool)):
                    safe_data[k] = v
        xray.event(event_type, **safe_data)
        return await original_emit(event_type, data)

    bus.emit = traced_emit


# ══════════════════════════════════════════════════════════════
#  SERVING PIPELINE HOOKS
# ══════════════════════════════════════════════════════════════

def _hook_serving_pipeline(orchestrator, xray):
    """Trace serving events: client processing, order matching, dish prep."""
    serving = orchestrator.serving

    # Hook set_menu
    original_set_menu = serving.set_menu

    @functools.wraps(original_set_menu)
    def traced_set_menu(menu_items):
        result = original_set_menu(menu_items)
        xray.serving("menu_set", status="success",
                     menu_count=len(menu_items),
                     items=[m.get("name", m) if isinstance(m, dict) else str(m)
                            for m in (menu_items or [])])
        return result

    serving.set_menu = traced_set_menu

    # Hook start_serving
    original_start = serving.start_serving

    @functools.wraps(original_start)
    async def traced_start_serving(turn_id):
        xray.serving("serving_started", status="running",
                     turn_id=turn_id,
                     menu_count=len(serving.menu))
        result = await original_start(turn_id)
        return result

    serving.start_serving = traced_start_serving

    # Hook stop_serving
    original_stop = serving.stop_serving

    @functools.wraps(original_stop)
    async def traced_stop_serving():
        served = len(serving.served_this_turn)
        xray.serving("serving_stopped", status="info",
                     total_served=served)
        xray.update_serving_stats(
            total_served=served,
            serving_active=False,
        )
        return await original_stop()

    serving.stop_serving = traced_stop_serving

    # Hook handle_client_spawned
    original_client = serving.handle_client_spawned

    @functools.wraps(original_client)
    async def traced_client_spawned(data):
        client_name = data.get("client_name", data.get("name", "?"))
        xray.serving("client_spawned", status="info",
                     client_name=client_name)
        return await original_client(data)

    serving.handle_client_spawned = traced_client_spawned

    # Hook handle_preparation_complete
    original_prep = serving.handle_preparation_complete

    @functools.wraps(original_prep)
    async def traced_prep_complete(data):
        dish = data.get("dish_name", data.get("dish", "?"))
        xray.serving("preparation_complete", status="success",
                     dish=dish)
        return await original_prep(data)

    serving.handle_preparation_complete = traced_prep_complete


# ══════════════════════════════════════════════════════════════
#  INTELLIGENCE PIPELINE HOOKS
# ══════════════════════════════════════════════════════════════

def _hook_intelligence_pipeline(orchestrator, xray):
    """Trace intelligence pipeline execution and results."""
    intel = orchestrator.intelligence
    original_run = intel.run

    @functools.wraps(original_run)
    async def traced_run(turn_id):
        start = time.monotonic()
        xray.intelligence("pipeline_started", turn_id=turn_id)

        result = await original_run(turn_id)
        elapsed_ms = (time.monotonic() - start) * 1000

        # Extract key results
        briefings = result.get("briefings", {})
        clusters = result.get("clusters", {})
        connected = sum(1 for b in briefings.values()
                       if b.get("is_connected", False))

        xray.intelligence(
            "pipeline_complete",
            turn_id=turn_id,
            duration_ms=round(elapsed_ms, 1),
            briefing_count=len(briefings),
            connected_competitors=connected,
            cluster_count=len(clusters),
            clusters=clusters,
        )

        # Update competitor panel
        xray.update_competitors(briefings)

        return result

    intel.run = traced_run


# ══════════════════════════════════════════════════════════════
#  DIPLOMACY HOOKS
# ══════════════════════════════════════════════════════════════

def _hook_diplomacy(orchestrator, xray):
    """Trace diplomacy messages and deception strategy."""
    diplo = orchestrator.diplomacy

    # Hook run_diplomacy_turn
    original_run = diplo.run_diplomacy_turn

    @functools.wraps(original_run)
    async def traced_diplomacy_turn(**kwargs):
        start = time.monotonic()
        turn_id = kwargs.get("turn_id", 0)
        xray.diplomacy("turn_started", turn_id=turn_id)

        result = await original_run(**kwargs)
        elapsed_ms = (time.monotonic() - start) * 1000

        xray.diplomacy(
            "turn_complete",
            turn_id=turn_id,
            messages_sent=len(result) if result else 0,
            duration_ms=round(elapsed_ms, 1),
            targets=[m.get("target_id", "?") for m in (result or [])],
            strategies=[m.get("strategy", "?") for m in (result or [])],
        )
        return result

    diplo.run_diplomacy_turn = traced_diplomacy_turn

    # Hook process_incoming_message
    original_process = diplo.process_incoming_message

    @functools.wraps(original_process)
    def traced_process_message(data, *args, **kwargs):
        result = original_process(data, *args, **kwargs)
        sender = result.get("sender_name", data.get("sender_name", "?"))
        credibility = result.get("sender_credibility", 0)
        text = result.get("text", data.get("text", ""))[:80]
        xray.diplomacy(
            "message_received",
            sender=sender,
            credibility=round(credibility, 2),
            text_preview=text,
            trust_level=result.get("trust_level", "untrusted"),
        )
        return result

    diplo.process_incoming_message = traced_process_message


# ══════════════════════════════════════════════════════════════
#  DECISION HOOKS
# ══════════════════════════════════════════════════════════════

def _hook_decision(orchestrator, xray):
    """Trace zone selection and ILP solver decisions."""
    router = orchestrator.subagent_router

    # Hook route (zone selection)
    original_route = router.route

    @functools.wraps(original_route)
    def traced_route(**kwargs):
        start = time.monotonic()
        zone = original_route(**kwargs)
        elapsed_ms = (time.monotonic() - start) * 1000

        xray.decision(
            "zone_selection",
            choice=zone,
            reason=f"Selected based on balance={kwargs.get('balance', '?')}, "
                   f"reputation={kwargs.get('reputation', '?')}, "
                   f"{len(kwargs.get('competitor_briefings', {}))} competitors",
            duration_ms=round(elapsed_ms, 1),
            balance=kwargs.get("balance", 0),
            reputation=kwargs.get("reputation", 0),
        )
        return zone

    router.route = traced_route


# ══════════════════════════════════════════════════════════════
#  CONTEXT BUILDER HOOK
# ══════════════════════════════════════════════════════════════

def _hook_context_builder(orchestrator, xray):
    """Trace game state updates when SkillContext is built."""
    original_build = orchestrator._build_skill_context

    @functools.wraps(original_build)
    async def traced_build_context(data, our_state=None):
        ctx = await original_build(data, our_state=our_state)

        # Update the dashboard's game state panel
        zone = ""
        if hasattr(orchestrator.subagent_router, "active_zone"):
            zone = orchestrator.subagent_router.active_zone or ""

        xray.update_game_state(
            balance=ctx.balance,
            inventory=ctx.inventory,
            reputation=ctx.reputation,
            menu=list(orchestrator.serving.menu.values()) if orchestrator.serving.menu else [],
            is_open=ctx.restaurant_open,
            zone=zone,
        )
        return ctx

    orchestrator._build_skill_context = traced_build_context
