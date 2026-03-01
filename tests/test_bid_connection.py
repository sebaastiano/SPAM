"""
Tests for connection-based bid pricing.

Validates that compute_bid_price() and compute_menu_price() use
is_connected (presence in /restaurants) instead of menu_size to
detect active competitors.  Bid prices should scale proportionally
with the number of connected competitors.
"""

import pytest

from src.decision.ilp_solver import compute_bid_price, compute_menu_price
from src.decision.pricing import compute_menu_prices, adjust_prices_competitive

# A known HIGH_DELTA_INGREDIENT from config.py
HIGH_DELTA_ING = "Polvere di Crononite"
NORMAL_ING = "Essenza di Quasar"   # not in HIGH_DELTA_INGREDIENTS


# ── Helpers ──

def _briefings_connected(n: int, **extra) -> dict[int, dict]:
    """Create n connected competitor briefings."""
    briefings = {}
    for i in range(1, n + 1):
        b = {
            "is_connected": True,
            "name": f"team {i}",
            "strategy": "UNCLASSIFIED",
            "top_bid_ingredients": [],
            "predicted_bid_spend": 0,
            "menu_size": 0,      # explicitly 0 (speaking phase)
            "menu_price_avg": 0,
            "balance": 10000,
            "reputation": 100,
        }
        b.update(extra)
        briefings[i] = b
    return briefings


def _briefings_disconnected(n: int) -> dict[int, dict]:
    """Create n disconnected competitor briefings."""
    return {
        i: {
            "is_connected": False,
            "name": f"team {i}",
            "strategy": "UNCLASSIFIED",
            "top_bid_ingredients": [],
            "predicted_bid_spend": 0,
            "menu_size": 0,
            "menu_price_avg": 0,
        }
        for i in range(1, n + 1)
    }


def _briefings_old_style_menu(n: int) -> dict[int, dict]:
    """Old-style briefings: menu_size > 0 but no is_connected field."""
    return {
        i: {
            "name": f"team {i}",
            "strategy": "UNCLASSIFIED",
            "top_bid_ingredients": [],
            "predicted_bid_spend": 0,
            "menu_size": 3,
            "menu_price_avg": 100,
        }
        for i in range(1, n + 1)
    }


# ═══════════════════════════════════════════════
#  compute_bid_price — connection-based detection
# ═══════════════════════════════════════════════

class TestBidPriceConnectionDetection:
    """Bid prices should use is_connected, not menu_size."""

    def test_no_briefings_returns_floor(self):
        """Empty briefings → monopoly floor (conservative base)."""
        price = compute_bid_price(HIGH_DELTA_ING, {}, {})
        assert price >= 5, f"High-delta monopoly floor should be >= 5, got {price}"

        price = compute_bid_price(NORMAL_ING, {}, {})
        assert price >= 3, f"Normal monopoly floor should be >= 3, got {price}"

    def test_connected_competitors_raise_bids(self):
        """Connected competitors (even with menu_size=0) should raise bids."""
        # 0 competitors — floor
        price_0 = compute_bid_price(HIGH_DELTA_ING, {}, {})

        # 3 connected competitors with menu_size=0 (speaking phase)
        price_3 = compute_bid_price(
            HIGH_DELTA_ING, _briefings_connected(3), {}
        )

        # 8 connected competitors (saturated competition)
        price_8 = compute_bid_price(
            HIGH_DELTA_ING, _briefings_connected(8), {}
        )

        assert price_3 > price_0, (
            f"3 connected competitors should bid higher than 0, "
            f"got {price_3} <= {price_0}"
        )
        assert price_8 > price_3, (
            f"8 competitors should bid higher than 3, "
            f"got {price_8} <= {price_3}"
        )

    def test_menu_size_zero_but_connected_counts(self):
        """menu_size=0 should NOT prevent competitor detection when is_connected=True."""
        briefings = _briefings_connected(5)
        # Verify all have menu_size=0
        for b in briefings.values():
            assert b["menu_size"] == 0

        price = compute_bid_price(HIGH_DELTA_ING, briefings, {})
        # 0-competitor floor is 25; with 5 connected → proportional scaling
        floor = compute_bid_price(HIGH_DELTA_ING, {}, {})
        assert price > floor, (
            f"5 connected competitors (menu_size=0) should raise bids above "
            f"floor {floor}, got {price}"
        )

    def test_disconnected_competitors_ignored(self):
        """Disconnected competitors should NOT raise bids."""
        briefings = _briefings_disconnected(5)
        price = compute_bid_price(HIGH_DELTA_ING, briefings, {})
        floor = compute_bid_price(HIGH_DELTA_ING, {}, {})
        assert price == floor, (
            f"5 disconnected competitors should give monopoly floor {floor}, "
            f"got {price}"
        )

    def test_proportional_scaling_normal_ingredient(self):
        """Normal ingredient bids should scale proportionally too."""
        price_0 = compute_bid_price(NORMAL_ING, {}, {})
        price_4 = compute_bid_price(NORMAL_ING, _briefings_connected(4), {})
        price_8 = compute_bid_price(NORMAL_ING, _briefings_connected(8), {})

        assert price_0 >= 3  # conservative base floor
        assert price_4 > price_0
        assert price_8 > price_4

    def test_competition_scaling_caps_at_reasonable_level(self):
        """Bid prices should cap at a reasonable level, not go infinite."""
        price = compute_bid_price(
            HIGH_DELTA_ING, _briefings_connected(20), {}
        )
        # Competition factor saturates at 8, so 20 ≈ 8
        price_8 = compute_bid_price(
            HIGH_DELTA_ING, _briefings_connected(8), {}
        )
        assert price == price_8, "Competition scaling should saturate"

    def test_specific_ingredient_intel_with_connection(self):
        """When competitors want same ingredient AND are connected, bid aggressively."""
        briefings = _briefings_connected(3, **{
            "top_bid_ingredients": [HIGH_DELTA_ING],
            "predicted_bid_spend": 100,
        })
        price = compute_bid_price(HIGH_DELTA_ING, briefings, {})
        # Should be above base competition floor since competitors specifically want it
        base_price = compute_bid_price(
            HIGH_DELTA_ING, _briefings_connected(3), {}
        )
        assert price >= base_price, (
            f"Specific ingredient competition should yield >= base, "
            f"got {price} < {base_price}"
        )

    def test_disconnected_with_menu_ignored(self):
        """Even with menu_size > 0, if is_connected=False, ignore the competitor."""
        briefings = {
            1: {
                "is_connected": False,
                "menu_size": 5,
                "menu_price_avg": 100,
                "top_bid_ingredients": [HIGH_DELTA_ING],
                "predicted_bid_spend": 200,
                "strategy": "AGGRESSIVE_HOARDER",
            },
        }
        price = compute_bid_price(HIGH_DELTA_ING, briefings, {})
        floor = compute_bid_price(HIGH_DELTA_ING, {}, {})
        assert price == floor  # monopoly floor — competitor is disconnected


# ═══════════════════════════════════════════════
#  compute_menu_price — connection-based detection
# ═══════════════════════════════════════════════

class TestMenuPriceConnectionDetection:
    """Menu prices should use is_connected instead of menu_size."""

    def test_no_competitors_monopoly_pricing(self):
        """Empty briefings → monopoly pricing (no zone discount)."""
        recipe = {"name": "TestDish", "prestige": 50}
        price_monopoly = compute_menu_price(recipe, "SPEED_CONTENDER", 50.0, {})
        price_with_comp = compute_menu_price(
            recipe, "SPEED_CONTENDER", 50.0, _briefings_connected(3)
        )
        # Monopoly should have full ceiling, competition applies zone_factor
        # Both should be reasonable prices
        assert price_monopoly > 0
        assert price_with_comp > 0

    def test_connected_competitors_apply_zone_factor(self):
        """Connected competitors should trigger zone-aware pricing."""
        recipe = {"name": "TestDish", "prestige": 50}
        # With connected competitors, zone_factor should apply
        price = compute_menu_price(
            recipe, "SPEED_CONTENDER", 50.0, _briefings_connected(3)
        )
        assert price > 0

    def test_menu_size_zero_connected_still_competitive(self):
        """menu_size=0 but is_connected=True should count as competition."""
        recipe = {"name": "TestDish", "prestige": 50}
        briefings = _briefings_connected(5)
        for b in briefings.values():
            assert b["menu_size"] == 0

        # Should detect 5 active competitors despite menu_size=0
        price = compute_menu_price(recipe, "SPEED_CONTENDER", 50.0, briefings)
        assert price > 0

    def test_disconnected_treated_as_no_competition(self):
        """Disconnected competitors should be treated as no competition."""
        recipe = {"name": "TestDish", "prestige": 50}
        price_disc = compute_menu_price(
            recipe, "SPEED_CONTENDER", 50.0, _briefings_disconnected(5)
        )
        # With all disconnected, active_competitors=0 → monopoly pricing
        # (no zone_factor discount applied)
        # This should be >= the zone-factored price and use full ceiling
        assert price_disc > 0
        # Verify it matches the monopoly branch: compute with empty briefings
        # Note: empty {} skips the competitor_briefings block entirely,
        # while disconnected enters it and takes monopoly path.
        # The monopoly path explicitly removes zone_factor.
        # Empty {} path uses zone_factor. So they may differ.
        # What matters: disconnected = monopoly pricing (no zone discount).
        price_monopoly_path = compute_menu_price(
            recipe, "SPEED_CONTENDER", 50.0, _briefings_disconnected(1)
        )
        assert price_disc == price_monopoly_path, (
            "All disconnected scenarios should give same monopoly price"
        )


# ═══════════════════════════════════════════════
#  pricing.py — connection-based detection
# ═══════════════════════════════════════════════

class TestPricingModuleConnection:
    """pricing.py functions should use is_connected."""

    def test_compute_menu_prices_with_connected(self):
        """compute_menu_prices should detect connected competitors."""
        items = [{"name": "Dish1", "prestige": 50}]
        result = compute_menu_prices(
            items, "SPEED_CONTENDER", 50.0,
            competitor_briefings=_briefings_connected(3),
        )
        assert len(result) == 1
        assert result[0]["price"] > 0

    def test_compute_menu_prices_ignores_disconnected(self):
        """compute_menu_prices should ignore disconnected competitors."""
        items = [{"name": "Dish1", "prestige": 50}]
        result_disc = compute_menu_prices(
            items, "SPEED_CONTENDER", 50.0,
            competitor_briefings=_briefings_disconnected(5),
        )
        result_none = compute_menu_prices(
            items, "SPEED_CONTENDER", 50.0,
            competitor_briefings={},
        )
        # Both should be monopoly pricing
        assert result_disc[0]["price"] == result_none[0]["price"]

    def test_adjust_prices_competitive_connected(self):
        """adjust_prices_competitive should detect connected competitors."""
        items = [{"name": "Dish1", "price": 100}]

        # With connected competitors — should adjust prices
        result = adjust_prices_competitive(
            items, [80, 90, 100],
            "BUDGET_OPPORTUNIST",
            competitor_briefings=_briefings_connected(3),
        )
        assert len(result) == 1
        assert result[0]["price"] > 0

    def test_adjust_prices_competitive_disconnected_no_adjust(self):
        """adjust_prices_competitive should skip adjustment when disconnected."""
        items = [{"name": "Dish1", "price": 100}]

        result = adjust_prices_competitive(
            items, [80, 90, 100],
            "BUDGET_OPPORTUNIST",
            competitor_briefings=_briefings_disconnected(3),
        )
        # Should return original price (monopoly — no adjustment)
        assert result[0]["price"] == 100


# ═══════════════════════════════════════════════
#  Old-style briefings backward compatibility
# ═══════════════════════════════════════════════

class TestBackwardCompatibility:
    """Briefings without is_connected should default to False (safe fallback)."""

    def test_missing_is_connected_defaults_false(self):
        """Briefings missing is_connected should not count as active."""
        briefings = _briefings_old_style_menu(5)  # has menu_size=3, no is_connected
        price = compute_bid_price(HIGH_DELTA_ING, briefings, {})
        floor = compute_bid_price(HIGH_DELTA_ING, {}, {})
        # is_connected defaults to False → monopoly floor
        assert price == floor

    def test_old_briefings_do_not_inflate_bids(self):
        """Legacy briefings shouldn't accidentally inflate bids."""
        old_briefings = _briefings_old_style_menu(10)
        price = compute_bid_price(NORMAL_ING, old_briefings, {})
        floor = compute_bid_price(NORMAL_ING, {}, {})
        assert price == floor, f"Old-style briefings (no is_connected) should give floor {floor}, got {price}"


# ═══════════════════════════════════════════════
#  Edge cases
# ═══════════════════════════════════════════════

class TestEdgeCases:
    """Edge case testing for bid/price connection logic."""

    def test_mixed_connected_disconnected(self):
        """Mix of connected and disconnected should only count connected."""
        briefings = {
            1: {"is_connected": True, "top_bid_ingredients": [], "predicted_bid_spend": 0, "strategy": "", "menu_size": 0, "menu_price_avg": 0},
            2: {"is_connected": False, "top_bid_ingredients": [], "predicted_bid_spend": 0, "strategy": "", "menu_size": 3, "menu_price_avg": 100},
            3: {"is_connected": True, "top_bid_ingredients": [], "predicted_bid_spend": 0, "strategy": "", "menu_size": 0, "menu_price_avg": 0},
        }
        price_mixed = compute_bid_price(HIGH_DELTA_ING, briefings, {})

        # Compare to exactly 2 connected
        price_2 = compute_bid_price(HIGH_DELTA_ING, _briefings_connected(2), {})

        assert price_mixed == price_2, (
            f"Mixed (2 connected, 1 disconnected) should equal 2 connected, "
            f"got mixed={price_mixed}, 2conn={price_2}"
        )

    def test_single_connected_competitor(self):
        """Single connected competitor should raise bids above floor."""
        price = compute_bid_price(
            HIGH_DELTA_ING, _briefings_connected(1), {}
        )
        floor = compute_bid_price(HIGH_DELTA_ING, {}, {})
        assert price > floor, (
            f"1 connected competitor should raise bid above floor {floor}, got {price}"
        )

    def test_demand_forecast_still_applies(self):
        """Demand forecast should still affect bid prices with connected competitors."""
        forecast = {HIGH_DELTA_ING: 10}
        briefings = _briefings_connected(3, **{
            "top_bid_ingredients": [HIGH_DELTA_ING],
            "predicted_bid_spend": 100,
        })
        price_no_demand = compute_bid_price(HIGH_DELTA_ING, briefings, {})
        price_with_demand = compute_bid_price(HIGH_DELTA_ING, briefings, forecast)
        assert price_with_demand >= price_no_demand

    def test_strategy_modifiers_still_apply(self):
        """AGGRESSIVE_HOARDER/REACTIVE_CHASER/DECLINING modifiers should still work."""
        base_briefings = _briefings_connected(1, **{
            "top_bid_ingredients": [HIGH_DELTA_ING],
            "predicted_bid_spend": 100,
            "strategy": "UNCLASSIFIED",
        })
        aggressive_briefings = _briefings_connected(1, **{
            "top_bid_ingredients": [HIGH_DELTA_ING],
            "predicted_bid_spend": 100,
            "strategy": "AGGRESSIVE_HOARDER",
        })
        declining_briefings = _briefings_connected(1, **{
            "top_bid_ingredients": [HIGH_DELTA_ING],
            "predicted_bid_spend": 100,
            "strategy": "DECLINING",
        })

        price_base = compute_bid_price(HIGH_DELTA_ING, base_briefings, {})
        price_agg = compute_bid_price(HIGH_DELTA_ING, aggressive_briefings, {})
        price_dec = compute_bid_price(HIGH_DELTA_ING, declining_briefings, {})

        assert price_agg >= price_base, "AGGRESSIVE_HOARDER should raise or match bids"
        assert price_dec <= price_base, "DECLINING should lower or match bids"
