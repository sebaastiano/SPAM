"""
SPAM! — Archetype Classifier (v2 — Hybrid: Rule-based + LLM)
==============================================================
Two-tier archetype inference from natural-language order text:

  **Tier 1 — Rule-based fast-path (0 ms)**
    Keyword / regex scoring against known archetype signal words.
    Handles ~60-70% of orders with high confidence and zero latency.

  **Tier 2 — LLM fallback (gpt-oss-120b via Regolo.ai)**
    For ambiguous orders where no single archetype dominates,
    call the LLM for a nuanced classification. Adds ~0.5-2s latency
    per unique order (cached for repeats).

Why this matters:
  The `client_spawned` SSE event gives us `clientName` (a person's name,
  NOT an archetype label) and `orderText`.  The order text is rich with
  linguistic signals (tone, urgency, price sensitivity, quality language)
  that reveal the archetype.

  Knowing the archetype unlocks:
    1. **Archetype-aware dish routing** — prestige dishes for Astrobarone,
       budget-friendly for Esploratore, balanced for Famiglie.
    2. **Better intolerance priors** — archetype-specific Bayesian updates.
    3. **Serving priority** — Astrobarone (impatient, high-value) first.
    4. **Cross-turn learning** — archetype distributions feed into menu
       composition and zone selection.
"""

import asyncio
import json
import logging
import re
from dataclasses import dataclass

from src.config import REGOLO_API_KEY, REGOLO_BASE_URL, PRIMARY_MODEL

logger = logging.getLogger("spam.serving.archetype_classifier")

# Lazy import: datapizza may not be installed in test environments
OpenAILikeClient = None  # type: ignore[assignment]


def _get_openai_client_class():
    """Lazy-load datapizza OpenAILikeClient."""
    global OpenAILikeClient
    if OpenAILikeClient is None:
        from datapizza.clients.openai_like import OpenAILikeClient as _cls
        OpenAILikeClient = _cls
    return OpenAILikeClient

# ── Canonical archetype names (must match the rest of the codebase) ──
ARCHETYPES = [
    "Esploratore Galattico",
    "Astrobarone",
    "Saggi del Cosmo",
    "Famiglie Orbitali",
]

# ══════════════════════════════════════════════════════════════════
#  TIER 1 — RULE-BASED KEYWORD SCORING
# ══════════════════════════════════════════════════════════════════
#
# Each archetype has weighted keyword groups. We score every order
# against all four archetypes simultaneously. If the top archetype
# has a clear lead (score >= threshold AND margin >= gap over runner-up),
# we return it instantly without calling the LLM.
#
# Keywords drawn from the game's archetype definitions + common
# Italian/English order patterns observed in Hackapizza 2.0.

_KEYWORDS: dict[str, list[tuple[str, float]]] = {
    "Esploratore Galattico": [
        # Urgency / speed
        (r"\bveloc[ei]\b", 2.0),
        (r"\bin fretta\b", 2.5),
        (r"\bsbrigati\b", 2.0),
        (r"\brapid[oa]\b", 1.5),
        (r"\bquick(?:ly)?\b", 2.0),
        (r"\bhurr(?:y|ied)\b", 2.0),
        (r"\bfast\b", 2.0),
        (r"\bsubito\b", 1.0),  # shared w/ Astrobarone (lower weight here)
        # Cheapness / budget
        (r"\beconomic[oa]\b", 2.5),
        (r"\bpoco\b", 1.5),
        (r"\bcheap\b", 2.0),
        (r"\bbudget\b", 2.0),
        (r"\bsemplicem?\b", 1.5),
        (r"\bsimple\b", 1.5),
        (r"\bbasic\b", 1.5),
        (r"\bqualsiasi\b", 1.5),  # "anything"
        (r"\bqualunque\b", 1.5),
        (r"\bwhatever\b", 1.5),
        # Indifference to quality
        (r"\bcommestibile\b", 3.0),  # "as long as it's edible"
        (r"\bedible\b", 2.5),
        (r"\bnon.{0,5}import[ai]\b", 1.5),  # "non importa"
        (r"\bdon'?t care\b", 1.5),
        (r"\banything\b", 1.0),
        (r"\bwhatever.{0,5}fine\b", 1.5),
        # Short / terse orders
        (r"\balla svelta\b", 2.0),
        (r"\bspicciati\b", 2.0),
    ],
    "Astrobarone": [
        # Status / prestige / luxury
        (r"\bprestigio[so]?\b", 3.0),
        (r"\besclusiv[oa]\b", 2.5),
        (r"\braffinat[oa]\b", 2.5),
        (r"\bluss[uo]\b", 2.5),
        (r"\bluxur(?:y|ious)\b", 2.5),
        (r"\bprestigiou?s\b", 3.0),
        (r"\bexclusiv[oe]\b", 2.5),
        (r"\brefined\b", 2.0),
        (r"\belegant[ei]?\b", 2.0),
        (r"\bil migliore\b", 2.5),
        (r"\bil vostro migliore\b", 3.0),
        (r"\bthe best\b", 2.5),
        (r"\bfinest\b", 2.5),
        (r"\btop\b", 1.0),
        (r"\bsuperb[oa]?\b", 2.0),
        # Impatience + authority
        (r"\bsubito\b", 1.5),  # "immediately" — stronger signal here
        (r"\bnon ho tempo\b", 2.5),
        (r"\bnon.{0,5}aspett\b", 2.0),  # "non aspettare"
        (r"\bimmediatel?y?\b", 1.5),
        (r"\bright now\b", 1.5),
        # Price indifference (affluence)
        (r"\bnon.{0,5}bado.{0,5}al prezzo\b", 3.0),
        (r"\bmoney.{0,5}no.{0,5}object\b", 3.0),
        (r"\bprezzo.{0,5}non.{0,5}(?:e|è).{0,5}un.{0,5}problema\b", 3.0),
        (r"\bcost.{0,5}doesn.?t.{0,5}matter\b", 2.5),
        (r"\bexpense\b", 1.5),
        (r"\bpremium\b", 2.0),
        (r"\bpreg(?:iat|evol)[oaei]\b", 2.0),  # "pregiato/pregevole"
    ],
    "Saggi del Cosmo": [
        # Patience / contemplation
        (r"\bcon calma\b", 2.5),
        (r"\bprenditi.{0,5}tempo\b", 2.5),
        (r"\bnon.{0,5}(?:ho|c'è).{0,5}fretta\b", 2.5),
        (r"\btake.{0,5}(?:your|all).{0,5}time\b", 2.5),
        (r"\bno.{0,5}rush\b", 2.0),
        (r"\bpatien(?:t|ce|za)\b", 1.5),
        # Excellence / rarity / cosmic
        (r"\beccellen[tz][ea]\b", 2.5),
        (r"\bexcellen(?:t|ce)\b", 2.5),
        (r"\brar[oa]\b", 2.0),
        (r"\brare\b", 2.0),
        (r"\bpreg(?:iat|evol)[oaei]\b", 1.5),
        (r"\bcosmic[oa]?\b", 2.0),
        (r"\bstellar[ei]?\b", 1.5),
        (r"\bgalattic[oa]\b", 1.0),
        (r"\bstraordinar[ioae]\b", 2.0),
        (r"\bextraordinar(?:y|io)\b", 2.0),
        # Cultural / philosophical / poetic
        (r"\btradizion[ei]\b", 2.0),
        (r"\btradition(?:al)?\b", 2.0),
        (r"\bsapien[tz]a\b", 2.0),
        (r"\bwisdom\b", 2.0),
        (r"\bcontemplat\b", 2.0),
        (r"\bmeditat\b", 1.5),
        (r"\barmoni[ae]\b", 1.5),
        (r"\bharmon(?:y|ious)\b", 1.5),
        (r"\bantico\b", 1.5),
        (r"\bancient\b", 1.5),
        (r"\bricerca\b", 1.5),  # "research/quest"
        (r"\bquest\b", 1.0),
        (r"\besperienza\b", 1.5),
        (r"\bexperience\b", 1.5),
    ],
    "Famiglie Orbitali": [
        # Value / balance / affordability
        (r"\brapporto.{0,5}qualit[àa].{0,5}prezzo\b", 3.0),
        (r"\bvalue.{0,5}for.{0,5}money\b", 3.0),
        (r"\bequilibrat[oa]\b", 2.5),
        (r"\bbalanced?\b", 2.0),
        (r"\bragionevol[ei]\b", 2.0),
        (r"\breasonabl[ey]\b", 2.0),
        (r"\baccessibil[ei]\b", 2.0),
        (r"\baffordabl[ey]\b", 2.0),
        (r"\bnon.{0,5}troppo.{0,5}car[oa]\b", 2.5),
        (r"\bnot.{0,5}too.{0,5}expensive\b", 2.5),
        # Family references
        (r"\bfamigli[ae]\b", 3.0),
        (r"\bfamily\b", 3.0),
        (r"\bbambin[oi]\b", 2.5),
        (r"\bchild(?:ren)?\b", 2.5),
        (r"\bkids?\b", 2.0),
        (r"\bpiccol[oi]\b", 1.5),
        (r"\blittle.{0,5}ones?\b", 1.5),
        (r"\btutti\b", 1.5),  # "for everyone"
        (r"\beveryone\b", 1.5),
        (r"\bper tutti\b", 2.5),
        (r"\bfor.{0,5}all\b", 1.5),
        # Moderation / care
        (r"\bmoderat[oa]\b", 1.5),
        (r"\bsicur[oa]\b", 1.5),  # "safe"
        (r"\bsafe\b", 1.5),
        (r"\bsalutare\b", 1.5),  # "healthy"
        (r"\bhealthy\b", 1.5),
        (r"\bdietary\b", 1.5),
        (r"\ballergi[eac]\b", 1.5),
        (r"\bintolleran[tz]\b", 1.0),  # dietary concern signal
    ],
}

# ── Scoring thresholds ──
FAST_PATH_MIN_SCORE = 2.0     # minimum score for top archetype
FAST_PATH_MIN_MARGIN = 1.0    # minimum gap between top and runner-up
FAST_PATH_HIGH_CONF = 4.0     # above this -> confidence = 0.95


@dataclass
class ClassificationResult:
    """Result of an archetype classification."""
    archetype: str
    confidence: float
    method: str  # "rules", "llm", "fallback", etc.


# ── Pre-compile all keyword regexes for speed ──
_COMPILED_KEYWORDS: dict[str, list[tuple[re.Pattern, float]]] = {}
for _arch, _kw_list in _KEYWORDS.items():
    _COMPILED_KEYWORDS[_arch] = [
        (re.compile(pattern, re.IGNORECASE), weight)
        for pattern, weight in _kw_list
    ]


def classify_fast(order_text: str) -> ClassificationResult | None:
    """
    Tier 1 -- Rule-based keyword classification.

    Scores the order text against all 4 archetype keyword sets.
    Returns a ClassificationResult if one archetype clearly dominates,
    or None if the result is ambiguous (triggering LLM fallback).

    Complexity: O(N * K) where N = len(order_text), K = total keywords.
    Latency: <1ms even for long orders.
    """
    if not order_text or not order_text.strip():
        return None

    text = order_text.lower().strip()

    scores: dict[str, float] = {arch: 0.0 for arch in ARCHETYPES}

    for arch, patterns in _COMPILED_KEYWORDS.items():
        for regex, weight in patterns:
            if regex.search(text):
                scores[arch] += weight

    # Sort by score descending
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    top_arch, top_score = ranked[0]
    runner_up_score = ranked[1][1]
    margin = top_score - runner_up_score

    # Decision: is the top archetype clear enough?
    if top_score >= FAST_PATH_MIN_SCORE and margin >= FAST_PATH_MIN_MARGIN:
        # Confidence scales with score and margin
        if top_score >= FAST_PATH_HIGH_CONF:
            confidence = 0.95
        else:
            confidence = min(0.90, 0.60 + (margin / 10.0) + (top_score / 20.0))

        logger.debug(
            f"[RULES] '{order_text[:60]}' -> {top_arch} "
            f"(score={top_score:.1f}, margin={margin:.1f}, conf={confidence:.2f})"
        )
        return ClassificationResult(
            archetype=top_arch,
            confidence=confidence,
            method="rules",
        )

    # Ambiguous -- not enough signal for a confident classification
    logger.debug(
        f"[RULES] Ambiguous: '{order_text[:60]}' -- "
        f"top={top_arch}({top_score:.1f}), margin={margin:.1f} -> LLM fallback"
    )
    return None


# ══════════════════════════════════════════════════════════════════
#  TIER 2 — LLM FALLBACK
# ══════════════════════════════════════════════════════════════════

_LLM_SYSTEM_PROMPT = """\
You are a client-archetype classifier for a galactic restaurant game.

Given a client's order text, determine which of the 4 archetypes they belong to.

## Archetypes

1. **Esploratore Galattico**
   - In a hurry, low budget, not picky about quality ("purche sia commestibile")
   - Language cues: urgency ("veloce", "in fretta", "sbrigati"), cheapness
     ("economico", "poco", "semplice"), indifference to quality
   - Orders tend to be short, direct, no-frills

2. **Astrobarone**
   - Extremely short on time, demands quality, money is no object
   - Language cues: status/prestige ("il migliore", "prestigioso", "esclusivo",
     "raffinato"), impatience ("subito", "non ho tempo"), price indifference
   - Orders are assertive, may reference luxury or status

3. **Saggi del Cosmo**
   - Patient, seeks excellence, price-insensitive
   - Language cues: contemplation ("con calma", "prenditi tempo"), quality
     ("eccellente", "raro", "pregiato", "cosmico"), cultural/narrative
     references, philosophical tone
   - Orders are elaborate, poetic, may reference lore or ingredients

4. **Famiglie Orbitali**
   - Patient, watches both price and quality, seeks balance
   - Language cues: value ("buon rapporto qualita-prezzo", "equilibrato",
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
    Hybrid archetype classifier: rule-based fast-path + LLM fallback.

    Usage::

        classifier = ArchetypeClassifier()
        result = await classifier.classify(order_text, client_name)
        # result.archetype, result.confidence, result.method

    The classifier is fully async and safe to use in the serving pipeline.
    Results are cached in-memory (order_text -> result) so repeated orders
    incur zero cost.
    """

    def __init__(self, client=None):
        self._explicit_client = client
        self._client = None  # lazy-initialized on first LLM call
        # In-memory cache: normalized_order_text -> ClassificationResult
        self._cache: dict[str, ClassificationResult] = {}
        # Stats
        self.stats = {
            "rules_hits": 0,
            "llm_hits": 0,
            "llm_errors": 0,
            "cache_hits": 0,
            "total": 0,
        }

    def _get_client(self):
        """Lazy-initialize the LLM client on first use."""
        if self._client is None:
            if self._explicit_client is not None:
                self._client = self._explicit_client
            else:
                cls = _get_openai_client_class()
                self._client = cls(
                    api_key=REGOLO_API_KEY,
                    model=PRIMARY_MODEL,
                    base_url=REGOLO_BASE_URL,
                    system_prompt=_LLM_SYSTEM_PROMPT,
                )
        return self._client

    async def classify(
        self,
        order_text: str,
        client_name: str = "",
    ) -> ClassificationResult:
        """
        Classify a client's archetype from their order text.

        Tier 1: Rule-based keyword scoring (instant).
        Tier 2: LLM call via Regolo.ai (if Tier 1 is ambiguous).

        Results are cached -- repeated order texts return instantly.

        Args:
            order_text:  The raw orderText from SSE or /meals.
            client_name: The clientName -- extra context, not primary signal.

        Returns:
            ClassificationResult with archetype, confidence, method.
            Falls back to ("unknown", 0.0, "fallback") on total failure.
        """
        self.stats["total"] += 1

        # -- Cache hit --
        cache_key = order_text.strip().lower()
        if cache_key in self._cache:
            self.stats["cache_hits"] += 1
            return self._cache[cache_key]

        # -- Tier 1: Rule-based fast-path --
        result = classify_fast(order_text)
        if result is not None:
            self.stats["rules_hits"] += 1
            self._cache[cache_key] = result
            logger.info(
                f"[FAST] '{order_text[:50]}' -> {result.archetype} "
                f"(conf={result.confidence:.2f})"
            )
            return result

        # -- Tier 2: LLM fallback --
        result = await self._classify_llm(order_text, client_name)
        self._cache[cache_key] = result
        return result

    def classify_sync(self, order_text: str) -> ClassificationResult:
        """
        Synchronous classification -- rule-based only (for non-async contexts).

        Does NOT call the LLM. Returns "unknown" if rules are ambiguous.
        """
        self.stats["total"] += 1

        cache_key = order_text.strip().lower()
        if cache_key in self._cache:
            self.stats["cache_hits"] += 1
            return self._cache[cache_key]

        result = classify_fast(order_text)
        if result is not None:
            self.stats["rules_hits"] += 1
            self._cache[cache_key] = result
            return result

        return ClassificationResult(
            archetype="unknown", confidence=0.0, method="rules_only"
        )

    async def _classify_llm(
        self, order_text: str, client_name: str
    ) -> ClassificationResult:
        """Tier 2 -- LLM classification via Regolo.ai."""
        user_msg = f'Client name: "{client_name}"\nOrder text: "{order_text}"'

        try:
            client = self._get_client()
            response = await asyncio.wait_for(
                client.a_complete(user_msg),
                timeout=5.0,  # hard cap: don't block serving for >5s
            )
            raw = response.text.strip()
            result = self._parse_response(raw)
            self.stats["llm_hits"] += 1
            logger.info(
                f"[LLM] '{order_text[:50]}' -> {result.archetype} "
                f"(conf={result.confidence:.2f})"
            )
            return result

        except asyncio.TimeoutError:
            logger.warning(f"LLM classification timed out for: '{order_text[:60]}'")
            self.stats["llm_errors"] += 1
            return ClassificationResult(
                archetype="unknown", confidence=0.0, method="llm_timeout"
            )
        except Exception as exc:
            logger.error(f"LLM classification failed: {exc}")
            self.stats["llm_errors"] += 1
            return ClassificationResult(
                archetype="unknown", confidence=0.0, method="llm_error"
            )

    @staticmethod
    def _parse_response(raw: str) -> ClassificationResult:
        """Parse the LLM's JSON response."""
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            lines = [l for l in lines if not l.strip().startswith("```")]
            cleaned = "\n".join(lines).strip()

        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", cleaned, re.DOTALL)
            if match:
                data = json.loads(match.group())
            else:
                logger.warning(f"Could not parse LLM response: {raw[:120]}")
                return ClassificationResult(
                    archetype="unknown", confidence=0.0, method="llm_parse_error"
                )

        archetype = data.get("archetype", "unknown")
        confidence = float(data.get("confidence", 0.0))

        # Validate archetype name -- fuzzy match against canonical
        if archetype not in ARCHETYPES:
            arch_lower = archetype.lower()
            for canonical in ARCHETYPES:
                if canonical.lower() in arch_lower or arch_lower in canonical.lower():
                    archetype = canonical
                    break
            else:
                logger.warning(f"Unknown archetype from LLM: '{archetype}'")
                archetype = "unknown"

        confidence = max(0.0, min(1.0, confidence))
        return ClassificationResult(
            archetype=archetype,
            confidence=confidence,
            method="llm",
        )

    def clear_cache(self):
        """Clear the classification cache (e.g., between games)."""
        self._cache.clear()

    def get_stats_summary(self) -> str:
        """Human-readable stats summary."""
        s = self.stats
        total = max(s["total"], 1)
        return (
            f"Archetype Classifier: {s['total']} total | "
            f"rules={s['rules_hits']} ({s['rules_hits']/total:.0%}) | "
            f"llm={s['llm_hits']} ({s['llm_hits']/total:.0%}) | "
            f"cache={s['cache_hits']} | errors={s['llm_errors']}"
        )
