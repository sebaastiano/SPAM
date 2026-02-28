"""
SPAM! — Message Log
====================
Memory for tracking sent and received inter-team messages.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone

logger = logging.getLogger("spam.memory.message_log")


@dataclass
class MessageEntry:
    """Single message record."""
    message_id: str
    sender_id: int
    sender_name: str
    receiver_id: int | None  # None for broadcasts
    text: str
    timestamp: str
    direction: str  # "sent" | "received" | "broadcast"
    trust_level: str = "untrusted"
    credibility_score: float = 0.5


class MessageLog:
    """
    Memory for all inter-team messages.

    Tracks:
    - Sent messages (our outbox — no API retrieval, must log ourselves)
    - Received messages (from new_message SSE events)
    - Broadcasts (from message SSE events)
    """

    def __init__(self):
        self.sent: list[MessageEntry] = []
        self.received: list[MessageEntry] = []
        self.broadcasts: list[MessageEntry] = []
        self._credibility: dict[int, float] = {}  # sender_id → credibility

    def log_sent(self, receiver_id: int, text: str):
        """Log a message we sent."""
        entry = MessageEntry(
            message_id=f"sent_{len(self.sent)}",
            sender_id=17,
            sender_name="SPAM!",
            receiver_id=receiver_id,
            text=text,
            timestamp=datetime.now(timezone.utc).isoformat(),
            direction="sent",
            trust_level="self",
        )
        self.sent.append(entry)
        logger.debug(f"Logged sent message to {receiver_id}: {text[:50]}...")

    def log_received(self, data: dict):
        """Log an incoming message from new_message SSE event."""
        entry = MessageEntry(
            message_id=data.get("messageId", ""),
            sender_id=data.get("senderId", 0),
            sender_name=data.get("senderName", "unknown"),
            receiver_id=17,
            text=data.get("text", ""),
            timestamp=data.get("datetime", datetime.now(timezone.utc).isoformat()),
            direction="received",
            trust_level="untrusted",
            credibility_score=self.get_credibility(data.get("senderId", 0)),
        )
        self.received.append(entry)
        logger.info(f"Received message from {entry.sender_name} ({entry.sender_id}): {entry.text[:80]}...")

    def log_broadcast(self, data: dict):
        """Log a broadcast message."""
        entry = MessageEntry(
            message_id=data.get("messageId", ""),
            sender_id=data.get("senderId", 0),
            sender_name=data.get("senderName", "unknown"),
            receiver_id=None,
            text=data.get("text", ""),
            timestamp=data.get("datetime", datetime.now(timezone.utc).isoformat()),
            direction="broadcast",
            trust_level="untrusted",
        )
        self.broadcasts.append(entry)

    def get_credibility(self, sender_id: int) -> float:
        """Get credibility score for a sender (0.0 = liar, 1.0 = trustworthy)."""
        return self._credibility.get(sender_id, 0.5)

    def update_credibility(self, sender_id: int, delta: float):
        """
        Update credibility based on claim verification.

        delta > 0: claim verified true
        delta < 0: claim proven false
        """
        current = self._credibility.get(sender_id, 0.5)
        self._credibility[sender_id] = max(0.0, min(1.0, current + delta * 0.1))

    def messages_from(self, sender_id: int) -> list[MessageEntry]:
        """Get all messages from a specific sender."""
        return [m for m in self.received if m.sender_id == sender_id]

    def messages_to(self, receiver_id: int) -> list[MessageEntry]:
        """Get all messages we sent to a specific receiver."""
        return [m for m in self.sent if m.receiver_id == receiver_id]

    def clear(self):
        """Clear all messages (game_reset)."""
        self.sent.clear()
        self.received.clear()
        self.broadcasts.clear()
        self._credibility.clear()
