"""
SPAM! — Phase-Aware Skill System
==================================
Modular action units that the orchestrator activates based on current
game phase, mid-turn entry status, and strategic context.

Each Skill represents a discrete, self-contained action (e.g. run
intelligence, compute bids, open restaurant). The SkillOrchestrator
decides at each phase transition which skills to execute and in what
order — handling both normal turn progression and mid-turn catch-up.

Architecture:
    PhaseRouter  →  SkillOrchestrator  →  [Skill_1, Skill_2, ...]
                                              ↓         ↓
                                         execute()  execute()

Design principles:
    - Skills are idempotent: re-running is safe
    - Skills declare which phases they're valid for
    - Priority ordering ensures dependencies (e.g. intel before zone select)
    - Mid-turn catch-up skips skills whose window has passed
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Awaitable, Callable, TYPE_CHECKING

if TYPE_CHECKING:
    pass

logger = logging.getLogger("spam.skills")


# ── Phase Enum ──

class Phase(str, Enum):
    SPEAKING = "speaking"
    CLOSED_BID = "closed_bid"
    WAITING = "waiting"
    SERVING = "serving"
    STOPPED = "stopped"


# ── Skill Context ──

@dataclass
class SkillContext:
    """
    Snapshot of game state passed to every skill execution.

    Populated by the orchestrator before dispatching skills.
    """
    turn_id: int
    phase: str
    balance: float
    inventory: dict[str, int]
    reputation: float
    recipes: dict[str, dict]
    intel: dict[str, Any]
    is_mid_turn_entry: bool = False
    skipped_phases: list[str] = field(default_factory=list)
    time_remaining_estimate: float | None = None  # seconds left in phase
    our_state: dict = field(default_factory=dict)
    menu_set: bool = False  # whether a menu has been saved this turn
    restaurant_open: bool = False
    incoming_messages: list[dict] = field(default_factory=list)  # firewall-processed messages this turn


@dataclass
class SkillResult:
    """Outcome of a skill execution."""
    skill_name: str
    success: bool
    data: dict[str, Any] = field(default_factory=dict)
    error: str | None = None


# ── Skill Definition ──

@dataclass
class Skill:
    """
    A discrete, phase-gated action unit.

    Attributes:
        name: Unique identifier
        description: Human-readable purpose
        valid_phases: Phases where this skill can execute
        priority: Lower = runs first (for dependency ordering)
        execute_fn: The async function to call
        mid_turn_applicable: Whether this skill makes sense in catch-up mode
        requires_skills: Skills that should have run before this one
    """
    name: str
    description: str
    valid_phases: set[str]
    priority: int
    execute_fn: Callable[[SkillContext], Awaitable[SkillResult]]
    mid_turn_applicable: bool = True
    requires_skills: list[str] = field(default_factory=list)


# ── Phase → Skill availability (normal flow) ──

NORMAL_PHASE_SKILLS: dict[str, list[str]] = {
    "speaking": [
        "strategic_plan",       # Agent plans turn strategy FIRST
        "intelligence_scan",
        "strategic_refine",     # Agent refines after intel
        "zone_selection",
        "menu_planning",
        "menu_save",
        "diplomacy_send",
        "market_ops",
    ],
    "closed_bid": [
        "bid_compute",
        "bid_submit",
        "menu_save",       # allowed in this phase
        "market_ops",
        # diplomacy_send NOT allowed — messages only in speaking phase
    ],
    "waiting": [
        "inventory_verify",
        "menu_planning",
        "menu_save",
        "market_ops",
        "restaurant_open",
        "serving_prep",
    ],
    "serving": [
        "serving_monitor",
        "close_decision",
    ],
    "stopped": [
        "end_turn_snapshot",
        "info_gather",
    ],
}


# ── Mid-turn catch-up skill sets ──
#
# When entering mid-turn, we run a subset of skills from BOTH the
# current phase AND earlier phases that we skipped — but only skills
# whose actions are still permitted by the server.

MID_TURN_CATCHUP_SKILLS: dict[str, list[str]] = {
    "speaking": [
        # Full pipeline — we didn't miss anything
        "strategic_plan",
        "intelligence_scan",
        "strategic_refine",
        "zone_selection",
        "menu_planning",
        "menu_save",
        "market_ops",
        "diplomacy_send",
    ],
    "closed_bid": [
        # Missed speaking: quick intel → zone → menu → bid
        "quick_intelligence",   # lightweight version
        "strategic_plan",       # agent plans even mid-turn
        "zone_selection",
        "menu_planning",
        "menu_save",
        "bid_compute",
        "bid_submit",
        "market_ops",           # buy missing ingredients via market too
    ],
    "waiting": [
        # Missed speaking + bidding: work with whatever we have
        "quick_intelligence",
        "strategic_plan",
        "zone_selection",
        "inventory_verify",
        "menu_planning",
        "menu_save",
        "market_ops",
        "restaurant_open",
        "serving_prep",
    ],
    "serving": [
        # Missed everything preparatory
        # Check if we can serve at all, if so start; if not, close
        "serving_readiness_check",
        "emergency_menu",       # set minimal menu if none exists
        "restaurant_open",      # open if we have a menu
        "serving_prep",
        "close_decision",       # close if hopeless
    ],
    "stopped": [
        # Nothing to catch up — just observe
        "end_turn_snapshot",
        "info_gather",
    ],
}


# ── Orchestrator ──

class SkillOrchestrator:
    """
    Phase-aware skill orchestrator.

    Decides which skills to activate based on:
    1. Current phase
    2. Whether this is a mid-turn entry (and which phases were skipped)
    3. Which skills have already run this turn

    Usage:
        orch = SkillOrchestrator()
        orch.register(Skill(...))
        results = await orch.execute_for_phase(ctx)
    """

    def __init__(self):
        self.skills: dict[str, Skill] = {}
        self.executed_this_turn: set[str] = set()
        self.results_this_turn: dict[str, SkillResult] = {}

    def register(self, skill: Skill):
        """Register a skill."""
        self.skills[skill.name] = skill

    def new_turn(self):
        """Reset turn-scoped tracking."""
        self.executed_this_turn.clear()
        self.results_this_turn.clear()

    async def execute_for_phase(self, ctx: SkillContext, agent_skills: list[str] | None = None) -> list[SkillResult]:
        """
        Execute all applicable skills for the current phase context.

        Selects skills based on:
        - Normal flow: NORMAL_PHASE_SKILLS[phase]
        - Mid-turn: MID_TURN_CATCHUP_SKILLS[phase]

        If agent_skills is provided, only skills in that list (plus core
        always-run skills like strategic_plan/strategic_refine) will run.
        This gives the strategy agent control over which optional skills execute.

        Respects priority ordering and dependency requirements.
        """
        if ctx.is_mid_turn_entry:
            skill_names = MID_TURN_CATCHUP_SKILLS.get(ctx.phase, [])
            logger.info(
                f"[MID-TURN CATCHUP] Phase={ctx.phase}, "
                f"skipped={ctx.skipped_phases}, "
                f"skills to run: {skill_names}"
            )
        else:
            skill_names = NORMAL_PHASE_SKILLS.get(ctx.phase, [])

        # Agent-driven skill filtering: if the agent specified which skills
        # to activate, respect that — but always run core planning skills
        # and phase-critical skills (bid_submit, menu_save, etc.)
        _ALWAYS_RUN = {
            "strategic_plan", "strategic_refine", "intelligence_scan",
            "zone_selection", "menu_planning", "menu_save",
            "bid_compute", "bid_submit", "restaurant_open",
            "end_turn_snapshot", "info_gather", "serving_prep",
            "serving_monitor", "close_decision", "inventory_verify",
            "quick_intelligence", "emergency_menu",
            "serving_readiness_check",
            "diplomacy_send",  # always attempt diplomacy when in speaking phase
        }
        if agent_skills:
            agent_set = set(agent_skills) | _ALWAYS_RUN
            skill_names = [s for s in skill_names if s in agent_set]
            logger.info(f"Agent filtered skills for {ctx.phase}: {skill_names}")

        # Resolve to Skill objects, filter already-executed + unregistered
        applicable: list[Skill] = []
        for name in skill_names:
            skill = self.skills.get(name)
            if skill is None:
                logger.debug(f"Skill '{name}' not registered — skipping")
                continue
            if name in self.executed_this_turn:
                logger.debug(f"Skill '{name}' already executed this turn — skipping")
                continue
            if ctx.phase not in skill.valid_phases:
                logger.debug(f"Skill '{name}' not valid for phase {ctx.phase}")
                continue
            applicable.append(skill)

        # Sort by priority (lower = first)
        applicable.sort(key=lambda s: s.priority)

        # Execute in order
        results: list[SkillResult] = []
        for skill in applicable:
            # Check dependencies
            missing_deps = [
                dep for dep in skill.requires_skills
                if dep not in self.executed_this_turn
            ]
            if missing_deps:
                logger.warning(
                    f"Skill '{skill.name}' missing deps {missing_deps} — skipping"
                )
                continue

            logger.info(f"▸ Executing skill: {skill.name}")
            try:
                result = await skill.execute_fn(ctx)
                results.append(result)
                self.executed_this_turn.add(skill.name)
                self.results_this_turn[skill.name] = result
                if result.success:
                    logger.info(f"  ✓ {skill.name} succeeded")
                else:
                    logger.warning(
                        f"  ✗ {skill.name} failed: {result.error}"
                    )
            except Exception as e:
                logger.error(
                    f"  ✗ {skill.name} crashed: {e}", exc_info=True
                )
                fail_result = SkillResult(
                    skill_name=skill.name, success=False, error=str(e)
                )
                results.append(fail_result)
                self.results_this_turn[skill.name] = fail_result

        return results

    def get_result(self, skill_name: str) -> SkillResult | None:
        """Get the result of a previously executed skill."""
        return self.results_this_turn.get(skill_name)

    def was_executed(self, skill_name: str) -> bool:
        """Check if a skill was executed this turn."""
        return skill_name in self.executed_this_turn


# ── Phase ordering (for determining skipped phases) ──

PHASE_ORDER = ["speaking", "closed_bid", "waiting", "serving", "stopped"]


def compute_skipped_phases(current_phase: str) -> list[str]:
    """
    Given the current phase we entered at, compute which phases
    we missed (for mid-turn catch-up).

    E.g. if we enter at 'waiting', skipped = ['speaking', 'closed_bid']
    """
    if current_phase not in PHASE_ORDER:
        return []
    idx = PHASE_ORDER.index(current_phase)
    return PHASE_ORDER[:idx]
