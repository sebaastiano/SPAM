"""
SPAM! — Order Matcher (v3 — Ingredient-aware + LLM fallback)
================================================================
Multi-tier dish matching that handles both:
  - Direct dish name orders: "I want Sinfonia Cosmica"
  - Ingredient-list orders: "I want something with X, Y, Z"
  - Intolerance declarations: "... I'm intolerant to Funghi Orbitali"

Matching tiers:
  T0: Cache lookup (instant, from previous successful matches)
  T1: Exact/fuzzy dish name matching (no LLM)
  T2: Ingredient-set matching — parse ingredients from text, find best
      recipe on menu whose ingredient set matches (deterministic, fast)
  T3: LLM fallback — delegate to fast LLM for complex/ambiguous text
"""

import logging
import re
from difflib import get_close_matches

logger = logging.getLogger("spam.serving.order_matcher")


class OrderMatcher:
    """
    Ingredient-aware order-to-dish matching with LLM fallback.

    Initialise with menu items AND the full recipe DB so we can match
    orders that list ingredients rather than dish names.
    """

    # Regex patterns to detect ingredient-list orders
    _INGREDIENT_ORDER_PATTERNS = [
        # "I want something with X, Y, and Z"
        r"(?:i\s+want|i'd\s+like|vorrei|desidero)\s+(?:something|qualcosa)\s+(?:with|con)\s+(.+)",
        # "something with X, Y, and Z"
        r"something\s+with\s+(.+)",
        r"qualcosa\s+con\s+(.+)",
        # "with X, Y, and Z" (bare)
        r"^with\s+(.+)",
        r"^con\s+(.+)",
    ]

    # Intolerance extraction patterns
    _INTOLERANCE_PATTERNS = [
        r"[.!;,]?\s*(?:i[''']?m|i\s+am)\s+intolerant\s+to\s+(.+?)(?:\.|!|$)",
        r"[.!;,]?\s*sono\s+intollerante\s+(?:a|al|alla|ai|alle|allo|agli)\s+(.+?)(?:\.|!|$)",
        r"[.!;,]?\s*intolerant\s+to\s+(.+?)(?:\.|!|$)",
        r"[.!;,]?\s*intollerante\s+(?:a|al|alla|ai|alle|allo|agli)\s+(.+?)(?:\.|!|$)",
        r"[.!;,]?\s*(?:but\s+)?(?:i[''']?m|i\s+am)\s+intolerant\s+(?:to\s+)?(.+?)(?:\.|!|$)",
        r"[.!;,]?\s*(?:no|without)\s+(.+?)\s*(?:please|per\s+favore)?(?:\.|!|$)",
    ]

    # Common prefixes to strip for dish-name extraction
    _STRIP_PREFIXES = [
        "i'd like to eat a ", "i'd like to eat ", "i'd like a ", "i'd like ",
        "i want to eat a ", "i want to eat ", "i want a ", "i want ",
        "i'll have a ", "i'll have ",
        "i would like to eat a ", "i would like to eat ",
        "i would like a ", "i would like ",
        "vorrei ", "vorrei un ", "vorrei una ", "vorrei il ", "vorrei la ", "vorrei lo ",
        "mi piacerebbe ", "mi piacerebbe un ", "mi piacerebbe una ",
        "desidero ", "desidero un ", "desidero una ",
        "potrei avere ", "potrei avere un ", "potrei avere una ",
        "per me ", "per me un ", "per me una ",
        "prendo ", "prendo il ", "prendo la ", "prendo un ", "prendo una ",
        "could i get a ", "could i get ", "could i have a ", "could i have ",
        "can i have a ", "can i have ", "can i get a ", "can i get ",
        "please give me a ", "please give me ", "give me a ", "give me ",
        "may i have a ", "may i have ",
        "one ", "the ", "a ", "un ", "una ", "il ", "la ", "lo ",
    ]

    _STRIP_SUFFIXES = [
        ", please", " please", ", per favore", " per favore",
        ", grazie", " grazie", ".", "!", "?",
    ]

    def __init__(
        self,
        menu_items: list[dict],
        recipe_db: dict[str, dict] | None = None,
        order_cache: dict[str, str] | None = None,
        llm_client=None,
    ):
        """
        Args:
            menu_items: list of {name, price} dicts for current menu
            recipe_db: full recipe DB mapping name → {name, ingredients: {ing: qty}, ...}
            order_cache: cached order_text → dish_name mappings
            llm_client: optional datapizza LLM client for fallback parsing
        """
        self.menu = {item["name"]: item for item in menu_items}
        self.menu_lower = {name.lower(): name for name in self.menu}
        self.order_cache = order_cache or {}
        self.recipe_db = recipe_db or {}
        self.llm_client = llm_client
        self.lookup = self._build_lookup()

        # Pre-compute token sets for dish name matching
        self._dish_tokens: dict[str, set[str]] = {}
        for dish_name in self.menu:
            self._dish_tokens[dish_name] = set(self._tokenize(dish_name.lower()))

        # Pre-compute ingredient sets for menu dishes (for ingredient matching)
        self._menu_ingredient_sets: dict[str, set[str]] = {}
        for dish_name in self.menu:
            recipe = self.recipe_db.get(dish_name, {})
            ings = recipe.get("ingredients", {})
            self._menu_ingredient_sets[dish_name] = {
                ing.lower().strip() for ing in ings.keys()
            }

    def _build_lookup(self) -> dict[str, str]:
        """Pre-compute normalized text → dish mapping."""
        lookup = {}
        for dish_name in self.menu:
            normalized = dish_name.lower().strip()
            lookup[normalized] = dish_name
            for prefix in self._STRIP_PREFIXES:
                lookup[prefix + normalized] = dish_name
        for order, dish in self.order_cache.items():
            if dish in self.menu:
                lookup[order.lower().strip()] = dish
        return lookup

    # ──────────────────────────────────────────────
    #  PUBLIC API
    # ──────────────────────────────────────────────

    def match(self, order_text: str) -> str | None:
        """
        Match order text to a menu dish. Returns canonical dish name or None.
        Handles both dish-name orders and ingredient-list orders.
        """
        if not order_text or not order_text.strip():
            logger.warning("Empty order text — cannot match")
            return None

        raw_lower = order_text.lower().strip()

        # T0: Cache hit (instant — covers previously seen orders)
        if raw_lower in self.order_cache and self.order_cache[raw_lower] in self.menu:
            dish = self.order_cache[raw_lower]
            logger.debug(f"Cache hit: '{order_text[:60]}' → '{dish}'")
            return dish

        # Strip intolerance suffix before matching
        clean_text = self._strip_intolerance(raw_lower)

        # Detect if this is an ingredient-list order
        requested_ingredients = self._extract_ingredients(clean_text)
        if requested_ingredients:
            # T2: Ingredient-set matching
            dish = self._match_by_ingredients(requested_ingredients)
            if dish:
                logger.info(
                    f"Ingredient match: {requested_ingredients} → '{dish}'"
                )
                self.add_to_cache(order_text, dish)
                return dish
            logger.warning(
                f"Ingredient-list order but no menu dish matches: "
                f"{requested_ingredients}"
            )
            # Fall through to LLM / fallback

        # T1: Dish name matching (exact → fuzzy → substring → token overlap)
        normalized = self._normalize_for_dish_name(clean_text)
        if normalized:
            dish = self._match_dish_name(normalized)
            if dish:
                self.add_to_cache(order_text, dish)
                return dish

        # T3: LLM fallback (if client available)
        if self.llm_client:
            dish = self._llm_match(order_text)
            if dish:
                self.add_to_cache(order_text, dish)
                return dish

        logger.warning(f"No match for order: '{order_text}'")
        return self._fallback_best_cookable()

    def extract_intolerances(self, order_text: str) -> list[str]:
        """
        Extract declared intolerances from order text.

        Returns list of ingredient names the client is intolerant to.
        """
        if not order_text:
            return []

        intolerances = []
        text_lower = order_text.lower()
        for pattern in self._INTOLERANCE_PATTERNS:
            matches = re.findall(pattern, text_lower, re.IGNORECASE)
            for m in matches:
                # Split on commas/and to handle "intolerant to X, Y, and Z"
                parts = re.split(r',\s*(?:and\s+)?|\s+and\s+|\s+e\s+', m.strip())
                for part in parts:
                    cleaned = part.strip().rstrip(".,!?; ")
                    if cleaned and len(cleaned) > 2:
                        intolerances.append(cleaned)

        return intolerances

    # ──────────────────────────────────────────────
    #  T2: INGREDIENT-SET MATCHING
    # ──────────────────────────────────────────────

    def _extract_ingredients(self, text: str) -> list[str] | None:
        """
        Detect if the order lists ingredients and extract them.

        Returns list of ingredient names, or None if this isn't an
        ingredient-list order.

        Handles: "I want something with X, Y, Z, and W"
        """
        for pattern in self._INGREDIENT_ORDER_PATTERNS:
            m = re.search(pattern, text, re.IGNORECASE)
            if m:
                raw_list = m.group(1).strip()
                # Split by commas and "and"/"e"
                parts = re.split(
                    r',\s*(?:and\s+)?|\s+and\s+|\s+e\s+', raw_list
                )
                ingredients = []
                for part in parts:
                    cleaned = part.strip().rstrip(".,!?; ")
                    if cleaned and len(cleaned) > 2:
                        ingredients.append(cleaned)
                if ingredients:
                    return ingredients
        return None

    def _match_by_ingredients(self, requested: list[str]) -> str | None:
        """
        Find the menu dish whose recipe ingredients best match the
        requested ingredient list.

        Uses normalized fuzzy comparison: for each requested ingredient,
        check if it matches any ingredient in each recipe. Score by
        overlap ratio.
        """
        requested_lower = {ing.lower().strip() for ing in requested}

        best_dish = None
        best_score = 0.0

        for dish_name, recipe_ings in self._menu_ingredient_sets.items():
            if not recipe_ings:
                continue

            # Count how many requested ingredients match recipe ingredients
            matches = 0
            for req_ing in requested_lower:
                for rec_ing in recipe_ings:
                    if self._ingredients_match(req_ing, rec_ing):
                        matches += 1
                        break

            # Count how many recipe ingredients match requested
            reverse_matches = 0
            for rec_ing in recipe_ings:
                for req_ing in requested_lower:
                    if self._ingredients_match(req_ing, rec_ing):
                        reverse_matches += 1
                        break

            if matches == 0:
                continue

            # Both the requested set and recipe set should overlap well
            forward_ratio = matches / len(requested_lower)
            backward_ratio = reverse_matches / len(recipe_ings)
            # Weighted: exact set match > partial match
            score = (forward_ratio * 0.6 + backward_ratio * 0.4)

            if score > best_score:
                best_score = score
                best_dish = dish_name

        # Require a decent match (at least 50% overlap)
        if best_dish and best_score >= 0.5:
            logger.debug(
                f"Ingredient match score={best_score:.2f} for '{best_dish}'"
            )
            return best_dish

        return None

    @staticmethod
    def _ingredients_match(a: str, b: str) -> bool:
        """
        Check if two ingredient names refer to the same ingredient.
        Handles partial matches, accent differences, etc.
        """
        a, b = a.strip(), b.strip()
        # Exact
        if a == b:
            return True
        # One contains the other
        if a in b or b in a:
            return True
        # Fuzzy: difflib
        matches = get_close_matches(a, [b], n=1, cutoff=0.75)
        return len(matches) > 0

    # ──────────────────────────────────────────────
    #  T1: DISH NAME MATCHING
    # ──────────────────────────────────────────────

    def _match_dish_name(self, normalized: str) -> str | None:
        """Multi-tier dish name matching."""
        # Exact lookup
        if normalized in self.lookup:
            dish = self.lookup[normalized]
            logger.debug(f"Exact match: → '{dish}'")
            return dish

        if normalized in self.menu_lower:
            dish = self.menu_lower[normalized]
            logger.debug(f"Direct name match: → '{dish}'")
            return dish

        # Fuzzy match
        for cutoff in (0.7, 0.55):
            matches = get_close_matches(
                normalized, list(self.menu_lower.keys()), n=1, cutoff=cutoff
            )
            if matches:
                dish = self.menu_lower[matches[0]]
                logger.debug(f"Fuzzy match (cutoff={cutoff}): → '{dish}'")
                return dish

        # Substring
        for dish_lower, dish_name in self.menu_lower.items():
            if dish_lower in normalized or normalized in dish_lower:
                logger.debug(f"Substring match: → '{dish_name}'")
                return dish_name

        # Token overlap
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
                logger.debug(f"Token overlap ({best_overlap:.0%}): → '{best_dish}'")
                return best_dish

        return None

    # ──────────────────────────────────────────────
    #  T3: LLM FALLBACK
    # ──────────────────────────────────────────────

    def _llm_match(self, order_text: str) -> str | None:
        """
        Use the fast LLM to parse the order and match to a menu dish.
        Uses synchronous invoke() since we're called from the sync match() method.
        """
        return self._llm_match_sync(order_text)

    def _llm_match_sync(self, order_text: str) -> str | None:
        """Synchronous LLM matching — uses invoke() instead of a_invoke()."""
        menu_info_parts = []
        for dish_name in self.menu:
            recipe = self.recipe_db.get(dish_name, {})
            ings = list(recipe.get("ingredients", {}).keys())
            if ings:
                menu_info_parts.append(f"  - {dish_name}: ingredients = {', '.join(ings)}")
            else:
                menu_info_parts.append(f"  - {dish_name}")
        menu_info = "\n".join(menu_info_parts)

        prompt = (
            f"A restaurant customer said: \"{order_text}\"\n\n"
            f"Our menu dishes and their ingredients:\n{menu_info}\n\n"
            f"Which dish from the menu does the customer want? "
            f"The customer may have named the dish, or listed the ingredients they want. "
            f"Find the best matching dish.\n"
            f"Reply with ONLY the exact dish name from the menu, nothing else. "
            f"If no dish matches at all, reply NONE."
        )
        try:
            response = self.llm_client.invoke(
                input=prompt, temperature=0.0, max_tokens=200,
            )
            text = ""
            if hasattr(response, "text"):
                text = response.text.strip()
            elif hasattr(response, "content"):
                text = response.content.strip()
            elif isinstance(response, str):
                text = response.strip()

            if text and text != "NONE" and text in self.menu:
                logger.info(f"LLM match: '{order_text[:50]}' → '{text}'")
                return text
            # Try fuzzy match on LLM response
            if text and text != "NONE":
                matches = get_close_matches(
                    text.lower(), list(self.menu_lower.keys()), n=1, cutoff=0.7
                )
                if matches:
                    dish = self.menu_lower[matches[0]]
                    logger.info(f"LLM fuzzy match: '{order_text[:50]}' → '{dish}'")
                    return dish
        except Exception as e:
            logger.warning(f"LLM match failed: {e}")
        return None

    async def llm_match_async(self, order_text: str) -> str | None:
        """Async LLM matching — for use from async contexts."""
        menu_info_parts = []
        for dish_name in self.menu:
            recipe = self.recipe_db.get(dish_name, {})
            ings = list(recipe.get("ingredients", {}).keys())
            if ings:
                menu_info_parts.append(f"  - {dish_name}: ingredients = {', '.join(ings)}")
            else:
                menu_info_parts.append(f"  - {dish_name}")
        menu_info = "\n".join(menu_info_parts)

        prompt = (
            f"A restaurant customer said: \"{order_text}\"\n\n"
            f"Our menu dishes and their ingredients:\n{menu_info}\n\n"
            f"Which dish from the menu does the customer want? "
            f"The customer may have named the dish, or listed the ingredients they want. "
            f"Find the best matching dish.\n"
            f"Reply with ONLY the exact dish name from the menu, nothing else. "
            f"If no dish matches at all, reply NONE."
        )
        try:
            response = await self.llm_client.a_invoke(
                input=prompt, temperature=0.0, max_tokens=200,
            )
            text = ""
            if hasattr(response, "text"):
                text = response.text.strip()
            elif hasattr(response, "content"):
                text = response.content.strip()
            elif isinstance(response, str):
                text = response.strip()

            if text and text != "NONE" and text in self.menu:
                logger.info(f"LLM async match: '{order_text[:50]}' → '{text}'")
                return text
            if text and text != "NONE":
                matches = get_close_matches(
                    text.lower(), list(self.menu_lower.keys()), n=1, cutoff=0.7
                )
                if matches:
                    dish = self.menu_lower[matches[0]]
                    logger.info(f"LLM async fuzzy match: '{order_text[:50]}' → '{dish}'")
                    return dish
        except Exception as e:
            logger.warning(f"LLM async match failed: {e}")
        return None

    # ──────────────────────────────────────────────
    #  HELPERS
    # ──────────────────────────────────────────────

    def _strip_intolerance(self, text: str) -> str:
        """Remove intolerance declarations from text (for matching only)."""
        for pattern in self._INTOLERANCE_PATTERNS:
            text = re.sub(pattern, "", text, flags=re.IGNORECASE).strip()
        return text

    def _normalize_for_dish_name(self, text: str) -> str:
        """Normalize text assuming it contains a dish name."""
        # Strip suffixes
        for suffix in self._STRIP_SUFFIXES:
            if text.endswith(suffix):
                text = text[: -len(suffix)].strip()
        # Strip prefixes (longest first)
        for prefix in sorted(self._STRIP_PREFIXES, key=len, reverse=True):
            if text.startswith(prefix):
                text = text[len(prefix):].strip()
                break
        return re.sub(r"\s+", " ", text).strip()

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        """Split into meaningful tokens."""
        stop_words = {
            "di", "del", "della", "dello", "dei", "degli", "delle",
            "con", "in", "e", "al", "alla", "allo", "a", "da",
            "il", "la", "lo", "le", "gli", "un", "una", "uno",
            "the", "a", "an", "of", "with", "and", "in", "on",
            "per", "su", "tra", "fra", "something", "qualcosa",
            "want", "like", "vorrei", "desidero",
        }
        words = re.findall(r"[a-zàèéìòù]+", text.lower())
        return [w for w in words if len(w) >= 2 and w not in stop_words]

    def _fallback_best_cookable(self) -> str | None:
        """Return first menu dish as last resort."""
        if self.menu:
            first = next(iter(self.menu))
            logger.warning(f"Fallback: returning first menu dish '{first}'")
            return first
        return None

    def update_menu(self, menu_items: list[dict]):
        """Update menu and rebuild all lookup structures."""
        self.menu = {item["name"]: item for item in menu_items}
        self.menu_lower = {name.lower(): name for name in self.menu}
        self.lookup = self._build_lookup()
        self._dish_tokens = {}
        for dish_name in self.menu:
            self._dish_tokens[dish_name] = set(self._tokenize(dish_name.lower()))
        self._menu_ingredient_sets = {}
        for dish_name in self.menu:
            recipe = self.recipe_db.get(dish_name, {})
            ings = recipe.get("ingredients", {})
            self._menu_ingredient_sets[dish_name] = {
                ing.lower().strip() for ing in ings.keys()
            }

    def add_to_cache(self, order_text: str, dish_name: str):
        """Cache a successful order→dish mapping."""
        raw_key = order_text.lower().strip()
        self.order_cache[raw_key] = dish_name
        self.lookup[raw_key] = dish_name
