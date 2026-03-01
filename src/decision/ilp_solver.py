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
    spending_fraction: float = None,
) -> ZoneDecision:
    """
    Solve the zone-specific MILP for menu selection and bid allocation.

    Decision variables  (stacked vector  v = [y_0 … y_{J-1}, x_0 … x_{I-1}]):
      y_j ∈ {0,1}  — include recipe j on menu
      x_i ∈ Z≥0    — quantity of ingredient i to bid on

    Objective (minimised by scipy):
      min  -Σ_j(revenue_j · y_j) + Σ_i(bid_price_i · x_i)

    Subject to:
      menu_min ≤ Σ y_j ≤ menu_max                                      (C1)
      SERVINGS_BUFFER * Σ_j(need_{ij} · y_j) - x_i ≤ inventory_i  ∀ i  (C2)
      Σ_i(bid_price_i · x_i) ≤ budget                                  (C3)
    """
    decision = ZoneDecision()
    decision.zone = zone

    # ── Spending fraction: auto-select based on competition ──
    if spending_fraction is None:
        active_competitors = sum(
            1 for b in competitor_briefings.values()
            if b.get("is_connected", False)
        )
        if active_competitors >= 4:
            spending_fraction = AGGRESSIVE_SPENDING_FRACTION
        else:
            spending_fraction = DEFAULT_SPENDING_FRACTION

    # ── Zone constraints ──
    prestige_min, prestige_max = ZONE_PRESTIGE_RANGE.get(zone, (0, 100))
    menu_min, menu_max = ZONE_MENU_SIZE.get(zone, (3, 10))
    max_prep_time = ZONE_MAX_PREP_TIME.get(zone, 10.0)

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

    # ── Per-recipe revenue (price estimate) ──
    revenues = np.array(
        [compute_menu_price(r, zone, reputation, competitor_briefings) for r in eligible_recipes],
        dtype=float,
    )

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
    for j in range(J):
        if y_sol[j]:
            recipe = eligible_recipes[j]
            price = int(revenues[j])
            decision.menu.append({"name": recipe["name"], "price": price})

    for i in range(I):
        if x_sol[i] > 0:
            decision.bids.append({
                "ingredient": all_ingredients[i],
                "bid": int(bid_prices[i]),
                "quantity": int(x_sol[i]),
            })

    decision.total_bid_cost = float(bid_prices @ x_sol)
    decision.expected_revenue = float(revenues @ y_sol)  # no discount — full revenue potential

    logger.info(
        f"MILP [{zone}]: {len(decision.menu)} menu items, "
        f"{len(decision.bids)} bids (total_qty={sum(int(x) for x in x_sol)}), "
        f"cost={decision.total_bid_cost:.0f}/{budget:.0f} budget, "
        f"expected_rev={decision.expected_revenue:.0f}"
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
    """Score and rank recipes for a zone — favor volume and diversity."""
    scored = []

    high_delta_set = {ing for ing, _ in HIGH_DELTA_INGREDIENTS}

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

        total_score = (
            prestige_score * 0.20
            + speed_score * 0.25
            + inventory_score * 0.30   # heavily favor what we already have
            + simplicity_bonus
            + delta_bonus * 0.05
            - competition_penalty * 0.05
        )

        scored.append({"recipe": recipe, "score": total_score})

    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored


def compute_menu_price(
    recipe: dict, zone: str, reputation: float,
    competitor_briefings: dict[int, dict] | None = None,
) -> float:
    """
    Compute menu price for a dish using MIXED TIERED PRICING.

    VOLUME-FIRST STRATEGY:
    - Prestige determines the tier → each tier has a different base price
    - Low-prestige dishes are CHEAP → attract Esploratori, Famiglie (volume!)
    - Mid-prestige dishes are MODERATE → broad appeal, solid margins
    - High-prestige dishes are HIGHER → extract value from Astrobaroni, Saggi
    - The menu naturally offers something for EVERY archetype

    Key insight: 10 customers × 50 credits = 500 revenue
                 0 customers × 500 credits = 0 revenue
    Volume wins. Always.
    """
    prestige = recipe.get("prestige", 50)

    # TIERED BASE PRICES — determined by prestige level
    # Each tier targets a different customer segment
    base_price = 60  # fallback
    for tier_name, (p_min, p_max, tier_price) in PRICE_TIERS.items():
        if p_min <= prestige <= p_max:
            base_price = tier_price
            break

    # Gentle prestige scaling WITHIN each tier (±20% max)
    prestige_mult = 1.0 + (prestige - 50) / 250

    # Reputation bonus — subtle, we're building trust not gouging
    # At rep=50: mult=1.0, at rep=100: mult=1.17
    rep_mult = 1.0 + (reputation - 50) / 300

    # Zone factor — still differentiate zones, but less aggressively
    zone_factor = ZONE_PRICE_FACTORS.get(zone, 0.65)

    price = int(base_price * prestige_mult * rep_mult * zone_factor)

    # COMPETITION ADJUSTMENT: undercut to win customers
    if competitor_briefings:
        active_competitors = sum(
            1 for b in competitor_briefings.values()
            if b.get("is_connected", False)
        )
        if active_competitors == 0:
            # Monopoly — modest increase (don't get greedy, volume still matters)
            price = int(price * 1.15)
        else:
            # Competition exists — match or undercut depending on tier
            competitor_prices = [
                b.get("menu_price_avg", 0)
                for b in competitor_briefings.values()
                if b.get("menu_price_avg", 0) > 0
            ]
            if competitor_prices:
                avg_comp_price = sum(competitor_prices) / len(competitor_prices)
                if prestige <= 50:
                    # Bargain/budget tier: aggressively undercut
                    price = min(price, int(avg_comp_price * 0.75))
                elif prestige <= 70:
                    # Mid tier: slight undercut to stay competitive
                    price = min(price, int(avg_comp_price * 0.90))
                # Premium tier: keep our price (rich clients don't mind)

    # Hard floor and ceiling
    # Floor: 12 credits minimum (never give food away)
    # Ceiling: 250 credits max (nobody likes being gouged)
    price = max(12, min(price, 250))

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
