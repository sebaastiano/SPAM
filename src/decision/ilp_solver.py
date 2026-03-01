"""
SPAM! — ILP Solver
====================
Zone-specific ILP bid and menu optimization.
Uses scipy.optimize.milp for exact optimal solutions.

Decision variables (stacked into a single vector):
  y_j  (j=0..J-1)  — binary: 1 if recipe j is on the menu
  x_i  (i=0..I-1)  — integer: quantity of ingredient i to bid on

Objective: maximize  sum_j(revenue_j * y_j) - sum_i(bid_price_i * x_i)
           (milp minimises, so we negate)

Constraints:
  C1  menu_min  ≤ sum(y_j)                ≤ menu_max        (zone menu size)
  C2  For each ingredient i used by recipe j:
        sum_j(need_{ij} * y_j) ≤ inventory_i + x_i           (ingredient supply)
  C3  sum_i(bid_price_i * x_i) ≤ balance * spending_fraction (budget cap)
"""

import logging

import numpy as np
from scipy.optimize import milp, LinearConstraint, Bounds
from scipy.sparse import eye as speye

from src.config import (
    ZONE_PRESTIGE_RANGE,
    ZONE_MENU_SIZE,
    ZONE_MAX_PREP_TIME,
    ZONE_PRICE_FACTORS,
    ARCHETYPE_CEILINGS,
    ZONE_TARGET_ARCHETYPES,
    PRICE_TIERS,
    HIGH_DELTA_INGREDIENTS,
    SERVINGS_BUFFER,
    DEFAULT_SPENDING_FRACTION,
    AGGRESSIVE_SPENDING_FRACTION,
    BASE_BID_PRICES,
    DEFAULT_BASE_BID,
    MINIMUM_PROFIT_MARGIN,
)

logger = logging.getLogger("spam.decision.ilp_solver")


class ZoneDecision:
    """Output of the ILP solver for a specific zone."""

    def __init__(self):
        self.bids: list[dict] = []  # [{ingredient, bid, quantity}]
        self.menu: list[dict] = []  # [{name, price}]
        self.zone: str = ""
        self.expected_revenue: float = 0.0
        self.total_bid_cost: float = 0.0


def solve_zone_ilp(
    zone: str,
    balance: float,
    inventory: dict[str, int],
    recipes: list[dict],
    demand_forecast: dict[str, float],
    competitor_briefings: dict[int, dict],
    reputation: float = 100.0,
    spending_fraction: float | None = None,
    agent_guidance: dict | None = None,
    pnl_history: list[dict] | None = None,
) -> ZoneDecision:
    """
    Solve the zone-specific MILP for menu selection and bid allocation.

    Decision variables  (stacked vector  v = [y_0 … y_{J-1}, x_0 … x_{I-1}]):
      y_j ∈ {0,1}  — include recipe j on menu
      x_i ∈ Z≥0    — quantity of ingredient i to bid on

    Objective (minimised by scipy):
      min  -Σ_j(realistic_revenue_j · y_j) + Σ_i(bid_price_i · x_i)

    Subject to:
      menu_min ≤ Σ y_j ≤ menu_max                                      (C1)
      SERVINGS_BUFFER * Σ_j(need_{ij} · y_j) - x_i ≤ inventory_i  ∀ i  (C2)
      Σ_i(bid_price_i · x_i) ≤ budget                                  (C3)

    REVENUE REALISM (new): The raw menu price is discounted by an
    "order probability" factor based on:
      - Historical avg revenue per client / dish price
      - Menu competition (more items → each gets fewer orders)
      - Client archetype distribution (budget vs premium)
    This prevents the solver from thinking every dish = 1 guaranteed sale.
    """
    decision = ZoneDecision()
    decision.zone = zone

    # ── Spending fraction: P&L-aware auto-selection ──
    if spending_fraction is None:
        spending_fraction = _compute_smart_spending(
            balance, competitor_briefings, pnl_history,
        )

    # ── Zone constraints (optionally overridden by agent guidance) ──
    prestige_min, prestige_max = ZONE_PRESTIGE_RANGE.get(zone, (0, 100))
    menu_min, menu_max = ZONE_MENU_SIZE.get(zone, (3, 10))
    max_prep_time = ZONE_MAX_PREP_TIME.get(zone, 10.0)

    # Apply agent guidance overrides if available
    if agent_guidance:
        ag_pmin = agent_guidance.get("prestige_min")
        ag_pmax = agent_guidance.get("prestige_max")
        ag_prep = agent_guidance.get("max_prep_time")
        ag_size = agent_guidance.get("target_size")

        if ag_pmin is not None:
            prestige_min = min(prestige_min, ag_pmin)  # widen lower bound
        if ag_pmax is not None:
            prestige_max = max(prestige_max, ag_pmax)  # widen upper bound
        if ag_prep is not None:
            max_prep_time = max(max_prep_time, ag_prep)  # relax prep time
        if ag_size is not None:
            # Agent can push for larger menu — widen upper bound
            menu_max = max(menu_max, ag_size)
            # But keep a reasonable minimum
            menu_min = max(menu_min, min(8, ag_size - 4))

        logger.info(
            f"Agent guidance applied: prestige=[{prestige_min},{prestige_max}], "
            f"menu=[{menu_min},{menu_max}], prep≤{max_prep_time}s"
        )

    # ── Filter eligible recipes ──
    eligible_recipes: list[dict] = []
    for recipe in recipes:
        prestige = recipe.get("prestige", 50)
        prep_time = recipe.get("prep_time", 5.0)
        if prestige_min <= prestige <= prestige_max and prep_time <= max_prep_time:
            eligible_recipes.append(recipe)

    if not eligible_recipes:
        logger.warning(f"No eligible recipes for zone {zone}")
        return decision

    J = len(eligible_recipes)

    # ── Collect the union of all ingredients used by eligible recipes ──
    all_ingredients_set: set[str] = set()
    for recipe in eligible_recipes:
        all_ingredients_set.update(recipe.get("ingredients", {}).keys())
    all_ingredients = sorted(all_ingredients_set)
    I = len(all_ingredients)
    ing_idx = {name: idx for idx, name in enumerate(all_ingredients)}

    # ── Extract agent pricing guidance if available ──
    agent_pricing = None
    if agent_guidance:
        agent_pricing = {
            "strategy": agent_guidance.get("price_strategy", "volume_first"),
            "adjustment_factor": agent_guidance.get("price_adjustment", 1.0),
            "undercut": agent_guidance.get("undercut", True),
        }

    # ── Per-recipe revenue (REALISTIC: price × order probability) ──
    raw_prices = np.array(
        [compute_menu_price(r, zone, reputation, competitor_briefings, agent_pricing)
         for r in eligible_recipes],
        dtype=float,
    )

    # Discount prices by realistic order probability
    # NOT every dish gets ordered. A menu of 15 dishes might see 3-8 orders
    # total in a serving window. Each dish's "expected revenue" is:
    #   price × P(ordered) where P depends on menu size, prestige tier, speed
    menu_size_target = menu_max  # approximate final menu size
    order_probabilities = _estimate_order_probabilities(
        eligible_recipes, menu_size_target, reputation, competitor_briefings,
    )
    revenues = raw_prices * order_probabilities

    # ── Per-ingredient bid price ──
    bid_prices = np.array(
        [
            compute_bid_price(ing, competitor_briefings, demand_forecast)
            for ing in all_ingredients
        ],
        dtype=float,
    )

    # ── need matrix  need[i, j] = qty of ingredient i required by recipe j ──
    # Multiply by SERVINGS_BUFFER: we need enough ingredients for multiple
    # servings per dish (multiple customers may order the same dish).
    need = np.zeros((I, J), dtype=float)
    for j, recipe in enumerate(eligible_recipes):
        for ing, qty in recipe.get("ingredients", {}).items():
            need[ing_idx[ing], j] = qty * SERVINGS_BUFFER

    # ── Current inventory for each ingredient ──
    inv = np.array(
        [inventory.get(ing, 0) for ing in all_ingredients], dtype=float
    )

    budget = balance * spending_fraction

    # ── Decision variable layout:  v = [y_0 … y_{J-1},  x_0 … x_{I-1}] ──
    N = J + I

    # Objective:  min  -revenue·y + bidprice·x
    c = np.zeros(N)
    c[:J] = -revenues          # negate because milp minimises
    c[J:] = bid_prices

    # Integrality: y_j binary (1), x_i integer (1)
    integrality = np.ones(N, dtype=int)  # 1 = integer for all

    # Bounds: y_j ∈ [0,1], x_i ∈ [0, large]
    lb = np.zeros(N)
    ub = np.full(N, np.inf)
    ub[:J] = 1.0  # binary

    bounds = Bounds(lb=lb, ub=ub)

    # ── Constraints ──
    constraints: list[LinearConstraint] = []

    # C1: menu_min ≤ Σ y_j ≤ menu_max
    A_menu = np.zeros((1, N))
    A_menu[0, :J] = 1.0
    constraints.append(LinearConstraint(A_menu, lb=menu_min, ub=menu_max))

    # C2: For each ingredient i:  Σ_j(need_{ij} · y_j) - x_i ≤ inv_i
    #     i.e.   need[i,:] · y  -  x_i  ≤  inv_i
    A_supply = np.zeros((I, N))
    A_supply[:, :J] = need            # need[i,j] * y_j
    for i in range(I):
        A_supply[i, J + i] = -1.0     # - x_i
    constraints.append(
        LinearConstraint(A_supply, lb=-np.inf, ub=inv)
    )

    # C3: Σ_i(bid_price_i · x_i) ≤ budget
    A_budget = np.zeros((1, N))
    A_budget[0, J:] = bid_prices
    constraints.append(LinearConstraint(A_budget, lb=0, ub=budget))

    # ── Solve ──
    try:
        result = milp(
            c=c,
            constraints=constraints,
            integrality=integrality,
            bounds=bounds,
        )

        if result.success:
            y_sol = np.round(result.x[:J]).astype(int)
            x_sol = np.round(result.x[J:]).astype(int)
        else:
            logger.warning(
                f"MILP infeasible for zone {zone}: {result.message} — "
                f"falling back to greedy"
            )
            return _greedy_fallback(
                zone, balance, inventory, eligible_recipes,
                demand_forecast, competitor_briefings, reputation,
                spending_fraction,
            )
    except Exception as e:
        logger.warning(f"MILP solver error for zone {zone}: {e} — falling back to greedy")
        return _greedy_fallback(
            zone, balance, inventory, eligible_recipes,
            demand_forecast, competitor_briefings, reputation,
            spending_fraction,
        )

    # ── Build decision from solution ──
    total_ingredient_cost_selected = 0.0
    for j in range(J):
        if y_sol[j]:
            recipe = eligible_recipes[j]
            price = int(revenues[j])
            # Compute per-dish ingredient cost for logging
            dish_cost = sum(
                BASE_BID_PRICES.get(ing, DEFAULT_BASE_BID) * qty
                for ing, qty in recipe.get("ingredients", {}).items()
            )
            total_ingredient_cost_selected += dish_cost
            decision.menu.append({"name": recipe["name"], "price": price})
            margin_pct = ((price - dish_cost) / max(dish_cost, 1)) * 100
            logger.info(
                f"  Menu: {recipe['name'][:45]:45s} price={price:4d}, "
                f"ing_cost={dish_cost:.0f}, margin={margin_pct:+.0f}%"
            )

    for i in range(I):
        if x_sol[i] > 0:
            decision.bids.append({
                "ingredient": all_ingredients[i],
                "bid": int(bid_prices[i]),
                "quantity": int(x_sol[i]),
            })

    decision.total_bid_cost = float(bid_prices @ x_sol)
    decision.expected_revenue = float(revenues @ y_sol)

    net_profit = decision.expected_revenue - decision.total_bid_cost
    logger.info(
        f"MILP [{zone}]: {len(decision.menu)} menu items, "
        f"{len(decision.bids)} bids (total_qty={sum(int(x) for x in x_sol)}), "
        f"cost={decision.total_bid_cost:.0f}/{budget:.0f} budget, "
        f"expected_rev={decision.expected_revenue:.0f}, "
        f"NET PROFIT={net_profit:+.0f}"
    )

    return decision


def _greedy_fallback(
    zone: str,
    balance: float,
    inventory: dict[str, int],
    eligible_recipes: list[dict],
    demand_forecast: dict[str, float],
    competitor_briefings: dict[int, dict],
    reputation: float,
    spending_fraction: float,
) -> ZoneDecision:
    """
    Greedy fallback when MILP is infeasible / errors out.
    Scores and ranks recipes then greedily allocates bids within budget.
    """
    decision = ZoneDecision()
    decision.zone = zone

    menu_min, menu_max = ZONE_MENU_SIZE.get(zone, (3, 10))

    scored_recipes = _score_recipes(
        eligible_recipes, zone, inventory, reputation, demand_forecast
    )

    selected = scored_recipes[:menu_max]
    if len(selected) < menu_min:
        selected = scored_recipes[:min(menu_min, len(scored_recipes))]

    for entry in selected:
        recipe = entry["recipe"]
        price = compute_menu_price(recipe, zone, reputation, competitor_briefings)
        decision.menu.append({"name": recipe["name"], "price": int(price)})

    needed_ingredients: dict[str, int] = {}
    for entry in selected:
        recipe = entry["recipe"]
        for ing, qty in recipe.get("ingredients", {}).items():
            current = inventory.get(ing, 0)
            # Bid for SERVINGS_BUFFER servings, minus what we already have
            need = max(0, qty * SERVINGS_BUFFER - current)
            needed_ingredients[ing] = needed_ingredients.get(ing, 0) + need

    budget = balance * spending_fraction
    total_bid_cost = 0.0

    for ing, qty in needed_ingredients.items():
        if qty <= 0:
            continue
        bid_price = compute_bid_price(ing, competitor_briefings, demand_forecast)
        cost = bid_price * qty
        if total_bid_cost + cost <= budget:
            decision.bids.append({
                "ingredient": ing,
                "bid": int(bid_price),
                "quantity": qty,
            })
            total_bid_cost += cost
        else:
            affordable_qty = max(1, int((budget - total_bid_cost) / bid_price))
            if affordable_qty > 0:
                decision.bids.append({
                    "ingredient": ing,
                    "bid": int(bid_price),
                    "quantity": affordable_qty,
                })
                total_bid_cost += bid_price * affordable_qty
            break

    decision.total_bid_cost = total_bid_cost
    decision.expected_revenue = sum(
        item["price"] for item in decision.menu
    )  # no discount — full revenue potential

    logger.info(
        f"Greedy [{zone}]: {len(decision.menu)} menu items, "
        f"{len(decision.bids)} bids, cost={total_bid_cost:.0f}, "
        f"expected_rev={decision.expected_revenue:.0f}"
    )

    return decision


def _score_recipes(
    recipes: list[dict],
    zone: str,
    inventory: dict[str, int],
    reputation: float,
    demand_forecast: dict[str, float],
) -> list[dict]:
    """Score and rank recipes for a zone — favor volume, diversity, and speed."""
    scored = []

    high_delta_set = {ing for ing, _ in HIGH_DELTA_INGREDIENTS}

    # Track prestige distribution for diversity bonus
    prestige_buckets = {}  # bucket_id -> count

    for recipe in recipes:
        prestige = recipe.get("prestige", 50)
        prep_time = recipe.get("prep_time", 5.0)
        ingredients = recipe.get("ingredients", {})

        # Score components
        prestige_score = prestige / 100.0

        # Speed score (faster = better — MORE customers served)
        speed_score = max(0, 1.0 - prep_time / 15.0)

        # Inventory fit (CRITICAL for volume: cook what we HAVE = no bidding cost)
        total_needed = sum(ingredients.values())
        have = sum(
            min(inventory.get(ing, 0), qty)
            for ing, qty in ingredients.items()
        )
        inventory_score = have / max(total_needed, 1)

        # Ingredient simplicity bonus: fewer distinct ingredients = cheaper to stock
        simplicity_bonus = max(0, 1.0 - len(ingredients) / 10.0) * 0.15

        # High-delta ingredient bonus
        delta_bonus = sum(
            0.1
            for ing in ingredients
            if ing in high_delta_set
        )

        # Competition penalty (high demand forecast = harder to get)
        competition_penalty = sum(
            demand_forecast.get(ing, 0) * 0.01
            for ing in ingredients
        )

        # Diversity bonus: recipes in underrepresented prestige buckets
        # score higher. This ensures the menu covers all price tiers.
        bucket = int(prestige // 20)  # 5 buckets: 0-19, 20-39, 40-59, 60-79, 80-100
        bucket_count = prestige_buckets.get(bucket, 0)
        diversity_bonus = max(0, 0.15 - bucket_count * 0.03)  # first in bucket gets most
        prestige_buckets[bucket] = bucket_count + 1

        # Zone-specific bonuses
        zone_bonus = 0.0
        if zone == "DIVERSIFIED":
            # DIVERSIFIED zone: extra bonus for covering extreme tiers
            if prestige <= 30 or prestige >= 80:
                zone_bonus = 0.08  # bonus for extreme tiers (budget + premium)
            # Extra speed bonus for diversified (need to serve many quickly)
            zone_bonus += speed_score * 0.05

        total_score = (
            prestige_score * 0.15
            + speed_score * 0.25
            + inventory_score * 0.30   # heavily favor what we already have
            + simplicity_bonus
            + delta_bonus * 0.05
            - competition_penalty * 0.05
            + diversity_bonus
            + zone_bonus
        )

        scored.append({"recipe": recipe, "score": total_score})

    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored


def compute_menu_price(
    recipe: dict, zone: str, reputation: float,
    competitor_briefings: dict[int, dict] | None = None,
    agent_pricing: dict | None = None,
) -> float:
    """
    Compute menu price for a dish: PROFIT-AWARE PRICING.

    The price is the MAXIMUM of:
      1. Prestige-tier base price (customer-facing value)
      2. Ingredient cost × MINIMUM_PROFIT_MARGIN (ensures profit)

    Then capped by archetype ceilings to remain attractive.
    """
    prestige = recipe.get("prestige", 50)
    ingredients = recipe.get("ingredients", {})

    # ── 1. Prestige-tier base price (demand-side) ──
    base_price = 60  # fallback
    for tier_name, (p_min, p_max, tier_price) in PRICE_TIERS.items():
        if p_min <= prestige <= p_max:
            base_price = tier_price
            break

    # Gentle prestige scaling WITHIN each tier (±20% max)
    prestige_mult = 1.0 + (prestige - 50) / 250

    # Reputation bonus — subtle
    rep_mult = 1.0 + (reputation - 50) / 300

    # Zone factor
    zone_factor = ZONE_PRICE_FACTORS.get(zone, 1.0)

    # Agent pricing adjustments
    agent_factor = 1.0
    agent_undercut = True
    if agent_pricing:
        agent_factor = agent_pricing.get("adjustment_factor", 1.0)
        strategy = agent_pricing.get("strategy", "volume_first")
        agent_undercut = agent_pricing.get("undercut", True)
        if strategy == "premium":
            agent_factor *= 1.15
        elif strategy == "balanced":
            agent_factor *= 1.05

    prestige_price = int(base_price * prestige_mult * rep_mult * zone_factor * agent_factor)

    # ── 2. Cost-based floor (supply-side) ──
    # Estimate ingredient cost for ONE serving of this dish
    total_ingredient_cost = 0.0
    for ing, qty in ingredients.items():
        bid_price = BASE_BID_PRICES.get(ing, DEFAULT_BASE_BID)
        total_ingredient_cost += bid_price * qty

    cost_floor = int(total_ingredient_cost * MINIMUM_PROFIT_MARGIN)

    # Take the HIGHER of prestige-price and cost-floor
    price = max(prestige_price, cost_floor)

    # ── 3. Competition adjustment ──
    if competitor_briefings:
        active_competitors = sum(
            1 for b in competitor_briefings.values()
            if b.get("is_connected", False)
        )
        if active_competitors == 0:
            # Monopoly — modest increase
            price = int(price * 1.15)
        elif agent_undercut:
            # Don't undercut below cost floor
            competitor_prices = [
                b.get("menu_price_avg", 0)
                for b in competitor_briefings.values()
                if b.get("menu_price_avg", 0) > 0
            ]
            if competitor_prices:
                avg_comp_price = sum(competitor_prices) / len(competitor_prices)
                if prestige <= 50:
                    undercut_price = int(avg_comp_price * 0.85)
                elif prestige <= 70:
                    undercut_price = int(avg_comp_price * 0.92)
                else:
                    undercut_price = int(avg_comp_price * 0.95)
                # Only undercut if it's still above cost floor
                price = max(min(price, undercut_price), cost_floor)

    # ── 4. Hard floor and ceiling ──
    # Floor: cost_floor or 20 credits minimum
    # Ceiling: 550 credits (stay under Saggi 600 ceiling with margin)
    price = max(max(cost_floor, 20), min(price, 550))

    return price


def compute_bid_price(
    ingredient: str,
    competitor_briefings: dict[int, dict],
    demand_forecast: dict[str, float],
) -> float:
    """
    Compute bid price for an ingredient.

    PROFIT-FIRST BIDDING: every credit spent on ingredients is a credit
    NOT in our pocket. The real profit comes from selling dishes at high
    prices, not from hoarding ingredients.

    Strategy:
    - Start from conservative BASE_BID_PRICES
    - Only scale up modestly when competitors specifically target this ingredient
    - HARD CAP: never bid more than MAX_BID_PER_INGREDIENT
    - When no competition: bid absolute minimum
    - The goal is to WIN cheaply, maximising dish profit margin
    """
    MAX_BID_PER_INGREDIENT = 80  # hard ceiling — no ingredient is worth more

    # Count active competitors
    active_competitors = sum(
        1 for b in competitor_briefings.values()
        if b.get("is_connected", False)
    )

    high_delta_names = {ing for ing, _ in HIGH_DELTA_INGREDIENTS}
    is_high_delta = ingredient in high_delta_names

    # Start from configured base price (ingredient-specific or default)
    base = BASE_BID_PRICES.get(ingredient, DEFAULT_BASE_BID)

    # Gather competitor intelligence for this specific ingredient
    predicted_competitor_bids = []
    for rid, brief in competitor_briefings.items():
        if not brief.get("is_connected", False):
            continue
        if ingredient in brief.get("top_bid_ingredients", []):
            est_bid = brief.get("predicted_bid_spend", 100) / max(
                len(brief.get("top_bid_ingredients", [1])), 1
            )
            strategy = brief.get("strategy", "")
            if strategy == "AGGRESSIVE_HOARDER":
                est_bid *= 1.2
            elif strategy == "REACTIVE_CHASER":
                est_bid *= 1.1
            elif strategy == "DECLINING":
                est_bid *= 0.6
            predicted_competitor_bids.append(est_bid)

    if not predicted_competitor_bids:
        # No competitor specifically targeting this ingredient.
        if active_competitors == 0:
            # True monopoly — bid bare minimum
            return max(base * 0.3, 8) if is_high_delta else max(base * 0.25, 5)

        # Light competition — bid conservatively, just above base
        competition_factor = min(active_competitors / 6.0, 1.0)
        scaled = base * (1.0 + competition_factor * 0.25)
        return int(min(max(scaled, 10), MAX_BID_PER_INGREDIENT))

    # Competitors target this ingredient — bid just enough to beat them.
    predicted_max = max(predicted_competitor_bids)

    # Demand pressure (mild, we're conservative)
    demand = demand_forecast.get(ingredient, 0)
    demand_multiplier = 1.0 + min(demand / 20, 0.2)

    # Modest overbid — just enough to win, not a penny more
    targeting_count = len(predicted_competitor_bids)
    overbid_factor = 1.05 + 0.03 * min(targeting_count, 5)

    bid = predicted_max * demand_multiplier * overbid_factor

    # Ensure bid is at least our base price
    bid = max(bid, base)

    # Tiny premium for high-delta (they boost prestige → higher dish prices)
    if is_high_delta:
        bid *= 1.05

    # HARD CAP: never overspend on any single ingredient
    bid = min(bid, MAX_BID_PER_INGREDIENT)

    return int(bid) + 1


# ─────────────────────────────────────────────────────────────────
# P&L-Aware Spending & Realistic Revenue Estimation
# ─────────────────────────────────────────────────────────────────

def _compute_smart_spending(
    balance: float,
    competitor_briefings: dict[int, dict],
    pnl_history: list[dict] | None = None,
) -> float:
    """
    Compute spending fraction using ACTUAL P&L history.

    Instead of hardcoded 0.25/0.35, adapts based on:
    - How much we actually earned vs. spent in recent turns
    - Whether spending more led to more profit (or just more loss)
    - Competition level (more competitors → need to bid more)
    - Balance trend (declining → be conservative)

    The goal: NEVER spend more than we can realistically earn back.
    """
    active_competitors = sum(
        1 for b in competitor_briefings.values()
        if b.get("is_connected", False)
    )

    # Base spending by competition level (conservative defaults)
    if active_competitors == 0:
        base = 0.10  # monopoly: barely spend anything
    elif active_competitors <= 2:
        base = 0.15
    elif active_competitors <= 4:
        base = 0.20
    else:
        base = 0.25

    if not pnl_history or len(pnl_history) < 2:
        return base

    # Analyse recent P&L: are we profitable?
    recent = pnl_history[-5:]
    avg_delta = sum(p.get("balance_delta", 0) for p in recent) / len(recent)
    avg_bid_cost = sum(p.get("bid_cost", 0) for p in recent) / len(recent)
    avg_clients = sum(p.get("clients_served", 0) for p in recent) / len(recent)

    # If we're losing money on average, cut spending aggressively
    if avg_delta < -100:
        # Losing money → spend less
        reduction = min(0.10, abs(avg_delta) / 2000)
        base = max(0.05, base - reduction)
        logger.info(
            f"P&L-aware spending: avg_delta={avg_delta:.0f} (losing), "
            f"reducing to {base:.2f}"
        )
    elif avg_delta > 200:
        # Profitable → can afford slightly more, but stay conservative
        boost = min(0.05, avg_delta / 5000)
        base = min(0.30, base + boost)
        logger.info(
            f"P&L-aware spending: avg_delta={avg_delta:.0f} (profitable), "
            f"increasing to {base:.2f}"
        )

    # If we're spending a lot on bids but not getting clients, cut spending
    if avg_bid_cost > 0 and avg_clients < 2:
        base = max(0.05, base * 0.7)
        logger.info(
            f"P&L-aware: high bid cost ({avg_bid_cost:.0f}) but few clients "
            f"({avg_clients:.1f}) → reducing to {base:.2f}"
        )

    # Never spend more than 30% even under pressure
    return min(0.30, max(0.05, base))


def _estimate_order_probabilities(
    recipes: list[dict],
    menu_size: int,
    reputation: float,
    competitor_briefings: dict[int, dict],
) -> np.ndarray:
    """
    Estimate the probability that each dish gets at least one order.

    Factors:
    - Menu size: more items → each gets fewer orders (dilution)
    - Prestige tier: mid-range dishes get ordered more (larger client pool)
    - Speed: faster dishes can be served more times
    - Competition: more competitors → fewer clients reach us

    Returns array of probabilities [0, 1] for each recipe.
    """
    n = len(recipes)
    if n == 0:
        return np.array([])

    active_competitors = sum(
        1 for b in competitor_briefings.values()
        if b.get("is_connected", False)
    )

    # Base order probability: assume ~5-10 clients per serving window total,
    # split across N competitors. Each client orders 1 dish.
    # So our restaurant might see 2-8 clients per turn.
    total_clients_estimate = 8  # typical game clients per turn
    our_share = 1.0 / max(active_competitors + 1, 1)
    our_clients_estimate = total_clients_estimate * our_share

    # Reputation bonus: higher rep → slightly more clients
    rep_factor = 0.8 + (reputation / 100) * 0.4  # 0.8 to 1.2

    expected_orders = our_clients_estimate * rep_factor

    # Each dish's probability = expected_orders / menu_size (uniform-ish)
    # but adjusted by prestige tier appeal
    probs = np.zeros(n)
    for i, recipe in enumerate(recipes):
        prestige = recipe.get("prestige", 50)
        prep_time = recipe.get("prep_time", 5.0)

        # Prestige tier appeal: mid-range dishes appeal to more archetypes
        if prestige <= 30:
            tier_appeal = 0.7   # budget-only clients
        elif prestige <= 60:
            tier_appeal = 1.0   # broad appeal
        elif prestige <= 80:
            tier_appeal = 0.8   # fewer but richer clients
        else:
            tier_appeal = 0.5   # premium-only clients

        # Speed bonus: faster dishes can be served more
        speed_bonus = max(0.5, min(1.2, 1.0 - (prep_time - 5) / 20))

        # Base probability for this dish
        dish_prob = (expected_orders / max(menu_size, 1)) * tier_appeal * speed_bonus

        # Cap at 1.0 — a dish can't be ordered more than once in our model
        # (actually it can, but for spending decisions 1 order is conservative)
        probs[i] = min(1.0, dish_prob)

    # Ensure we're conservative overall: scale so total expected revenue
    # roughly matches realistic expectations
    total_expected = sum(probs)
    if total_expected > expected_orders * 1.5:
        probs *= (expected_orders * 1.5) / total_expected

    return probs
