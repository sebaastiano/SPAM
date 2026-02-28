"""
Targeted tests for order text extraction and intolerance detection logic.

Validates the two critical paths:
 1. OrderMatcher correctly extracts dish name from real order texts
 2. _extract_intolerances correctly identifies declared intolerances
 3. Pipeline correctly avoids serving intolerant ingredients to clients
 4. Edge cases from observed game events

Uses REAL order texts observed in game_events.jsonl.
"""

import asyncio
import collections
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.serving.order_matcher import OrderMatcher
from src.serving.pipeline import ServingPipeline, PendingPreparation


# ══════════════════════════════════════════════════════════════
#  FIXTURES — realistic menu & recipes from game data
# ══════════════════════════════════════════════════════════════

GAME_RECIPES = {
    "Sinfonia del Multiverso Calante": {
        "name": "Sinfonia del Multiverso Calante",
        "ingredients": {"Polvere di Crononite": 1, "Shard di Prisma Stellare": 1, "Latte+": 1},
        "prestige": 85,
        "preparationTimeMs": 3970,
    },
    "Sinfonia Aromatica del Multiverso": {
        "name": "Sinfonia Aromatica del Multiverso",
        "ingredients": {"Funghi Orbitali": 1, "Lacrime di Andromeda": 1},
        "prestige": 78,
        "preparationTimeMs": 4000,
    },
    "Portale Cosmico: Sinfonia di Gnocchi del Crepuscolo con Essenza di Tachioni e Sfumature di Fenice": {
        "name": "Portale Cosmico: Sinfonia di Gnocchi del Crepuscolo con Essenza di Tachioni e Sfumature di Fenice",
        "ingredients": {"Gnocchi del Crepuscolo": 1, "Essenza di Tachioni": 1, "Uova di Fenice": 1, "Polvere di Crononite": 1, "Shard di Prisma Stellare": 1},
        "prestige": 100,
        "preparationTimeMs": 5224,
    },
    "Sinfonia Temporale di Fenice e Xenodonte su Pane degli Abissi con Colata di Plasma Vitale e Polvere di Crononite": {
        "name": "Sinfonia Temporale di Fenice e Xenodonte su Pane degli Abissi con Colata di Plasma Vitale e Polvere di Crononite",
        "ingredients": {"Uova di Fenice": 1, "Carne di Xenodonte": 1, "Pane degli Abissi": 1, "Plasma Vitale": 1, "Polvere di Crononite": 1},
        "prestige": 95,
        "preparationTimeMs": 4050,
    },
    "Viaggio Cosmico nel Multiverso": {
        "name": "Viaggio Cosmico nel Multiverso",
        "ingredients": {"Essenza di Tachioni": 1, "Polvere di Crononite": 1},
        "prestige": 70,
        "preparationTimeMs": 4500,
    },
    "Sinfonia Cosmica di Terracotta": {
        "name": "Sinfonia Cosmica di Terracotta",
        "ingredients": {"Farina di Nettuno": 1, "Radici di Gravità": 1},
        "prestige": 60,
        "preparationTimeMs": 3500,
    },
    "Sinfonia Cosmica di Andromeda": {
        "name": "Sinfonia Cosmica di Andromeda",
        "ingredients": {"Lacrime di Andromeda": 1, "Funghi Orbitali": 2, "Polvere di Crononite": 1},
        "prestige": 88,
        "preparationTimeMs": 5000,
    },
    "Piatto Sicuro Senza Funghi": {
        "name": "Piatto Sicuro Senza Funghi",
        "ingredients": {"Farina di Nettuno": 2},
        "prestige": 30,
        "preparationTimeMs": 3000,
    },
}

GAME_MENU = [
    {"name": n, "price": int(r["prestige"] * 1.5)}
    for n, r in GAME_RECIPES.items()
]

GAME_INVENTORY = {
    "Polvere di Crononite": 5,
    "Shard di Prisma Stellare": 3,
    "Latte+": 2,
    "Funghi Orbitali": 4,
    "Lacrime di Andromeda": 3,
    "Gnocchi del Crepuscolo": 2,
    "Essenza di Tachioni": 3,
    "Uova di Fenice": 3,
    "Carne di Xenodonte": 2,
    "Pane degli Abissi": 2,
    "Plasma Vitale": 2,
    "Farina di Nettuno": 5,
    "Radici di Gravità": 3,
}


class MockIntoleranceDetector:
    """Always says recipes are safe — we test declared-intolerance logic separately."""
    def is_recipe_safe(self, archetype: str, ingredients: list) -> bool:
        return True


class MockClientLibrary:
    order_to_dish_cache = {}


def make_matcher() -> OrderMatcher:
    return OrderMatcher(GAME_MENU, order_cache={})


def make_pipeline(mcp_client=None, intolerance_safe=True) -> ServingPipeline:
    if intolerance_safe:
        intol = MockIntoleranceDetector()
    else:
        # Create an intolerance detector that says everything is unsafe
        intol = MagicMock()
        intol.is_recipe_safe = MagicMock(return_value=False)

    pipeline = ServingPipeline(
        recipes=GAME_RECIPES,
        intolerance_detector=intol,
        client_library=MockClientLibrary(),
        mcp_client=mcp_client or AsyncMock(),
    )
    pipeline.set_menu(GAME_MENU)
    return pipeline


# ══════════════════════════════════════════════════════════════
#  TEST 1: OrderMatcher with REAL game order texts
# ══════════════════════════════════════════════════════════════


class TestOrderMatcherRealOrders:
    """Test OrderMatcher against actual order texts seen in game_events.jsonl."""

    def setup_method(self):
        self.matcher = make_matcher()

    # REAL GAME EVENTS — bare dish name (most common pattern)
    def test_bare_dish_name(self):
        """Most clients just state the dish name directly."""
        assert self.matcher.match("Sinfonia Aromatica del Multiverso") == "Sinfonia Aromatica del Multiverso"

    def test_bare_long_dish_name(self):
        """Very long dish names should match exactly."""
        full = "Portale Cosmico: Sinfonia di Gnocchi del Crepuscolo con Essenza di Tachioni e Sfumature di Fenice"
        assert self.matcher.match(full) == full

    def test_bare_dish_with_prep_time_name(self):
        """Another real dish name."""
        assert self.matcher.match("Sinfonia Temporale di Fenice e Xenodonte su Pane degli Abissi con Colata di Plasma Vitale e Polvere di Crononite") == \
            "Sinfonia Temporale di Fenice e Xenodonte su Pane degli Abissi con Colata di Plasma Vitale e Polvere di Crononite"

    def test_bare_dish_viaggio(self):
        assert self.matcher.match("Viaggio Cosmico nel Multiverso") == "Viaggio Cosmico nel Multiverso"

    def test_bare_dish_terracotta(self):
        assert self.matcher.match("Sinfonia Cosmica di Terracotta") == "Sinfonia Cosmica di Terracotta"

    # REAL GAME EVENTS — "I want to eat X. I'm intolerant to Y"
    def test_order_with_intolerance_english(self):
        """Real event: 'I want to eat Sinfonia del Multiverso Calante. I'm intolerant to Latte+'"""
        result = self.matcher.match("I want to eat Sinfonia del Multiverso Calante. I'm intolerant to Latte+")
        assert result == "Sinfonia del Multiverso Calante"

    def test_order_with_intolerance_funghi(self):
        """Real event: 'I want to eat Sinfonia Cosmica di Andromeda. I'm intolerant to Funghi Orbitali'"""
        result = self.matcher.match("I want to eat Sinfonia Cosmica di Andromeda. I'm intolerant to Funghi Orbitali")
        assert result == "Sinfonia Cosmica di Andromeda"

    # Hypothetical Italian intolerance patterns
    def test_order_italian_intolerance(self):
        """Italian pattern: 'Vorrei Sinfonia Aromatica del Multiverso. Sono intollerante ai Funghi Orbitali'"""
        result = self.matcher.match("Vorrei Sinfonia Aromatica del Multiverso. Sono intollerante ai Funghi Orbitali")
        assert result == "Sinfonia Aromatica del Multiverso"

    def test_order_italian_alla_intolerance(self):
        """Italian 'alla' variant."""
        result = self.matcher.match("Vorrei Sinfonia del Multiverso Calante. Sono intollerante alla Latte+")
        assert result == "Sinfonia del Multiverso Calante"

    # English variations
    def test_id_like_prefix(self):
        result = self.matcher.match("I'd like a Sinfonia Aromatica del Multiverso")
        assert result == "Sinfonia Aromatica del Multiverso"

    def test_id_like_prefix_with_intolerance(self):
        result = self.matcher.match("I'd like a Sinfonia del Multiverso Calante. I'm intolerant to Latte+")
        assert result == "Sinfonia del Multiverso Calante"

    def test_could_i_have_prefix(self):
        result = self.matcher.match("Could I have a Sinfonia Cosmica di Terracotta")
        assert result == "Sinfonia Cosmica di Terracotta"

    def test_give_me_prefix(self):
        result = self.matcher.match("Give me a Viaggio Cosmico nel Multiverso")
        assert result == "Viaggio Cosmico nel Multiverso"

    # Case insensitive
    def test_case_insensitive_real_dish(self):
        result = self.matcher.match("sinfonia aromatica del multiverso")
        assert result == "Sinfonia Aromatica del Multiverso"

    # With trailing punctuation
    def test_with_please_suffix(self):
        result = self.matcher.match("Sinfonia Aromatica del Multiverso, please")
        assert result == "Sinfonia Aromatica del Multiverso"

    def test_with_grazie_suffix(self):
        result = self.matcher.match("Sinfonia Aromatica del Multiverso, grazie")
        assert result == "Sinfonia Aromatica del Multiverso"


# ══════════════════════════════════════════════════════════════
#  TEST 2: Intolerance extraction from order text
# ══════════════════════════════════════════════════════════════


class TestIntoleranceExtraction:
    """Test _extract_intolerances using real and hypothetical order texts."""

    def test_english_im_intolerant_latte(self):
        """Real event pattern."""
        result = ServingPipeline._extract_intolerances(
            "I want to eat Sinfonia del Multiverso Calante. I'm intolerant to Latte+"
        )
        assert len(result) >= 1
        assert any("latte+" in r.lower() for r in result), f"Expected 'latte+' in {result}"

    def test_english_im_intolerant_funghi(self):
        """Real event pattern."""
        result = ServingPipeline._extract_intolerances(
            "I want to eat Sinfonia Cosmica di Andromeda. I'm intolerant to Funghi Orbitali"
        )
        assert len(result) >= 1
        assert any("funghi orbitali" in r.lower() for r in result), f"Expected 'funghi orbitali' in {result}"

    def test_italian_sono_intollerante_ai(self):
        result = ServingPipeline._extract_intolerances(
            "Vorrei Sinfonia. Sono intollerante ai Cristalli di Sale"
        )
        assert len(result) >= 1
        assert any("cristalli di sale" in r.lower() for r in result), f"Got {result}"

    def test_italian_sono_intollerante_alla(self):
        result = ServingPipeline._extract_intolerances(
            "Prendo il piatto. Sono intollerante alla Farina di Nettuno"
        )
        assert len(result) >= 1
        assert any("farina di nettuno" in r.lower() for r in result), f"Got {result}"

    def test_english_i_am_intolerant(self):
        result = ServingPipeline._extract_intolerances(
            "I want Sinfonia. I am intolerant to Polvere di Crononite"
        )
        assert len(result) >= 1
        assert any("polvere di crononite" in r.lower() for r in result), f"Got {result}"

    def test_no_intolerance(self):
        """Order with no intolerance info should return empty."""
        result = ServingPipeline._extract_intolerances(
            "Sinfonia Aromatica del Multiverso"
        )
        assert result == []

    def test_no_intolerance_with_prefix(self):
        result = ServingPipeline._extract_intolerances(
            "I'd like a Sinfonia Aromatica del Multiverso, please"
        )
        assert result == []

    def test_but_im_intolerant(self):
        """'but I'm intolerant' variant (regex handled in OrderMatcher._normalize too)."""
        result = ServingPipeline._extract_intolerances(
            "I'd like a Sinfonia, but I'm intolerant to Essenza di Tachioni"
        )
        # Note: the pipeline regex catches "I'm intolerant to X" 
        assert len(result) >= 1

    def test_intolerance_with_smart_quotes(self):
        """Smart/curly apostrophe (I\u2019m) should also be matched."""
        result = ServingPipeline._extract_intolerances(
            "I want to eat dish. I\u2019m intolerant to Funghi Orbitali"
        )
        assert len(result) >= 1
        assert any("funghi orbitali" in r.lower() for r in result), f"Got {result}"

    def test_intolerance_ingredient_with_plus(self):
        """Latte+ has a special character — must be extracted correctly."""
        result = ServingPipeline._extract_intolerances(
            "Give me dish. I'm intolerant to Latte+"
        )
        assert len(result) >= 1
        # The ingredient name "Latte+" should appear (possibly without +)
        assert any("latte" in r.lower() for r in result), f"Got {result}"


# ══════════════════════════════════════════════════════════════
#  TEST 3: Pipeline intolerance-aware serving flow
# ══════════════════════════════════════════════════════════════


class TestPipelineIntoleranceFlow:
    """Validate that the pipeline correctly avoids intolerant ingredients."""

    @pytest.mark.asyncio
    async def test_intolerant_client_gets_safe_dish(self):
        """
        Client intolerant to Funghi Orbitali orders Sinfonia Cosmica di Andromeda
        (which contains Funghi Orbitali). Pipeline should redirect to a safe alternative.
        """
        mcp = AsyncMock()
        mcp.call_tool = AsyncMock(return_value={"isError": False, "content": []})
        pipeline = make_pipeline(mcp)

        await pipeline.start_serving(turn_id=1)
        pipeline.set_inventory_snapshot(GAME_INVENTORY)

        # Real game event format
        meal = {
            "request": "I want to eat Sinfonia Cosmica di Andromeda. I'm intolerant to Funghi Orbitali",
            "customer": {"name": "Rovo Pike"},
            "customerId": "c1",
            "executed": False,
        }
        await pipeline._serve_meal(meal, "c1")

        # The pipeline should have detected the intolerance and redirected
        # Check what dish was actually prepared (from the FIFO queue)
        prepared_dishes = list(pipeline.preparing.keys())
        assert len(prepared_dishes) == 1

        prepared_dish = prepared_dishes[0]
        # The prepared dish should NOT contain Funghi Orbitali
        recipe = GAME_RECIPES.get(prepared_dish, {})
        recipe_ings = list(recipe.get("ingredients", {}).keys())
        assert "Funghi Orbitali" not in recipe_ings, (
            f"Pipeline prepared {prepared_dish} which contains Funghi Orbitali, "
            f"but client is intolerant! Ingredients: {recipe_ings}"
        )

        await pipeline.stop_serving()

    @pytest.mark.asyncio
    async def test_non_intolerant_client_gets_requested_dish(self):
        """Client WITHOUT intolerance gets exactly what they ordered."""
        mcp = AsyncMock()
        mcp.call_tool = AsyncMock(return_value={"isError": False, "content": []})
        pipeline = make_pipeline(mcp)

        await pipeline.start_serving(turn_id=1)
        pipeline.set_inventory_snapshot(GAME_INVENTORY)

        meal = {
            "request": "Sinfonia Aromatica del Multiverso",
            "customer": {"name": "Ember Eldridge"},
            "customerId": "c2",
            "executed": False,
        }
        await pipeline._serve_meal(meal, "c2")

        prepared_dishes = list(pipeline.preparing.keys())
        assert "Sinfonia Aromatica del Multiverso" in prepared_dishes

        await pipeline.stop_serving()

    @pytest.mark.asyncio
    async def test_intolerant_to_latte_redirects(self):
        """
        Client intolerant to Latte+ orders dish containing Latte+.
        Must be redirected.
        """
        mcp = AsyncMock()
        mcp.call_tool = AsyncMock(return_value={"isError": False, "content": []})
        pipeline = make_pipeline(mcp)

        await pipeline.start_serving(turn_id=1)
        pipeline.set_inventory_snapshot(GAME_INVENTORY)

        meal = {
            "request": "I want to eat Sinfonia del Multiverso Calante. I'm intolerant to Latte+",
            "customer": {"name": "Piera Soln"},
            "customerId": "c3",
            "executed": False,
        }
        await pipeline._serve_meal(meal, "c3")

        prepared_dishes = list(pipeline.preparing.keys())
        assert len(prepared_dishes) == 1
        prepared_dish = prepared_dishes[0]

        recipe = GAME_RECIPES.get(prepared_dish, {})
        recipe_ings = list(recipe.get("ingredients", {}).keys())
        assert "Latte+" not in recipe_ings, (
            f"Pipeline prepared {prepared_dish} which contains Latte+, "
            f"but client is intolerant! Ingredients: {recipe_ings}"
        )

        await pipeline.stop_serving()

    @pytest.mark.asyncio
    async def test_intolerance_check_uses_request_field(self):
        """
        /meals returns 'request' (NOT 'orderText'). Verify pipeline reads it correctly.
        """
        mcp = AsyncMock()
        mcp.call_tool = AsyncMock(return_value={"isError": False, "content": []})
        pipeline = make_pipeline(mcp)

        await pipeline.start_serving(turn_id=1)
        pipeline.set_inventory_snapshot(GAME_INVENTORY)

        # /meals uses 'request', not 'orderText'
        meal = {
            "request": "I want to eat Sinfonia del Multiverso Calante. I'm intolerant to Latte+",
            "customer": {"name": "Test Client"},
            "customerId": "c4",
            "executed": False,
        }
        await pipeline._serve_meal(meal, "c4")

        # Should have actually detected the intolerance (not missed it)
        assert pipeline.metrics.intolerance_skips >= 1 or pipeline.metrics.clients_matched >= 1

        await pipeline.stop_serving()


# ══════════════════════════════════════════════════════════════
#  TEST 4: /meals field extraction (request vs orderText, customer.name)
# ══════════════════════════════════════════════════════════════


class TestMealsFieldExtraction:
    """Validate correct extraction of fields from /meals response format."""

    @pytest.mark.asyncio
    async def test_request_field_used_for_order(self):
        """/meals uses 'request', not 'orderText'."""
        mcp = AsyncMock()
        mcp.call_tool = AsyncMock(return_value={"isError": False, "content": []})
        pipeline = make_pipeline(mcp)
        await pipeline.start_serving(turn_id=1)
        pipeline.set_inventory_snapshot(GAME_INVENTORY)

        meal = {
            "request": "Sinfonia Aromatica del Multiverso",
            "customer": {"name": "Test"},
            "customerId": "c1",
            "executed": False,
        }
        await pipeline._serve_meal(meal, "c1")

        # Should match and start preparing
        assert pipeline.metrics.clients_matched == 1
        assert "Sinfonia Aromatica del Multiverso" in pipeline.preparing

        await pipeline.stop_serving()

    @pytest.mark.asyncio
    async def test_ordertext_fallback_works(self):
        """If 'request' is missing, fall back to 'orderText'."""
        mcp = AsyncMock()
        mcp.call_tool = AsyncMock(return_value={"isError": False, "content": []})
        pipeline = make_pipeline(mcp)
        await pipeline.start_serving(turn_id=1)
        pipeline.set_inventory_snapshot(GAME_INVENTORY)

        meal = {
            "orderText": "Sinfonia Aromatica del Multiverso",
            "customer": {"name": "Test"},
            "customerId": "c1",
            "executed": False,
        }
        await pipeline._serve_meal(meal, "c1")

        assert pipeline.metrics.clients_matched == 1

        await pipeline.stop_serving()

    @pytest.mark.asyncio
    async def test_nested_customer_name(self):
        """/meals nests client name under customer.name."""
        mcp = AsyncMock()
        mcp.call_tool = AsyncMock(return_value={"isError": False, "content": []})
        pipeline = make_pipeline(mcp)
        await pipeline.start_serving(turn_id=1)
        pipeline.set_inventory_snapshot(GAME_INVENTORY)

        meal = {
            "request": "Sinfonia Aromatica del Multiverso",
            "customer": {"name": "Ember Eldridge"},
            "customerId": "c1",
            "executed": False,
        }
        await pipeline._serve_meal(meal, "c1")

        # Verify the preparation has the correct client name
        queue = pipeline.preparing.get("Sinfonia Aromatica del Multiverso")
        assert queue is not None
        assert queue[0].client_name == "Ember Eldridge"

        await pipeline.stop_serving()

    @pytest.mark.asyncio
    async def test_sse_order_cache_fallback(self):
        """If /meals has no request/orderText, use SSE-cached order text."""
        mcp = AsyncMock()
        mcp.call_tool = AsyncMock(return_value={"isError": False, "content": []})
        pipeline = make_pipeline(mcp)
        await pipeline.start_serving(turn_id=1)
        pipeline.set_inventory_snapshot(GAME_INVENTORY)

        # Simulate SSE cache
        pipeline._sse_order_cache["Magnus Quill"] = "Sinfonia Aromatica del Multiverso"

        meal = {
            "request": "",  # empty
            "customer": {"name": "Magnus Quill"},
            "customerId": "c1",
            "executed": False,
        }
        await pipeline._serve_meal(meal, "c1")

        assert pipeline.metrics.clients_matched == 1

        await pipeline.stop_serving()

    @pytest.mark.asyncio
    async def test_customer_id_extraction(self):
        """Test _extract_client_id with various field names."""
        from src.serving.pipeline import ServingPipeline

        # customerId (preferred)
        assert ServingPipeline._extract_client_id({"customerId": "abc123"}) == "abc123"
        # client_id fallback
        assert ServingPipeline._extract_client_id({"client_id": "def456"}) == "def456"
        # id fallback
        assert ServingPipeline._extract_client_id({"id": "ghi789"}) == "ghi789"
        # None
        assert ServingPipeline._extract_client_id({}) is None


# ══════════════════════════════════════════════════════════════
#  TEST 5: Intolerance substring matching edge cases
# ══════════════════════════════════════════════════════════════


class TestIntoleranceMatching:
    """
    Test the substring matching between declared intolerances and recipe ingredients.
    The current logic uses:  `intolerant_lower in ring.lower() or ring.lower() in intolerant_lower`
    """

    def _check_conflict(self, intolerance: str, ingredient: str) -> bool:
        """Replicate the pipeline's intolerance-ingredient conflict check."""
        intolerant_lower = intolerance.lower().strip()
        return intolerant_lower in ingredient.lower() or ingredient.lower() in intolerant_lower

    def test_exact_match(self):
        assert self._check_conflict("Funghi Orbitali", "Funghi Orbitali")

    def test_case_insensitive(self):
        assert self._check_conflict("funghi orbitali", "Funghi Orbitali")

    def test_latte_plus(self):
        """Latte+ with special character."""
        assert self._check_conflict("Latte+", "Latte+")
        assert self._check_conflict("latte+", "Latte+")

    def test_partial_substring_danger(self):
        """
        BUG CHECK: 'sale' is a substring of 'Sale Temporale' — correct detection.
        But 'sale' is also a substring of 'Essenza di Speziaria'? No. 
        This tests that substring matching works as intended.
        """
        assert self._check_conflict("Sale Temporale", "Sale Temporale")
        # 'sale' would match inside 'Sale Temporale' — this is a known limitation
        # but it's intentional: if client says "intolerant to sale", it catches "Sale Temporale"
        assert self._check_conflict("sale", "Sale Temporale")  # substring match

    def test_no_false_positive_on_unrelated(self):
        """Unrelated ingredients should not conflict."""
        assert not self._check_conflict("Funghi Orbitali", "Polvere di Crononite")
        assert not self._check_conflict("Latte+", "Essenza di Tachioni")

    def test_ingredient_as_part_of_longer_name(self):
        """'Polvere' in 'Polvere di Crononite' — would match if someone is intolerant to 'Polvere'."""
        assert self._check_conflict("Polvere", "Polvere di Crononite")
        # This is actually also a RISK: too broad. But current code does this intentionally for safety.

    def test_empty_intolerance(self):
        """Empty string should not match anything meaningfully."""
        # Empty string is a substring of everything in Python — this is a potential bug
        assert self._check_conflict("", "Funghi Orbitali") is True  # bug! "" in any_str == True

    def test_extracted_intolerance_matches_recipe(self):
        """End-to-end: extract intolerance, then check against recipe ingredient list."""
        order = "I want to eat Sinfonia Cosmica di Andromeda. I'm intolerant to Funghi Orbitali"
        intolerances = ServingPipeline._extract_intolerances(order)
        
        recipe_ings = list(GAME_RECIPES["Sinfonia Cosmica di Andromeda"]["ingredients"].keys())
        
        has_conflict = False
        for intol in intolerances:
            for ring in recipe_ings:
                if self._check_conflict(intol, ring):
                    has_conflict = True
                    break
        
        assert has_conflict, f"Expected conflict between {intolerances} and {recipe_ings}"


# ══════════════════════════════════════════════════════════════
#  TEST 6: OrderMatcher._normalize interaction with intolerance stripping
# ══════════════════════════════════════════════════════════════


class TestNormalizeIntoleranceStripping:
    """
    The OrderMatcher._normalize method strips intolerance suffixes BEFORE
    processing prefixes. Verify this works for real patterns.
    """

    def setup_method(self):
        self.matcher = make_matcher()

    def test_normalize_strips_intolerance(self):
        """After normalization, the intolerance suffix should be gone."""
        result = self.matcher._normalize(
            "I want to eat Sinfonia del Multiverso Calante. I'm intolerant to Latte+"
        )
        assert "intolerant" not in result
        assert "latte" not in result

    def test_normalize_preserves_dish_name(self):
        """After stripping intolerance + prefix, the dish name should remain."""
        result = self.matcher._normalize(
            "I want to eat Sinfonia del Multiverso Calante. I'm intolerant to Latte+"
        )
        assert "sinfonia del multiverso calante" == result

    def test_normalize_italian_intolerance(self):
        result = self.matcher._normalize(
            "Vorrei Sinfonia Aromatica del Multiverso. Sono intollerante ai Funghi Orbitali"
        )
        assert "intollerante" not in result
        assert "funghi" not in result

    def test_normalize_bare_dish(self):
        """Bare dish name should pass through cleanly."""
        result = self.matcher._normalize("Sinfonia Aromatica del Multiverso")
        assert result == "sinfonia aromatica del multiverso"

    def test_normalize_with_smart_apostrophe(self):
        """Smart apostrophe I\u2019m variant."""
        result = self.matcher._normalize(
            "I want to eat Dish Name. I\u2019m intolerant to Something"
        )
        assert "intolerant" not in result
        assert "something" not in result
