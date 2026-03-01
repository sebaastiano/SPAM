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

    # Skill activation (agent decides which skills to run)
    skills_to_activate: list[str] = field(default_factory=lambda: [
        "intelligence_scan", "zone_selection", "menu_planning", "menu_save",
    ])

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
        pnl_history: list[dict] | None = None,
        feature_vectors: dict | None = None,
        trajectory_predictions: dict | None = None,
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
                pnl_history=pnl_history,
                feature_vectors=feature_vectors,
                trajectory_predictions=trajectory_predictions,
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
            "skills": strategy.skills_to_activate,
        })

        return strategy

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
        Provide menu composition guidance.

        Returns dict with keys:
          - target_size: int
          - prestige_min: int
          - prestige_max: int
          - max_prep_time: float
          - priority_recipes: list[str]
          - diversity_bonus: float (0.0-1.0, how much to reward prestige spread)
        """
        strat = self._last_strategy or TurnStrategy()

        guidance = {
            "target_size": strat.menu_target_size,
            "prestige_min": strat.menu_prestige_min,
            "prestige_max": strat.menu_prestige_max,
            "max_prep_time": strat.menu_max_prep_time,
            "priority_recipes": strat.menu_priority_recipes,
            "diversity_bonus": 0.3 if strat.menu_diversify else 0.0,
            "diversify": strat.menu_diversify,
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
                f"diversify={guidance['diversify']}"
            )
        else:
            # Low confidence — use broad defaults for diversification
            guidance["target_size"] = max(12, guidance["target_size"])
            guidance["prestige_min"] = 15
            guidance["prestige_max"] = 100
            guidance["max_prep_time"] = 12.0
            guidance["diversity_bonus"] = 0.25
            guidance["diversify"] = True

        return guidance

    async def consult_bid(
        self,
        zone: str,
        balance: float,
        active_competitors: int,
    ) -> dict:
        """
        Provide bidding guidance.

        Returns dict with keys:
          - spending_fraction: float (0.0-0.6)
          - priority_ingredients: list[str]
          - aggressiveness: float (0.0-1.0)
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

        guidance = {
            "spending_fraction": spending,
            "priority_ingredients": strat.bid_priority_ingredients,
            "aggressiveness": aggr,
        }

        logger.info(
            f"Bid guidance from agent: spending={spending:.2f}, "
            f"aggr={aggr:.2f}, priority={strat.bid_priority_ingredients[:3]}"
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
        pnl_history: list[dict] | None = None,
        feature_vectors: dict | None = None,
        trajectory_predictions: dict | None = None,
    ) -> dict:
        """Build a compact context dict for the LLM, including P&L and vector space."""
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

        # Competitor summary (enriched with vector + trajectory data)
        comp_summary = []
        for rid, b in briefings.items():
            entry = {
                "id": rid,
                "name": b.get("name", f"Team {rid}"),
                "strategy": b.get("strategy", "UNKNOWN"),
                "connected": b.get("is_connected", False),
                "menu_size": b.get("menu_size", 0),
                "avg_price": b.get("menu_price_avg", 0),
                "reputation": b.get("reputation", 0),
                "balance": b.get("balance", 0),
                "threat": b.get("threat_level", 0),
            }
            # Attach bid history from briefing if available
            if b.get("recent_bids"):
                entry["recent_bids"] = b["recent_bids"][-3:]  # last 3 turns
            # Attach trajectory prediction if available
            if trajectory_predictions and str(rid) in trajectory_predictions:
                tp = trajectory_predictions[str(rid)]
                entry["trajectory"] = {
                    "predicted_direction": tp.get("direction", "stable"),
                    "momentum": tp.get("momentum", 0),
                }
            comp_summary.append(entry)

        # History summary (what worked in past turns?)
        history_summary = list(self._turn_history[-5:])

        # ── P&L summary ──
        pnl_summary = {}
        if pnl_history:
            total_spent = sum(p.get("bid_cost", 0) + p.get("market_cost", 0) for p in pnl_history)
            total_revenue = sum(p.get("market_income", 0) for p in pnl_history)
            total_profit = sum(p.get("net_profit", 0) for p in pnl_history)
            pnl_summary = {
                "turns_tracked": len(pnl_history),
                "total_spent": round(total_spent, 1),
                "total_revenue": round(total_revenue, 1),
                "total_profit": round(total_profit, 1),
                "avg_profit_per_turn": round(total_profit / len(pnl_history), 1) if pnl_history else 0,
                "last_turn": pnl_history[-1] if pnl_history else {},
                "trend": "improving" if len(pnl_history) >= 2 and pnl_history[-1].get("net_profit", 0) > pnl_history[-2].get("net_profit", 0) else "declining" if len(pnl_history) >= 2 else "unknown",
            }

        # ── Vector space gap analysis ──
        # Feature labels for interpretability
        _FEAT_LABELS = [
            "bid_aggr", "bid_conc", "bid_consist", "bid_vol",
            "price_pos", "menu_stab", "spec_depth", "mkt_activity",
            "buy_sell", "bal_growth", "rep_rate", "prestige_tgt",
            "recipe_complex", "menu_size",
        ]
        gap_analysis = {}
        if feature_vectors:
            for rid, fv in feature_vectors.items():
                if hasattr(fv, 'tolist'):
                    fv = fv.tolist()
                top_features = sorted(
                    enumerate(fv), key=lambda x: abs(x[1]), reverse=True
                )[:5]
                gap_analysis[rid] = {
                    _FEAT_LABELS[i]: round(v, 3) for i, v in top_features
                }

        # ── Demand forecast summary ──
        demand_forecast = intel.get("demand_forecast", {})
        top_demanded = []
        if demand_forecast:
            sorted_items = sorted(
                demand_forecast.items(), key=lambda x: x[1], reverse=True
            )[:8]
            top_demanded = [{"ingredient": k, "demand_score": round(v, 2)} for k, v in sorted_items]

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
            "pnl": pnl_summary,
            "vector_gaps": gap_analysis,
            "top_demanded": top_demanded,
        }

    def _build_strategy_prompt(self, context: dict) -> str:
        """Build the strategy reasoning prompt for the LLM, including P&L and vector context."""
        competitors_text = ""
        for c in context.get("competitors", []):
            if c.get("connected"):
                line = (
                    f"  - {c['name']} (ID {c['id']}): strategy={c['strategy']}, "
                    f"menu_size={c['menu_size']}, avg_price={c['avg_price']:.0f}, "
                    f"reputation={c['reputation']}, threat={c['threat']:.2f}"
                )
                if c.get("trajectory"):
                    t = c["trajectory"]
                    line += f", direction={t['predicted_direction']}, momentum={t['momentum']:.2f}"
                if c.get("recent_bids"):
                    line += f", recent_bids={c['recent_bids']}"
                competitors_text += line + "\n"

        history_text = ""
        for h in context.get("history", []):
            history_text += (
                f"  Turn {h['turn_id']}: zone={h['zone']}, "
                f"menu_size={h['menu_size']}, bid_aggr={h['bid_aggr']:.2f}\n"
            )

        # ── P&L section ──
        pnl_text = ""
        pnl = context.get("pnl", {})
        if pnl:
            pnl_text = f"""
P&L PERFORMANCE (last {pnl.get('turns_tracked', 0)} turns):
- Total spent: {pnl.get('total_spent', 0):.0f} credits
- Total revenue: {pnl.get('total_revenue', 0):.0f} credits
- Total profit: {pnl.get('total_profit', 0):.0f} credits
- Avg profit/turn: {pnl.get('avg_profit_per_turn', 0):.0f} credits
- Trend: {pnl.get('trend', 'unknown')}
- Last turn: spent={pnl.get('last_turn', {}).get('bid_cost', 0):.0f}, revenue={pnl.get('last_turn', {}).get('market_income', 0):.0f}, profit={pnl.get('last_turn', {}).get('net_profit', 0):.0f}

CRITICAL: If profit is negative or trending down, REDUCE bid_aggressiveness and INCREASE prices.
If spending > revenue consistently, switch to a more conservative zone with lower bids.
"""

        # ── Vector space section ──
        vector_text = ""
        gaps = context.get("vector_gaps", {})
        if gaps:
            vector_text = "\nCOMPETITOR BEHAVIORAL SIGNATURES (top features per competitor):\n"
            for rid, feats in list(gaps.items())[:6]:
                feat_str = ", ".join(f"{k}={v}" for k, v in feats.items())
                vector_text += f"  - Team {rid}: {feat_str}\n"
            vector_text += (
                "  Use these to identify where competition is weakest.\n"
                "  High bid_aggr = aggressive bidder, high spec_depth = niche player.\n"
                "  Look for underserved zones where no competitor has strong features.\n"
            )

        # ── Demand forecast section ──
        demand_text = ""
        top_demanded = context.get("top_demanded", [])
        if top_demanded:
            demand_text = "\nTOP DEMANDED INGREDIENTS:\n"
            for d in top_demanded:
                demand_text += f"  - {d['ingredient']}: demand_score={d['demand_score']}\n"
            demand_text += "  Prioritize bidding on high-demand ingredients.\n"

        prompt = f"""You are the strategic brain of restaurant SPAM! (Team 17) in a competitive restaurant game.

CURRENT STATE (Turn {context['turn_id']}):
- Balance: {context['balance']:.0f} credits
- Reputation: {context['reputation']:.1f}/100
- Inventory: {context['total_inventory']} items ({context['unique_ingredients']} types)
- Cookable recipes (from inventory): {context['cookable_recipes']}/{context['total_recipes']}
- Recipe prestige range: {context['prestige_range'][0]:.0f} - {context['prestige_range'][1]:.0f}
- Active competitors: {context['active_competitors']}
{pnl_text}
COMPETITORS:
{competitors_text if competitors_text else "  No active competitors detected."}
{vector_text}
PAST TURNS:
{history_text if history_text else "  No history yet (first turn)."}
{demand_text}
CUSTOMER ARCHETYPES (all present in the game):
- Esploratore Galattico: budget-conscious, max budget ~60 credits
- Famiglie Orbitali: moderate budget, max ~150 credits
- Saggi del Cosmo: high spenders, max ~600 credits
- Astrobarone: luxury spenders, max ~500 credits

STRATEGIC PRIORITIES:
1. MAXIMIZE PROFIT (revenue minus costs). Revenue without profit is useless.
2. MINIMIZE BID SPENDING — only bid what's necessary to win key ingredients
3. Keep a LARGE, DIVERSE menu spanning ALL price tiers to attract ALL archetypes
4. Price dishes to MAXIMIZE EXPECTED REVENUE (considering order probability at each price point)
5. Use vector space intelligence to find competitive gaps and avoid direct conflicts
6. Use diplomacy strategically to create advantages, not waste time

AVAILABLE ZONES:
- DIVERSIFIED: Targets ALL archetypes with a broad menu (15+ dishes). Best when you want maximum customer coverage.
- PREMIUM_MONOPOLIST: High-prestige dishes for rich clients. Best when no competition in premium tier.
- BUDGET_OPPORTUNIST: High-volume budget dishes. Best when budget gap exists.
- SPEED_CONTENDER: Fast dishes across prestiges. Best when speed advantage matters.
- NICHE_SPECIALIST: Focus on one underserved archetype.
- MARKET_ARBITRAGEUR: Trade-focused, minimal menu.

SKILLS YOU CAN ACTIVATE THIS TURN:
You decide which skills run. At minimum, "intelligence_scan", "zone_selection", "menu_planning", "menu_save" should always run.
Optional skills: "diplomacy_send" (send diplomatic messages), "market_ops" (buy/sell on market).
During closed_bid phase: "bid_compute", "bid_submit" always run.

Respond with a JSON object (no markdown, no explanation outside JSON):
{{
  "recommended_zone": "DIVERSIFIED or one of the zones above",
  "zone_reasoning": "brief reason for zone choice, referencing P&L and vector data",
  "menu_target_size": 12-20,
  "menu_diversify": true or false,
  "menu_prestige_min": 15-40,
  "menu_prestige_max": 80-100,
  "menu_max_prep_time": 8.0-15.0,
  "bid_aggressiveness": 0.0-1.0,
  "bid_priority_ingredients": ["top 3 ingredient names to prioritize"],
  "bid_reasoning": "brief bid strategy referencing P&L data and spending efficiency",
  "price_strategy": "volume_first or balanced or premium",
  "price_adjustment_factor": 0.8-1.2,
  "undercut_competitors": true or false,
  "diplomacy_priority": "aggressive or moderate or passive or silent",
  "diplomacy_targets": [competitor IDs to focus on],
  "diplomacy_reasoning": "brief diplomacy strategy",
  "skills_to_activate": ["intelligence_scan", "zone_selection", "menu_planning", "menu_save", ...],
  "confidence": 0.3-0.9
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

            # Parse diplomacy
            diplo = data.get("diplomacy_priority", "moderate")
            if diplo in ("aggressive", "moderate", "passive", "silent"):
                strategy.diplomacy_priority = diplo
            strategy.diplomacy_targets = [int(t) for t in data.get("diplomacy_targets", []) if t][:5]
            strategy.diplomacy_reasoning = str(data.get("diplomacy_reasoning", ""))[:200]

            # Parse skills to activate
            requested_skills = data.get("skills_to_activate", [])
            if isinstance(requested_skills, list) and requested_skills:
                # Always include core skills
                core = {"intelligence_scan", "zone_selection", "menu_planning", "menu_save"}
                strategy.skills_to_activate = list(core | set(requested_skills))
            else:
                strategy.skills_to_activate = [
                    "intelligence_scan", "zone_selection", "menu_planning", "menu_save",
                ]

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
        Biased toward DIVERSIFIED zone with broad menu.
        """
        strategy = TurnStrategy()
        active = context.get("active_competitors", 0)

        if active == 0:
            strategy.recommended_zone = "DIVERSIFIED"
            strategy.zone_reasoning = "No competition — diversify to serve all archetypes"
            strategy.bid_aggressiveness = 0.20
            strategy.price_strategy = "balanced"
            strategy.diplomacy_priority = "silent"
        elif active <= 2:
            strategy.recommended_zone = "DIVERSIFIED"
            strategy.zone_reasoning = "Light competition — broad menu captures most customers"
            strategy.bid_aggressiveness = 0.30
            strategy.price_strategy = "volume_first"
            strategy.diplomacy_priority = "moderate"
        else:
            strategy.recommended_zone = "DIVERSIFIED"
            strategy.zone_reasoning = "Heavy competition — diversify to avoid direct conflicts"
            strategy.bid_aggressiveness = 0.40
            strategy.price_strategy = "volume_first"
            strategy.undercut_competitors = True
            strategy.diplomacy_priority = "aggressive"

        strategy.menu_target_size = 15
        strategy.menu_diversify = True
        strategy.menu_prestige_min = 15
        strategy.menu_prestige_max = 100
        strategy.menu_max_prep_time = 12.0
        strategy.confidence = 0.4
        strategy.raw_reasoning = "Default strategy (LLM unavailable)"
        strategy.skills_to_activate = [
            "intelligence_scan", "zone_selection", "menu_planning",
            "menu_save", "diplomacy_send", "market_ops",
        ]

        return strategy
