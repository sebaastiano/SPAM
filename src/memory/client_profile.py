"""
SPAM! — Client Profile Memory
===============================
Two-level client profiling: GlobalClientLibrary + ZoneClientLibrary.
Includes Bayesian intolerance detection.
"""

import logging
from dataclasses import dataclass, field

from src.config import KNOWN_ARCHETYPES, ZONE_TARGET_ARCHETYPES

logger = logging.getLogger("spam.memory.client_profile")


@dataclass
class ClientProfile:
    """Profile of a single client interaction."""
    archetype: str
    order_text: str
    matched_dish: str | None = None
    served: bool = False
    revenue: float = 0.0
    intolerance_triggered: bool = False
    prep_time_ms: int = 0
    turn_id: int = 0
    timestamp: str = ""


@dataclass
class ArchetypeStats:
    """Aggregate statistics for one archetype."""
    total_visits: int = 0
    total_served: int = 0
    total_revenue: float = 0.0
    total_failures: int = 0
    avg_revenue_per_serve: float = 0.0
    intolerance_rate: float = 0.0
    common_orders: dict = field(default_factory=dict)  # order_text → count
    preferred_dishes: dict = field(default_factory=dict)  # dish_name → count

    def update(self, profile: ClientProfile):
        self.total_visits += 1
        if profile.served:
            self.total_served += 1
            self.total_revenue += profile.revenue
            self.avg_revenue_per_serve = (
                self.total_revenue / max(self.total_served, 1)
            )
            if profile.matched_dish:
                self.preferred_dishes[profile.matched_dish] = (
                    self.preferred_dishes.get(profile.matched_dish, 0) + 1
                )
        if profile.intolerance_triggered:
            self.total_failures += 1
        self.intolerance_rate = self.total_failures / max(self.total_visits, 1)

        # Track order patterns
        self.common_orders[profile.order_text] = (
            self.common_orders.get(profile.order_text, 0) + 1
        )


class IntoleranceDetector:
    """
    Bayesian intolerance detection.

    When a serve fails (revenue = 0 + reputation loss), we know ONE of the
    ingredients in the served dish triggered an intolerance. We track suspicion
    scores per archetype×ingredient pair using Beta distributions.
    """

    def __init__(self):
        # suspicion[archetype][ingredient] = (alpha, beta)
        # alpha = evidence of danger, beta = evidence of safety
        self.suspicion: dict[str, dict[str, tuple[float, float]]] = {
            arch: {} for arch in KNOWN_ARCHETYPES
        }

    def record_success(self, archetype: str, ingredients: list[str]):
        """Dish served successfully — lower suspicion for all ingredients."""
        if archetype not in self.suspicion:
            self.suspicion[archetype] = {}
        for ing in ingredients:
            a, b = self.suspicion[archetype].get(ing, (1.0, 1.0))
            self.suspicion[archetype][ing] = (a, b + 1)

    def record_failure(self, archetype: str, ingredients: list[str]):
        """Dish serve failed — raise suspicion for all ingredients."""
        if archetype not in self.suspicion:
            self.suspicion[archetype] = {}
        for ing in ingredients:
            a, b = self.suspicion[archetype].get(ing, (1.0, 1.0))
            self.suspicion[archetype][ing] = (a + 1, b)

    def is_safe(self, archetype: str, ingredient: str, threshold: float = 0.3) -> bool:
        """Is this ingredient safe for this archetype? (Bayesian estimate)"""
        if archetype not in self.suspicion:
            return True  # unknown archetype = assume safe
        a, b = self.suspicion[archetype].get(ingredient, (1.0, 1.0))
        p_intolerant = a / (a + b)
        return p_intolerant < threshold

    def is_recipe_safe(self, archetype: str, ingredients: list[str], threshold: float = 0.3) -> bool:
        """Are ALL ingredients in a recipe safe for this archetype?"""
        return all(self.is_safe(archetype, ing, threshold) for ing in ingredients)

    def get_danger_score(self, archetype: str, ingredient: str) -> float:
        """Get the intolerance probability for an ingredient+archetype pair."""
        if archetype not in self.suspicion:
            return 0.0
        a, b = self.suspicion[archetype].get(ingredient, (1.0, 1.0))
        return a / (a + b)


class GlobalClientLibrary:
    """
    Cross-turn, cross-zone aggregate client knowledge.

    Tracks per-archetype statistics and intolerance patterns
    across all turns and zones.
    """

    def __init__(self):
        self.archetype_stats: dict[str, ArchetypeStats] = {
            arch: ArchetypeStats() for arch in KNOWN_ARCHETYPES
        }
        self.intolerance_detector = IntoleranceDetector()
        self.order_to_dish_cache: dict[str, str] = {}
        self.all_profiles: list[ClientProfile] = []

    def update_from_profile(self, profile: ClientProfile):
        """Integrate a single client interaction."""
        self.all_profiles.append(profile)

        # Update archetype stats
        if profile.archetype in self.archetype_stats:
            self.archetype_stats[profile.archetype].update(profile)
        else:
            self.archetype_stats[profile.archetype] = ArchetypeStats()
            self.archetype_stats[profile.archetype].update(profile)

        # Cache successful order→dish mappings
        if profile.served and profile.matched_dish:
            normalized = profile.order_text.lower().strip()
            self.order_to_dish_cache[normalized] = profile.matched_dish

    def update_intolerance(
        self,
        archetype: str,
        ingredients: list[str],
        success: bool,
    ):
        """Update intolerance model from serve result."""
        if success:
            self.intolerance_detector.record_success(archetype, ingredients)
        else:
            self.intolerance_detector.record_failure(archetype, ingredients)

    def get_cached_dish(self, order_text: str) -> str | None:
        """Look up a previously successful order→dish mapping."""
        return self.order_to_dish_cache.get(order_text.lower().strip())


class ZoneClientLibrary:
    """Zone-specific client profile subset."""

    def __init__(self, zone: str):
        self.zone = zone
        self.target_archetypes = ZONE_TARGET_ARCHETYPES.get(zone, [])

    def get_relevant_stats(
        self, global_lib: GlobalClientLibrary
    ) -> dict[str, ArchetypeStats]:
        """Get stats for this zone's target archetypes only."""
        return {
            arch: global_lib.archetype_stats.get(arch, ArchetypeStats())
            for arch in self.target_archetypes
        }

    def recommend_menu(
        self,
        inventory: dict[str, int],
        recipes: list[dict],
        global_lib: GlobalClientLibrary,
    ) -> list[dict]:
        """
        Select recipes that best serve this zone's target archetypes.

        Returns recipes sorted by composite score:
        archetype_fit × intolerance_safety × throughput_value
        """
        scored = []
        for recipe in recipes:
            # Check ingredient availability
            recipe_ings = recipe.get("ingredients", {})
            if not all(
                inventory.get(ing, 0) >= qty
                for ing, qty in recipe_ings.items()
            ):
                continue

            # Archetype fit score
            archetype_fit = self._score_archetype_fit(recipe)

            # Intolerance safety score
            safety = 1.0
            for arch in self.target_archetypes:
                ings = list(recipe_ings.keys())
                if not global_lib.intolerance_detector.is_recipe_safe(arch, ings):
                    safety *= 0.3  # penalize risky recipes

            # Throughput value (faster = better)
            prep_time = recipe.get("prep_time", 5.0)
            throughput = 1.0 / max(prep_time, 0.1)

            score = archetype_fit * safety * throughput
            scored.append({"recipe": recipe, "score": score})

        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored

    def _score_archetype_fit(self, recipe: dict) -> float:
        """Score how well a recipe fits this zone's target archetypes."""
        prestige = recipe.get("prestige", 50)

        from src.config import ZONE_PRESTIGE_RANGE
        pmin, pmax = ZONE_PRESTIGE_RANGE.get(self.zone, (0, 100))

        if pmin <= prestige <= pmax:
            return 1.0
        elif prestige < pmin:
            return max(0.1, 1.0 - (pmin - prestige) / 50)
        else:
            return max(0.1, 1.0 - (prestige - pmax) / 50)
