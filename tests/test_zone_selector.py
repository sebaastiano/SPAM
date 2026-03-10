"""Tests for embedding-aware zone selection."""
import numpy as np
import pytest

from src.decision.zone_selector import (
    select_zone,
    count_active_competitors,
    _compute_gap_score,
    _compute_trajectory_penalty,
    _compute_demand_viability,
    _ZONE_CENTROIDS,
)


# ── count_active_competitors ──

def test_count_zero_when_empty():
    assert count_active_competitors({}) == 0


def test_count_connected():
    briefings = {
        1: {"is_connected": True, "menu_size": 3},
        2: {"is_connected": True, "menu_size": 5},
        3: {"is_connected": False, "menu_size": 0},
    }
    assert count_active_competitors(briefings) == 2


def test_count_fallback_to_all_states():
    briefings = {
        1: {"is_connected": False, "menu_size": 0},
    }
    all_states = {
        10: {"menu": {"items": [{"name": "x", "price": 50}]}, "isOpen": True},
    }
    assert count_active_competitors(briefings, all_states) == 1


# ── select_zone basics ──

def test_no_competitors_gives_diversified():
    zone = select_zone(
        balance=5000, inventory={}, reputation=80,
        recipes=[{"name": "x", "prestige": 50, "ingredients": {}, "prep_time": 3}],
        competitor_clusters={}, competitor_briefings={},
    )
    assert zone == "DIVERSIFIED"


def test_with_competitors_returns_valid_zone():
    briefings = {
        1: {"is_connected": True, "menu_size": 3, "menu_price_avg": 200,
            "strategy": "PREMIUM_MONOPOLIST"},
        2: {"is_connected": True, "menu_size": 5, "menu_price_avg": 50,
            "strategy": "BUDGET_OPPORTUNIST"},
    }
    recipes = [
        {"name": "a", "prestige": 50, "ingredients": {"X": 1}, "prep_time": 3},
        {"name": "b", "prestige": 80, "ingredients": {"Y": 1}, "prep_time": 4},
    ]
    zone = select_zone(
        balance=5000, inventory={"X": 5, "Y": 5}, reputation=80,
        recipes=recipes,
        competitor_clusters={}, competitor_briefings=briefings,
    )
    from src.config import ZONES
    assert zone in ZONES


# ── gap score ──

def test_gap_score_neutral_when_no_features():
    assert _compute_gap_score("DIVERSIFIED", None) == 0.5
    assert _compute_gap_score("DIVERSIFIED", {}) == 0.5


def test_gap_score_low_when_competitor_near_centroid():
    centroid = _ZONE_CENTROIDS["PREMIUM_MONOPOLIST"].copy()
    # Competitor is *exactly* at the centroid → gap ≈ 0
    features = {1: centroid}
    gap = _compute_gap_score("PREMIUM_MONOPOLIST", features)
    assert gap < 0.1, f"Expected gap < 0.1, got {gap}"


def test_gap_score_high_when_competitor_far():
    centroid = _ZONE_CENTROIDS["PREMIUM_MONOPOLIST"].copy()
    far_away = centroid + 20  # very far in every dimension
    features = {1: far_away}
    gap = _compute_gap_score("PREMIUM_MONOPOLIST", features)
    assert gap > 0.8, f"Expected gap > 0.8, got {gap}"


# ── trajectory penalty ──

def test_trajectory_penalty_zero_when_no_predictor():
    assert _compute_trajectory_penalty("DIVERSIFIED", None) == 0.0


# ── demand viability ──

def test_demand_viability_neutral_when_no_forecast():
    assert _compute_demand_viability("DIVERSIFIED", [], None) == 0.5


def test_demand_viability_high_when_uncontested():
    recipes = [
        {"name": "a", "prestige": 50, "ingredients": {"X": 1, "Y": 1}},
    ]
    # Zero demand for all ingredients → uncontested → score ≈ 1.0
    demand = {"X": 0, "Y": 0}
    score = _compute_demand_viability("DIVERSIFIED", recipes, demand)
    assert score > 0.9, f"Expected > 0.9, got {score}"


def test_demand_viability_low_when_contested():
    recipes = [
        {"name": "a", "prestige": 50, "ingredients": {"X": 1, "Y": 1}},
    ]
    # Very high demand → heavily contested → score ≈ 0
    demand = {"X": 20, "Y": 20}
    score = _compute_demand_viability("DIVERSIFIED", recipes, demand)
    assert score < 0.1, f"Expected < 0.1, got {score}"


# ── Integration: gap score influences zone choice ──

def test_gap_score_pushes_away_from_crowded_zone():
    """When competitors cluster around PREMIUM, the zone selector should
    prefer a different zone thanks to the gap score."""
    briefings = {
        1: {"is_connected": True, "menu_size": 3, "menu_price_avg": 200,
            "strategy": "PREMIUM_MONOPOLIST"},
        2: {"is_connected": True, "menu_size": 3, "menu_price_avg": 250,
            "strategy": "PREMIUM_MONOPOLIST"},
        3: {"is_connected": True, "menu_size": 4, "menu_price_avg": 180,
            "strategy": "STABLE_SPECIALIST"},
    }
    # All competitors near PREMIUM centroid
    centroid = _ZONE_CENTROIDS["PREMIUM_MONOPOLIST"]
    features = {
        1: centroid + np.random.randn(14) * 0.1,
        2: centroid + np.random.randn(14) * 0.1,
        3: centroid + np.random.randn(14) * 0.2,
    }
    recipes = [
        {"name": f"r{i}", "prestige": p, "ingredients": {"X": 1}, "prep_time": 3}
        for i, p in enumerate([20, 40, 50, 60, 70, 80, 90])
    ]
    zone = select_zone(
        balance=5000, inventory={"X": 50}, reputation=80,
        recipes=recipes,
        competitor_clusters={}, competitor_briefings=briefings,
        features=features,
    )
    # Should NOT be PREMIUM because it's crowded
    assert zone != "PREMIUM_MONOPOLIST", \
        f"Expected non-PREMIUM zone when competitors cluster there, got {zone}"
