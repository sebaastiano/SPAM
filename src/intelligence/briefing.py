"""
Briefing generator — produces per-competitor tactical briefings
by aggregating intelligence products.
"""

from __future__ import annotations

from src.intelligence.trajectory import AdvancedTrajectoryPredictor


class BriefingGenerator:
    """Thin wrapper around the trajectory predictor's briefing output
    with additional tactical annotations."""

    def __init__(self, predictor: AdvancedTrajectoryPredictor) -> None:
        self.predictor = predictor

    def generate(self) -> dict[int, dict]:
        """Returns ``{rid: briefing_dict}``."""
        return self.predictor.generate_briefings()
