"""
SubagentRouter — dispatches game operations to the active zone's
subagent (or direct ILP-driven logic).
"""

from __future__ import annotations

import logging
from typing import Any

from src.config import DEFAULT_ZONE, ZONES
from src.decision.ilp_solver import solve_zone_ilp
from src.decision.zone_selector import select_zone
from src.models import GameState, Recipe, ZoneDecision

log = logging.getLogger(__name__)


class SubagentRouter:
    """Routes each turn's strategic decisions through the ILP-driven
    zone selector, then executes the zone-specific plan."""

    def __init__(self) -> None:
        self.active_zone: str = DEFAULT_ZONE
        self._last_decision: ZoneDecision | None = None

    def select(
        self,
        game_state: GameState,
        clusters: dict[int, str],
        briefings: dict[int, dict],
    ) -> str:
        """Pick the best zone for this turn and return its name."""
        self.active_zone = select_zone(
            game_state, clusters, briefings
        )
        log.info("Zone selected: %s", self.active_zone)
        return self.active_zone

    def plan(
        self,
        game_state: GameState,
        recipes: dict[str, Recipe],
        demand_forecast: dict[str, float] | None = None,
        briefings: dict[int, dict] | None = None,
    ) -> ZoneDecision:
        """Generate the ILP-driven plan for the active zone."""
        decision = solve_zone_ilp(
            zone=self.active_zone,
            game_state=game_state,
            recipes=recipes,
            demand_forecast=demand_forecast,
            briefings=briefings,
        )
        self._last_decision = decision
        return decision

    @property
    def last_decision(self) -> ZoneDecision | None:
        return self._last_decision
