"""
Message memory — tracks sent and received messages for diplomacy.
"""

from __future__ import annotations

from typing import Any


class MessageMemory:
    """Stores sent and received messages plus broadcasts."""

    def __init__(self) -> None:
        self.sent: list[dict[str, Any]] = []
        self.received: list[dict[str, Any]] = []
        self.broadcasts: list[dict[str, Any]] = []

    def record_sent(
        self,
        recipient_id: int,
        text: str,
        arm: str = "",
        turn_id: int = 0,
    ) -> None:
        self.sent.append(
            {
                "recipient_id": recipient_id,
                "text": text,
                "arm": arm,
                "turn_id": turn_id,
            }
        )

    def record_received(self, data: dict[str, Any]) -> None:
        self.received.append(data)

    def record_broadcast(self, data: dict[str, Any]) -> None:
        self.broadcasts.append(data)

    def messages_from(self, sender_id: int) -> list[dict]:
        return [m for m in self.received if m.get("senderId") == sender_id]

    def messages_to(self, recipient_id: int) -> list[dict]:
        return [m for m in self.sent if m.get("recipient_id") == recipient_id]

    def reset(self) -> None:
        self.sent.clear()
        self.received.clear()
        self.broadcasts.clear()
