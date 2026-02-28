"""
DeceptionBandit — per-competitor Thompson Sampling for selecting
deception strategies.
"""

from __future__ import annotations

import numpy as np
from scipy.stats import beta as beta_dist

from src.models import CompetitorTurnState, DeceptionAction


class DeceptionBandit:
    """Thompson Sampling bandit over deception arms, per-competitor."""

    ARMS: dict[str, tuple[float, float]] = {
        "truthful_warning": (1.0, 1.0),
        "inflated_intel": (1.0, 1.0),
        "manufactured_scarcity": (1.0, 1.0),
        "ingredient_misdirect": (1.0, 1.0),
        "alliance_offer": (1.0, 1.0),
        "price_anchoring": (1.0, 1.0),
        "silence": (1.0, 1.0),
    }

    def __init__(self) -> None:
        # {rid: {arm: [alpha, beta]}}
        self._arms: dict[int, dict[str, list[float]]] = {}

    def _get_arms(self, rid: int) -> dict[str, list[float]]:
        if rid not in self._arms:
            self._arms[rid] = {
                name: list(prior) for name, prior in self.ARMS.items()
            }
        return self._arms[rid]

    def select_arm(self, rid: int) -> str:
        arms = self._get_arms(rid)
        samples = {
            name: float(beta_dist.rvs(a, b))
            for name, (a, b) in arms.items()
        }
        return max(samples, key=samples.get)  # type: ignore[arg-type]

    def update(self, rid: int, arm: str, reward: float) -> None:
        arms = self._get_arms(rid)
        a, b = arms[arm]
        if reward > 0:
            arms[arm] = [a + 1, b]
        else:
            arms[arm] = [a, b + 1]

    def measure_reward(
        self,
        pre: CompetitorTurnState,
        post: CompetitorTurnState,
        desired_effect: str,
    ) -> float:
        """Measure whether observable behaviour changed as desired."""
        if desired_effect == "bid_away_from_ingredient":
            return 1.0 if len(pre.bid_ingredients - post.bid_ingredients) > 0 else 0.0
        if desired_effect == "raise_prices":
            old_avg = np.mean(list(pre.menu.values())) if pre.menu else 0
            new_avg = np.mean(list(post.menu.values())) if post.menu else 0
            return 1.0 if new_avg > old_avg * 1.05 else 0.0
        if desired_effect == "overbid_on_ingredient":
            return (
                1.0 if post.total_bid_spend > pre.total_bid_spend * 1.15 else 0.0
            )
        return 0.0

    # ── Target selection ─────────────────────────────────────────

    def select_targets(
        self, briefings: dict[int, dict]
    ) -> list[DeceptionAction]:
        """Pick up to 3 targets and strategies for this turn."""
        actions: list[DeceptionAction] = []

        for rid, brief in briefings.items():
            if brief.get("strategy") == "DORMANT":
                continue

            opp = brief.get("opportunity_level", 0)
            threat = brief.get("threat_level", 0)

            if opp > 0.5:
                arm = self.select_arm(rid)
                action = self._build_action(rid, brief, arm, opp)
                if action:
                    actions.append(action)
            elif threat > 0.6:
                action = self._build_threat_response(rid, brief, threat)
                if action:
                    actions.append(action)

        actions.sort(key=lambda a: a.priority, reverse=True)
        return actions[:3]

    def _build_action(
        self, rid: int, brief: dict, arm: str, priority: float
    ) -> DeceptionAction | None:
        if arm == "silence":
            return None

        action = DeceptionAction(
            target_rid=rid,
            arm=arm,
            target_name=brief.get("name", ""),
            target_strategy=brief.get("strategy", ""),
            priority=priority,
        )

        top_bids = brief.get("top_bid_ingredients", [])
        vuln = brief.get("vulnerable_ingredients", [])

        if arm == "ingredient_misdirect" and top_bids:
            action.desired_effect = "bid_away_from_ingredient"
            action.message_hint = (
                f"Pivot away from {top_bids[0]}"
            )
        elif arm == "manufactured_scarcity" and vuln:
            action.desired_effect = "overbid_on_ingredient"
            action.message_hint = f"Claim stockpiling {vuln[0]}"
        elif arm == "price_anchoring":
            action.desired_effect = "raise_prices"
            action.message_hint = "Signal premium positioning"
        elif arm == "alliance_offer" and brief.get("balance_trend") == "falling":
            action.desired_effect = "alliance_cooperation"
            action.message_hint = "Offer ingredient trade"
        elif arm == "truthful_warning":
            action.desired_effect = "build_credibility"
            action.message_hint = "Share verifiable intel about a third team"
        elif arm == "inflated_intel":
            action.desired_effect = "bid_away_from_ingredient"
            action.message_hint = "Recommend a recipe we don't use"
        else:
            return None

        return action

    def _build_threat_response(
        self, rid: int, brief: dict, priority: float
    ) -> DeceptionAction | None:
        top_bids = brief.get("top_bid_ingredients", [])
        if not top_bids:
            return None
        return DeceptionAction(
            target_rid=rid,
            arm="manufactured_scarcity",
            target_name=brief.get("name", ""),
            target_strategy=brief.get("strategy", ""),
            priority=priority,
            desired_effect="overbid_on_ingredient",
            message_hint=f"Signal hoarding {top_bids[0]}",
        )
