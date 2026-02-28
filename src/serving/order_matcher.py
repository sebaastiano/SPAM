"""
SPAM! — Order Matcher
======================
Three-tier dish matching: exact lookup → fuzzy → LLM fallback.
"""

import logging
from difflib import get_close_matches

logger = logging.getLogger("spam.serving.order_matcher")


class OrderMatcher:
    """
    Three-tier order-to-dish matching.

    Tier 1: Exact normalized lookup (O(1), no LLM) — handles 90%+ of cases
    Tier 2: Fuzzy match (difflib, no LLM) — handles typos/variations
    Tier 3: LLM fallback (only for truly ambiguous orders) — <5% of cases
    """

    # Common prefixes to strip from order text
    STRIP_PREFIXES = [
        "i'd like a ",
        "i'd like ",
        "i want a ",
        "i want ",
        "i'll have a ",
        "i'll have ",
        "vorrei ",
        "mi piacerebbe ",
        "could i get a ",
        "could i get ",
        "can i have a ",
        "can i have ",
        "please give me a ",
        "please give me ",
        "one ",
        "the ",
    ]

    def __init__(self, menu_items: list[dict], order_cache: dict[str, str] | None = None):
        """
        Args:
            menu_items: List of menu items [{name: str, price: float}, ...]
            order_cache: Optional cached order→dish mappings from GlobalClientLibrary
        """
        self.menu = {item["name"]: item for item in menu_items}
        self.menu_lower = {name.lower(): name for name in self.menu}
        self.order_cache = order_cache or {}
        self.lookup = self._build_lookup()

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
        normalized = self._normalize(order_text)

        # Tier 1: Exact lookup
        if normalized in self.lookup:
            logger.debug(f"Exact match: '{order_text}' → '{self.lookup[normalized]}'")
            return self.lookup[normalized]

        # Also check if the order text is a direct dish name
        if normalized in self.menu_lower:
            return self.menu_lower[normalized]

        # Tier 2: Fuzzy match
        matches = get_close_matches(
            normalized, list(self.menu_lower.keys()), n=1, cutoff=0.6
        )
        if matches:
            dish = self.menu_lower[matches[0]]
            logger.debug(f"Fuzzy match: '{order_text}' → '{dish}' (score≥0.6)")
            return dish

        # Tier 3: Substring check — does any menu item name appear in the order?
        for dish_lower, dish_name in self.menu_lower.items():
            if dish_lower in normalized or normalized in dish_lower:
                logger.debug(f"Substring match: '{order_text}' → '{dish_name}'")
                return dish_name

        logger.warning(f"No match for order: '{order_text}'")
        return None

    def _normalize(self, text: str) -> str:
        """Normalize order text by lowercasing and stripping common prefixes."""
        text = text.lower().strip()
        for prefix in self.STRIP_PREFIXES:
            if text.startswith(prefix):
                text = text[len(prefix):].strip()
                break
        return text

    def update_menu(self, menu_items: list[dict]):
        """Update the menu and rebuild the lookup table."""
        self.menu = {item["name"]: item for item in menu_items}
        self.menu_lower = {name.lower(): name for name in self.menu}
        self.lookup = self._build_lookup()

    def add_to_cache(self, order_text: str, dish_name: str):
        """Cache a successful order→dish mapping."""
        normalized = order_text.lower().strip()
        self.order_cache[normalized] = dish_name
        self.lookup[normalized] = dish_name
