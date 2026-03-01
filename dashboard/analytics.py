"""
SPAM! Dashboard — Analytics Engine
====================================
Reads raw data from tracker (localhost:5555) and computes strategic insights.
NO direct game server calls — all data comes from the tracker sidecar.
"""

import logging
from collections import defaultdict
from datetime import datetime

logger = logging.getLogger("spam.dashboard.analytics")

TEAM_ID = 17


# ── Bid Analysis ──────────────────────────────────────────────

def analyse_bids(bid_history: list[dict], restaurant_names: dict[int, str]) -> dict:
    """
    Analyse bid history to extract:
    - Per-team spending totals, averages, and ingredient preferences
    - Per-ingredient competition (who bids on what, avg price)
    - Our own bid efficiency (won vs lost)
    """
    if not bid_history:
        return {"teams": {}, "ingredients": {}, "summary": {}}

    # Per-team aggregation
    team_data = defaultdict(lambda: {
        "total_spent": 0,
        "bid_count": 0,
        "ingredients": defaultdict(lambda: {"total_bid": 0, "total_qty": 0, "count": 0}),
        "avg_bid": 0,
        "max_bid": 0,
    })

    # Per-ingredient aggregation
    ingredient_data = defaultdict(lambda: {
        "total_bids": 0,
        "total_qty": 0,
        "bid_count": 0,
        "avg_price": 0,
        "max_price": 0,
        "min_price": float("inf"),
        "bidders": defaultdict(lambda: {"total_bid": 0, "total_qty": 0}),
    })

    for bid in bid_history:
        rid = bid.get("restaurantId") or bid.get("restaurant_id")
        ingredient = (
            bid.get("ingredient", {}).get("name")
            if isinstance(bid.get("ingredient"), dict)
            else bid.get("ingredient") or bid.get("ingredient_name")
        )
        amount = bid.get("priceForEach") or bid.get("bid") or bid.get("amount") or bid.get("price") or 0
        qty = bid.get("quantity") or 1

        if not rid or not ingredient:
            continue

        rid = int(rid)
        total = amount * qty

        # Team stats
        td = team_data[rid]
        td["total_spent"] += total
        td["bid_count"] += 1
        td["max_bid"] = max(td["max_bid"], amount)
        td["ingredients"][ingredient]["total_bid"] += total
        td["ingredients"][ingredient]["total_qty"] += qty
        td["ingredients"][ingredient]["count"] += 1

        # Ingredient stats
        ig = ingredient_data[ingredient]
        ig["total_bids"] += total
        ig["total_qty"] += qty
        ig["bid_count"] += 1
        ig["max_price"] = max(ig["max_price"], amount)
        ig["min_price"] = min(ig["min_price"], amount)
        ig["bidders"][rid]["total_bid"] += total
        ig["bidders"][rid]["total_qty"] += qty

    # Compute averages
    for rid, td in team_data.items():
        td["avg_bid"] = round(td["total_spent"] / max(td["bid_count"], 1), 1)
        td["name"] = restaurant_names.get(rid, f"Team {rid}")
        # Convert ingredient defaultdict to regular dict for JSON
        td["ingredients"] = {
            k: dict(v) for k, v in td["ingredients"].items()
        }

    for ing, ig in ingredient_data.items():
        ig["avg_price"] = round(ig["total_bids"] / max(ig["total_qty"], 1), 1)
        if ig["min_price"] == float("inf"):
            ig["min_price"] = 0
        # Convert bidders
        ig["bidders"] = {
            str(k): dict(v) for k, v in ig["bidders"].items()
        }

    # Summary
    total_market_spend = sum(td["total_spent"] for td in team_data.values())
    our_spend = team_data.get(TEAM_ID, {}).get("total_spent", 0)

    return {
        "teams": {str(k): dict(v) for k, v in team_data.items()},
        "ingredients": {k: dict(v) for k, v in ingredient_data.items()},
        "summary": {
            "total_market_spend": total_market_spend,
            "our_spend": our_spend,
            "our_share_pct": round(our_spend / max(total_market_spend, 1) * 100, 1),
            "unique_ingredients_bid": len(ingredient_data),
            "active_bidders": len(team_data),
            "most_contested": sorted(
                ingredient_data.items(),
                key=lambda x: x[1]["bid_count"],
                reverse=True,
            )[:10],
        },
    }


# ── Market Analysis ──────────────────────────────────────────

def analyse_market(market_entries: list[dict], restaurant_names: dict[int, str]) -> dict:
    """
    Analyse market entries to find:
    - Active buy/sell listings per ingredient
    - Completed trades and volumes
    - Arbitrage opportunities (buy price < sell price for same ingredient)
    - Who is selling/buying what (competitor strategy signals)
    """
    if not market_entries:
        return {"sells": [], "buys": [], "trades": [], "arbitrage": [], "by_ingredient": {}}

    sells = []
    buys = []
    trades = []
    by_ingredient = defaultdict(lambda: {"sells": [], "buys": [], "trades": []})

    for entry in market_entries:
        side = entry.get("side", "").upper()
        status = entry.get("status", "open")
        ingredient = entry.get("ingredient_name", "?")

        enriched = dict(entry)
        sid = entry.get("seller_id")
        bid = entry.get("buyer_id")
        enriched["seller_name"] = restaurant_names.get(sid, f"Team {sid}") if sid else "?"
        enriched["buyer_name"] = restaurant_names.get(bid, f"Team {bid}") if bid else "?"

        if status == "closed":
            trades.append(enriched)
            by_ingredient[ingredient]["trades"].append(enriched)
        elif side == "SELL":
            sells.append(enriched)
            by_ingredient[ingredient]["sells"].append(enriched)
        elif side == "BUY":
            buys.append(enriched)
            by_ingredient[ingredient]["buys"].append(enriched)

    # Find arbitrage: ingredients where someone is selling below what others want to buy
    arbitrage = []
    for ing, data in by_ingredient.items():
        open_sells = [s for s in data["sells"] if s.get("status") in (None, "open")]
        open_buys = [b for b in data["buys"] if b.get("status") in (None, "open")]
        for s in open_sells:
            for b in open_buys:
                sell_unit = s.get("unit_price", 0) or 0
                buy_unit = b.get("unit_price", 0) or 0
                if sell_unit > 0 and buy_unit > sell_unit:
                    arbitrage.append({
                        "ingredient": ing,
                        "buy_price": sell_unit,
                        "sell_price": buy_unit,
                        "spread": round(buy_unit - sell_unit, 2),
                        "seller": s.get("seller_name", "?"),
                        "buyer": b.get("buyer_name", "?"),
                        "seller_id": s.get("seller_id"),
                        "buyer_entry_id": b.get("id"),
                        "sell_entry_id": s.get("id"),
                    })

    arbitrage.sort(key=lambda x: x["spread"], reverse=True)

    return {
        "sells": sells,
        "buys": buys,
        "trades": trades,
        "arbitrage": arbitrage,
        "by_ingredient": {k: dict(v) for k, v in by_ingredient.items()},
        "summary": {
            "open_sells": len([s for s in sells if s.get("status") in (None, "open")]),
            "open_buys": len([b for b in buys if b.get("status") in (None, "open")]),
            "completed_trades": len(trades),
            "arbitrage_opportunities": len(arbitrage),
            "total_trade_volume": sum(t.get("total_price", 0) or 0 for t in trades),
        },
    }


# ── Competitor Analysis ──────────────────────────────────────

def analyse_competitors(
    restaurants: dict,
    bid_analysis: dict,
    market_analysis: dict,
) -> dict:
    """
    Build competitor profiles from restaurant data + bid/market intel:
    - Balance trajectory (spending vs earning)
    - Menu strategy (price range, item count)
    - Ingredient focus (what they bid on most)
    - Market behaviour (net buyer vs seller)
    - Threat level (high balance + aggressive bidding = dangerous)
    """
    profiles = {}

    for rid_str, rdata in restaurants.items():
        rid = int(rid_str) if isinstance(rid_str, str) else rid_str
        if rid == TEAM_ID:
            continue  # separate analysis for ourselves

        raw = rdata if not isinstance(rdata, dict) or "_flat" not in rdata else rdata
        flat = rdata.get("_flat", rdata) if isinstance(rdata, dict) else rdata

        name = rdata.get("name", f"Team {rid}")
        balance = flat.get("balance") or rdata.get("balance", 0)
        reputation = flat.get("reputation") or rdata.get("reputation", 0)
        is_open = flat.get("isOpen") or rdata.get("isOpen", False)

        # Menu
        menu_data = flat.get("menu", {})
        if isinstance(menu_data, dict):
            menu_items = list(menu_data.items())
            menu_prices = [v for v in menu_data.values() if isinstance(v, (int, float)) and v > 0]
        elif isinstance(menu_data, list):
            menu_items = menu_data
            menu_prices = [
                it.get("price", 0) for it in menu_data
                if isinstance(it, dict) and it.get("price")
            ]
        else:
            menu_items = []
            menu_prices = []

        avg_price = round(sum(menu_prices) / len(menu_prices), 1) if menu_prices else 0
        max_price = max(menu_prices) if menu_prices else 0
        min_price = min(menu_prices) if menu_prices else 0

        # Bid intel
        team_bids = bid_analysis.get("teams", {}).get(str(rid), {})
        total_bid_spend = team_bids.get("total_spent", 0)
        bid_count = team_bids.get("bid_count", 0)
        top_ingredients = sorted(
            team_bids.get("ingredients", {}).items(),
            key=lambda x: x[1].get("total_bid", 0),
            reverse=True,
        )[:5]

        # Market behaviour
        sells = [e for e in market_analysis.get("sells", [])
                 if e.get("seller_id") == rid]
        buys = [e for e in market_analysis.get("buys", [])
                if e.get("seller_id") == rid]  # seller_id = creator

        # Threat assessment
        threat_score = 0
        if balance and balance > 5000:
            threat_score += 2
        if is_open:
            threat_score += 1
        if len(menu_prices) >= 3:
            threat_score += 1
        if total_bid_spend > 500:
            threat_score += 1
        if avg_price > 200:
            threat_score += 1  # premium competitor

        threat_level = "LOW" if threat_score <= 2 else "MEDIUM" if threat_score <= 4 else "HIGH"

        profiles[rid] = {
            "name": name,
            "balance": balance,
            "reputation": reputation,
            "is_open": is_open,
            "menu_count": len(menu_items),
            "avg_price": avg_price,
            "max_price": max_price,
            "min_price": min_price,
            "menu_items": menu_items,
            "total_bid_spend": total_bid_spend,
            "bid_count": bid_count,
            "top_ingredients": [
                {"name": name, "spend": data.get("total_bid", 0), "qty": data.get("total_qty", 0)}
                for name, data in top_ingredients
            ],
            "market_sells": len(sells),
            "market_buys": len(buys),
            "threat_level": threat_level,
            "threat_score": threat_score,
        }

    return profiles


# ── Our Performance ──────────────────────────────────────────

def analyse_our_performance(
    our_restaurant: dict,
    bid_analysis: dict,
    market_analysis: dict,
    meals: list[dict],
) -> dict:
    """
    Analyse our own performance:
    - Revenue from served meals vs spending on ingredients
    - Profit margin per dish
    - Ingredient utilisation
    - Service success rate
    """
    flat = our_restaurant.get("_flat", our_restaurant)
    balance = flat.get("balance") or our_restaurant.get("balance", 0)
    reputation = flat.get("reputation") or our_restaurant.get("reputation", 0)
    inventory = flat.get("inventory", {})
    if not isinstance(inventory, dict):
        inventory = {}

    menu_data = flat.get("menu", {})
    if isinstance(menu_data, dict):
        menu_prices = menu_data
    else:
        menu_prices = {}

    # Our bid spending
    our_bids = bid_analysis.get("teams", {}).get(str(TEAM_ID), {})
    total_bid_spend = our_bids.get("total_spent", 0)

    # Meals analysis
    total_meals = len(meals)
    served_meals = len([m for m in meals if m.get("executed")])
    unserved = total_meals - served_meals

    # Revenue estimate from menu prices × served meals
    estimated_revenue = 0
    for meal in meals:
        if meal.get("executed"):
            dish = meal.get("dish") or meal.get("dish_name", "")
            price = menu_prices.get(dish, 0)
            if isinstance(price, (int, float)):
                estimated_revenue += price

    # Profit = revenue - bid costs (simplified)
    estimated_profit = estimated_revenue - total_bid_spend

    # Inventory value (what we have that could be sold)
    inventory_total = sum(inventory.values()) if inventory else 0

    return {
        "balance": balance,
        "reputation": reputation,
        "inventory_types": len(inventory),
        "inventory_total": inventory_total,
        "inventory_detail": inventory,
        "menu_items": len(menu_prices),
        "menu_prices": menu_prices,
        "total_bid_spend": total_bid_spend,
        "total_meals": total_meals,
        "served_meals": served_meals,
        "unserved_meals": unserved,
        "service_rate": round(served_meals / max(total_meals, 1) * 100, 1),
        "estimated_revenue": estimated_revenue,
        "estimated_profit": estimated_profit,
    }
