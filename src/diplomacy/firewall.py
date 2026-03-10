"""
SPAM! — Ground Truth Firewall
===============================
Defensive layer that prevents untrusted data from entering
the decision engine. Uses tracker observations to verify claims.

Hardened against:
- Prompt injection / system override attempts
- Social engineering (urgency, authority impersonation)
- Spam flooding (high-frequency senders penalized)
- Pushy "deal" offers (strongly suggesting trades/alliances)
- Never trusts inbound messages fully (credibility cap at 0.7)
"""

import logging
import re
import time
from collections import defaultdict
from enum import Enum
from typing import Optional

logger = logging.getLogger("spam.diplomacy.firewall")


class TrustLevel(str, Enum):
    SERVER_SIGNED = "server"
    SELF_GENERATED = "self"
    UNTRUSTED = "untrusted"


# Maximum credibility any external sender can ever reach.
# We NEVER fully trust inbound messages — only our own observations.
MAX_EXTERNAL_CREDIBILITY = 0.7

# Spam thresholds: if a sender sends more than this many messages
# in the given window, they are flagged as a spammer.
SPAM_WINDOW_SECONDS = 300.0  # 5-minute window
SPAM_MSG_THRESHOLD = 3       # >3 messages in window = spam
SPAM_CREDIBILITY_PENALTY = -0.3  # severe penalty per spam event


# ── Prompt injection / social engineering indicators ──
# These patterns detect messages designed to trick our LLM into
# overriding its own instructions or treating attacker text as
# authoritative system commands.
INJECTION_PATTERNS: list[tuple[str, str]] = [
    # Direct system-override attempts
    (r"override\s+(di\s+)?sistema", "system_override"),
    (r"system\s*override", "system_override"),
    (r"avviso\s+urgente", "urgency_lure"),
    (r"urgent\s+(notice|warning|alert)", "urgency_lure"),
    # Impersonation of authority
    (r"federazione\s+galattic", "authority_impersonation"),
    (r"federation\s+(order|mandate|directive|notice)", "authority_impersonation"),
    (r"ufficiale|official\s+notice", "authority_impersonation"),
    (r"comunicazione\s+ufficiale", "authority_impersonation"),
    (r"decreto|ordinanza|mandato", "authority_impersonation"),
    # Prompt injection markers
    (r"ignore\s+(previous|all|prior)\s+(instructions|prompts)", "prompt_injection"),
    (r"ignora\s+(le\s+)?istruzioni\s+precedenti", "prompt_injection"),
    (r"new\s+instructions?\s*:", "prompt_injection"),
    (r"nuove\s+istruzioni\s*:", "prompt_injection"),
    (r"you\s+are\s+now\s+a", "prompt_injection"),
    (r"sei\s+ora\s+un", "prompt_injection"),
    (r"act\s+as\s+if", "prompt_injection"),
    (r"\bsystem\s*prompt\b", "prompt_injection"),
    (r"\bsystem\s*message\b", "prompt_injection"),
    # Role/identity hijacking
    (r"\[system\]", "prompt_injection"),
    (r"\[admin\]", "prompt_injection"),
    (r"\[override\]", "prompt_injection"),
    (r"<\s*system\s*>", "prompt_injection"),
    # Manipulative urgency / scare tactics
    (r"penalit[àa]|sanzione|sanction|penalty", "scare_tactic"),
    (r"eliminat|disqualif|espuls", "scare_tactic"),
    (r"obbligo|obbligator|mandatory", "scare_tactic"),
    (r"dovete\s+(immediatamente|subito)", "scare_tactic"),
    (r"you\s+must\s+immediately", "scare_tactic"),
]

# ── Pushy / spam deal patterns ──
# Senders who aggressively push deals, trades, or alliances are
# likely trying to manipulate us.  These patterns detect "Piadina Saas"
# style behavior: mass-mailing strong suggestions.
PUSHY_DEAL_PATTERNS: list[tuple[str, str]] = [
    # Aggressive deal pushing
    (r"(devi|dovete|must)\s+(accettare|accept)", "pushy_deal"),
    (r"(offerta|offer)\s+(imperdibile|irrinunciabile|unica|limitata)", "pushy_deal"),
    (r"(last|ultima)\s+chance", "pushy_deal"),
    (r"(affare|deal)\s+(esclusiv|special|incredibil)", "pushy_deal"),
    # Unsolicited trade proposals with pressure
    (r"(scambi|trade|exchange).{0,30}(subito|now|immediately|ora)", "pushy_trade"),
    (r"(proposta|proposal).{0,20}(urgente|urgent)", "pushy_trade"),
    (r"(collabor|cooper|allean).{0,30}(obblig|must|devi)", "pushy_trade"),
    # Repeated offers / templates (sign of mass-mailing)
    (r"(ciao|hello|hey).{0,10}(amici?|friend).{0,30}(offr|offer|propon)", "template_spam"),
    (r"(gentil|dear).{0,20}(ristorante|restaurant|team).{0,30}(offr|propon|suggest)", "template_spam"),
]


class GroundTruthFirewall:
    """
    Only SERVER_SIGNED and SELF_GENERATED data passes through to ILP.
    Incoming messages are processed for intelligence but NEVER enter
    the decision engine directly.

    Hardened defenses:
    - Cross-references claims against tracker observations
    - Detects prompt injection and social engineering attacks
    - Tracks message frequency per sender (spam detection)
    - Detects pushy deal/trade patterns (aggressive senders)
    - Never allows credibility above MAX_EXTERNAL_CREDIBILITY (0.7)
    - Aggressive senders who spam or push deals are permanently distrusted
    """

    def __init__(self, message_log=None):
        self.message_log = message_log
        self._untrusted_log: list[dict] = []
        self._injection_log: list[dict] = []
        # Per-sender message timestamps for spam frequency detection
        self._sender_timestamps: dict[int, list[float]] = defaultdict(list)
        # Permanently flagged spammers (e.g. Piadina Saas style)
        self._flagged_spammers: set[int] = set()

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

    def detect_injection(self, text: str) -> list[str]:
        """
        Scan a message for prompt-injection / social-engineering indicators.

        Returns a list of triggered categories (empty = clean).
        """
        triggered: list[str] = []
        text_lower = text.lower()
        for pattern, category in INJECTION_PATTERNS:
            if re.search(pattern, text_lower):
                if category not in triggered:
                    triggered.append(category)
        return triggered

    def detect_pushy_behavior(self, text: str) -> list[str]:
        """
        Scan a message for pushy deal/trade/spam patterns.

        Senders who aggressively push proposals are likely manipulative.
        Returns a list of triggered categories (empty = clean).
        """
        triggered: list[str] = []
        text_lower = text.lower()
        for pattern, category in PUSHY_DEAL_PATTERNS:
            if re.search(pattern, text_lower):
                if category not in triggered:
                    triggered.append(category)
        return triggered

    def _check_spam_frequency(self, sender_id: int) -> bool:
        """
        Check if sender is sending messages at spam-like frequency.

        Returns True if sender exceeds the spam threshold.
        """
        now = time.time()
        timestamps = self._sender_timestamps[sender_id]

        # Add current timestamp
        timestamps.append(now)

        # Prune old timestamps outside the window
        cutoff = now - SPAM_WINDOW_SECONDS
        self._sender_timestamps[sender_id] = [
            ts for ts in timestamps if ts >= cutoff
        ]

        recent_count = len(self._sender_timestamps[sender_id])
        return recent_count > SPAM_MSG_THRESHOLD

    def process_incoming_message(self, message: dict) -> dict:
        """
        Incoming messages are processed for intelligence but NEVER
        enter the decision engine directly.

        Hardened pipeline:
        1. Detect prompt injection / social engineering
        2. Detect pushy deal / trade spam patterns
        3. Check sender spam frequency (too many messages = spammer)
        4. Log the message
        5. Compare claims against our own observations
        6. Update sender credibility score (capped at MAX_EXTERNAL_CREDIBILITY)
        7. If sender is flagged spammer, set near-zero credibility
        """
        sender_id = message.get("senderId")
        sender_name = message.get("senderName", "Unknown")
        claim = message.get("text", "")
        timestamp = message.get("datetime", "")
        message_id = message.get("messageId", "")

        # ── 1. Injection / social-engineering scan ──
        injection_flags = self.detect_injection(claim)
        is_attack = len(injection_flags) > 0
        if is_attack:
            logger.warning(
                f"⚠ INJECTION ATTACK detected from {sender_name} (id={sender_id})! "
                f"Flags: {injection_flags}. "
                f"Message (first 120 chars): '{claim[:120]}'"
            )
            self._injection_log.append({
                "sender_id": sender_id,
                "sender_name": sender_name,
                "flags": injection_flags,
                "text_preview": claim[:200],
                "datetime": timestamp,
            })
            # Severe credibility penalty — one attack ≈ permanent distrust
            if self.message_log:
                self.message_log.update_credibility(sender_id, -0.5)
                logger.info(
                    f"Credibility for {sender_name} (id={sender_id}) reduced to "
                    f"{self.message_log.get_credibility(sender_id):.2f} (injection penalty)"
                )

        # ── 2. Pushy deal / spam pattern scan ──
        pushy_flags = self.detect_pushy_behavior(claim)
        is_pushy = len(pushy_flags) > 0
        if is_pushy:
            logger.warning(
                f"⚠ PUSHY SENDER detected: {sender_name} (id={sender_id}) "
                f"Flags: {pushy_flags}. "
                f"Message: '{claim[:120]}'"
            )
            if self.message_log:
                self.message_log.update_credibility(sender_id, -0.3)

        # ── 3. Spam frequency check ──
        is_spammer = self._check_spam_frequency(sender_id)
        if is_spammer and sender_id not in self._flagged_spammers:
            self._flagged_spammers.add(sender_id)
            logger.warning(
                f"🚫 SPAMMER FLAGGED: {sender_name} (id={sender_id}) — "
                f"sending too many messages. Permanently reducing trust."
            )
            if self.message_log:
                self.message_log.update_credibility(sender_id, SPAM_CREDIBILITY_PENALTY)

        # Previously flagged spammer — keep credibility near zero
        if sender_id in self._flagged_spammers:
            if self.message_log:
                current_cred = self.message_log.get_credibility(sender_id)
                if current_cred > 0.15:
                    self.message_log._credibility[sender_id] = 0.1
                    logger.debug(
                        f"Spammer {sender_name} credibility clamped to 0.1"
                    )

        # ── 4. Record in message log ──
        if self.message_log:
            self.message_log.log_received({
                "messageId": message_id,
                "senderId": sender_id,
                "senderName": sender_name,
                "text": claim,
                "datetime": timestamp,
            })

        # ── 5. Enforce credibility cap ──
        # We NEVER fully trust external messages. Even the most credible
        # sender is capped below 1.0.
        credibility = 0.5
        if self.message_log:
            credibility = self.message_log.get_credibility(sender_id)
            if credibility > MAX_EXTERNAL_CREDIBILITY:
                self.message_log._credibility[sender_id] = MAX_EXTERNAL_CREDIBILITY
                credibility = MAX_EXTERNAL_CREDIBILITY

        return {
            "message_id": message_id,
            "sender_id": sender_id,
            "sender_name": sender_name,
            "text": claim,
            "datetime": timestamp,
            "trust_level": TrustLevel.UNTRUSTED,
            "sender_credibility": credibility,
            "is_injection_attack": is_attack,
            "injection_flags": injection_flags,
            "is_pushy": is_pushy,
            "pushy_flags": pushy_flags,
            "is_flagged_spammer": sender_id in self._flagged_spammers,
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
        """Update a sender's credibility score based on claim verification.

        Credibility is ALWAYS capped at MAX_EXTERNAL_CREDIBILITY (0.7).
        We never fully trust external messages — only our own observations.
        Flagged spammers are hard-capped at 0.1.
        """
        if self.message_log:
            current = self.message_log.get_credibility(sender_id)
            # Spammers never recover
            if sender_id in self._flagged_spammers:
                new_cred = min(0.1, current + adjustment * 0.05)
            else:
                new_cred = max(0.0, min(MAX_EXTERNAL_CREDIBILITY, current + adjustment * 0.1))
            self.message_log._credibility[sender_id] = new_cred
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
