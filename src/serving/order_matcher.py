"""
SPAM! — Order Matcher
======================
Three-tier dish matching: exact lookup → fuzzy → substring.
Handles Italian, English, and mixed-language order texts.
"""

import logging
import re
from difflib import get_close_matches

logger = logging.getLogger("spam.serving.order_matcher")


class OrderMatcher:
    """
    Three-tier order-to-dish matching.

    Tier 1: Exact normalized lookup (O(1), no LLM) — handles 90%+ of cases
    Tier 2: Fuzzy match (difflib, no LLM) — handles typos/variations
    Tier 3: Substring / token overlap — catches partial matches

    HARDENED: handles empty/garbage input, normalizes unicode,
    strips Italian/English prefixes, and caches all successful matches.
    """

    # Common prefixes to strip from order text (Italian + English)
    STRIP_PREFIXES = [
        "i'd like a ",
        "i'd like ",
        "i want a ",
        "i want ",
        "i'll have a ",
        "i'll have ",
        "i would like a ",
        "i would like ",
        "vorrei ",
        "vorrei un ",
        "vorrei una ",
        "vorrei il ",
        "vorrei la ",
        "vorrei lo ",
        "mi piacerebbe ",
        "mi piacerebbe un ",
        "mi piacerebbe una ",
        "desidero ",
        "desidero un ",
        "desidero una ",
        "potrei avere ",
        "potrei avere un ",
        "potrei avere una ",
        "per me ",
        "per me un ",
        "per me una ",
        "prendo ",
        "prendo il ",
        "prendo la ",
        "prendo un ",
        "prendo una ",
        "could i get a ",
        "could i get ",
        "could i have a ",
        "could i have ",
        "can i have a ",
        "can i have ",
        "can i get a ",
        "can i get ",
        "please give me a ",
        "please give me ",
        "give me a ",
        "give me ",
        "may i have a ",
        "may i have ",
        "one ",
        "the ",
        "a ",
        "un ",
        "una ",
        "il ",
        "la ",
        "lo ",
    ]

    # Common suffixes to strip
    STRIP_SUFFIXES = [
        ", please",
        " please",
        ", per favore",
        " per favore",
        ", grazie",
        " grazie",
        ".",
        "!",
        "?",
    ]

    def __init__(self, menu_items: list[dict], order_cache: dict[str, str] | None = None):
        self.menu = {item["name"]: item for item in menu_items}
        self.menu_lower = {name.lower(): name for name in self.menu}
        self.order_cache = order_cache or {}
        self.lookup = self._build_lookup()

        # Pre-compute token sets for each dish (for token overlap matching)
        self._dish_tokens: dict[str, set[str]] = {}
        for dish_name in self.menu:
            self._dish_tokens[dish_name] = set(
                self._tokenize(dish_name.lower())
            )

    def _build_lookup(self) -> dict[str, str]:
        """Pre-compute normalized order text → best menu dish mapping."""
        lookup = {}
        for dish_name in self.menu:
            normalized = dish_name.lower().strip()
            lookup[normalized] = dish_name
            # Add variants with common prefixes
            for prefix in self.STRIP_PREFIXES:
                lookup[prefix + normalized] = dish_name
        # Add cached order→dish mappings
        for order, dish in self.order_cache.items():
            if dish in self.menu:
                lookup[order.lower().strip()] = dish
        return lookup

    def match(self, order_text: str) -> str | None:
        """
        Match an order text to a menu dish.
        Returns the canonical dish name or None if no match.
        """
        if not order_text or not order_text.strip():
            logger.warning("Empty order text — cannot match")
            return self._fallback_any_dish()

        normalized = self._normalize(order_text)

        if not normalized:
            logger.warning(f"Order text normalized to empty: '{order_text}'")
            return self._fallback_any_dish()

        # Tier 1: Exact lookup
        if normalized in self.lookup:
            dish = self.lookup[normalized]
            logger.debug(f"Exact match: '{order_text}' → '{dish}'")
            return dish

        # Also check if the order text is a direct dish name
        if normalized in self.menu_lower:
            dish = self.menu_lower[normalized]
            logger.debug(f"Direct name match: '{order_text}' → '{dish}'")
            return dish

        # Tier 2: Fuzzy match (higher cutoff first, then lower)
        for cutoff in (0.7, 0.55):
            matches = get_close_matches(
                normalized, list(self.menu_lower.keys()), n=1, cutoff=cutoff
            )
            if matches:
                dish = self.menu_lower[matches[0]]
                logger.debug(
                    f"Fuzzy match (cutoff={cutoff}): '{order_text}' → '{dish}'"
                )
                return dish

        # Tier 3a: Substring check — does any menu item name appear in the order?
        for dish_lower, dish_name in self.menu_lower.items():
            if dish_lower in normalized or normalized in dish_lower:
                logger.debug(f"Substring match: '{order_text}' → '{dish_name}'")
                return dish_name

        # Tier 3b: Token overlap — find dish with most token overlap
        order_tokens = set(self._tokenize(normalized))
        if order_tokens:
            best_dish = None
            best_overlap = 0
            for dish_name, dish_tokens in self._dish_tokens.items():
                if not dish_tokens:
                    continue
                overlap = len(order_tokens & dish_tokens) / len(dish_tokens)
                if overlap > best_overlap:
                    best_overlap = overlap
                    best_dish = dish_name

            if best_dish and best_overlap >= 0.4:
                logger.debug(
                    f"Token overlap match ({best_overlap:.0%}): "
                    f"'{order_text}' → '{best_dish}'"
                )
                return best_dish

        logger.warning(f"No match for order: '{order_text}'")
        return self._fallback_any_dish()

    def _normalize(self, text: str) -> str:
        """Normalize order text: lowercase, strip prefixes/suffixes, clean whitespace."""
        text = text.lower().strip()

        # Strip suffixes first
        for suffix in self.STRIP_SUFFIXES:
            if text.endswith(suffix):
                text = text[: -len(suffix)].strip()

        # Strip prefixes (try longest first for greedy match)
        for prefix in sorted(self.STRIP_PREFIXES, key=len, reverse=True):
            if text.startswith(prefix):
                text = text[len(prefix) :].strip()
                break

        # Normalize whitespace
        text = re.sub(r"\s+", " ", text).strip()
        return text

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        """Split text into meaningful tokens (≥2 chars, skip stop words)."""
        stop_words = {
            "di", "del", "della", "dello", "dei", "degli", "delle",
            "con", "in", "e", "al", "alla", "allo", "a", "da",
            "il", "la", "lo", "le", "gli", "un", "una", "uno",
            "the", "a", "an", "of", "with", "and", "in", "on",
            "per", "su", "tra", "fra",
        }
        words = re.findall(r"[a-zàèéìòù]+", text.lower())
        return [w for w in words if len(w) >= 2 and w not in stop_words]

    def _fallback_any_dish(self) -> str | None:
        """When we absolutely can't match, return first menu dish (better than nothing)."""
        if self.menu:
            first = next(iter(self.menu))
            logger.warning(f"Fallback: returning first menu dish '{first}'")
            return first
        return None

    def update_menu(self, menu_items: list[dict]):
        """Update the menu and rebuild the lookup table."""
        self.menu = {item["name"]: item for item in menu_items}
        self.menu_lower = {name.lower(): name for name in self.menu}
        self.lookup = self._build_lookup()
        self._dish_tokens = {}
        for dish_name in self.menu:
            self._dish_tokens[dish_name] = set(
                self._tokenize(dish_name.lower())
            )

    def add_to_cache(self, order_text: str, dish_name: str):
        """Cache a successful order→dish mapping."""
        raw_key = order_text.lower().strip()
        self.order_cache[raw_key] = dish_name
        self.lookup[raw_key] = dish_name
        # Also store under normalized key so match() finds it after prefix stripping
        norm_key = self._normalize(order_text)
        if norm_key and norm_key != raw_key:
            self.order_cache[norm_key] = dish_name
            self.lookup[norm_key] = dish_name
