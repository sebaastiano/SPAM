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
    "PREMIUM_MONOPOLIST",
    "BUDGET_OPPORTUNIST",
    "NICHE_SPECIALIST",
    "SPEED_CONTENDER",
    "MARKET_ARBITRAGEUR",
]

# ── Archetype price ceilings (estimated from analysis) ──
# Astrobarone: "guarda poco al prezzo" → price very high!
# Saggi del Cosmo: "badano poco al prezzo" → price very high!
# These are NOT spending limits — they're our target prices.
ARCHETYPE_CEILINGS = {
    "Esploratore Galattico": 60,
    "Astrobarone": 500,
    "Saggi del Cosmo": 600,
    "Famiglie Orbitali": 150,
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
# PREMIUM_MONOPOLIST: NO discount — rich clients pay full price!
# BUDGET: slight discount to attract volume (still profitable).
ZONE_PRICE_FACTORS = {
    "PREMIUM_MONOPOLIST": 1.0,
    "BUDGET_OPPORTUNIST": 0.60,
    "NICHE_SPECIALIST": 0.85,
    "SPEED_CONTENDER": 0.75,
    "MARKET_ARBITRAGEUR": 0.65,
}

# ── Zone-specific system prompts ──
ZONE_SYSTEM_PROMPTS = {
    "PREMIUM_MONOPOLIST": (
        "You are managing a premium galactic restaurant.\n"
        "Target clients: Saggi del Cosmo, Astrobaroni.\n"
        "Price strategy: High prices (near archetype ceiling).\n"
        "Recipe focus: Prestige ≥ 85, prep time ≤ 6s preferred.\n"
        "Bidding priority: High-Δ ingredients (Polvere di Crononite, Shard di Prisma Stellare, "
        "Lacrime di Andromeda, Essenza di Tachioni).\n"
        "Risk tolerance: Accept negative immediate margin if prestige gain > 5.\n"
        "Key principle: Serve quality fast. Never miss a client."
    ),
    "BUDGET_OPPORTUNIST": (
        "You are managing a high-volume budget restaurant.\n"
        "Target clients: Esploratori Galattici, Famiglie Orbitali.\n"
        "Price strategy: Low prices, high throughput.\n"
        "Recipe focus: Prestige 23-60, prep time ≤ 5s, minimal ingredients.\n"
        "Bidding priority: Common ingredients at lowest possible price.\n"
        "Risk tolerance: Avoid all negative margins. Volume > prestige.\n"
        "Key principle: Serve many clients fast. Throughput is revenue."
    ),
    "NICHE_SPECIALIST": (
        "You are managing a niche specialist restaurant.\n"
        "Target clients: One specific archetype (determined at runtime).\n"
        "Price strategy: Archetype-optimal pricing.\n"
        "Recipe focus: Archetype-specific prestige range.\n"
        "Key principle: Own one niche completely."
    ),
    "SPEED_CONTENDER": (
        "You are managing a speed-focused restaurant.\n"
        "Target clients: All archetypes (speed wins).\n"
        "Price strategy: Moderate pricing.\n"
        "Recipe focus: Prestige 50-80, ALL recipes with prep time ≤ 5s.\n"
        "Key principle: Serve the most clients in the serving window."
    ),
    "MARKET_ARBITRAGEUR": (
        "You are managing a trade-focused operation.\n"
        "Minimal menu (1-2 dishes).\n"
        "Focus: Exploit ingredient price spreads between buy/sell listings.\n"
        "Key principle: Profit from market inefficiencies."
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
    "PREMIUM_MONOPOLIST": ["Saggi del Cosmo", "Astrobarone"],
    "BUDGET_OPPORTUNIST": ["Esploratore Galattico", "Famiglie Orbitali"],
    "NICHE_SPECIALIST": [],  # determined at runtime
    "SPEED_CONTENDER": list(KNOWN_ARCHETYPES),
    "MARKET_ARBITRAGEUR": [],
}

# ── Zone prestige ranges ──
ZONE_PRESTIGE_RANGE = {
    "PREMIUM_MONOPOLIST": (85, 100),
    "BUDGET_OPPORTUNIST": (23, 60),
    "NICHE_SPECIALIST": (50, 100),
    "SPEED_CONTENDER": (50, 80),
    "MARKET_ARBITRAGEUR": (23, 100),
}

# ── Zone menu size constraints ──
# More items = more customers we can serve = more revenue.
# This is one of the most important levers for winning.
ZONE_MENU_SIZE = {
    "PREMIUM_MONOPOLIST": (5, 8),
    "BUDGET_OPPORTUNIST": (8, 12),
    "NICHE_SPECIALIST": (5, 8),
    "SPEED_CONTENDER": (6, 10),
    "MARKET_ARBITRAGEUR": (2, 4),
}

# ── Max prep time per zone (seconds) ──
ZONE_MAX_PREP_TIME = {
    "PREMIUM_MONOPOLIST": 7.0,
    "BUDGET_OPPORTUNIST": 6.0,
    "NICHE_SPECIALIST": 10.0,
    "SPEED_CONTENDER": 5.0,
    "MARKET_ARBITRAGEUR": 15.0,
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
# With buffer=2, if a dish needs 3x IngA, we bid for 6x IngA.
# This prevents running out when multiple customers order the same dish.
# Keep low to avoid overspending — profit = revenue - costs!
SERVINGS_BUFFER = 2

# SPENDING_FRACTION: fraction of balance allocated to bidding.
# PROFIT = REVENUE - COSTS. Keep spending LOW to maximise profit.
# We only need enough ingredients to cook the menu — not a war chest.
# 0.30 = conservative: spend ≤30% of balance, keep 70% as profit buffer.
DEFAULT_SPENDING_FRACTION = 0.30

# AGGRESSIVE_SPENDING_FRACTION: used when we detect heavy competition.
# Even under pressure, never spend more than 45% of balance.
AGGRESSIVE_SPENDING_FRACTION = 0.45

# ── Base bid prices (fallback when no competitor data) ──
# CONSERVATIVE: bid just enough to win, not more. Every credit saved
# on ingredients is pure profit when we sell the dish at high prices.
# The real money comes from SELLING dishes, not winning auctions.
BASE_BID_PRICES = {
    "Polvere di Crononite": 40,
    "Shard di Prisma Stellare": 38,
    "Lacrime di Andromeda": 35,
    "Essenza di Tachioni": 32,
    "Frutti del Diavolo": 25,
    "Gnocchi del Crepuscolo": 22,
    "Polvere di Stelle": 22,
}
DEFAULT_BASE_BID = 15
