"""
Order matcher — 3-tier dish matching (exact → fuzzy → LLM fallback).
"""

from __future__ import annotations

from difflib import get_close_matches
from typing import Any


class OrderMatcher:
    """Maps raw ``orderText`` strings to menu dish names.

    Tier 1: exact normalised lookup (O(1), no LLM)
    Tier 2: fuzzy match via ``difflib`` (no LLM)
    Tier 3: LLM fallback (placeholder — only for truly ambiguous orders)
    """

    def __init__(self) -> None:
        # normalised_order → dish_name
        self._exact: dict[str, str] = {}
        # dish_name → dish_name (canonical casing)
        self._dishes: dict[str, str] = {}

    def build_lookup(self, menu_items: list[dict[str, Any]]) -> None:
        """Pre-compute lookup table from current menu."""
        self._exact.clear()
        self._dishes.clear()
        for item in menu_items:
            name: str = item.get("name", "")
            if not name:
                continue
            norm = name.lower().strip()
            self._dishes[norm] = name
            self._exact[norm] = name
            # Alias with common order prefixes stripped
            for prefix in (
                "i'd like a ",
                "i'd like ",
                "vorrei ",
                "mi piacerebbe ",
            ):
                self._exact[prefix + norm] = name

    def match(self, order_text: str) -> str | None:
        """Return the best matching dish name, or ``None``."""
        norm = self._normalise(order_text)

        # Tier 1: exact
        if norm in self._exact:
            return self._exact[norm]

        # Tier 2: fuzzy
        matches = get_close_matches(norm, self._dishes.keys(), n=1, cutoff=0.6)
        if matches:
            return self._dishes[matches[0]]

        # Tier 3: LLM fallback (not implemented — returns None)
        return None

    @staticmethod
    def _normalise(text: str) -> str:
        text = text.lower().strip()
        for prefix in ("i'd like a ", "i'd like ", "vorrei ", "mi piacerebbe "):
            if text.startswith(prefix):
                text = text[len(prefix):]
                break
        return text.strip()
