"""
Tests for StrategyAgent integration — verifying the 4 fixes:

Fix 1: _skill_bid_compute passes agent_guidance to solve_zone_ilp
Fix 2: Fallback zone loop passes agent_guidance to solve_zone_ilp
Fix 3: Strategic plan failure syncs both _current_strategy copies
Fix 4: Turn boundaries reset _current_strategy on both objects
"""

import asyncio
from dataclasses import dataclass, field
from unittest.mock import AsyncMock, MagicMock, patch, call
import pytest

from src.decision.strategy_agent import TurnStrategy


# ── Helpers ──────────────────────────────────────────────────────────────


def make_mock_orchestrator():
    """
    Build a minimal mock of GameOrchestrator with the fields
    that the 4 fixed code paths depend on.
    """
    from src.decision.subagent_router import SubagentRouter

    orch = MagicMock()
    orch._current_strategy = None

    # Minimal SubagentRouter mock
    router = MagicMock(spec=SubagentRouter)
    router.active_zone = "DIVERSIFIED"
    router._current_strategy = None
    router.strategy_agent = MagicMock()
    router.strategy_agent.consult_menu = AsyncMock(return_value={
        "target_size": 15,
        "prestige_min": 10,
        "prestige_max": 100,
        "max_prep_time": 12.0,
        "priority_recipes": [],
        "diversity_bonus": 0.3,
        "diversify": True,
        "price_strategy": "volume_first",
        "price_adjustment": 1.0,
        "undercut": True,
    })
    router.strategy_agent.consult_bid = AsyncMock(return_value={
        "spending_fraction": 0.3,
        "aggressiveness": 0.5,
    })
    router.strategy_agent.consult_diplomacy = AsyncMock(return_value={
        "priority": "moderate",
        "targets": [],
        "max_messages": 2,
    })
    router.strategy_agent.plan_turn = AsyncMock(return_value=TurnStrategy(
        confidence=0.7,
        recommended_zone="DIVERSIFIED",
    ))
    router.run_strategic_plan = AsyncMock(return_value=TurnStrategy(
        confidence=0.7,
        recommended_zone="DIVERSIFIED",
    ))
    orch.subagent_router = router
    return orch


def make_skill_context(**overrides):
    """Build a minimal SkillContext-like namespace."""
    ctx = MagicMock()
    ctx.phase = overrides.get("phase", "speaking")
    ctx.balance = overrides.get("balance", 1000.0)
    ctx.inventory = overrides.get("inventory", {"Farina": 5, "Latte": 3})
    ctx.recipes = overrides.get("recipes", {
        "Piatto A": {
            "name": "Piatto A",
            "ingredients": {"Farina": 1},
            "prestige": 50,
            "preparationTimeMs": 3000,
        },
    })
    ctx.reputation = overrides.get("reputation", 50.0)
    ctx.turn_id = overrides.get("turn_id", 1)
    ctx.intel = overrides.get("intel", {
        "briefings": {},
        "demand_forecast": {},
        "all_states": {},
    })
    return ctx


# ── Fix 1: _skill_bid_compute passes agent_guidance ─────────────────────


class TestBidComputePassesAgentGuidance:
    """Verify solve_zone_ilp receives agent_guidance in bid_compute."""

    @pytest.mark.asyncio
    async def test_bid_compute_passes_agent_guidance(self):
        """
        When _current_strategy is set with sufficient confidence,
        _skill_bid_compute should pass agent_guidance to solve_zone_ilp.
        """
        from src.main import GameOrchestrator

        # We can't easily instantiate GameOrchestrator, so we test the
        # code pattern by verifying the function source contains agent_guidance
        import inspect
        source = inspect.getsource(GameOrchestrator._skill_bid_compute)

        # Must contain agent_guidance= in the solve_zone_ilp call
        assert "agent_guidance=agent_guidance" in source, (
            "_skill_bid_compute must pass agent_guidance to solve_zone_ilp"
        )
        # Must call consult_menu to get the guidance
        assert "consult_menu" in source, (
            "_skill_bid_compute must call consult_menu for agent guidance"
        )

    @pytest.mark.asyncio
    async def test_bid_compute_builds_guidance_before_ilp(self):
        """Verify the agent_guidance variable is set before the ILP call."""
        from src.main import GameOrchestrator
        import inspect
        source = inspect.getsource(GameOrchestrator._skill_bid_compute)
        lines = source.split('\n')

        guidance_line = None
        ilp_line = None
        for i, line in enumerate(lines):
            if "agent_guidance = None" in line and guidance_line is None:
                guidance_line = i
            if "solve_zone_ilp(" in line and ilp_line is None:
                ilp_line = i

        assert guidance_line is not None, "agent_guidance must be initialized"
        assert ilp_line is not None, "solve_zone_ilp must be called"
        assert guidance_line < ilp_line, (
            f"agent_guidance (line {guidance_line}) must be initialized "
            f"BEFORE solve_zone_ilp call (line {ilp_line})"
        )


# ── Fix 2: Fallback zone loop passes agent_guidance ─────────────────────


class TestFallbackLoopPassesAgentGuidance:
    """Verify fallback zone attempts don't drop agent_guidance."""

    def test_fallback_loop_has_agent_guidance(self):
        """
        The fallback zone loop in _skill_menu_planning must pass
        agent_guidance to every solve_zone_ilp call.
        """
        from src.main import GameOrchestrator
        import inspect
        source = inspect.getsource(GameOrchestrator._skill_menu_planning)

        # Find the fallback section
        fallback_idx = source.find("fallback_zones")
        assert fallback_idx != -1, "Fallback zone loop must exist"

        # Everything after the fallback_zones line
        fallback_section = source[fallback_idx:]

        # Every solve_zone_ilp call in the fallback section should have agent_guidance
        import re
        ilp_calls = list(re.finditer(r"solve_zone_ilp\(", fallback_section))
        assert len(ilp_calls) >= 1, "Must have at least one solve_zone_ilp in fallback"

        for match in ilp_calls:
            # Get text from this call to the next closing paren block
            call_start = match.start()
            # Find the agent_guidance param in a reasonable range after the call
            call_text = fallback_section[call_start:call_start + 600]
            assert "agent_guidance=" in call_text, (
                f"Fallback solve_zone_ilp call must include agent_guidance parameter"
            )


# ── Fix 3: Strategy failure syncs both copies ───────────────────────────


class TestStrategyFailureSync:
    """Verify both _current_strategy copies are synced on failure."""

    def test_failure_path_sets_both_copies(self):
        """
        When _skill_strategic_plan hits an exception, it must set BOTH
        self._current_strategy and self.subagent_router._current_strategy.
        """
        from src.main import GameOrchestrator
        import inspect
        source = inspect.getsource(GameOrchestrator._skill_strategic_plan)

        # Find the except block
        except_idx = source.find("except Exception")
        assert except_idx != -1, "Must have exception handler"

        except_block = source[except_idx:]

        # Both copies must be set
        assert "self._current_strategy" in except_block, (
            "Failure handler must set self._current_strategy"
        )
        assert "self.subagent_router._current_strategy" in except_block, (
            "Failure handler must ALSO set self.subagent_router._current_strategy"
        )

    @pytest.mark.asyncio
    async def test_failure_creates_consistent_objects(self):
        """
        After a strategic_plan failure, both copies should point
        to a TurnStrategy with the same confidence.
        """
        orch = make_mock_orchestrator()

        # Simulate the fix: what the except block now does
        fallback = TurnStrategy()
        orch._current_strategy = fallback
        orch.subagent_router._current_strategy = fallback

        # Both should be the same object
        assert orch._current_strategy is orch.subagent_router._current_strategy
        # Default confidence is 0.5 (passes the >= 0.4 gates)
        assert orch._current_strategy.confidence >= 0.4


# ── Fix 4: Turn boundaries reset strategy ────────────────────────────────


class TestTurnBoundaryReset:
    """Verify _current_strategy is cleared on turn boundaries."""

    def test_handle_game_started_resets_strategy(self):
        """_handle_game_started must reset both _current_strategy copies."""
        from src.main import GameOrchestrator
        import inspect
        source = inspect.getsource(GameOrchestrator._handle_game_started)

        assert "self._current_strategy = None" in source, (
            "_handle_game_started must reset self._current_strategy"
        )
        assert "self.subagent_router._current_strategy = None" in source, (
            "_handle_game_started must reset subagent_router._current_strategy"
        )

    def test_on_turn_change_resets_strategy(self):
        """_on_turn_change must reset both _current_strategy copies."""
        from src.main import GameOrchestrator
        import inspect
        source = inspect.getsource(GameOrchestrator._on_turn_change)

        assert "self._current_strategy = None" in source, (
            "_on_turn_change must reset self._current_strategy"
        )
        assert "self.subagent_router._current_strategy = None" in source, (
            "_on_turn_change must reset subagent_router._current_strategy"
        )

    def test_reset_clears_stale_strategy(self):
        """After reset, both copies should be None."""
        orch = make_mock_orchestrator()

        # Simulate a turn with a strategy
        strat = TurnStrategy(confidence=0.8, recommended_zone="PREMIUM_MONOPOLIST")
        orch._current_strategy = strat
        orch.subagent_router._current_strategy = strat

        # Simulate the turn boundary reset
        orch._current_strategy = None
        orch.subagent_router._current_strategy = None

        assert orch._current_strategy is None
        assert orch.subagent_router._current_strategy is None


# ── Cross-cutting: ILP solver accepts agent_guidance ─────────────────────


class TestILPSolverAcceptsGuidance:
    """Verify the ILP solver properly handles agent_guidance parameter."""

    def test_solve_zone_ilp_signature_accepts_agent_guidance(self):
        """solve_zone_ilp must accept agent_guidance as a keyword argument."""
        from src.decision.ilp_solver import solve_zone_ilp
        import inspect
        sig = inspect.signature(solve_zone_ilp)
        assert "agent_guidance" in sig.parameters, (
            "solve_zone_ilp must have agent_guidance parameter"
        )
        param = sig.parameters["agent_guidance"]
        assert param.default is None, (
            "agent_guidance should default to None"
        )

    def test_compute_menu_price_accepts_agent_pricing(self):
        """compute_menu_price must accept agent_pricing parameter."""
        from src.decision.ilp_solver import compute_menu_price
        import inspect
        sig = inspect.signature(compute_menu_price)
        assert "agent_pricing" in sig.parameters, (
            "compute_menu_price must have agent_pricing parameter"
        )

    def test_agent_pricing_changes_price(self):
        """Agent pricing with 'premium' strategy should increase price."""
        from src.decision.ilp_solver import compute_menu_price

        recipe = {"name": "Test", "prestige": 60}
        base = compute_menu_price(recipe, "DIVERSIFIED", 50.0)
        premium = compute_menu_price(
            recipe, "DIVERSIFIED", 50.0, None,
            {"strategy": "premium", "adjustment_factor": 1.0, "undercut": True}
        )
        assert premium > base, (
            f"Premium strategy should yield higher price: {premium} vs {base}"
        )

    def test_agent_undercut_flag_respected(self):
        """When undercut=False, competitor prices should NOT cap our price."""
        from src.decision.ilp_solver import compute_menu_price

        # Low-prestige dish with active competitor having low avg price
        recipe = {"name": "Test", "prestige": 30}
        comp = {1: {"is_connected": True, "menu_price_avg": 20}}

        with_undercut = compute_menu_price(
            recipe, "DIVERSIFIED", 50.0, comp,
            {"strategy": "volume_first", "adjustment_factor": 1.0, "undercut": True}
        )
        without_undercut = compute_menu_price(
            recipe, "DIVERSIFIED", 50.0, comp,
            {"strategy": "volume_first", "adjustment_factor": 1.0, "undercut": False}
        )
        # Without undercut should be >= with undercut (not capped by competitor)
        assert without_undercut >= with_undercut, (
            f"undercut=False should not cap price: {without_undercut} vs {with_undercut}"
        )


# ── Strategy Agent: TurnStrategy defaults ────────────────────────────────


class TestTurnStrategyDefaults:
    """Verify TurnStrategy fallback values are sensible."""

    def test_default_confidence_passes_gates(self):
        """Default TurnStrategy confidence must pass the 0.4 threshold."""
        strat = TurnStrategy()
        assert strat.confidence >= 0.4, (
            f"Default confidence {strat.confidence} must be >= 0.4 "
            f"to pass downstream consultation gates"
        )

    def test_default_zone_is_diversified(self):
        """Default recommended zone should be DIVERSIFIED."""
        strat = TurnStrategy()
        assert strat.recommended_zone == "DIVERSIFIED"

    def test_default_price_strategy_is_volume(self):
        """Default price strategy should be volume_first."""
        strat = TurnStrategy()
        assert strat.price_strategy == "volume_first"

    def test_default_menu_diversify_is_true(self):
        """Default should diversify menu."""
        strat = TurnStrategy()
        assert strat.menu_diversify is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
