"""
GroundTruthFirewall — ensures strategic decisions only use
server-signed GET data, never incoming messages.
"""

from __future__ import annotations

import logging
from typing import Any

from src.models import CompetitorTurnState

log = logging.getLogger(__name__)


class TrustLevel:
    SERVER_SIGNED = "server"
    SELF_GENERATED = "self"
    UNTRUSTED = "untrusted"


class GroundTruthFirewall:
    """Middleware that separates trusted data (GET responses) from
    untrusted data (incoming messages)."""

    def __init__(self) -> None:
        # sender_id → running credibility score [0, 1]
        self._credibility: dict[int, float] = {}
        self._untrusted_log: list[dict] = []

    def validate_for_decisions(
        self, data: dict, trust_level: str
    ) -> dict | None:
        """Only ``SERVER_SIGNED`` and ``SELF_GENERATED`` data passes."""
        if trust_level == TrustLevel.UNTRUSTED:
            self._untrusted_log.append(data)
            return None
        return data

    def process_incoming_message(self, message: dict) -> dict:
        """Log and tag an incoming message. Never inject into decisions."""
        sender_id = message.get("senderId", 0)
        return {
            "message_id": message.get("messageId"),
            "sender_id": sender_id,
            "sender_name": message.get("senderName", ""),
            "text": message.get("text", ""),
            "datetime": message.get("datetime", ""),
            "trust_level": TrustLevel.UNTRUSTED,
            "sender_credibility": self.get_credibility(sender_id),
        }

    def verify_claim_against_state(
        self, sender_id: int, claim: str, state: CompetitorTurnState
    ) -> float:
        """Cross-reference a message claim against tracker observations.

        Returns credibility adjustment: +1 true, −1 false, 0 unverifiable.
        """
        lower = claim.lower()

        # "I have lots of X" — check inventory
        for ing, qty in state.inventory.items():
            if ing.lower() in lower:
                if any(w in lower for w in ("lot", "much", "surplus")):
                    return 1.0 if qty >= 3 else -1.0

        # "Not interested in X" — check bids
        for bid_ing in state.bid_ingredients:
            if bid_ing.lower() in lower and (
                "not interested" in lower or "don't need" in lower
            ):
                return -1.0  # they bid on it → lying

        # "Low balance"
        if "low" in lower and "balance" in lower:
            return 1.0 if state.balance < 4000 else -1.0

        return 0.0

    def update_credibility(self, sender_id: int, delta: float) -> None:
        cur = self._credibility.get(sender_id, 0.5)
        self._credibility[sender_id] = max(0.0, min(1.0, cur + delta * 0.1))

    def get_credibility(self, sender_id: int) -> float:
        return self._credibility.get(sender_id, 0.5)
