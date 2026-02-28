"""
SPAM! — Strategy Inferrer
===========================
Infer competitor strategy from observable patterns.
"""

import logging

import numpy as np

from src.intelligence.competitor_state import CompetitorTurnState

logger = logging.getLogger("spam.intelligence.strategy_inferrer")


class StrategyInferrer:
    """
    Infer competitor strategy from observable patterns.

    Each inference rule maps observable signals → strategy hypothesis
    with a confidence score. The highest-confidence hypothesis wins.
    """

    def infer(
        self, state: CompetitorTurnState, history: list[CompetitorTurnState]
    ) -> dict:
        """Returns {strategy: str, confidence: float, evidence: list[str]}."""
        hypotheses = []

        # ── Premium strategy detection ──
        if state.menu:
            avg_price = np.mean(list(state.menu.values()))
            menu_size = len(state.menu)
            if avg_price > 150 and menu_size <= 5:
                hypotheses.append({
                    "strategy": "PREMIUM_MONOPOLIST",
                    "confidence": min(0.9, avg_price / 250),
                    "evidence": [
                        f"avg_price={avg_price:.0f} (>150)",
                        f"menu_size={menu_size} (≤5)",
                    ],
                })

        # ── Budget/volume strategy detection ──
        if state.menu:
            avg_price = np.mean(list(state.menu.values()))
            menu_size = len(state.menu)
            if avg_price < 100 and menu_size >= 6:
                hypotheses.append({
                    "strategy": "BUDGET_OPPORTUNIST",
                    "confidence": min(0.85, menu_size / 15),
                    "evidence": [
                        f"avg_price={avg_price:.0f} (<100)",
                        f"menu_size={menu_size} (≥6)",
                    ],
                })

        # ── Aggressive hoarding detection ──
        if len(history) >= 2:
            recent_bid_spend = sum(s.total_bid_spend for s in history[-2:])
            if state.balance > 0 and recent_bid_spend > state.balance * 0.3:
                hypotheses.append({
                    "strategy": "AGGRESSIVE_HOARDER",
                    "confidence": min(
                        0.8, recent_bid_spend / max(state.balance, 1)
                    ),
                    "evidence": [
                        f"bid_spend_ratio={recent_bid_spend / max(state.balance, 1):.2f}",
                        "balance_trend=declining",
                    ],
                })

        # ── Market arbitrageur detection ──
        total_market = len(state.market_buys) + len(state.market_sells)
        if total_market > 3 and len(state.menu) <= 2:
            hypotheses.append({
                "strategy": "MARKET_ARBITRAGEUR",
                "confidence": 0.7,
                "evidence": [
                    f"market_entries={total_market}",
                    f"menu_size={len(state.menu)} (≤2)",
                ],
            })

        # ── Reactive chaser detection ──
        if len(history) >= 3:
            menu_changes = sum(
                1
                for i in range(1, len(history))
                if history[i].menu != history[i - 1].menu
            )
            rate = menu_changes / len(history)
            if rate >= 0.6:
                hypotheses.append({
                    "strategy": "REACTIVE_CHASER",
                    "confidence": min(0.75, rate),
                    "evidence": [f"menu_change_rate={rate:.2f}"],
                })

        # ── Declining / inactive detection ──
        if len(history) >= 2:
            if state.balance_delta < 0 and state.reputation_delta <= 0:
                consecutive_losses = 0
                for s in reversed(history):
                    if s.balance_delta < 0:
                        consecutive_losses += 1
                    else:
                        break
                if consecutive_losses >= 2:
                    hypotheses.append({
                        "strategy": "DECLINING",
                        "confidence": min(0.9, consecutive_losses * 0.3),
                        "evidence": [
                            f"consecutive_losses={consecutive_losses}",
                            f"balance_delta={state.balance_delta}",
                            f"reputation_delta={state.reputation_delta}",
                        ],
                    })

        # ── Dormant detection ──
        if not state.is_open and len(state.menu) == 0 and state.balance >= 7500:
            hypotheses.append({
                "strategy": "DORMANT",
                "confidence": 0.95,
                "evidence": ["never_opened", f"balance={state.balance}"],
            })

        if not hypotheses:
            return {"strategy": "UNCLASSIFIED", "confidence": 0.0, "evidence": []}

        return max(hypotheses, key=lambda h: h["confidence"])
