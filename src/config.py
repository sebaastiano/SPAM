"""
SPAM! — Configuration & Constants
==================================
All game constants, API keys, zone definitions, and statistical data.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ── Team ──
TEAM_ID = 17
TEAM_NAME = "SPAM!"
API_KEY = "dTpZhKpZ02-4ac2be8821b52df78bf06070"

# ── Server ──
BASE_URL = "https://hackapizza.datapizza.tech"
SSE_URL = f"{BASE_URL}/events/{TEAM_ID}"
MCP_URL = f"{BASE_URL}/mcp"

# ── Tracker sidecar ──
TRACKER_BASE_URL = "http://localhost:5555"

# ── LLM (Regolo.ai) ──
REGOLO_BASE_URL = "https://api.regolo.ai/v1"
REGOLO_API_KEY = os.getenv("REGOLO_API_KEY", "")
PRIMARY_MODEL = "gpt-oss-120b"
FAST_MODEL = "gpt-oss-20b"
VISION_MODEL = "qwen3-vl-32b"

# ── Headers ──
HEADERS = {
    "x-api-key": API_KEY,
    "Content-Type": "application/json",
}

# ── Strategic Zones ──
ZONES = [
    "DIVERSIFIED",
    "PREMIUM_MONOPOLIST",
    "BUDGET_OPPORTUNIST",
    "NICHE_SPECIALIST",
    "SPEED_CONTENDER",
    "MARKET_ARBITRAGEUR",
]

# ── Archetype price ceilings (estimated from analysis) ──
# These are the MAXIMUM a client archetype will tolerate.
# We should price WELL BELOW these to attract volume!
# Pricing far below ceiling → more clients → more total revenue.
ARCHETYPE_CEILINGS = {
    "Esploratore Galattico": 60,
    "Astrobarone": 500,
    "Saggi del Cosmo": 600,
    "Famiglie Orbitali": 150,
}

# ── ACTUAL target prices per tier (profit-aware mixed pricing) ──
# These are MINIMUM base prices per prestige tier.
# CRITICAL CONSTRAINT: price MUST exceed ingredient cost per serving.
# Typical dish needs 3-10 ingredient units at 15-18 each = 45-180 cost.
# Prices are further adjusted UP by cost-floor logic in compute_menu_price.
# LOW tiers: ROCK BOTTOM to attract max volume (Esploratori, Famiglie)
# HIGH tiers: price AGGRESSIVELY — Saggi (≤600) and Astrobaroni (≤500)
#   will pay handsomely. Wider spread = more archetypes served.
#   1000 credits for closing restaurant = we MUST beat that with serving.
PRICE_TIERS = {
    "ultra_bargain": (0,  20,  18),   # (prestige_min, prestige_max, base_price)
    "bargain":       (21, 35,  28),
    "budget":        (36, 50,  42),
    "mid_low":       (51, 60,  60),
    "mid":           (61, 70,  85),
    "mid_high":      (71, 80,  150),
    "premium":       (81, 90,  280),  # Astrobaroni territory (ceiling 500)
    "luxury":        (91, 100, 420),  # Saggi territory (ceiling 600)
}

# ── Known archetypes ──
KNOWN_ARCHETYPES = {
    "Esploratore Galattico",
    "Astrobarone",
    "Saggi del Cosmo",
    "Famiglie Orbitali",
}

# ── High-Δ ingredients (from statistical analysis, prestige boosters) ──
HIGH_DELTA_INGREDIENTS = [
    ("Polvere di Crononite", 9.93),
    ("Shard di Prisma Stellare", 8.84),
    ("Lacrime di Andromeda", 8.28),
    ("Essenza di Tachioni", 6.04),
]

# ── Ingredients absent from ALL S-Tier recipes (avoid these for premium) ──
AVOID_PREMIUM_INGREDIENTS = {
    "Essenza di Speziaria",
    "Salsa Szechuan",
    "Cristalli di Nebulite",
    "Spore Quantiche",
    "Spezie Melange",
    "Burrobirra",
    "Slurm",
    "Sashimi di Magikarp",
    "Pickle Rick Croccante",
    "Chocobo Wings",
    "Latte+",
    "Ravioli al Vaporeon",
}

# ── Salsa Szechuan: statistically significant NEGATIVE impact (−9.14, p=0.015) ──
NEGATIVE_DELTA_INGREDIENTS = [
    ("Salsa Szechuan", -9.14),
    ("Cristalli di Nebulite", -7.29),
]

# ── Zone-specific price factors ──
# These multiply the base price. Must be >= 1.0 for premium zones
# to ensure we never sell below cost. Budget zones use slight discount
# but the cost-floor in compute_menu_price prevents selling at a loss.
ZONE_PRICE_FACTORS = {
    "DIVERSIFIED": 1.00,
    "PREMIUM_MONOPOLIST": 1.10,
    "BUDGET_OPPORTUNIST": 0.85,
    "NICHE_SPECIALIST": 1.00,
    "SPEED_CONTENDER": 0.90,
    "MARKET_ARBITRAGEUR": 0.80,
}

# ── Zone-specific system prompts ──
ZONE_SYSTEM_PROMPTS = {
    "DIVERSIFIED": (
        "You are managing a diversified galactic restaurant targeting ALL customer types.\n"
        "Target clients: ALL archetypes (Esploratori, Famiglie, Saggi, Astrobaroni).\n"
        "Price strategy: Mixed tiered pricing — cheap dishes for budget clients, "
        "moderate dishes for families, premium dishes for luxury clients.\n"
        "Recipe focus: Full prestige spectrum (15-100), prep time ≤ 12s.\n"
        "Menu size: LARGE (12-20 dishes) to maximize choice and customer attraction.\n"
        "Bidding priority: Diverse ingredients for broad menu coverage.\n"
        "Risk tolerance: Moderate — invest in variety, not luxury.\n"
        "PROFIT RULE: MINIMIZE bid spending. Only bid on ingredients you NEED for cookable "
        "recipes. Every credit saved on bids is pure profit. Target spending < 20% of balance.\n"
        "VECTOR INTELLIGENCE: Use competitor behavioral signatures to find demand gaps. "
        "If competitors have high bid_aggressiveness, avoid bidding wars — let them overpay. "
        "If a competitor has high specialization_depth, avoid their niche.\n"
        "Key principle: MAX PROFIT through MAX CHOICE with MIN COST."
    ),
    "PREMIUM_MONOPOLIST": (
        "You are managing a premium galactic restaurant.\n"
        "Target clients: Saggi del Cosmo, Astrobaroni.\n"
        "Price strategy: High prices (near archetype ceiling).\n"
        "Recipe focus: Prestige ≥ 85, prep time ≤ 6s preferred.\n"
        "Bidding priority: High-Δ ingredients (Polvere di Crononite, Shard di Prisma Stellare, "
        "Lacrime di Andromeda, Essenza di Tachioni).\n"
        "Risk tolerance: Accept negative immediate margin if prestige gain > 5.\n"
        "PROFIT RULE: Premium dishes have high margins. Bid only on premium ingredients "
        "where competitor bid_concentration is low — find gaps in the vector space.\n"
        "Key principle: Serve quality fast. High margin per dish beats volume."
    ),
    "BUDGET_OPPORTUNIST": (
        "You are managing a high-volume budget restaurant.\n"
        "Target clients: Esploratori Galattici, Famiglie Orbitali.\n"
        "Price strategy: Low prices, high throughput.\n"
        "Recipe focus: Prestige 23-60, prep time ≤ 5s, minimal ingredients.\n"
        "Bidding priority: Common ingredients at lowest possible price.\n"
        "Risk tolerance: Avoid all negative margins. Volume > prestige.\n"
        "PROFIT RULE: NEVER overbid. Budget dishes have thin margins — every credit of "
        "bid cost matters. Target bid prices < 15 credits per ingredient.\n"
        "Key principle: Serve many clients fast. Throughput times margin is profit."
    ),
    "NICHE_SPECIALIST": (
        "You are managing a niche specialist restaurant.\n"
        "Target clients: One specific archetype (determined at runtime).\n"
        "Price strategy: Archetype-optimal pricing.\n"
        "Recipe focus: Archetype-specific prestige range.\n"
        "PROFIT RULE: Use vector space intelligence to identify which archetype niche "
        "has the LEAST competitor coverage. Dominate that niche with minimal bid spending.\n"
        "Key principle: Own one niche completely at lowest cost."
    ),
    "SPEED_CONTENDER": (
        "You are managing a speed-focused restaurant.\n"
        "Target clients: All archetypes (speed wins).\n"
        "Price strategy: Moderate pricing.\n"
        "Recipe focus: Prestige 50-80, ALL recipes with prep time ≤ 5s.\n"
        "PROFIT RULE: Fast dishes require fewer ingredients. Keep bids minimal — "
        "your advantage is SPEED, not ingredient quality.\n"
        "Key principle: Serve the most clients in the serving window at lowest ingredient cost."
    ),
    "MARKET_ARBITRAGEUR": (
        "You are managing a trade-focused operation.\n"
        "Minimal menu (1-2 dishes).\n"
        "Focus: Exploit ingredient price spreads between buy/sell listings.\n"
        "PROFIT RULE: Only enter trades with positive expected value. Use competitor "
        "buy_sell_ratio and market_activity features to identify mispriced ingredients.\n"
        "Key principle: Profit from market inefficiencies with zero risk."
    ),
}

# ── Serving priority per archetype (lower = higher priority) ──
ARCHETYPE_PRIORITY = {
    "Astrobarone": 0,
    "Saggi del Cosmo": 1,
    "Famiglie Orbitali": 2,
    "Esploratore Galattico": 3,
}

# ── Zone target archetypes ──
ZONE_TARGET_ARCHETYPES = {
    "DIVERSIFIED": list(KNOWN_ARCHETYPES),  # ALL archetypes
    "PREMIUM_MONOPOLIST": ["Saggi del Cosmo", "Astrobarone"],
    "BUDGET_OPPORTUNIST": ["Esploratore Galattico", "Famiglie Orbitali"],
    "NICHE_SPECIALIST": [],  # determined at runtime
    "SPEED_CONTENDER": list(KNOWN_ARCHETYPES),
    "MARKET_ARBITRAGEUR": [],
}

# ── Zone prestige ranges ──
# WIDER ranges = more eligible recipes = bigger menus = more customers.
# Mixed prestige naturally creates mixed prices (the core strategy).
# CRITICAL: Include LOW-prestige dishes in EVERY zone to attract budget customers!
# DIVERSIFIED uses the FULL spectrum to attract every archetype.
ZONE_PRESTIGE_RANGE = {
    "DIVERSIFIED": (5, 100),
    "PREMIUM_MONOPOLIST": (20, 100),
    "BUDGET_OPPORTUNIST": (5, 80),
    "NICHE_SPECIALIST": (15, 100),
    "SPEED_CONTENDER": (10, 95),
    "MARKET_ARBITRAGEUR": (5, 100),
}

# ── Zone menu size constraints ──
# MORE ITEMS = MORE CHOICE = MORE CUSTOMERS = MORE REVENUE.
# This is the single most important lever for winning.
# Bigger menus attract more archetypes and serve more clients.
# DIVERSIFIED has the largest menu to cover all price/prestige points.
ZONE_MENU_SIZE = {
    "DIVERSIFIED": (16, 30),
    "PREMIUM_MONOPOLIST": (14, 26),
    "BUDGET_OPPORTUNIST": (16, 28),
    "NICHE_SPECIALIST": (12, 24),
    "SPEED_CONTENDER": (14, 28),
    "MARKET_ARBITRAGEUR": (7, 14),
}

# ── Max prep time per zone (seconds) ──
# Relaxed to allow more recipes into the pool = bigger menus.
# DIVERSIFIED is generous on prep time to maximize recipe pool.
ZONE_MAX_PREP_TIME = {
    "DIVERSIFIED": 14.0,
    "PREMIUM_MONOPOLIST": 12.0,
    "BUDGET_OPPORTUNIST": 12.0,
    "NICHE_SPECIALIST": 16.0,
    "SPEED_CONTENDER": 8.0,
    "MARKET_ARBITRAGEUR": 16.0,
}

# ── Competitor cluster strategies ──
CLUSTER_STRATEGIES = {
    "STABLE_SPECIALIST": "Coexist — reinforce their niche",
    "REACTIVE_CHASER": "Generous Tit-for-Tat — feed slightly wrong signals",
    "AGGRESSIVE_HOARDER": "Targeted Spoiler — bid-deny their top 2 items",
    "DECLINING": "Ignore — offer cheap alliance",
    "DORMANT": "Monitor only — no action until they wake",
    "UNCLASSIFIED": "Probe — 1 cooperative message, classify reply",
}

# ── Default starting balance ──
DEFAULT_STARTING_BALANCE = 10000

# ── Bidding strategy constants ──
# SERVINGS_BUFFER: bid enough ingredients for N servings per menu item.
# With buffer=1, if a dish needs 3x IngA, we bid for 3x IngA.
# We used to keep buffer=1 because buffer=2 was DOUBLING costs —
# but now bid prices are lower (12 default vs 15 before) and we
# finish ingredients way before the serving window ends, losing
# customers. Better to have surplus ingredients than to turn away
# paying clients. 2 servings per dish = can serve repeat orders.
SERVINGS_BUFFER = 2

# SPENDING_FRACTION: fraction of balance allocated to bidding.
# PROFIT = REVENUE - COSTS. Keep spending relative to expected revenue.
# 0.30 = moderate: spend up to 30%. We earn it back with dish margins
# now that per-ingredient bids are low (12-32 range).
DEFAULT_SPENDING_FRACTION = 0.30

# AGGRESSIVE_SPENDING_FRACTION: used when we detect heavy competition.
# With lower bid prices per unit, we can afford to spend 40% and still
# maintain healthy margins on every dish sale.
AGGRESSIVE_SPENDING_FRACTION = 0.40

# MINIMUM_PROFIT_MARGIN: the minimum ratio of (price / ingredient_cost).
# A dish must sell for at least this multiple of its ingredient cost.
# 1.5 means 50% gross margin (spend 100 on ingredients → sell for ≥150).
MINIMUM_PROFIT_MARGIN = 1.5

# ── Base bid prices (fallback when no competitor data) ──
# These represent the MINIMUM we expect to need to win a bid.
# Without a speaking phase, competitor intel is often stale/empty,
# so these fallbacks must be high enough to actually win auctions.
# Bidding too low = winning nothing = zero revenue from serving.
BASE_BID_PRICES = {
    "Polvere di Crononite": 52,
    "Shard di Prisma Stellare": 50,
    "Lacrime di Andromeda": 46,
    "Essenza di Tachioni": 42,
    "Frutti del Diavolo": 32,
    "Gnocchi del Crepuscolo": 30,
    "Polvere di Stelle": 30,
}
DEFAULT_BASE_BID = 25
