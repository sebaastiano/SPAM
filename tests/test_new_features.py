"""Tests for the new strategy enhancements: bid history, turn rotation, multi-layer pricing."""
import inspect
import re
import pytest

from src.decision.strategy_agent import StrategyAgent, TurnStrategy
from src.decision.ilp_solver import compute_bid_price, _score_recipes
from src.phase_router import PhaseRouter


class TestBidHistoryRecording:
    """Test that bid history is properly recorded and used."""

    def test_record_bid_history_stores_winning_prices(self):
        agent = StrategyAgent(llm_client=None)
        agent.record_bid_history([
            {"ingredient": "Salt", "bid": 10, "quantity": 5, "status": "completed"},
            {"ingredient": "Salt", "bid": 12, "quantity": 3, "status": "completed"},
            {"ingredient": "Pepper", "bid": 8, "quantity": 2, "status": "completed"},
        ])
        assert "Salt" in agent._ingredient_avg_prices
        assert agent._ingredient_avg_prices["Salt"] == pytest.approx(11.0)
        assert "Pepper" in agent._ingredient_avg_prices

    def test_record_bid_history_ignores_failed_bids(self):
        agent = StrategyAgent(llm_client=None)
        agent.record_bid_history([
            {"ingredient": "Gold", "bid": 50, "quantity": 1, "status": "failed"},
        ])
        assert "Gold" not in agent._ingredient_avg_prices

    def test_availability_tracked(self):
        agent = StrategyAgent(llm_client=None)
        agent.record_bid_history([
            {"ingredient": "Common", "bid": 10, "quantity": 1, "status": "completed"},
            {"ingredient": "Common", "bid": 12, "quantity": 1, "status": "completed"},
            {"ingredient": "Common", "bid": 11, "quantity": 1, "status": "failed"},
        ])
        # 2 wins out of 3 total = 66.7% availability
        assert agent._ingredient_availability["Common"] == pytest.approx(2/3, abs=0.01)

    def test_get_bid_price_intelligence_returns_dict(self):
        agent = StrategyAgent(llm_client=None)
        agent.record_bid_history([
            {"ingredient": "X", "bid": 20, "quantity": 1, "status": "completed"},
        ])
        intel = agent.get_bid_price_intelligence()
        assert "avg_prices" in intel
        assert "availability" in intel
        assert "history_depth" in intel
        assert "X" in intel["avg_prices"]

    def test_rolling_window_capped_at_30(self):
        agent = StrategyAgent(llm_client=None)
        entries = [
            {"ingredient": "Flood", "bid": i, "quantity": 1, "status": "completed"}
            for i in range(50)
        ]
        agent.record_bid_history(entries)
        assert len(agent._bid_price_history["Flood"]) == 30


class TestTurnResultRecording:
    """Test that turn results are properly recorded for strategy performance tracking."""

    def test_record_turn_result_stores_data(self):
        agent = StrategyAgent(llm_client=None)
        agent.record_turn_result(
            turn_id=1, revenue=500, customers_served=5,
            balance_delta=200, strategy_used="volume_first", zone_used="DIVERSIFIED",
        )
        assert len(agent._turn_results) == 1
        assert agent._turn_results[0]["revenue"] == 500

    def test_strategy_performance_tracked(self):
        agent = StrategyAgent(llm_client=None)
        agent.record_turn_result(1, 500, 5, 200, "volume_first", "DIVERSIFIED")
        agent.record_turn_result(2, 700, 8, 400, "balanced", "DIVERSIFIED")
        agent.record_turn_result(3, 600, 6, 300, "volume_first", "DIVERSIFIED")
        assert agent._strategy_performance["volume_first"] == [500, 600]
        assert agent._strategy_performance["balanced"] == [700]


class TestFocusArchetypeRotation:
    """Test that focus archetype rotates across turns."""

    def test_default_strategy_rotates_focus(self):
        agent = StrategyAgent(llm_client=None)
        focuses = []
        for turn_id in range(1, 7):
            ctx = {"active_competitors": 2, "turn_id": turn_id}
            s = agent._default_strategy(ctx)
            focuses.append(s.focus_archetype)
        # Should not all be the same
        assert len(set(focuses)) > 1, f"Focus should vary: {focuses}"

    def test_default_strategy_rotates_price_strategy(self):
        agent = StrategyAgent(llm_client=None)
        strategies = []
        for turn_id in range(1, 6):
            ctx = {"active_competitors": 2, "turn_id": turn_id}
            s = agent._default_strategy(ctx)
            strategies.append(s.price_strategy)
        assert len(set(strategies)) > 1, f"Price strategy should vary: {strategies}"

    def test_focus_affects_expected_customers(self):
        agent = StrategyAgent(llm_client=None)
        # Find a turn that gives "premium" focus
        for turn_id in range(1, 20):
            ctx = {"active_competitors": 2, "turn_id": turn_id}
            s = agent._default_strategy(ctx)
            if s.focus_archetype == "premium":
                assert s.expected_high_value > s.expected_budget or s.expected_high_value >= 3
                break
        else:
            pytest.fail("Never got premium focus in 20 turns")


class TestTurnStrategyNewFields:
    """Test new TurnStrategy dataclass fields."""

    def test_focus_archetype_default(self):
        ts = TurnStrategy()
        assert ts.focus_archetype == "all"

    def test_expected_customers_default(self):
        ts = TurnStrategy()
        assert ts.expected_customers == 8

    def test_expected_high_value_default(self):
        ts = TurnStrategy()
        assert ts.expected_high_value == 2

    def test_expected_budget_default(self):
        ts = TurnStrategy()
        assert ts.expected_budget == 4


class TestBidPriceWithHistory:
    """Test compute_bid_price respects bid history intelligence."""

    def test_high_availability_ingredient_capped(self):
        """If ingredient is historically cheap and available, bid should be low."""
        price_no_hist = compute_bid_price("TestIng", {}, {})
        price_with_hist = compute_bid_price("TestIng", {}, {}, bid_price_intel={
            "avg_prices": {"TestIng": 10.0},
            "availability": {"TestIng": 0.85},
        })
        # With high availability + low historical avg, should bid low
        assert price_with_hist < 20, f"Should bid conservatively with history: {price_with_hist}"

    def test_scarce_ingredient_bids_higher(self):
        """Scarce ingredients should get higher bids."""
        # Use higher avg price (50) so the 0.25x floor (12.5) doesn't clamp both
        # to the same minimum. With 0 competitors and no demand, bid = base * 0.25
        # avail=0.9 → base=50*1.05=52.5 → 52.5*0.25=13.1 → 14
        # avail=0.2 → base=50*1.35=67.5 → 67.5*0.25=16.9 → 17
        price_easy = compute_bid_price("Scarce", {}, {}, bid_price_intel={
            "avg_prices": {"Scarce": 50.0},
            "availability": {"Scarce": 0.9},  # easy
        })
        price_hard = compute_bid_price("Scarce", {}, {}, bid_price_intel={
            "avg_prices": {"Scarce": 50.0},
            "availability": {"Scarce": 0.2},  # scarce
        })
        assert price_hard > price_easy, (
            f"Scarce should bid higher ({price_hard}) than easy ({price_easy})"
        )

    def test_bid_price_intel_param_accepted(self):
        """compute_bid_price should accept bid_price_intel param."""
        sig = inspect.signature(compute_bid_price)
        assert "bid_price_intel" in sig.parameters


class TestMultiLayerScoring:
    """Test _score_recipes enforces multi-layer diversity."""

    def test_score_recipes_accepts_tier_targets(self):
        sig = inspect.signature(_score_recipes)
        assert "tier_targets" in sig.parameters

    def test_recipes_have_tier_label(self):
        recipes = [
            {"name": "cheap", "prestige": 20, "prep_time": 3, "ingredients": {"a": 1}},
            {"name": "mid", "prestige": 50, "prep_time": 5, "ingredients": {"b": 2}},
            {"name": "prem", "prestige": 90, "prep_time": 7, "ingredients": {"c": 3}},
        ]
        scored = _score_recipes(recipes, "DIVERSIFIED", {}, 100.0, {})
        for entry in scored:
            assert "tier" in entry, "Each scored recipe should have a 'tier' label"

    def test_underrepresented_tier_gets_bonus(self):
        """If a tier is underrepresented, recipes in that tier should score higher."""
        # Create recipes with only budget recipes already filled
        recipes_pool = [
            {"name": "budget1", "prestige": 20, "prep_time": 3, "ingredients": {"a": 1}},
            {"name": "budget2", "prestige": 25, "prep_time": 3, "ingredients": {"a": 1}},
            {"name": "budget3", "prestige": 30, "prep_time": 3, "ingredients": {"a": 1}},
            # Premium tier needs filling
            {"name": "premium1", "prestige": 90, "prep_time": 7, "ingredients": {"c": 3}},
        ]
        # Target: high budget target already met, premium still needed
        scored = _score_recipes(
            recipes_pool, "DIVERSIFIED", {}, 100.0, {},
            tier_targets={"budget": 1, "mid": 3, "mid_high": 3, "premium": 3}
        )
        # The first budget recipe should get a small bonus, subsequent budgets less
        budget_scores = [s["score"] for s in scored if s["tier"] == "budget"]
        assert budget_scores[0] > budget_scores[-1] or len(budget_scores) <= 1

    def test_tier_distribution_covers_spectrum(self):
        """With diverse recipes, tiers should be well represented."""
        recipes = [
            {"name": f"r{i}", "prestige": p, "prep_time": 5, "ingredients": {"x": 1}}
            for i, p in enumerate([10, 20, 30, 40, 50, 60, 70, 80, 90, 95])
        ]
        scored = _score_recipes(recipes, "DIVERSIFIED", {}, 100.0, {})
        tiers = [s["tier"] for s in scored]
        assert "budget" in tiers
        assert "mid" in tiers
        assert "premium" in tiers


class TestConsultBidWithHistory:
    """Test that consult_bid returns bid price intelligence."""

    @pytest.mark.asyncio
    async def test_consult_bid_returns_price_caps(self):
        agent = StrategyAgent(llm_client=None)
        # Record some history
        agent.record_bid_history([
            {"ingredient": "Water", "bid": 5, "quantity": 10, "status": "completed"},
            {"ingredient": "Water", "bid": 6, "quantity": 8, "status": "completed"},
        ])
        agent._last_strategy = TurnStrategy(bid_aggressiveness=0.3)
        guidance = await agent.consult_bid("DIVERSIFIED", 5000, 2)
        assert "bid_price_caps" in guidance
        assert "cheap_ingredients" in guidance
        assert "expected_servings" in guidance
        assert "Water" in guidance["bid_price_caps"]

    @pytest.mark.asyncio
    async def test_consult_bid_accepts_menu_recipes(self):
        agent = StrategyAgent(llm_client=None)
        agent._last_strategy = TurnStrategy(bid_aggressiveness=0.3)
        menu_recipes = [
            {"name": "dish", "prestige": 50, "ingredients": {"a": 2, "b": 3}},
        ]
        guidance = await agent.consult_bid(
            "DIVERSIFIED", 5000, 2, menu_recipes=menu_recipes
        )
        assert "spending_fraction" in guidance


class TestConsultMenuMultiLayer:
    """Test that consult_menu returns tier_targets for multi-layer enforcement."""

    @pytest.mark.asyncio
    async def test_consult_menu_returns_tier_targets(self):
        agent = StrategyAgent(llm_client=None)
        agent._last_strategy = TurnStrategy(confidence=0.6, focus_archetype="all")
        guidance = await agent.consult_menu("DIVERSIFIED", [], {}, 5000)
        assert "tier_targets" in guidance
        assert "budget" in guidance["tier_targets"]
        assert "mid" in guidance["tier_targets"]
        assert "premium" in guidance["tier_targets"]

    @pytest.mark.asyncio
    async def test_premium_focus_shifts_tier_targets(self):
        agent = StrategyAgent(llm_client=None)
        agent._last_strategy = TurnStrategy(confidence=0.6, focus_archetype="premium")
        guidance = await agent.consult_menu("DIVERSIFIED", [], {}, 5000)
        assert guidance["tier_targets"]["premium"] >= guidance["tier_targets"]["budget"]

    @pytest.mark.asyncio
    async def test_budget_focus_shifts_tier_targets(self):
        agent = StrategyAgent(llm_client=None)
        agent._last_strategy = TurnStrategy(confidence=0.6, focus_archetype="budget")
        guidance = await agent.consult_menu("DIVERSIFIED", [], {}, 5000)
        assert guidance["tier_targets"]["budget"] >= guidance["tier_targets"]["premium"]

    @pytest.mark.asyncio
    async def test_consult_menu_returns_bid_price_intelligence(self):
        agent = StrategyAgent(llm_client=None)
        agent._last_strategy = TurnStrategy(confidence=0.6)
        agent.record_bid_history([
            {"ingredient": "X", "bid": 10, "quantity": 1, "status": "completed"},
        ])
        guidance = await agent.consult_menu("DIVERSIFIED", [], {}, 5000)
        assert "bid_price_intelligence" in guidance
        assert "X" in guidance["bid_price_intelligence"]["avg_prices"]


class TestMainWiring:
    """Test that main.py properly wires bid history and turn results."""

    def test_info_gather_feeds_bid_history_to_agent(self):
        """Verify _skill_info_gather has code to call record_bid_history."""
        source = inspect.getsource(
            __import__("src.main", fromlist=["GameOrchestrator"]).GameOrchestrator._skill_info_gather
        )
        assert "record_bid_history" in source
        assert "record_turn_result" in source

    def test_game_started_tracks_balance(self):
        """Verify _handle_game_started captures starting balance."""
        source = inspect.getsource(
            __import__("src.main", fromlist=["GameOrchestrator"]).GameOrchestrator._handle_game_started
        )
        assert "_turn_start_balance" in source
        assert "_turn_customers_served" in source

    def test_client_spawned_counts_customers(self):
        """Verify _handle_client_spawned increments customer counter."""
        source = inspect.getsource(
            __import__("src.main", fromlist=["GameOrchestrator"]).GameOrchestrator._handle_client_spawned
        )
        assert "_turn_customers_served" in source

    def test_consult_bid_passes_menu_recipes(self):
        """Verify consult_bid calls include menu_recipes parameter."""
        source = inspect.getsource(
            __import__("src.main", fromlist=["GameOrchestrator"]).GameOrchestrator
        )
        assert "menu_recipes=" in source


class TestMidTurnSkip:
    """Test that mid-turn entry skips the turn and waits for the next one."""

    @pytest.mark.asyncio
    async def test_mid_turn_entry_sets_skip_flag(self):
        """Joining at closed_bid should set _skip_until_next_turn."""
        router = PhaseRouter()
        await router.handle_phase_change({"phase": "closed_bid", "turn_id": 5})
        assert router._skip_until_next_turn is True
        assert router._is_mid_turn_entry is True
        assert router.current_phase == "closed_bid"

    @pytest.mark.asyncio
    async def test_mid_turn_skips_subsequent_phases(self):
        """After mid-turn entry, subsequent phases should be skipped."""
        router = PhaseRouter()
        handler_called = []

        async def mock_handler(data):
            handler_called.append(data.get("phase"))

        router.register("closed_bid", mock_handler)
        router.register("waiting", mock_handler)
        router.register("serving", mock_handler)
        router.register("stopped", mock_handler)

        # Join mid-turn at closed_bid
        await router.handle_phase_change({"phase": "closed_bid", "turn_id": 5})
        # Subsequent phases should all be skipped
        await router.handle_phase_change({"phase": "waiting", "turn_id": 5})
        await router.handle_phase_change({"phase": "serving", "turn_id": 5})
        await router.handle_phase_change({"phase": "stopped", "turn_id": 5})

        # No handlers should have been called
        assert handler_called == [], f"Handlers called during skip: {handler_called}"

    @pytest.mark.asyncio
    async def test_next_turn_resumes_after_skip(self):
        """After a skipped turn, the next speaking phase should resume normally."""
        router = PhaseRouter()
        handler_called = []

        async def mock_handler(data):
            handler_called.append(data.get("phase"))

        async def mock_turn_change(turn_id):
            pass

        router.register("speaking", mock_handler)
        router.register("closed_bid", mock_handler)
        router.register("waiting", mock_handler)
        router.register("serving", mock_handler)
        router.register("stopped", mock_handler)
        router.on_turn_change(mock_turn_change)

        # Join mid-turn at waiting
        await router.handle_phase_change({"phase": "waiting", "turn_id": 3})
        assert router._skip_until_next_turn is True

        # Remaining phases of this turn are skipped
        await router.handle_phase_change({"phase": "serving", "turn_id": 3})
        await router.handle_phase_change({"phase": "stopped", "turn_id": 3})
        assert handler_called == []

        # Next turn: speaking arrives — should resume
        await router.handle_phase_change({"phase": "speaking", "turn_id": 4})
        assert router._skip_until_next_turn is False
        assert "speaking" in handler_called

    @pytest.mark.asyncio
    async def test_game_started_clears_skip_flag(self):
        """game_started should clear the skip flag for a fresh turn."""
        router = PhaseRouter()
        # Simulate mid-turn entry
        await router.handle_phase_change({"phase": "serving", "turn_id": 2})
        assert router._skip_until_next_turn is True

        # game_started fires (new turn)
        await router.handle_game_started({"turn_id": 3})
        assert router._skip_until_next_turn is False

    @pytest.mark.asyncio
    async def test_normal_entry_does_not_set_skip(self):
        """Normal entry at speaking should NOT set _skip_until_next_turn."""
        router = PhaseRouter()
        handler_called = []

        async def mock_handler(data):
            handler_called.append(data.get("phase"))

        router.register("speaking", mock_handler)
        await router.handle_phase_change({"phase": "speaking", "turn_id": 1})
        assert router._skip_until_next_turn is False
        assert "speaking" in handler_called

    @pytest.mark.asyncio
    async def test_game_reset_clears_skip_flag(self):
        """game_reset should clear the skip flag."""
        router = PhaseRouter()
        router._skip_until_next_turn = True
        await router.handle_game_reset({})
        assert router._skip_until_next_turn is False
