"""
SPAM! — Deception Bandit
==========================
Per-competitor Thompson Sampling for strategic deception.
7 arms × per-competitor priors, reward measured via tracker diffs.
"""

import logging

import numpy as np
from scipy.stats import beta as beta_dist

logger = logging.getLogger("spam.diplomacy.deception_bandit")


class DeceptionBandit:
    """
    Thompson Sampling bandit for selecting deception strategies.

    Each ARM is parameterized by the target competitor's tactical briefing.
    The same arm ("inflated_intel") produces very different messages depending
    on whether the target is a Reactive Chaser vs. a Declining team.

    Arms represent different manipulation approaches.
    Reward = observable competitor behavior change in the desired direction
    (measurable via tracker: did their bid pattern change? did they add/remove
    a menu item? did their balance drop?).
    """

    ARMS = {
        "truthful_warning": (1.0, 1.0),
        "inflated_intel": (1.0, 1.0),
        "manufactured_scarcity": (1.0, 1.0),
        "ingredient_misdirect": (1.0, 1.0),
        "alliance_offer": (1.0, 1.0),
        "price_anchoring": (1.0, 1.0),
        "silence": (1.0, 1.0),
    }

    def __init__(self):
        # Per-competitor arm priors: {rid: {arm_name: [alpha, beta]}}
        self.per_competitor_arms: dict[int, dict[str, list[float]]] = {}

    def _get_arms(self, rid: int) -> dict[str, list[float]]:
        if rid not in self.per_competitor_arms:
            self.per_competitor_arms[rid] = {
                name: list(prior) for name, prior in self.ARMS.items()
            }
        return self.per_competitor_arms[rid]

    def select_arm(self, rid: int) -> str:
        """Sample from posterior and pick the arm with highest sample."""
        arms = self._get_arms(rid)
        samples = {
            name: beta_dist.rvs(a, b)
            for name, (a, b) in arms.items()
        }
        return max(samples, key=samples.get)

    def update(self, rid: int, arm: str, reward: float):
        """
        reward is measured by OBSERVABLE behavior change (via tracker):
        - +1: they changed bids/menu in the desired direction
        - 0: no observable effect
        - -1: they did the opposite (they're onto us)
        """
        arms = self._get_arms(rid)
        a, b = arms[arm]
        if reward > 0:
            arms[arm] = [a + 1, b]
        else:
            arms[arm] = [a, b + 1]

    def measure_deception_reward(
        self,
        rid: int,
        arm: str,
        pre_state,
        post_state,
        desired_effect: str,
    ) -> float:
        """
        Measure whether a deception message had the desired effect
        by comparing pre/post tracker observations.
        """
        if desired_effect == "bid_away_from_ingredient":
            old_bids = getattr(pre_state, "bid_ingredients", set())
            new_bids = getattr(post_state, "bid_ingredients", set())
            return 1.0 if len(old_bids - new_bids) > 0 else 0.0

        elif desired_effect == "raise_prices":
            old_menu = getattr(pre_state, "menu", {})
            new_menu = getattr(post_state, "menu", {})
            old_avg = np.mean(list(old_menu.values())) if old_menu else 0
            new_avg = np.mean(list(new_menu.values())) if new_menu else 0
            return 1.0 if new_avg > old_avg * 1.05 else 0.0

        elif desired_effect == "overbid_on_ingredient":
            old_spend = getattr(pre_state, "total_bid_spend", 0)
            new_spend = getattr(post_state, "total_bid_spend", 0)
            return 1.0 if new_spend > old_spend * 1.15 else 0.0

        elif desired_effect == "alliance_cooperation":
            return 1.0 if getattr(post_state, "market_sells", None) else 0.0

        return 0.0

    def select_target_and_strategy(
        self,
        competitor_briefings: dict[int, dict],
    ) -> list[dict]:
        """
        Using per-competitor tactical briefings from the trajectory predictor,
        select target(s) and deception strategy for this turn.

        Returns list of {target_rid, arm, desired_effect, message_context}
        """
        actions = []

        for rid, brief in competitor_briefings.items():
            if brief.get("strategy") == "DORMANT":
                continue

            opportunity = brief.get("opportunity_level", 0)
            threat = brief.get("threat_level", 0)

            if opportunity > 0.5:
                arm = self.select_arm(rid)
                context = self._build_deception_context(rid, brief, arm)
                if context:
                    actions.append(context)
            elif threat > 0.6:
                context = self._build_threat_response(rid, brief)
                if context:
                    actions.append(context)

        actions.sort(key=lambda a: a.get("priority", 0), reverse=True)
        return actions[:3]

    def _build_deception_context(
        self, rid: int, brief: dict, arm: str
    ) -> dict | None:
        """Build a deception action using the competitor's briefing data."""
        if arm == "silence":
            return None

        context = {
            "target_rid": rid,
            "arm": arm,
            "target_name": brief.get("name", f"Team {rid}"),
            "target_strategy": brief.get("strategy", "UNKNOWN"),
            "priority": brief.get("opportunity_level", 0.5),
        }

        top_bids = brief.get("top_bid_ingredients", [])
        vuln_ings = brief.get("vulnerable_ingredients", [])

        if arm == "ingredient_misdirect" and top_bids:
            context["desired_effect"] = "bid_away_from_ingredient"
            context["message_hint"] = (
                f"Pivot away from {top_bids[0]} — "
                f"make them think that ingredient is no longer valuable"
            )

        elif arm == "manufactured_scarcity" and vuln_ings:
            context["desired_effect"] = "overbid_on_ingredient"
            context["message_hint"] = (
                f"Claim we're stockpiling {vuln_ings[0]} — "
                f"force them to overbid or pivot"
            )

        elif arm == "price_anchoring":
            context["desired_effect"] = "raise_prices"
            context["message_hint"] = (
                f"Signal premium positioning — anchor their prices upward "
                f"(their avg: {brief.get('menu_price_avg', 0):.0f})"
            )

        elif arm == "alliance_offer" and brief.get("balance_trend") == "falling":
            context["desired_effect"] = "alliance_cooperation"
            context["message_hint"] = (
                f"Offer ingredient trade alliance — they're declining "
                f"(balance={brief.get('balance', 0):.0f})"
            )

        elif arm == "truthful_warning":
            context["desired_effect"] = "build_credibility"
            context["message_hint"] = "Share verifiable info about another team"

        elif arm == "inflated_intel":
            context["desired_effect"] = "bid_away_from_ingredient"
            context["message_hint"] = (
                "Recommend a recipe we DON'T use as 'amazing' — "
                "redirect their ingredient demand"
            )

        else:
            return None

        return context

    def _build_threat_response(
        self, rid: int, brief: dict
    ) -> dict | None:
        """Build a defensive response to a high-threat competitor."""
        top_bids = brief.get("top_bid_ingredients", [])
        if not top_bids:
            return None

        return {
            "target_rid": rid,
            "arm": "manufactured_scarcity",
            "target_name": brief.get("name", f"Team {rid}"),
            "target_strategy": brief.get("strategy", "UNKNOWN"),
            "priority": brief.get("threat_level", 0.5),
            "desired_effect": "overbid_on_ingredient",
            "message_hint": (
                f"Signal that we're hoarding {top_bids[0]} — "
                f"force them to overspend or switch strategy"
            ),
        }
