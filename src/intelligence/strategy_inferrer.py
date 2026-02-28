"""
StrategyInferrer — infers competitor strategy from observable patterns.
"""

from __future__ import annotations

import numpy as np

from src.models import CompetitorTurnState


class StrategyInferrer:
    """Rule-based strategy inference.  Each rule maps observable signals
    to a strategy hypothesis with a confidence score."""

    def infer(
        self,
        state: CompetitorTurnState,
        history: list[CompetitorTurnState],
    ) -> dict:
        """Returns ``{strategy, confidence, evidence}``."""
        hypotheses: list[dict] = []

        # ── Premium ──────────────────────────────────────────────
        if state.menu:
            avg_price = np.mean(list(state.menu.values()))
            if avg_price > 150 and len(state.menu) <= 5:
                hypotheses.append(
                    {
                        "strategy": "PREMIUM_MONOPOLIST",
                        "confidence": min(0.9, float(avg_price) / 250),
                        "evidence": [
                            f"avg_price={avg_price:.0f}",
                            f"menu_size={len(state.menu)}",
                        ],
                    }
                )

        # ── Budget / volume ──────────────────────────────────────
        if state.menu:
            avg_price = np.mean(list(state.menu.values()))
            if avg_price < 100 and len(state.menu) >= 6:
                hypotheses.append(
                    {
                        "strategy": "BUDGET_OPPORTUNIST",
                        "confidence": min(0.85, len(state.menu) / 15),
                        "evidence": [
                            f"avg_price={avg_price:.0f}",
                            f"menu_size={len(state.menu)}",
                        ],
                    }
                )

        # ── Aggressive hoarding ──────────────────────────────────
        if len(history) >= 2:
            recent_bid_spend = sum(s.total_bid_spend for s in history[-2:])
            if recent_bid_spend > state.balance * 0.3:
                hypotheses.append(
                    {
                        "strategy": "AGGRESSIVE_HOARDER",
                        "confidence": min(
                            0.8, recent_bid_spend / max(state.balance, 1)
                        ),
                        "evidence": [f"bid_spend_ratio={recent_bid_spend/max(state.balance,1):.2f}"],
                    }
                )

        # ── Arbitrageur ──────────────────────────────────────────
        market_entries = len(state.market_buys) + len(state.market_sells)
        if market_entries > 3 and len(state.menu) <= 2:
            hypotheses.append(
                {
                    "strategy": "MARKET_ARBITRAGEUR",
                    "confidence": 0.7,
                    "evidence": [
                        f"market_entries={market_entries}",
                        f"menu_size={len(state.menu)}",
                    ],
                }
            )

        # ── Reactive chaser ──────────────────────────────────────
        if len(history) >= 3:
            changes = sum(
                1
                for i in range(1, len(history))
                if history[i].menu != history[i - 1].menu
            )
            rate = changes / len(history)
            if rate >= 0.6:
                hypotheses.append(
                    {
                        "strategy": "REACTIVE_CHASER",
                        "confidence": min(0.75, rate),
                        "evidence": [f"menu_change_rate={rate:.2f}"],
                    }
                )

        # ── Declining ────────────────────────────────────────────
        if len(history) >= 2:
            consecutive = 0
            for s in reversed(history):
                if s.balance_delta < 0:
                    consecutive += 1
                else:
                    break
            if consecutive >= 2:
                hypotheses.append(
                    {
                        "strategy": "DECLINING",
                        "confidence": min(0.9, consecutive * 0.3),
                        "evidence": [f"consecutive_losses={consecutive}"],
                    }
                )

        # ── Dormant ──────────────────────────────────────────────
        if not state.is_open and len(state.menu) == 0 and state.balance >= 7500:
            hypotheses.append(
                {
                    "strategy": "DORMANT",
                    "confidence": 0.95,
                    "evidence": ["never_opened"],
                }
            )

        if not hypotheses:
            return {"strategy": "UNCLASSIFIED", "confidence": 0.0, "evidence": []}

        return max(hypotheses, key=lambda h: h["confidence"])
