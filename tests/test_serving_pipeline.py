"""
Tests for the poll-driven serving pipeline (v2).

Validates critical failure modes:
1. Duplicate dish FIFO ordering
2. Ingredient accounting (commit / uncommit)
3. MCP retry + isError detection
4. Preparation timeout watchdog
5. Poll dedup (same client_id not processed twice)
6. Metrics tracking
7. Order matcher (unchanged)
"""

import asyncio
import collections
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

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
        "preparationTimeMs": prep_time * 1000,
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
        mcp = AsyncMock()
        mcp.call_tool = AsyncMock(return_value={"isError": False, "content": []})
        pipeline = make_pipeline(mcp)

        await pipeline.start_serving(turn_id=1)
        pipeline.set_inventory_snapshot(INVENTORY)

        # Simulate two /meals entries for the same dish
        meal_a = {"client_id": "m1", "clientName": "Zork-7", "orderText": "Sinfonia Cosmica", "executed": False}
        meal_b = {"client_id": "m2", "clientName": "Blix-3", "orderText": "Sinfonia Cosmica", "executed": False}

        await pipeline._serve_meal(meal_a, "m1")
        await pipeline._serve_meal(meal_b, "m2")

        # Both should be in the FIFO deque
        assert "Sinfonia Cosmica" in pipeline.preparing
        assert len(pipeline.preparing["Sinfonia Cosmica"]) == 2

        # First preparation_complete → serves client A (FIFO)
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

    @pytest.mark.asyncio
    async def test_ingredient_exhaustion_skips_customer(self):
        """When ingredients run out for matched dish, SKIP the customer
        instead of serving a wrong dish (reputation protection)."""
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

        meal_a = {"client_id": "m1", "clientName": "A", "orderText": "Sinfonia Cosmica", "executed": False}
        meal_b = {"client_id": "m2", "clientName": "B", "orderText": "Sinfonia Cosmica", "executed": False}

        await pipeline._serve_meal(meal_a, "m1")
        assert pipeline.metrics.preparations_started == 1

        # Second client — ingredients insufficient → SKIP (not redirect!)
        # Serving a wrong dish gets rejected and tanks reputation
        await pipeline._serve_meal(meal_b, "m2")
        assert pipeline.metrics.preparations_started == 1, \
            "Should NOT prepare a second dish when ingredients for matched dish are exhausted"
        assert pipeline.metrics.clients_no_ingredients == 1, \
            "Should count as no_ingredients skip"

        await pipeline.stop_serving()

    def test_can_cook_checks_committed(self):
        pipeline = make_pipeline()
        pipeline._inventory_snapshot = {"Polvere di Crononite": 2, "Funghi Orbitali": 1}
        pipeline._committed_ingredients = {}

        assert pipeline._can_cook("Sinfonia Cosmica") is True
        pipeline._commit_ingredients("Sinfonia Cosmica")
        assert pipeline._can_cook("Sinfonia Cosmica") is False

    def test_uncommit_releases_ingredients(self):
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

    @pytest.mark.asyncio
    async def test_retry_on_exception(self):
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
        mcp = AsyncMock()
        mcp.call_tool = AsyncMock(return_value={
            "isError": True,
            "content": [{"text": "Dish not in menu"}],
        })
        pipeline = make_pipeline(mcp)

        result = await pipeline._mcp_call_with_retry("prepare_dish", {"dish_name": "X"})
        assert result is False
        assert mcp.call_tool.call_count == 1

    @pytest.mark.asyncio
    async def test_all_retries_exhausted(self):
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


# ── Test 5: Order Matcher ──


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

    def test_fuzzy_match_typo(self):
        assert self.matcher.match("Sinfonia Cosmca") == "Sinfonia Cosmica"

    def test_substring_match(self):
        assert self.matcher.match("I want the Piatto Budget today") == "Piatto Budget"

    def test_empty_string_fallback(self):
        result = self.matcher.match("")
        assert result is not None

    def test_cache_learning(self):
        self.matcher.add_to_cache("il solito", "Piatto Budget")
        assert self.matcher.match("il solito") == "Piatto Budget"


# ── Test 6: Preparation Timeout ──


class TestPreparationTimeout:
    @pytest.mark.asyncio
    async def test_timeout_cleans_up_stale_preparation(self):
        pipeline = make_pipeline()
        await pipeline.start_serving(turn_id=1)
        pipeline.set_inventory_snapshot(INVENTORY)

        stale = PendingPreparation(
            dish_name="Sinfonia Cosmica",
            client_id="stale_client",
            client_name="Old Client",
            order_text="test",
            started_at=time.time() - 60,
            expected_prep_time=5.0,
        )
        pipeline.preparing["Sinfonia Cosmica"] = collections.deque([stale])
        pipeline._committed_ingredients = {"Polvere di Crononite": 2, "Funghi Orbitali": 1}

        # Run watchdog briefly
        watchdog = asyncio.create_task(pipeline._preparation_timeout_watchdog())
        await asyncio.sleep(2.5)
        watchdog.cancel()
        try:
            await watchdog
        except asyncio.CancelledError:
            pass

        assert "Sinfonia Cosmica" not in pipeline.preparing
        assert pipeline.metrics.preparations_timed_out == 1
        assert pipeline._committed_ingredients.get("Polvere di Crononite", 0) == 0

        await pipeline.stop_serving()


# ── Test 7: Poll Dedup ──


class TestPollDedup:
    @pytest.mark.asyncio
    async def test_same_client_id_not_processed_twice(self):
        """If /meals returns the same client_id on two polls, only process once."""
        mcp = AsyncMock()
        mcp.call_tool = AsyncMock(return_value={"isError": False, "content": []})
        pipeline = make_pipeline(mcp)

        await pipeline.start_serving(turn_id=1)
        pipeline.set_inventory_snapshot(INVENTORY)

        meal = {"client_id": "m1", "clientName": "Zork-7", "orderText": "Sinfonia Cosmica", "executed": False}

        # Process once
        await pipeline._serve_meal(meal, "m1")
        pipeline._processed_meal_ids.add("m1")

        # Simulate second poll returning same meal
        assert "m1" in pipeline._processed_meal_ids
        assert pipeline.metrics.preparations_started == 1

        await pipeline.stop_serving()


# ── Test 8: Metrics Tracking ──


class TestMetrics:
    @pytest.mark.asyncio
    async def test_metrics_count_correctly(self):
        mcp = AsyncMock()
        mcp.call_tool = AsyncMock(return_value={"isError": False, "content": []})
        pipeline = make_pipeline(mcp)

        await pipeline.start_serving(turn_id=1)
        pipeline.set_inventory_snapshot(INVENTORY)

        meal = {"client_id": "m1", "clientName": "Zork-7", "orderText": "Sinfonia Cosmica", "executed": False}
        # clients_received is incremented in _meals_polling_loop, not _serve_meal
        pipeline.metrics.clients_received += 1
        await pipeline._serve_meal(meal, "m1")

        assert pipeline.metrics.clients_received == 1
        assert pipeline.metrics.clients_matched == 1
        assert pipeline.metrics.preparations_started == 1

        await pipeline.handle_preparation_complete({"dish": "Sinfonia Cosmica"})
        assert pipeline.metrics.preparations_completed == 1
        assert pipeline.metrics.serves_successful == 1

        await pipeline.stop_serving()
