"""
SPAM! — Archetype Classifier
===============================
Uses Regolo.ai (gpt-oss-120b) via datapizza OpenAILikeClient to infer the
client archetype from the natural-language order text.

Why this exists:
  The `client_spawned` SSE event gives us `clientName` (which is a person's
  name, NOT an archetype label) and `orderText`.  The current
  `classify_archetype()` in priority_queue.py tries a string match on the
  name, but person names like "Zork-7" or "Mara Stellanova" carry no
  archetype signal.

  The *order text*, however, is rich with signals:
    - Tone / urgency  → "qualcosa di veloce" (Esploratore), "il vostro
      piatto più prestigioso" (Astrobarone)
    - Price sensitivity → "economico" vs. "non bado al prezzo"
    - Quality language  → "commestibile" vs. "eccellenza culinaria"
    - Time language     → "in fretta" vs. "prenditi tutto il tempo"

  By classifying the archetype *from the order text* we unlock:
    1. **Better serving priority** — we can promote/demote clients in the
       priority queue based on inferred archetype rather than guessing
       from a person name.
    2. **Intolerance-aware dish selection** — archetype-specific intolerance
       priors differ; knowing the archetype lets us pick safer dishes.
    3. **Price/prestige alignment** — we know which prestige band to match
       (23-50 vs ≥85) and can route to the correct dish.
    4. **Cross-turn profiling** — aggregated archetype distributions per
       turn feed back into menu composition, zone selection, and the
       client library for future turns.
"""

import asyncio
import json
import logging
from functools import lru_cache

from datapizza.clients.openai_like import OpenAILikeClient

from src.config import REGOLO_API_KEY, REGOLO_BASE_URL, PRIMARY_MODEL

logger = logging.getLogger("spam.serving.archetype_classifier")

# ── Canonical archetype names (must match the rest of the codebase) ──
ARCHETYPES = [
    "Esploratore Galattico",
    "Astrobarone",
    "Saggi del Cosmo",
    "Famiglie Orbitali",
]

_SYSTEM_PROMPT = """\
You are a client-archetype classifier for a galactic restaurant game.

Given a client's order text, determine which of the 4 archetypes they belong to.

## Archetypes

1. **Esploratore Galattico** 🚀
   - In a hurry, low budget, not picky about quality ("purché sia commestibile")
   - Language cues: urgency ("veloce", "in fretta", "sbrigati"), cheapness
     ("economico", "poco", "semplice"), indifference to quality
   - Orders tend to be short, direct, no-frills

2. **Astrobarone** 💰
   - Extremely short on time, demands quality, money is no object
   - Language cues: status/prestige ("il migliore", "prestigioso", "esclusivo",
     "raffinato"), impatience ("subito", "non ho tempo"), price indifference
   - Orders are assertive, may reference luxury or status

3. **Saggi del Cosmo** 🔭
   - Patient, seeks excellence, price-insensitive
   - Language cues: contemplation ("con calma", "prenditi tempo"), quality
     ("eccellente", "raro", "pregiato", "cosmico"), cultural/narrative
     references, philosophical tone
   - Orders are elaborate, poetic, may reference lore or ingredients

4. **Famiglie Orbitali** 👨‍👩‍👧‍👦
   - Patient, watches both price and quality, seeks balance
   - Language cues: value ("buon rapporto qualità-prezzo", "equilibrato",
     "per tutti"), family references, moderation ("non troppo caro",
     "accessibile"), care for dietary needs
   - Orders mention balance, fairness, or family

## Response format

Respond with ONLY a JSON object:
{"archetype": "<one of the 4 names>", "confidence": <0.0-1.0>}

Do NOT include any other text.
"""


class ArchetypeClassifier:
    """
    Infer client archetype from order text via Regolo.ai LLM call.

    Uses gpt-oss-120b through datapizza's OpenAILikeClient pointed at
    Regolo's /v1/chat/completions endpoint, as mandated by the hackathon guidelines.

    The call is async and non-blocking; the serving pipeline can
    fire-and-forget or await the result depending on latency budget.
    """

    def __init__(self, client: OpenAILikeClient | None = None):
        """
        Args:
            client: Pre-configured datapizza OpenAILikeClient.
                    If None, a dedicated client is created.
        """
        self._client = client or OpenAILikeClient(
            api_key=REGOLO_API_KEY,
            model=PRIMARY_MODEL,
            base_url=REGOLO_BASE_URL,
            system_prompt=_SYSTEM_PROMPT,
        )
        # In-memory cache: order_text → (archetype, confidence)
        self._cache: dict[str, tuple[str, float]] = {}

    async def classify(
        self,
        order_text: str,
        client_name: str = "",
    ) -> tuple[str, float]:
        """
        Classify a client's archetype from their order text.

        Args:
            order_text:  The raw `orderText` from the `client_spawned` SSE event.
            client_name: The `clientName` — passed as extra context but NOT the
                         primary signal (it's a person's name, not an archetype).

        Returns:
            (archetype, confidence) where archetype ∈ ARCHETYPES and
            confidence ∈ [0.0, 1.0].  Falls back to ("unknown", 0.0) on
            failure.
        """
        # ── Cache hit ──
        cache_key = order_text.strip().lower()
        if cache_key in self._cache:
            logger.debug(f"Cache hit for '{order_text[:40]}…'")
            return self._cache[cache_key]

        # ── Build prompt ──
        user_msg = f'Client name: "{client_name}"\nOrder text: "{order_text}"'

        try:
            response = await self._client.a_complete(user_msg)
            raw = response.text.strip()
            result = self._parse_response(raw)
            self._cache[cache_key] = result
            logger.info(
                f"Classified '{order_text[:50]}…' → "
                f"{result[0]} (conf={result[1]:.2f})"
            )
            return result

        except Exception as exc:
            logger.error(f"Archetype classification failed: {exc}")
            return ("unknown", 0.0)

    # ──────────────────── internals ────────────────────

    @staticmethod
    def _parse_response(raw: str) -> tuple[str, float]:
        """
        Parse the LLM's JSON response into (archetype, confidence).

        Tolerates markdown code fences and minor formatting noise.
        """
        # Strip markdown code fences if present
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            # Remove opening and closing fences
            lines = cleaned.split("\n")
            lines = [l for l in lines if not l.strip().startswith("```")]
            cleaned = "\n".join(lines).strip()

        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError:
            # last-resort: try to find JSON object in the response
            import re
            match = re.search(r"\{.*\}", cleaned, re.DOTALL)
            if match:
                data = json.loads(match.group())
            else:
                logger.warning(f"Could not parse archetype response: {raw[:120]}")
                return ("unknown", 0.0)

        archetype = data.get("archetype", "unknown")
        confidence = float(data.get("confidence", 0.0))

        # Validate archetype name
        if archetype not in ARCHETYPES:
            # Fuzzy match against canonical names
            arch_lower = archetype.lower()
            for canonical in ARCHETYPES:
                if canonical.lower() in arch_lower or arch_lower in canonical.lower():
                    archetype = canonical
                    break
            else:
                logger.warning(f"Unknown archetype from LLM: '{archetype}'")
                archetype = "unknown"

        confidence = max(0.0, min(1.0, confidence))
        return (archetype, confidence)

    def clear_cache(self):
        """Clear the classification cache (e.g., between games)."""
        self._cache.clear()
