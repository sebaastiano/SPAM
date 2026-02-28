"""
Diplomacy agent — orchestrates message sending using the
DeceptionBandit, PseudoGAN, and GroundTruthFirewall.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import aiohttp

from src.config import BASE_URL, HEADERS
from src.diplomacy.deception_bandit import DeceptionBandit
from src.diplomacy.firewall import GroundTruthFirewall
from src.diplomacy.pseudo_gan import PseudoGAN
from src.memory.message_log import MessageMemory
from src.models import DeceptionAction

log = logging.getLogger(__name__)


class DiplomacyAgent:
    """Sends diplomatic messages during speaking / waiting phases.

    Uses:
      - ``DeceptionBandit`` to choose which competitors to target and
        which deception arm to deploy.
      - ``PseudoGAN`` to craft convincing messages.
      - ``GroundTruthFirewall`` to process *incoming* messages safely.
    """

    def __init__(
        self,
        bandit: DeceptionBandit,
        pseudo_gan: PseudoGAN | None,
        firewall: GroundTruthFirewall,
        message_memory: MessageMemory,
    ) -> None:
        self.bandit = bandit
        self.pseudo_gan = pseudo_gan
        self.firewall = firewall
        self.memory = message_memory
        self._mcp_url = f"{BASE_URL}/mcp"

    async def run_speaking_phase(
        self,
        briefings: dict[int, dict],
        session: aiohttp.ClientSession,
        turn_id: int = 0,
    ) -> None:
        """Execute diplomacy during speaking or waiting phase."""
        actions = self.bandit.select_targets(briefings)
        for action in actions:
            message = await self._craft(action, briefings)
            if message:
                await self._send(action.target_rid, message, session)
                self.memory.record_sent(
                    recipient_id=action.target_rid,
                    text=message,
                    arm=action.arm,
                    turn_id=turn_id,
                )

    async def handle_incoming(self, data: dict[str, Any]) -> None:
        """Process an incoming ``new_message`` SSE event."""
        tagged = self.firewall.process_incoming_message(data)
        self.memory.record_received(tagged)
        log.info(
            "Incoming message from %s (cred=%.2f): %s",
            tagged["sender_name"],
            tagged["sender_credibility"],
            tagged["text"][:80],
        )

    # ── internals ────────────────────────────────────────────────

    async def _craft(
        self, action: DeceptionAction, briefings: dict[int, dict]
    ) -> str | None:
        brief = briefings.get(action.target_rid)
        if not brief:
            return None

        if self.pseudo_gan:
            try:
                return await self.pseudo_gan.craft_message(
                    deception_action={
                        "target_name": action.target_name,
                        "arm": action.arm,
                        "desired_effect": action.desired_effect,
                        "message_hint": action.message_hint,
                    },
                    competitor_briefing=brief,
                )
            except Exception as exc:
                log.warning("PseudoGAN failed, using hint: %s", exc)

        # Fallback: raw hint
        return action.message_hint or None

    async def _send(
        self, recipient_id: int, text: str, session: aiohttp.ClientSession
    ) -> None:
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "send_message",
                "arguments": {"recipient_id": recipient_id, "text": text},
            },
        }
        try:
            async with session.post(
                self._mcp_url, json=payload, headers=HEADERS
            ) as resp:
                result = await resp.json()
                log.info("send_message(%d): %s", recipient_id, result)
        except Exception as exc:
            log.error("send_message failed: %s", exc)
