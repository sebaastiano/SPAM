"""
SPAM! — Strategy Agent
========================
LLM-driven strategic planner that actively participates in every
key decision of the turn workflow.

This is the BRAIN of the system. While ILP solvers and heuristics handle
the math, the Strategy Agent reasons about:
  - Which zone best fits our current situation (with nuance)
  - How to compose a menu that attracts the widest customer base
  - How aggressively to bid (risk vs. reward tradeoff)
  - How to adjust prices dynamically based on competition
  - Which diplomatic moves create the most advantage

Architecture:
  The agent uses the primary LLM (gpt-oss-120b) for structured reasoning.
  It does NOT call MCP tools directly — it produces JSON recommendations
  that downstream skills (ILP, pricing, diplomacy) use to configure their
  parameters. This keeps the agent safe (can't accidentally call save_menu
  at the wrong time) while giving it real influence over every decision.

Integration points:
  1. _skill_strategic_plan (speaking phase) → turn-level strategy
  2. _skill_zone_selection → agent validates/overrides zone choice
  3. _skill_menu_planning → agent sets diversification & sizing params
  4. _skill_bid_compute → agent sets aggressiveness
  5. _skill_diplomacy_send → agent picks diplomatic priorities
"""

import json
import logging
import math
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger("spam.decision.strategy_agent")


@dataclass
class TurnStrategy:
    """
    The agent's strategic plan for the current turn.
    Consumed by every downstream skill to adjust its behavior.
    """
    # Zone recommendation
    recommended_zone: str = "DIVERSIFIED"
    zone_reasoning: str = ""

    # Menu composition guidance
    menu_target_size: int = 15
    menu_diversify: bool = True  # True = span all prestige tiers
    menu_prestige_min: int = 15
    menu_prestige_max: int = 100
    menu_max_prep_time: float = 12.0
    menu_priority_recipes: list[str] = field(default_factory=list)  # names to prefer
    menu_avoid_recipes: list[str] = field(default_factory=list)  # names to avoid

    # Bid aggressiveness (0.0 = don't bid, 1.0 = all-in)
    bid_aggressiveness: float = 0.35
    bid_priority_ingredients: list[str] = field(default_factory=list)
    bid_reasoning: str = ""

    # Pricing guidance
    price_strategy: str = "volume_first"  # volume_first | balanced | premium
    price_adjustment_factor: float = 1.0  # multiplier on computed prices
    undercut_competitors: bool = True

    # Diplomacy guidance
    diplomacy_priority: str = "moderate"  # aggressive | moderate | passive | silent
    diplomacy_targets: list[int] = field(default_factory=list)
    diplomacy_reasoning: str = ""

    # Focus archetype for this turn (rotate to capture different segments)
    focus_archetype: str = "all"  # all | budget | mid | premium | luxury

    # Expected customer flow estimate
    expected_customers: int = 8  # total customers expected this turn
    expected_high_value: int = 2  # Saggi + Astrobaroni
    expected_budget: int = 4  # Esploratori + Famiglie

    # Overall confidence (how much to trust agent vs. algorithmic defaults)
    confidence: float = 0.5  # 0.0 = use defaults, 1.0 = fully trust agent

    # Raw reasoning (for logging/debugging)
    raw_reasoning: str = ""


class StrategyAgent:
    """
    LLM-powered strategic planner.

    Consults the primary LLM at key decision points and produces
    structured recommendations that downstream skills use.

    NOT a datapizza Agent (no tool calling). Uses the LLM client
    directly for safe, structured reasoning.
    """

    def __init__(self, llm_client, fast_client=None):
        """
        Args:
            llm_client: Primary OpenAILikeClient (gpt-oss-120b) for deep reasoning
            fast_client: Fast OpenAILikeClient (gpt-oss-20b) for quick parsing
        """
        self.llm_client = llm_client
        self.fast_client = fast_client or llm_client
        self._last_strategy: TurnStrategy | None = None
        self._turn_history: list[dict] = []  # track strategies across turns

        # ── Revenue Tracking (what worked?) ──
        self._turn_results: list[dict] = []  # [{turn_id, revenue, customers, balance_delta, strategy, zone}]
        self._strategy_performance: dict[str, list[float]] = defaultdict(list)  # strategy → [revenues]

        # ── Bid History Tracking (don't overbid) ──
        self._bid_price_history: dict[str, list[float]] = defaultdict(list)  # ingredient → [winning prices]
        self._ingredient_avg_prices: dict[str, float] = {}  # ingredient → rolling avg
        self._ingredient_availability: dict[str, float] = defaultdict(float)  # ingredient → avg availability

    @property
    def last_strategy(self) -> TurnStrategy | None:
        return self._last_strategy

    async def plan_turn(
        self,
        turn_id: int,
        balance: float,
        inventory: dict[str, int],
        reputation: float,
        recipes: dict[str, dict],
        intel: dict[str, Any],
        menu_set: bool = False,
        our_state: dict | None = None,
        phase: str = "speaking",
    ) -> TurnStrategy:
        """
        Generate a strategic plan for the entire turn.

        Called early in the speaking phase. The resulting TurnStrategy
        is consumed by all downstream skills.
        """
        strategy = TurnStrategy()

        try:
            # Build context for the LLM
            context = self._build_context(
                turn_id=turn_id,
                balance=balance,
                inventory=inventory,
                reputation=reputation,
                recipes=recipes,
                intel=intel,
                our_state=our_state,
                phase=phase,
            )

            prompt = self._build_strategy_prompt(context)

            logger.info(f"Consulting strategy agent for turn {turn_id}...")

            # Call LLM for strategic reasoning
            response = await self._call_llm(prompt, use_fast=False)

            if response:
                strategy = self._parse_strategy_response(response, context)
                strategy.confidence = min(0.85, strategy.confidence)  # cap confidence
                logger.info(
                    f"Strategy agent plan: zone={strategy.recommended_zone}, "
                    f"menu_size={strategy.menu_target_size}, "
                    f"bid_aggr={strategy.bid_aggressiveness:.2f}, "
                    f"price={strategy.price_strategy}, "
                    f"diplomacy={strategy.diplomacy_priority}, "
                    f"confidence={strategy.confidence:.2f}"
                )
            else:
                logger.warning("Strategy agent returned empty response — using defaults")
                strategy = self._default_strategy(context)

        except Exception as e:
            logger.error(f"Strategy agent failed: {e}", exc_info=True)
            strategy = self._default_strategy(
                self._build_context(
                    turn_id, balance, inventory, reputation,
                    recipes, intel, our_state, phase,
                )
            )

        self._last_strategy = strategy
        self._turn_history.append({
            "turn_id": turn_id,
            "zone": strategy.recommended_zone,
            "menu_size": strategy.menu_target_size,
            "bid_aggr": strategy.bid_aggressiveness,
            "focus": strategy.focus_archetype,
            "price_strategy": strategy.price_strategy,
        })

        return strategy

    def record_turn_result(
        self,
        turn_id: int,
        revenue: float,
        customers_served: int,
        balance_delta: float,
        strategy_used: str = "unknown",
        zone_used: str = "DIVERSIFIED",
    ):
        """Record the outcome of a completed turn for future strategy decisions."""
        result = {
            "turn_id": turn_id,
            "revenue": revenue,
            "customers_served": customers_served,
            "balance_delta": balance_delta,
            "strategy": strategy_used,
            "zone": zone_used,
        }
        self._turn_results.append(result)
        self._strategy_performance[strategy_used].append(revenue)
        logger.info(
            f"Turn {turn_id} result recorded: rev={revenue:.0f}, "
            f"customers={customers_served}, delta={balance_delta:+.0f}, "
            f"strategy={strategy_used}"
        )

    def record_bid_history(self, bid_entries: list[dict]):
        """Process bid history from the server to learn ingredient pricing patterns.

        bid_entries: list of dicts like {ingredient, bid, quantity, status, restaurant_id}.
        """
        if not bid_entries:
            return

        # Group by ingredient
        ingredient_bids: dict[str, list[float]] = defaultdict(list)
        ingredient_wins: dict[str, list[float]] = defaultdict(list)

        for entry in bid_entries:
            ing = entry.get("ingredient", "")
            bid_price = entry.get("bid", 0)
            status = entry.get("status", "")
            if ing and bid_price > 0:
                ingredient_bids[ing].append(bid_price)
                if status == "completed":
                    ingredient_wins[ing].append(bid_price)

        # Update rolling averages
        for ing, prices in ingredient_wins.items():
            self._bid_price_history[ing].extend(prices)
            # Keep last 30 data points per ingredient
            if len(self._bid_price_history[ing]) > 30:
                self._bid_price_history[ing] = self._bid_price_history[ing][-30:]
            self._ingredient_avg_prices[ing] = (
                sum(self._bid_price_history[ing]) / len(self._bid_price_history[ing])
            )

        # Track availability (ratio of bids that won)
        for ing, all_prices in ingredient_bids.items():
            wins = len(ingredient_wins.get(ing, []))
            total = len(all_prices)
            self._ingredient_availability[ing] = wins / max(total, 1)

        logger.info(
            f"Bid history processed: {len(ingredient_wins)} ingredients with wins, "
            f"avg prices: {dict(list(self._ingredient_avg_prices.items())[:5])}"
        )

    def get_bid_price_intelligence(self) -> dict:
        """Return bid pricing intelligence for use by ILP solver."""
        return {
            "avg_prices": dict(self._ingredient_avg_prices),
            "availability": dict(self._ingredient_availability),
            "history_depth": {
                ing: len(prices)
                for ing, prices in self._bid_price_history.items()
            },
        }

    async def consult_zone(
        self,
        algorithmic_zone: str,
        context: dict,
    ) -> str:
        """
        Validate or override the algorithmic zone selection.

        The agent can agree with the heuristic or suggest a better zone.
        Returns the final zone choice.
        """
        if self._last_strategy and self._last_strategy.confidence >= 0.5:
            recommended = self._last_strategy.recommended_zone
            if recommended != algorithmic_zone:
                logger.info(
                    f"Strategy agent overrides zone: "
                    f"{algorithmic_zone} → {recommended} "
                    f"(confidence={self._last_strategy.confidence:.2f}, "
                    f"reason: {self._last_strategy.zone_reasoning[:100]})"
                )
                return recommended

        return algorithmic_zone

    async def consult_menu(
        self,
        zone: str,
        eligible_recipes: list[dict],
        inventory: dict[str, int],
        balance: float,
    ) -> dict:
        """
        Provide menu composition guidance with MULTI-LAYER enforcement.

        Always ensures the menu spans multiple price tiers to capture
        customers from ALL archetypes. The distribution adapts based on
        the agent's focus_archetype and expected customer flow.

        Returns dict with keys:
          - target_size: int
          - prestige_min, prestige_max: int
          - max_prep_time: float
          - priority_recipes: list[str]
          - diversity_bonus: float (0.0-1.0)
          - tier_targets: dict  # min dishes per price tier
          - expected_customers: int
          - bid_price_intelligence: dict  # historical bid data
          - price_strategy, price_adjustment, undercut: pricing params
        """
        strat = self._last_strategy or TurnStrategy()

        # ── Multi-layer tier targets based on focus ──
        # Always have dishes in every layer; shift emphasis based on focus
        focus = strat.focus_archetype
        if focus == "premium" or focus == "luxury":
            # More high-prestige dishes, but still cover budget
            tier_targets = {
                "budget": 2,     # prestige 0-35: Esploratori bait
                "mid": 3,        # prestige 36-60: Famiglie sweet spot
                "mid_high": 3,   # prestige 61-80: crossover
                "premium": 4,    # prestige 81-100: Saggi + Astrobaroni
            }
        elif focus == "budget":
            # More budget dishes, light premium
            tier_targets = {
                "budget": 5,
                "mid": 4,
                "mid_high": 2,
                "premium": 2,
            }
        else:  # "all" / "balanced" / "mid"
            # Even spread across all tiers
            tier_targets = {
                "budget": 3,
                "mid": 4,
                "mid_high": 3,
                "premium": 3,
            }

        guidance = {
            "target_size": strat.menu_target_size,
            "prestige_min": strat.menu_prestige_min,
            "prestige_max": strat.menu_prestige_max,
            "max_prep_time": strat.menu_max_prep_time,
            "priority_recipes": strat.menu_priority_recipes,
            "diversity_bonus": 0.35 if strat.menu_diversify else 0.1,
            "diversify": strat.menu_diversify,
            "tier_targets": tier_targets,
            "expected_customers": strat.expected_customers,
            "expected_high_value": strat.expected_high_value,
            "focus_archetype": focus,
            # Bid price intelligence for the ILP solver
            "bid_price_intelligence": self.get_bid_price_intelligence(),
            # Pricing guidance (used by ILP solver's compute_menu_price)
            "price_strategy": strat.price_strategy,
            "price_adjustment": strat.price_adjustment_factor,
            "undercut": strat.undercut_competitors,
        }

        # If we have a strategy with good confidence, use its parameters
        if strat.confidence >= 0.4:
            logger.info(
                f"Menu guidance from agent: size={guidance['target_size']}, "
                f"prestige=[{guidance['prestige_min']}-{guidance['prestige_max']}], "
                f"prep≤{guidance['max_prep_time']}s, "
                f"focus={focus}, tiers={tier_targets}, "
                f"expected_customers={strat.expected_customers}"
            )
        else:
            # Low confidence — use broad defaults for maximum capture
            guidance["target_size"] = max(14, guidance["target_size"])
            guidance["prestige_min"] = 10
            guidance["prestige_max"] = 100
            guidance["max_prep_time"] = 12.0
            guidance["diversity_bonus"] = 0.35
            guidance["diversify"] = True
            guidance["tier_targets"] = {
                "budget": 3, "mid": 4, "mid_high": 3, "premium": 3
            }

        return guidance

    async def consult_bid(
        self,
        zone: str,
        balance: float,
        active_competitors: int,
        menu_recipes: list[dict] | None = None,
    ) -> dict:
        """
        Provide bidding guidance with bid history awareness.

        Uses historical winning prices to avoid overbidding on cheap
        ingredients. Adjusts spending based on menu needs and expected
        customer flow.

        Returns dict with keys:
          - spending_fraction: float (0.0-0.6)
          - priority_ingredients: list[str]
          - aggressiveness: float (0.0-1.0)
          - bid_price_caps: dict[str, float]  # ingredient → max reasonable bid
          - cheap_ingredients: list[str]  # ingredients historically available cheap
          - expected_servings: int  # how many servings to plan for
        """
        strat = self._last_strategy or TurnStrategy()

        # Base spending from agent recommendation
        aggr = strat.bid_aggressiveness
        spending = 0.15 + aggr * 0.35  # range: 0.15 to 0.50

        # Adjust for competition
        if active_competitors == 0:
            spending = min(spending, 0.20)  # monopoly: don't overspend
        elif active_competitors >= 4:
            spending = min(spending + 0.05, 0.50)  # heavy competition

        # ── Bid history-based price caps ──
        # If we know an ingredient usually wins at X, don't bid more than X * 1.3
        bid_price_caps: dict[str, float] = {}
        cheap_ingredients: list[str] = []

        for ing, avg_price in self._ingredient_avg_prices.items():
            availability = self._ingredient_availability.get(ing, 0.5)
            if availability >= 0.7:  # high availability → usually easy to get
                # Cap at avg + 20% — no need to overbid
                bid_price_caps[ing] = avg_price * 1.2
                if avg_price <= 15:
                    cheap_ingredients.append(ing)
            elif availability >= 0.4:  # moderate availability
                bid_price_caps[ing] = avg_price * 1.35
            else:  # scarce — allow higher bids
                bid_price_caps[ing] = avg_price * 1.6

        # ── Expected servings based on customer flow ──
        expected_servings = strat.expected_customers

        # If we have menu info, adjust spending for what we actually need
        if menu_recipes:
            total_ing_needed = sum(
                sum(r.get("ingredients", {}).values())
                for r in menu_recipes
            )
            # Scale spending with menu complexity
            if total_ing_needed > 0:
                complexity_factor = min(total_ing_needed / 50.0, 1.5)
                spending = min(spending * complexity_factor, 0.55)

        guidance = {
            "spending_fraction": spending,
            "priority_ingredients": strat.bid_priority_ingredients,
            "aggressiveness": aggr,
            "bid_price_caps": bid_price_caps,
            "cheap_ingredients": cheap_ingredients,
            "expected_servings": expected_servings,
        }

        logger.info(
            f"Bid guidance from agent: spending={spending:.2f}, "
            f"aggr={aggr:.2f}, priority={strat.bid_priority_ingredients[:3]}, "
            f"price_caps={len(bid_price_caps)} ingredients capped, "
            f"cheap={len(cheap_ingredients)}, expected_servings={expected_servings}"
        )

        return guidance

    async def consult_pricing(
        self,
        zone: str,
        active_competitors: int,
        reputation: float,
    ) -> dict:
        """
        Provide pricing guidance.

        Returns dict with keys:
          - strategy: str (volume_first | balanced | premium)
          - adjustment_factor: float
          - undercut: bool
        """
        strat = self._last_strategy or TurnStrategy()

        return {
            "strategy": strat.price_strategy,
            "adjustment_factor": strat.price_adjustment_factor,
            "undercut": strat.undercut_competitors,
        }

    async def consult_diplomacy(
        self,
        competitor_briefings: dict,
        balance: float,
    ) -> dict:
        """
        Provide diplomacy guidance.

        Returns dict with keys:
          - priority: str (aggressive | moderate | passive | silent)
          - targets: list[int] (restaurant IDs to focus on)
          - max_messages: int
        """
        strat = self._last_strategy or TurnStrategy()

        max_msgs = {
            "aggressive": 3,
            "moderate": 2,
            "passive": 1,
            "silent": 0,
        }.get(strat.diplomacy_priority, 2)

        return {
            "priority": strat.diplomacy_priority,
            "targets": strat.diplomacy_targets,
            "max_messages": max_msgs,
        }

    # ── Internal Methods ──

    def _build_context(
        self,
        turn_id: int,
        balance: float,
        inventory: dict[str, int],
        reputation: float,
        recipes: dict[str, dict],
        intel: dict[str, Any],
        our_state: dict | None = None,
        phase: str = "speaking",
    ) -> dict:
        """Build a compact context dict for the LLM, including history and bid data."""
        briefings = intel.get("briefings", {})
        active_competitors = sum(
            1 for b in briefings.values()
            if b.get("is_connected", False)
        )

        # Recipe stats
        all_recipes = list(recipes.values())
        prestige_values = [r.get("prestige", 50) for r in all_recipes]
        prep_times = [r.get("prep_time", 5.0) for r in all_recipes]

        # Inventory stats
        total_inv = sum(inventory.values()) if inventory else 0
        unique_ings = len(inventory) if inventory else 0

        # Cookable recipes (how many can we make right now?)
        cookable = 0
        for recipe in all_recipes:
            if all(
                inventory.get(ing, 0) >= qty
                for ing, qty in recipe.get("ingredients", {}).items()
            ):
                cookable += 1

        # Competitor summary
        comp_summary = []
        for rid, b in briefings.items():
            comp_summary.append({
                "id": rid,
                "name": b.get("name", f"Team {rid}"),
                "strategy": b.get("strategy", "UNKNOWN"),
                "connected": b.get("is_connected", False),
                "menu_size": b.get("menu_size", 0),
                "avg_price": b.get("menu_price_avg", 0),
                "reputation": b.get("reputation", 0),
                "balance": b.get("balance", 0),
                "threat": b.get("threat_level", 0),
            })

        # History summary with RESULTS (what worked in past turns?)
        history_summary = []
        for h in self._turn_history[-5:]:
            # Merge with results if available
            result = next(
                (r for r in self._turn_results if r["turn_id"] == h["turn_id"]),
                None
            )
            entry = dict(h)
            if result:
                entry["revenue"] = result["revenue"]
                entry["customers"] = result["customers_served"]
                entry["balance_delta"] = result["balance_delta"]
            history_summary.append(entry)

        # Strategy performance summary
        strategy_perf = {}
        for strat_name, revenues in self._strategy_performance.items():
            if revenues:
                strategy_perf[strat_name] = {
                    "avg_revenue": sum(revenues) / len(revenues),
                    "best_revenue": max(revenues),
                    "turns_used": len(revenues),
                }

        # Bid price intelligence (top N most relevant ingredients)
        bid_intel_summary = {}
        for ing, avg_price in sorted(
            self._ingredient_avg_prices.items(),
            key=lambda x: x[1],
        )[:15]:
            avail = self._ingredient_availability.get(ing, 0.5)
            bid_intel_summary[ing] = {
                "avg_winning_price": round(avg_price, 1),
                "availability": round(avail, 2),
                "cheap": avg_price <= 15,
            }

        # Prestige distribution of available recipes (for multi-layer guidance)
        prestige_buckets = {"budget": 0, "mid": 0, "mid_high": 0, "premium": 0}
        for p in prestige_values:
            if p <= 35:
                prestige_buckets["budget"] += 1
            elif p <= 60:
                prestige_buckets["mid"] += 1
            elif p <= 80:
                prestige_buckets["mid_high"] += 1
            else:
                prestige_buckets["premium"] += 1

        return {
            "turn_id": turn_id,
            "phase": phase,
            "balance": balance,
            "reputation": reputation,
            "total_inventory": total_inv,
            "unique_ingredients": unique_ings,
            "cookable_recipes": cookable,
            "total_recipes": len(all_recipes),
            "prestige_range": (
                min(prestige_values) if prestige_values else 0,
                max(prestige_values) if prestige_values else 100,
            ),
            "prep_time_range": (
                min(prep_times) if prep_times else 0,
                max(prep_times) if prep_times else 15,
            ),
            "active_competitors": active_competitors,
            "competitors": comp_summary[:10],
            "history": history_summary,
            "strategy_performance": strategy_perf,
            "bid_price_intel": bid_intel_summary,
            "recipe_prestige_distribution": prestige_buckets,
        }

    def _build_strategy_prompt(self, context: dict) -> str:
        """Build the strategy reasoning prompt with full intelligence."""
        competitors_text = ""
        for c in context.get("competitors", []):
            if c.get("connected"):
                competitors_text += (
                    f"  - {c['name']} (ID {c['id']}): strategy={c['strategy']}, "
                    f"menu_size={c['menu_size']}, avg_price={c['avg_price']:.0f}, "
                    f"reputation={c['reputation']}, threat={c['threat']:.2f}\n"
                )

        # Enhanced history with revenue results
        history_text = ""
        for h in context.get("history", []):
            line = (
                f"  Turn {h['turn_id']}: zone={h['zone']}, "
                f"menu_size={h['menu_size']}, bid_aggr={h['bid_aggr']:.2f}, "
                f"focus={h.get('focus', 'all')}, price={h.get('price_strategy', '?')}"
            )
            if "revenue" in h:
                line += (
                    f", REVENUE={h['revenue']:.0f}, "
                    f"customers={h.get('customers', '?')}, "
                    f"balance_delta={h.get('balance_delta', 0):+.0f}"
                )
            history_text += line + "\n"

        # Strategy performance summary
        perf_text = ""
        for strat_name, perf in context.get("strategy_performance", {}).items():
            perf_text += (
                f"  {strat_name}: avg_rev={perf['avg_revenue']:.0f}, "
                f"best={perf['best_revenue']:.0f}, used {perf['turns_used']}x\n"
            )

        # Bid price history
        bid_intel_text = ""
        for ing, data in context.get("bid_price_intel", {}).items():
            cheap_flag = " (✅ CHEAP — don't overbid!)" if data["cheap"] else ""
            avail_flag = f", avail={data['availability']:.0%}"
            bid_intel_text += (
                f"  {ing}: avg_win={data['avg_winning_price']:.0f}{avail_flag}{cheap_flag}\n"
            )

        # Recipe prestige distribution
        dist = context.get("recipe_prestige_distribution", {})
        dist_text = (
            f"  Budget (0-35): {dist.get('budget', 0)} recipes, "
            f"Mid (36-60): {dist.get('mid', 0)}, "
            f"Mid-High (61-80): {dist.get('mid_high', 0)}, "
            f"Premium (81-100): {dist.get('premium', 0)}"
        )

        prompt = f"""You are the strategic brain of restaurant SPAM! (Team 17) in a competitive restaurant game.

CURRENT STATE (Turn {context['turn_id']}):
- Balance: {context['balance']:.0f} credits
- Reputation: {context['reputation']:.1f}/100
- Inventory: {context['total_inventory']} items ({context['unique_ingredients']} types)
- Cookable recipes (from inventory): {context['cookable_recipes']}/{context['total_recipes']}
- Recipe prestige range: {context['prestige_range'][0]:.0f} - {context['prestige_range'][1]:.0f}
- Active competitors: {context['active_competitors']}
- Available recipe tiers: {dist_text}

COMPETITORS:
{competitors_text if competitors_text else "  No active competitors detected."}

PAST TURNS (with results):
{history_text if history_text else "  No history yet (first turn)."}

STRATEGY PERFORMANCE SUMMARY:
{perf_text if perf_text else "  No data yet."}

BID PRICE HISTORY (ingredient → average winning price):
{bid_intel_text if bid_intel_text else "  No bid history yet."}

CUSTOMER ARCHETYPES:
- Esploratore Galattico: budget, max ~60 credits (most common, ~40% of traffic)
- Famiglie Orbitali: moderate, max ~150 credits (~25% of traffic)
- Saggi del Cosmo: high, max ~600 credits (~20% of traffic, highest per-customer revenue)
- Astrobarone: luxury, max ~500 credits (~15% of traffic)

── MANDATORY RULES ──
1. ALWAYS offer dishes across MULTIPLE price layers (budget + mid + premium).
   A menu with ONLY premium dishes misses 65% of customers.
   A menu with ONLY budget dishes leaves money on the table.

2. VARY your strategy turn-by-turn. Don't repeat the same approach every turn.
   If last turn was volume_first, consider balanced or even a premium push.
   If premium worked well, keep some premium but add budget for volume.
   ROTATE your focus: some turns emphasize high-value clients (Saggi + Astrobaroni),
   some focus on volume (Esploratori + Famiglie), some go balanced.

3. BID SMART based on history:
   - If an ingredient historically wins at ~10 credits, DON'T bid 40.
   - If an ingredient is scarce (low availability), bid MORE aggressively.
   - If an ingredient is abundant (high availability), keep bids LOW.
   - ALWAYS consider what's on the menu — prioritize ingredients for
     high-margin dishes.

4. ESTIMATE CUSTOMER FLOW:
   - Typical turn: 6-12 customers.
   - More customers visit restaurants with diverse menus and good reputation.
   - Bid enough ingredients for expected servings, not 10x more.

5. REVENUE = (dishes_sold × price) − bidding_costs.
   High prices mean nothing if nobody buys. Low bids mean more profit per dish.

STRATEGIC PRIORITIES:
1. MAXIMIZE NET REVENUE (revenue minus costs)
2. Keep menu spanning ALL price tiers (3+ budget, 3+ mid, 3+ premium)
3. Bid ONLY what's needed, using historical prices as reference
4. Rotate between focus archetypes each turn for broader coverage over time
5. Adapt bids to expected customer flow and menu needs

AVAILABLE ZONES:
- DIVERSIFIED: All archetypes, 15+ dishes. Best default.
- PREMIUM_MONOPOLIST: High-prestige, rich clients. Risky unless no competition.
- BUDGET_OPPORTUNIST: High-volume budget. Good for quick profit.
- SPEED_CONTENDER: Fast dishes. Good when speed differentiates.
- NICHE_SPECIALIST: Focus one underserved archetype.
- MARKET_ARBITRAGEUR: Trade-focused (rarely best).

FOCUS ARCHETYPE OPTIONS (rotate each turn!):
- "all": balanced across all archetypes
- "budget": emphasize Esploratori + Famiglie (volume play)
- "mid": emphasize Famiglie + some Saggi (balanced revenue)
- "premium": emphasize Saggi + Astrobaroni (high per-customer revenue)
- "luxury": go all-in on Astrobaroni + Saggi (maximum per-dish price)

Respond with a JSON object (no markdown, no explanation outside JSON):
{{
  "recommended_zone": "DIVERSIFIED",
  "zone_reasoning": "why this zone fits this turn",
  "menu_target_size": 12-20,
  "menu_diversify": true,
  "menu_prestige_min": 10-35,
  "menu_prestige_max": 85-100,
  "menu_max_prep_time": 8.0-15.0,
  "focus_archetype": "all or budget or mid or premium or luxury",
  "expected_customers": 6-12,
  "expected_high_value": 1-4,
  "expected_budget": 3-8,
  "bid_aggressiveness": 0.0-1.0,
  "bid_priority_ingredients": ["top 3 ingredient names"],
  "bid_reasoning": "explain bid strategy using price history",
  "price_strategy": "volume_first or balanced or premium",
  "price_adjustment_factor": 0.85-1.2,
  "undercut_competitors": true or false,
  "diplomacy_priority": "aggressive or moderate or passive or silent",
  "diplomacy_targets": [],
  "diplomacy_reasoning": "brief",
  "confidence": 0.4-0.9
}}"""

        return prompt

    async def _call_llm(self, prompt: str, use_fast: bool = False) -> str:
        """Call the LLM via datapizza a_invoke and return the response text."""
        client = self.fast_client if use_fast else self.llm_client
        try:
            response = await client.a_invoke(
                input=prompt,
                temperature=0.3,
                max_tokens=2000,
            )
            # datapizza clients return a response with .text attribute
            if hasattr(response, "text"):
                return response.text
            elif hasattr(response, "content"):
                return response.content
            elif isinstance(response, str):
                return response
            else:
                logger.warning(f"Unexpected LLM response type: {type(response)}")
                return str(response)
        except Exception as e:
            logger.error(f"LLM call failed: {e}", exc_info=True)
            return ""

    def _parse_strategy_response(self, response: str, context: dict) -> TurnStrategy:
        """Parse the LLM's JSON response into a TurnStrategy."""
        strategy = TurnStrategy()
        strategy.raw_reasoning = response

        try:
            # Strip markdown code fences if present
            text = response.strip()
            if text.startswith("```"):
                # Remove opening fence
                first_newline = text.index("\n")
                text = text[first_newline + 1:]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()

            data = json.loads(text)

            # Parse zone
            zone = data.get("recommended_zone", "DIVERSIFIED")
            valid_zones = {
                "DIVERSIFIED", "PREMIUM_MONOPOLIST", "BUDGET_OPPORTUNIST",
                "SPEED_CONTENDER", "NICHE_SPECIALIST", "MARKET_ARBITRAGEUR",
            }
            strategy.recommended_zone = zone if zone in valid_zones else "DIVERSIFIED"
            strategy.zone_reasoning = str(data.get("zone_reasoning", ""))[:200]

            # Parse menu
            strategy.menu_target_size = max(8, min(25, int(data.get("menu_target_size", 15))))
            strategy.menu_diversify = bool(data.get("menu_diversify", True))
            strategy.menu_prestige_min = max(10, min(60, int(data.get("menu_prestige_min", 15))))
            strategy.menu_prestige_max = max(70, min(100, int(data.get("menu_prestige_max", 100))))
            strategy.menu_max_prep_time = max(5.0, min(20.0, float(data.get("menu_max_prep_time", 12.0))))
            strategy.menu_priority_recipes = list(data.get("menu_priority_recipes", []))[:10]
            strategy.menu_avoid_recipes = list(data.get("menu_avoid_recipes", []))[:10]

            # Parse bids
            strategy.bid_aggressiveness = max(0.0, min(1.0, float(data.get("bid_aggressiveness", 0.35))))
            strategy.bid_priority_ingredients = list(data.get("bid_priority_ingredients", []))[:5]
            strategy.bid_reasoning = str(data.get("bid_reasoning", ""))[:200]

            # Parse pricing
            price_strat = data.get("price_strategy", "volume_first")
            if price_strat in ("volume_first", "balanced", "premium"):
                strategy.price_strategy = price_strat
            strategy.price_adjustment_factor = max(0.6, min(1.5, float(data.get("price_adjustment_factor", 1.0))))
            strategy.undercut_competitors = bool(data.get("undercut_competitors", True))

            # Parse focus/customer flow
            focus = data.get("focus_archetype", "all")
            if focus in ("all", "budget", "mid", "premium", "luxury"):
                strategy.focus_archetype = focus
            strategy.expected_customers = max(3, min(20, int(data.get("expected_customers", 8))))
            strategy.expected_high_value = max(0, min(10, int(data.get("expected_high_value", 2))))
            strategy.expected_budget = max(0, min(15, int(data.get("expected_budget", 4))))

            # Parse diplomacy
            diplo = data.get("diplomacy_priority", "moderate")
            if diplo in ("aggressive", "moderate", "passive", "silent"):
                strategy.diplomacy_priority = diplo
            strategy.diplomacy_targets = [int(t) for t in data.get("diplomacy_targets", []) if t][:5]
            strategy.diplomacy_reasoning = str(data.get("diplomacy_reasoning", ""))[:200]

            # Confidence
            strategy.confidence = max(0.2, min(0.9, float(data.get("confidence", 0.5))))

        except (json.JSONDecodeError, ValueError, KeyError, IndexError) as e:
            logger.warning(f"Failed to parse strategy response: {e}")
            strategy = self._default_strategy(context)
            strategy.raw_reasoning = response

        return strategy

    def _default_strategy(self, context: dict) -> TurnStrategy:
        """
        Default strategy when LLM consultation fails.
        Rotates focus archetype based on turn number for variety.
        """
        strategy = TurnStrategy()
        active = context.get("active_competitors", 0)
        turn_id = context.get("turn_id", 1)

        # ── Auto-rotate focus archetype each turn ──
        focus_cycle = ["all", "budget", "mid", "premium", "all", "balanced"]
        strategy.focus_archetype = focus_cycle[turn_id % len(focus_cycle)]

        # ── Rotate price strategy too ──
        price_cycle = ["volume_first", "balanced", "volume_first", "premium", "balanced"]
        strategy.price_strategy = price_cycle[turn_id % len(price_cycle)]

        if active == 0:
            strategy.recommended_zone = "DIVERSIFIED"
            strategy.zone_reasoning = "No competition — diversify to serve all archetypes"
            strategy.bid_aggressiveness = 0.20
            strategy.diplomacy_priority = "silent"
        elif active <= 2:
            strategy.recommended_zone = "DIVERSIFIED"
            strategy.zone_reasoning = "Light competition — broad menu captures most customers"
            strategy.bid_aggressiveness = 0.30
            strategy.diplomacy_priority = "moderate"
        else:
            strategy.recommended_zone = "DIVERSIFIED"
            strategy.zone_reasoning = "Heavy competition — diversify to avoid direct conflicts"
            strategy.bid_aggressiveness = 0.40
            strategy.undercut_competitors = True
            strategy.diplomacy_priority = "aggressive"

        # ── Adjust for focus archetype ──
        if strategy.focus_archetype == "premium" or strategy.focus_archetype == "luxury":
            strategy.expected_high_value = 3
            strategy.expected_budget = 3
            strategy.price_adjustment_factor = 1.1
        elif strategy.focus_archetype == "budget":
            strategy.expected_high_value = 1
            strategy.expected_budget = 6
            strategy.price_adjustment_factor = 0.9
        else:
            strategy.expected_high_value = 2
            strategy.expected_budget = 4
            strategy.price_adjustment_factor = 1.0

        strategy.menu_target_size = 15
        strategy.menu_diversify = True
        strategy.menu_prestige_min = 10
        strategy.menu_prestige_max = 100
        strategy.menu_max_prep_time = 12.0
        strategy.expected_customers = 8
        strategy.confidence = 0.4
        strategy.raw_reasoning = f"Default strategy (focus={strategy.focus_archetype}, price={strategy.price_strategy})"

        return strategy
