"""
SPAM! — Diplomacy Agent
=========================
Orchestrates DeceptionBandit + PseudoGAN + GroundTruthFirewall.
Manages all outbound/inbound diplomatic communications.
"""

import logging

from datapizza.tools.mcp_client import MCPClient

from src.config import MCP_URL, HEADERS, TEAM_ID
from src.diplomacy.deception_bandit import DeceptionBandit
from src.diplomacy.pseudo_gan import PseudoGAN
from src.diplomacy.firewall import GroundTruthFirewall
from src.memory.message_log import MessageLog

logger = logging.getLogger("spam.diplomacy.agent")


class DiplomacyAgent:
    """
    Orchestrates all diplomatic communications:
    - Offense: DeceptionBandit selects arm → PseudoGAN crafts message
    - Defense: GroundTruthFirewall processes incoming messages
    - Tracking: MessageLog records all sent/received messages
    """

    def __init__(
        self,
        mcp_client: MCPClient | None = None,
        message_log: MessageLog | None = None,
    ):
        self.mcp_client = mcp_client
        self.message_log = message_log or MessageLog()
        self.firewall = GroundTruthFirewall(self.message_log)
        self.bandit = DeceptionBandit()
        self.pseudo_gan = PseudoGAN()

        # Track pending deceptions for reward measurement
        self._pending_deceptions: list[dict] = []

    async def run_diplomacy_turn(
        self,
        competitor_briefings: dict[int, dict],
        competitor_states: dict = None,
        turn_id: int = 0,
    ) -> list[dict]:
        """
        Execute a full diplomacy turn:
        1. Select targets and strategies (bandit)
        2. Craft messages (PseudoGAN)
        3. Send messages via MCP
        4. Record for reward tracking

        Returns list of sent message records.
        """
        # Quick-exit: if no briefings at all, nothing to do
        if not competitor_briefings:
            logger.warning(
                "No competitor briefings available — skipping diplomacy. "
                "This usually means intel did not propagate to the skill context."
            )
            return []

        # In monopoly / low-competition, skip diplomacy entirely to save time
        active = [
            b for b in competitor_briefings.values()
            if b.get("strategy") != "DORMANT"
        ]
        logger.info(
            f"Diplomacy candidates: {len(competitor_briefings)} total briefings, "
            f"{len(active)} non-dormant"
        )
        if len(active) == 0:
            logger.info(
                f"No active competitors (all {len(competitor_briefings)} are DORMANT) — "
                f"skipping diplomacy"
            )
            return []

        # 1. Select targets and strategies via bandit
        logger.info(f"Running DeceptionBandit target selection on {len(active)} candidates")
        actions = self.bandit.select_target_and_strategy(competitor_briefings)
        if not actions:
            logger.info("DeceptionBandit returned no actions (all scored too low)")
            return []
        logger.info(
            f"DeceptionBandit selected {len(actions)} action(s): "
            + ", ".join(
                f"{a['arm']}→{a.get('target_name', a['target_rid'])}"
                for a in actions
            )
        )

        sent = []
        for action in actions:
            rid = action["target_rid"]
            briefing = competitor_briefings.get(rid, {})

            # 2. Craft message via PseudoGAN (generator + discriminator loop)
            logger.info(
                f"PseudoGAN crafting [{action['arm']}] message for "
                f"{action.get('target_name', rid)} (desired: {action.get('desired_effect', '?')})"
            )
            try:
                message_text = await self.pseudo_gan.craft_message(
                    deception_action=action,
                    competitor_briefing=briefing,
                    max_iterations=2,
                )
                logger.info(
                    f"PseudoGAN result for {action.get('target_name', rid)}: "
                    f"'{message_text[:100]}'"
                )
            except Exception as e:
                logger.warning(f"PseudoGAN failed for {rid}: {e}")
                continue

            # 3. Send via MCP
            logger.info(f"Sending message to restaurant {rid} via MCP send_message")
            success = await self._send_message(rid, message_text)
            if success:
                record = {
                    "turn": turn_id,
                    "target_rid": rid,
                    "arm": action["arm"],
                    "desired_effect": action.get("desired_effect", ""),
                    "message": message_text,
                    "target_name": action.get("target_name", ""),
                }
                sent.append(record)

                # Track for reward measurement
                self._pending_deceptions.append({
                    **record,
                    "pre_state": competitor_states.get(rid) if competitor_states else None,
                })

                # Record in message log
                self.message_log.log_sent(
                    receiver_id=rid,
                    text=message_text,
                )

                logger.info(
                    f"Sent [{action['arm']}] to {action.get('target_name', rid)}: "
                    f"'{message_text[:50]}...'"
                )

        return sent

    async def measure_deception_rewards(
        self,
        competitor_states: dict,
    ):
        """
        After a turn, measure the effect of our deceptions
        by comparing pre/post competitor states via tracker.
        """
        for deception in self._pending_deceptions:
            rid = deception["target_rid"]
            arm = deception["arm"]
            desired_effect = deception.get("desired_effect", "")
            pre_state = deception.get("pre_state")
            post_state = competitor_states.get(rid)

            if pre_state is None or post_state is None:
                continue

            reward = self.bandit.measure_deception_reward(
                rid=rid,
                arm=arm,
                pre_state=pre_state,
                post_state=post_state,
                desired_effect=desired_effect,
            )

            self.bandit.update(rid, arm, reward)

            logger.info(
                f"Deception reward for {deception.get('target_name', rid)} "
                f"[{arm}]: {reward:.1f}"
            )

        self._pending_deceptions.clear()

    def process_incoming_message(
        self, message: dict, competitor_state=None
    ) -> dict:
        """
        Process an incoming message through the firewall.
        Returns processed message with trust level and credibility.
        """
        processed = self.firewall.process_incoming_message(message)

        # If we have competitor state, verify claims
        if competitor_state is not None:
            sender_id = message.get("senderId")
            claim_text = message.get("text", "")
            adjustment = self.firewall.verify_claim_against_tracker(
                sender_id, claim_text, competitor_state
            )
            if adjustment != 0:
                self.firewall.update_credibility(sender_id, adjustment)
                processed["verified"] = adjustment > 0
                processed["credibility_adjustment"] = adjustment

        return processed

    async def _send_message(self, target_rid: int, text: str) -> bool:
        """Send a message via MCP."""
        if self.mcp_client is None:
            logger.warning("No MCP client configured for diplomacy")
            return False

        try:
            result = await self.mcp_client.call_tool(
                "send_message",
                {
                    "recipient_id": target_rid,
                    "text": text,
                },
            )
            logger.debug(f"Message sent to {target_rid}: {result}")
            return True
        except Exception as e:
            logger.warning(f"Failed to send message to {target_rid}: {e}")
            return False
