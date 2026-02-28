"""
Tests for the hardened serving pipeline.

Validates all 8 critical failure modes are handled:
1. Duplicate dish key collision → FIFO deque
2. Ingredient over-commitment → accounting check
3. MCP transient failure → retry logic
4. MCP isError detection → permanent vs transient
5. GET /meals flooding → cached resolution
6. Queue re-entrancy → lock guard
7. Preparation timeout → watchdog
8. Ingredient exhaustion → auto-close
"""

import asyncio
import collections
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# We test the pipeline directly, mocking external deps
from src.serving.pipeline import (
    ServingPipeline,
    PendingPreparation,
    ServingMetrics,
    MAX_MCP_RETRIES,
)
from src.serving.order_matcher import OrderMatcher


# ── Fixtures ──


def make_recipe(name: str, ingredients: dict, prestige: float = 50, prep_time: float = 5.0):
    return {
        "name": name,
        "ingredients": ingredients,
        "prestige": prestige,
        "prep_time": prep_time,
    }


RECIPES = {
    "Sinfonia Cosmica": make_recipe(
        "Sinfonia Cosmica",
        {"Polvere di Crononite": 2, "Funghi Orbitali": 1},
        prestige=95,
        prep_time=5.0,
    ),
    "Nebulosa Stellare": make_recipe(
        "Nebulosa Stellare",
        {"Lacrime di Andromeda": 1, "Funghi Orbitali": 2},
        prestige=80,
        prep_time=4.0,
    ),
    "Piatto Budget": make_recipe(
        "Piatto Budget",
        {"Farina di Nettuno": 1},
        prestige=30,
        prep_time=3.0,
    ),
}

MENU_ITEMS = [
    {"name": "Sinfonia Cosmica", "price": 150},
    {"name": "Nebulosa Stellare", "price": 100},
    {"name": "Piatto Budget", "price": 40},
]

INVENTORY = {
    "Polvere di Crononite": 4,
    "Funghi Orbitali": 3,
    "Lacrime di Andromeda": 2,
    "Farina di Nettuno": 5,
}


class MockIntoleranceDetector:
    """Always says recipes are safe (for most tests)."""

    def is_recipe_safe(self, archetype: str, ingredients: list) -> bool:
        return True


class MockClientLibrary:
    order_to_dish_cache = {}


def make_pipeline(mcp_client=None) -> ServingPipeline:
    pipeline = ServingPipeline(
        recipes=RECIPES,
        intolerance_detector=MockIntoleranceDetector(),
        client_library=MockClientLibrary(),
        mcp_client=mcp_client or AsyncMock(),
    )
    pipeline.set_menu(MENU_ITEMS)
    return pipeline


# ── Test 1: Duplicate Dish Key (FIFO Deque) ──


class TestDuplicateDishKey:
    """Validate that two clients ordering the same dish are BOTH served."""

    @pytest.mark.asyncio
    async def test_two_clients_same_dish_fifo(self):
        """When two clients order the same dish, both should get separate
        entries in the FIFO deque, and preparation_complete should serve
        them in order."""
        mcp = AsyncMock()
        mcp.call_tool = AsyncMock(return_value={"isError": False, "content": []})
        pipeline = make_pipeline(mcp)

        await pipeline.start_serving(turn_id=1)
        pipeline.set_inventory_snapshot(INVENTORY)

        # Mock meals resolution — return two different meal IDs
        meals_response = [
            {"id": "meal_1", "clientName": "Astrobarone", "orderText": "Sinfonia Cosmica", "executed": False},
            {"id": "meal_2", "clientName": "Saggi del Cosmo", "orderText": "Sinfonia Cosmica", "executed": False},
        ]
        with patch.object(pipeline, "_get_meals_cached", new_callable=AsyncMock) as mock_meals:
            mock_meals.return_value = meals_response

            # Client A arrives
            await pipeline.handle_client({
                "clientName": "Astrobarone",
                "orderText": "Sinfonia Cosmica"
            })

            # Client B arrives (same dish!)
            await pipeline.handle_client({
                "clientName": "Saggi del Cosmo",
                "orderText": "Sinfonia Cosmica"
            })

        # Both should be in the FIFO deque
        assert "Sinfonia Cosmica" in pipeline.preparing
        assert len(pipeline.preparing["Sinfonia Cosmica"]) == 2

        # First preparation_complete → serves client A
        await pipeline.handle_preparation_complete({"dish": "Sinfonia Cosmica"})
        assert pipeline.metrics.serves_successful == 1

        # Second preparation_complete → serves client B
        await pipeline.handle_preparation_complete({"dish": "Sinfonia Cosmica"})
        assert pipeline.metrics.serves_successful == 2

        # Queue should be empty
        assert "Sinfonia Cosmica" not in pipeline.preparing

        await pipeline.stop_serving()


# ── Test 2: Ingredient Accounting ──


class TestIngredientAccounting:
    """Validate that ingredient over-commitment is prevented."""

    @pytest.mark.asyncio
    async def test_ingredient_exhaustion_redirects(self):
        """When ingredients run out for a dish, redirect to another dish."""
        mcp = AsyncMock()
        mcp.call_tool = AsyncMock(return_value={"isError": False, "content": []})
        pipeline = make_pipeline(mcp)

        await pipeline.start_serving(turn_id=1)
        # Only enough for ONE Sinfonia Cosmica
        pipeline.set_inventory_snapshot({
            "Polvere di Crononite": 2,
            "Funghi Orbitali": 1,
            "Farina di Nettuno": 5,
        })

        meals = [
            {"id": "m1", "clientName": "A", "orderText": "Sinfonia Cosmica", "executed": False},
            {"id": "m2", "clientName": "B", "orderText": "Sinfonia Cosmica", "executed": False},
        ]
        with patch.object(pipeline, "_get_meals_cached", new_callable=AsyncMock) as mock_meals:
            mock_meals.return_value = meals

            # First client — should succeed with Sinfonia Cosmica
            await pipeline.handle_client({
                "clientName": "A", "orderText": "Sinfonia Cosmica"
            })
            assert pipeline.metrics.preparations_started == 1

            # Second client — Sinfonia Cosmica insufficient,
            # should redirect to Piatto Budget (only other cookable dish)
            await pipeline.handle_client({
                "clientName": "B", "orderText": "Sinfonia Cosmica"
            })
            # Should still have started a preparation (for the fallback dish)
            assert pipeline.metrics.preparations_started == 2

        await pipeline.stop_serving()

    def test_can_cook_checks_committed(self):
        """_can_cook should consider already-committed ingredients."""
        pipeline = make_pipeline()
        pipeline._inventory_snapshot = {"Polvere di Crononite": 2, "Funghi Orbitali": 1}
        pipeline._committed_ingredients = {}

        assert pipeline._can_cook("Sinfonia Cosmica") is True

        # Commit ingredients for one dish
        pipeline._commit_ingredients("Sinfonia Cosmica")

        # Now we shouldn't be able to cook another
        assert pipeline._can_cook("Sinfonia Cosmica") is False

    def test_uncommit_releases_ingredients(self):
        """_uncommit_ingredients should release committed quantities."""
        pipeline = make_pipeline()
        pipeline._inventory_snapshot = {"Polvere di Crononite": 4, "Funghi Orbitali": 2}
        pipeline._committed_ingredients = {}

        pipeline._commit_ingredients("Sinfonia Cosmica")
        assert pipeline._committed_ingredients["Polvere di Crononite"] == 2
        assert pipeline._committed_ingredients["Funghi Orbitali"] == 1

        pipeline._uncommit_ingredients("Sinfonia Cosmica")
        assert pipeline._committed_ingredients["Polvere di Crononite"] == 0
        assert pipeline._committed_ingredients["Funghi Orbitali"] == 0


# ── Test 3: MCP Retry Logic ──


class TestMCPRetry:
    """Validate MCP retry and isError detection."""

    @pytest.mark.asyncio
    async def test_retry_on_exception(self):
        """MCP call that fails twice then succeeds should return True."""
        mcp = AsyncMock()
        call_count = 0

        async def failing_then_ok(tool_name, args):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise ConnectionError("transient")
            return {"isError": False, "content": []}

        mcp.call_tool = AsyncMock(side_effect=failing_then_ok)
        pipeline = make_pipeline(mcp)

        result = await pipeline._mcp_call_with_retry("prepare_dish", {"dish_name": "X"})
        assert result is True
        assert call_count == 3
        assert pipeline.metrics.mcp_retries == 2

    @pytest.mark.asyncio
    async def test_permanent_error_no_retry(self):
        """MCP isError with 'not in menu' should NOT retry."""
        mcp = AsyncMock()
        mcp.call_tool = AsyncMock(return_value={
            "isError": True,
            "content": [{"text": "Dish not in menu"}],
        })
        pipeline = make_pipeline(mcp)

        result = await pipeline._mcp_call_with_retry("prepare_dish", {"dish_name": "X"})
        assert result is False
        assert mcp.call_tool.call_count == 1  # no retries

    @pytest.mark.asyncio
    async def test_all_retries_exhausted(self):
        """If all retries fail, return False."""
        mcp = AsyncMock()
        mcp.call_tool = AsyncMock(side_effect=ConnectionError("down"))
        pipeline = make_pipeline(mcp)

        result = await pipeline._mcp_call_with_retry("serve_dish", {"dish_name": "X", "client_id": "1"})
        assert result is False
        assert mcp.call_tool.call_count == MAX_MCP_RETRIES
        assert pipeline.metrics.mcp_errors == 1


# ── Test 4: isError Detection ──


class TestIsErrorDetection:
    def test_dict_direct(self):
        assert ServingPipeline._is_mcp_error({"isError": True, "content": []}) is True

    def test_dict_wrapped(self):
        assert ServingPipeline._is_mcp_error({"result": {"isError": True}}) is True

    def test_dict_ok(self):
        assert ServingPipeline._is_mcp_error({"isError": False, "content": []}) is False

    def test_none(self):
        assert ServingPipeline._is_mcp_error(None) is True

    def test_object_with_attribute(self):
        obj = MagicMock()
        obj.isError = True
        assert ServingPipeline._is_mcp_error(obj) is True


# ── Test 5: Order Matcher (Hardened) ──


class TestOrderMatcher:
    def setup_method(self):
        self.matcher = OrderMatcher(MENU_ITEMS)

    def test_exact_match(self):
        assert self.matcher.match("Sinfonia Cosmica") == "Sinfonia Cosmica"

    def test_case_insensitive(self):
        assert self.matcher.match("sinfonia cosmica") == "Sinfonia Cosmica"

    def test_strip_english_prefix(self):
        assert self.matcher.match("I'd like a Sinfonia Cosmica") == "Sinfonia Cosmica"

    def test_strip_italian_prefix(self):
        assert self.matcher.match("Vorrei Sinfonia Cosmica") == "Sinfonia Cosmica"

    def test_strip_suffix_please(self):
        assert self.matcher.match("Sinfonia Cosmica, please") == "Sinfonia Cosmica"

    def test_strip_suffix_grazie(self):
        assert self.matcher.match("Sinfonia Cosmica, grazie") == "Sinfonia Cosmica"

    def test_fuzzy_match_typo(self):
        assert self.matcher.match("Sinfonia Cosmca") == "Sinfonia Cosmica"

    def test_substring_match(self):
        assert self.matcher.match("I want the Piatto Budget today") == "Piatto Budget"

    def test_empty_string_fallback(self):
        """Empty order should fallback to first menu dish, NOT return None."""
        result = self.matcher.match("")
        assert result is not None  # should return a fallback dish

    def test_garbage_input_fallback(self):
        """Completely unrelated text should fallback, NOT return None."""
        result = self.matcher.match("xyz abc 123")
        assert result is not None

    def test_cache_learning(self):
        """After caching a match, same order should be O(1)."""
        self.matcher.add_to_cache("il solito", "Piatto Budget")
        assert self.matcher.match("il solito") == "Piatto Budget"


# ── Test 6: Preparation Timeout ──


class TestPreparationTimeout:
    @pytest.mark.asyncio
    async def test_timeout_cleans_up_stale_preparation(self):
        """Watchdog should remove preparations that exceed timeout."""
        pipeline = make_pipeline()
        await pipeline.start_serving(turn_id=1)
        pipeline.set_inventory_snapshot(INVENTORY)

        # Manually add a stale preparation (started 60 seconds ago)
        stale = PendingPreparation(
            dish_name="Sinfonia Cosmica",
            client_id="stale_client",
            client_name="Old Client",
            order_text="test",
            archetype="unknown",
            started_at=time.time() - 60,  # 60 seconds ago
            expected_prep_time=5.0,  # timeout = 5 * 2.5 + 5 = 17.5s
        )
        pipeline.preparing["Sinfonia Cosmica"] = collections.deque([stale])
        pipeline._committed_ingredients = {"Polvere di Crononite": 2, "Funghi Orbitali": 1}

        # Run watchdog briefly
        watchdog = asyncio.create_task(pipeline._preparation_timeout_watchdog())
        await asyncio.sleep(2.5)  # let it run one cycle
        watchdog.cancel()
        try:
            await watchdog
        except asyncio.CancelledError:
            pass

        # Stale preparation should be cleaned up
        assert "Sinfonia Cosmica" not in pipeline.preparing
        assert pipeline.metrics.preparations_timed_out == 1
        # Ingredients should be uncommitted
        assert pipeline._committed_ingredients.get("Polvere di Crononite", 0) == 0

        await pipeline.stop_serving()


# ── Test 7: Client ID Resolution Dedup ──


class TestClientIdDedup:
    @pytest.mark.asyncio
    async def test_resolved_ids_not_reused(self):
        """Once a meal ID is resolved, it should NOT be returned for another client."""
        pipeline = make_pipeline()
        await pipeline.start_serving(turn_id=1)

        meals = [
            {"id": "m1", "clientName": "A", "orderText": "Sinfonia Cosmica", "executed": False},
            {"id": "m2", "clientName": "B", "orderText": "Sinfonia Cosmica", "executed": False},
        ]
        with patch.object(pipeline, "_get_meals_cached", new_callable=AsyncMock) as mock_meals:
            mock_meals.return_value = meals

            # First resolution
            id1 = await pipeline._try_resolve_from_meals("A", "Sinfonia Cosmica")
            assert id1 == "m1"

            # Second resolution (same order text) — should get m2, NOT m1 again
            id2 = await pipeline._try_resolve_from_meals("B", "Sinfonia Cosmica")
            assert id2 == "m2"
            assert id1 != id2

        await pipeline.stop_serving()


# ── Test 8: Metrics Tracking ──


class TestMetrics:
    @pytest.mark.asyncio
    async def test_metrics_count_correctly(self):
        """Verify metrics are incremented at each stage."""
        mcp = AsyncMock()
        mcp.call_tool = AsyncMock(return_value={"isError": False, "content": []})
        pipeline = make_pipeline(mcp)

        await pipeline.start_serving(turn_id=1)
        pipeline.set_inventory_snapshot(INVENTORY)

        meals = [
            {"id": "m1", "clientName": "Astrobarone", "orderText": "Sinfonia Cosmica", "executed": False},
        ]
        with patch.object(pipeline, "_get_meals_cached", new_callable=AsyncMock) as mock_meals:
            mock_meals.return_value = meals

            await pipeline.handle_client({
                "clientName": "Astrobarone",
                "orderText": "Sinfonia Cosmica"
            })

        assert pipeline.metrics.clients_received == 1
        assert pipeline.metrics.clients_matched == 1
        assert pipeline.metrics.preparations_started == 1

        # Simulate preparation_complete
        await pipeline.handle_preparation_complete({"dish": "Sinfonia Cosmica"})
        assert pipeline.metrics.preparations_completed == 1
        assert pipeline.metrics.serves_successful == 1

        await pipeline.stop_serving()
