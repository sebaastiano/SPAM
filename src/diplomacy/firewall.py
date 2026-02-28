"""
SPAM! — Ground Truth Firewall
===============================
Defensive layer that prevents untrusted data from entering
the decision engine. Uses tracker observations to verify claims.
"""

import logging
from enum import Enum
from typing import Optional

logger = logging.getLogger("spam.diplomacy.firewall")


class TrustLevel(str, Enum):
    SERVER_SIGNED = "server"
    SELF_GENERATED = "self"
    UNTRUSTED = "untrusted"


class GroundTruthFirewall:
    """
    Only SERVER_SIGNED and SELF_GENERATED data passes through to ILP.
    Incoming messages are processed for intelligence but NEVER enter
    the decision engine directly.

    Cross-references claims against tracker observations.
    """

    def __init__(self, message_log=None):
        self.message_log = message_log
        self._untrusted_log: list[dict] = []

    def validate_for_decisions(
        self, data: dict, trust_level: str
    ) -> Optional[dict]:
        """Only SERVER_SIGNED and SELF_GENERATED data passes through to ILP."""
        if trust_level == TrustLevel.UNTRUSTED:
            self.log_untrusted(data)
            return None
        return data

    def log_untrusted(self, data: dict):
        """Log untrusted data for intelligence purposes only."""
        self._untrusted_log.append(data)
        logger.debug(f"Blocked untrusted data: {data.get('type', 'unknown')}")

    def process_incoming_message(self, message: dict) -> dict:
        """
        Incoming messages are processed for intelligence but NEVER
        enter the decision engine directly.

        Steps:
        1. Log the message
        2. Compare claims against our own observations
        3. Update sender credibility score
        4. If claims are verifiable via GET, verify them
        """
        sender_id = message.get("senderId")
        sender_name = message.get("senderName", "Unknown")
        claim = message.get("text", "")
        timestamp = message.get("datetime", "")
        message_id = message.get("messageId", "")

        # Record in message log
        if self.message_log:
            self.message_log.record_received(
                sender_id=sender_id,
                sender_name=sender_name,
                text=claim,
                turn=0,
            )

        credibility = 0.5
        if self.message_log:
            credibility = self.message_log.get_credibility(sender_id)

        return {
            "message_id": message_id,
            "sender_id": sender_id,
            "sender_name": sender_name,
            "text": claim,
            "datetime": timestamp,
            "trust_level": TrustLevel.UNTRUSTED,
            "sender_credibility": credibility,
        }

    def verify_claim_against_tracker(
        self,
        sender_id: int,
        claim_text: str,
        competitor_state,
    ) -> float:
        """
        Cross-reference a message claim against tracker observations.

        Because we have exact balance, inventory, menu, and bid data for every
        competitor (from GET /restaurants + /bid_history), we can verify most
        claims automatically.

        Returns credibility adjustment: +1 (verified true), -1 (proven false), 0 (unverifiable)
        """
        claim_lower = claim_text.lower()

        # "I have lots of X" → check their inventory
        if hasattr(competitor_state, "inventory"):
            for ingredient, qty in competitor_state.inventory.items():
                if ingredient.lower() in claim_lower:
                    if any(
                        kw in claim_lower
                        for kw in ["lot", "much", "surplus", "plenty"]
                    ):
                        return 1.0 if qty >= 3 else -1.0

        # "I'm not interested in X" → check their bid history
        if hasattr(competitor_state, "bid_ingredients"):
            for bid_ing in competitor_state.bid_ingredients:
                if bid_ing.lower() in claim_lower and any(
                    kw in claim_lower
                    for kw in ["not interested", "don't need", "don't want"]
                ):
                    return -1.0  # they literally bid on it, they're lying

        # "My balance is low" → we can see their exact balance
        if "low" in claim_lower and "balance" in claim_lower:
            if hasattr(competitor_state, "balance"):
                return 1.0 if competitor_state.balance < 4000 else -1.0

        return 0.0  # unverifiable

    def update_credibility(
        self, sender_id: int, adjustment: float
    ):
        """Update a sender's credibility score based on claim verification."""
        if self.message_log:
            current = self.message_log.get_credibility(sender_id)
            new_cred = max(0.0, min(1.0, current + adjustment * 0.1))
            self.message_log.credibility[sender_id] = new_cred
            logger.debug(
                f"Credibility for {sender_id}: {current:.2f} → {new_cred:.2f}"
            )

    async def middleware(self, event_type: str, data: dict) -> Optional[dict]:
        """
        Event bus middleware: tag all events with trust level.
        Messages from competitors get UNTRUSTED tag.
        """
        if event_type == "new_message":
            data["_trust_level"] = TrustLevel.UNTRUSTED
            processed = self.process_incoming_message(data)
            data["_processed"] = processed
        else:
            data["_trust_level"] = TrustLevel.SERVER_SIGNED

        return data
