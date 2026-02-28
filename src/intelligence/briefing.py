"""
SPAM! — Briefing Generator
============================
Generates per-competitor tactical briefings from trajectory predictions
and cluster classifications.
"""

import logging

logger = logging.getLogger("spam.intelligence.briefing")


class BriefingGeneratorModule:
    """
    Pipeline module that generates per-competitor tactical briefings.

    Combines trajectory predictions, strategy inference, and cluster
    classification into actionable intelligence for:
    - DeceptionBandit (targeted deception)
    - ILP Solver (bid priorities)
    - SubagentRouter (zone selection)
    """

    def __init__(self, trajectory_predictor=None):
        self.trajectory_predictor = trajectory_predictor

    async def process(self, input_data: dict) -> dict:
        """
        Pipeline module interface.

        input_data should contain:
          - trajectory results (from trajectory module)
          - cluster results (from cluster module)

        Returns dict with 'briefings': {rid: briefing_dict}
        """
        if self.trajectory_predictor:
            briefings = self.trajectory_predictor.generate_per_competitor_briefing()
        else:
            briefings = input_data.get("briefings", {})

        # Enrich with cluster information
        clusters = input_data.get("clusters", {})
        for rid, cluster in clusters.items():
            if rid in briefings:
                briefings[rid]["cluster"] = cluster

        return {"briefings": briefings}
