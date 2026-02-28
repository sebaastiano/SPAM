"""
Client profiling — two-level memory (Global + Zone) with Bayesian
intolerance detection.
"""

from __future__ import annotations

from typing import Any

from src.config import KNOWN_ARCHETYPES, ZONES
from src.models import ArchetypeStats, ClientProfile, Recipe


# ── Intolerance Detector ─────────────────────────────────────────


class IntoleranceDetector:
    """Bayesian intolerance detection.

    When a serve fails (revenue=0 + reputation loss), one of the dish's
    ingredients triggered an intolerance.  We track suspicion scores per
    ``archetype × ingredient`` pair as Beta(α, β) distributions.
    """

    def __init__(self) -> None:
        # suspicion[archetype][ingredient] = (alpha, beta)
        self.suspicion: dict[str, dict[str, tuple[float, float]]] = {}

    def record_success(self, archetype: str, ingredients: list[str]) -> None:
        """Dish served OK — lower suspicion for all ingredients."""
        for ing in ingredients:
            a, b = self._get(archetype, ing)
            self._set(archetype, ing, (a, b + 1))

    def record_failure(self, archetype: str, ingredients: list[str]) -> None:
        """Dish serve failed — raise suspicion for all ingredients."""
        for ing in ingredients:
            a, b = self._get(archetype, ing)
            self._set(archetype, ing, (a + 1, b))

    def is_safe(
        self, archetype: str, ingredient: str, threshold: float = 0.3
    ) -> bool:
        a, b = self._get(archetype, ingredient)
        p_intolerant = a / (a + b)
        return p_intolerant < threshold

    def filter_safe_recipes(
        self, archetype: str, recipes: list[Recipe]
    ) -> list[Recipe]:
        """Return recipes whose ingredients are all safe for *archetype*."""
        safe: list[Recipe] = []
        for recipe in recipes:
            if all(
                self.is_safe(archetype, ing)
                for ing in recipe.ingredients
            ):
                safe.append(recipe)
        return safe

    # ── internals ─────────────────────────────────────────────────

    def _get(self, arch: str, ing: str) -> tuple[float, float]:
        return self.suspicion.setdefault(arch, {}).get(ing, (1.0, 1.0))

    def _set(self, arch: str, ing: str, val: tuple[float, float]) -> None:
        self.suspicion.setdefault(arch, {})[ing] = val


# ── Global Client Library ────────────────────────────────────────


class GlobalClientLibrary:
    """Cross-turn, cross-zone aggregate client knowledge."""

    def __init__(self) -> None:
        self.archetype_stats: dict[str, ArchetypeStats] = {
            arch: ArchetypeStats() for arch in KNOWN_ARCHETYPES
        }
        self.known_intolerances: dict[str, set[str]] = {
            arch: set() for arch in KNOWN_ARCHETYPES
        }
        self.order_to_dish_cache: dict[str, str] = {}

    def update_from_turn(self, profiles: list[ClientProfile]) -> None:
        for profile in profiles:
            arch = profile.archetype
            if arch not in self.archetype_stats:
                self.archetype_stats[arch] = ArchetypeStats()
            self.archetype_stats[arch].update(profile)

            # Cache successful order→dish mapping
            if profile.served and profile.matched_dish:
                key = profile.order_text.lower().strip()
                self.order_to_dish_cache[key] = profile.matched_dish

    def get_cached_dish(self, order_text: str) -> str | None:
        return self.order_to_dish_cache.get(order_text.lower().strip())


# ── Zone Client Library ──────────────────────────────────────────


# Target archetypes per zone
_ZONE_ARCHETYPES: dict[str, list[str]] = {
    "PREMIUM_MONOPOLIST": ["Saggi del Cosmo", "Astrobarone"],
    "BUDGET_OPPORTUNIST": ["Esploratore Galattico", "Famiglie Orbitali"],
    "NICHE_SPECIALIST": [],  # dynamically chosen
    "SPEED_CONTENDER": list(KNOWN_ARCHETYPES),
    "MARKET_ARBITRAGEUR": [],
}


class ZoneClientLibrary:
    """Zone-specific view of the global client library."""

    def __init__(self, zone: str) -> None:
        self.zone = zone
        self.target_archetypes = _ZONE_ARCHETYPES.get(zone, [])

    def get_relevant_stats(
        self, global_lib: GlobalClientLibrary
    ) -> dict[str, ArchetypeStats]:
        return {
            arch: global_lib.archetype_stats[arch]
            for arch in self.target_archetypes
            if arch in global_lib.archetype_stats
        }


# ── Combined profile memory ────────────────────────────────────


class ClientProfileMemory:
    """Aggregation wrapper that holds the global library, per-zone
    libraries, intolerance detector, and interaction log."""

    def __init__(self) -> None:
        self.global_lib = GlobalClientLibrary()
        self.intolerance = IntoleranceDetector()
        self.zone_libs: dict[str, ZoneClientLibrary] = {
            z: ZoneClientLibrary(z) for z in ZONES
        }
        self.turn_profiles: list[ClientProfile] = []

    def record_interaction(self, profile: ClientProfile) -> None:
        self.turn_profiles.append(profile)

    def end_turn(self) -> None:
        """Flush turn profiles into the global library and reset."""
        self.global_lib.update_from_turn(self.turn_profiles)
        self.turn_profiles.clear()

    def reset(self) -> None:
        self.turn_profiles.clear()
