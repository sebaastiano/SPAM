"""
Configuration constants for SPAM! agent.

All environment-specific and game-specific constants live here.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ── Team ──────────────────────────────────────────────────────────
TEAM_ID = 17
TEAM_NAME = "SPAM!"

# ── Server ────────────────────────────────────────────────────────
BASE_URL = "https://hackapizza.datapizza.tech"
SSE_URL = f"{BASE_URL}/events/{TEAM_ID}"
MCP_URL = f"{BASE_URL}/mcp"
TRACKER_BASE_URL = "http://localhost:5555"

# ── Auth ──────────────────────────────────────────────────────────
TEAM_API_KEY = os.getenv("TEAM_API_KEY", "dTpZhKpZ02-4ac2be8821b52df78bf06070")

HEADERS = {
    "x-api-key": TEAM_API_KEY,
    "Content-Type": "application/json",
}

SSE_HEADERS = {
    "x-api-key": TEAM_API_KEY,
    "Accept": "text/event-stream",
}

# ── LLM (Regolo.ai) ──────────────────────────────────────────────
REGOLO_BASE_URL = "https://api.regolo.ai/v1"
REGOLO_API_KEY = os.getenv("REGOLO_API_KEY", "")
PRIMARY_MODEL = "gpt-oss-120b"    # reasoning
FAST_MODEL = "gpt-oss-20b"        # fast/parsing
VISION_MODEL = "qwen3-vl-32b"     # vision

# ── Strategic Zones ───────────────────────────────────────────────
ZONES = [
    "PREMIUM_MONOPOLIST",
    "BUDGET_OPPORTUNIST",
    "NICHE_SPECIALIST",
    "SPEED_CONTENDER",
    "MARKET_ARBITRAGEUR",
]

DEFAULT_ZONE = "SPEED_CONTENDER"

# ── Archetype price ceilings (estimated from game data) ──────────
ARCHETYPE_CEILINGS = {
    "Esploratore Galattico": 50,
    "Astrobarone": 200,
    "Saggi del Cosmo": 250,
    "Famiglie Orbitali": 120,
}

# ── Known archetypes ─────────────────────────────────────────────
KNOWN_ARCHETYPES = {
    "Esploratore Galattico",
    "Astrobarone",
    "Saggi del Cosmo",
    "Famiglie Orbitali",
}

# ── High-Δ ingredients (from statistical analysis) ───────────────
HIGH_DELTA_INGREDIENTS = {
    "Polvere di Crononite": 9.93,
    "Shard di Prisma Stellare": 8.84,
    "Lacrime di Andromeda": 8.28,
    "Essenza di Tachioni": 6.04,
}

# ── Ingredients absent from S-tier — avoid for premium zone ──────
NEGATIVE_PRESTIGE_INGREDIENTS = {
    "Salsa Szechuan",       # -9.14 Δ, statistically significant
    "Cristalli di Nebulite", # -7.29 Δ
    "Essenza di Speziaria",  # -4.12 Δ
}

# ── S-tier enriched ingredients (enrichment ratio > 2×) ──────────
S_TIER_ENRICHED = {
    "Lacrime di Andromeda": 3.24,
    "Polvere di Stelle": 3.24,
    "Frammenti di Supernova": 2.42,
    "Essenza di Vuoto": 2.08,
}

# ── Zone-specific pricing factors ────────────────────────────────
ZONE_PRICE_FACTORS = {
    "PREMIUM_MONOPOLIST": 0.95,
    "BUDGET_OPPORTUNIST": 0.50,
    "NICHE_SPECIALIST": 0.80,
    "SPEED_CONTENDER": 0.70,
    "MARKET_ARBITRAGEUR": 0.60,
}

# ── Zone-specific system prompts ─────────────────────────────────
ZONE_SYSTEM_PROMPTS = {
    "PREMIUM_MONOPOLIST": (
        "You manage a premium galactic restaurant.\n"
        "Target clients: Saggi del Cosmo, Astrobaroni.\n"
        "Price strategy: High prices (near archetype ceiling).\n"
        "Recipe focus: Prestige >= 85, prep time <= 6s preferred.\n"
        "Bidding priority: High-Δ ingredients (Polvere di Crononite, "
        "Shard di Prisma Stellare, Lacrime di Andromeda, Essenza di Tachioni).\n"
        "Risk tolerance: Accept negative immediate margin if prestige gain > 5.\n"
        "Key principle: Serve quality fast. Never miss a client."
    ),
    "BUDGET_OPPORTUNIST": (
        "You manage a high-volume budget restaurant.\n"
        "Target clients: Esploratori Galattici, Famiglie Orbitali.\n"
        "Price strategy: Low prices, high throughput.\n"
        "Recipe focus: Prestige 23-60, prep time <= 5s, minimal ingredients.\n"
        "Bidding priority: Common ingredients at lowest possible price.\n"
        "Risk tolerance: Avoid all negative margins. Volume > prestige.\n"
        "Key principle: Serve many clients fast. Throughput is revenue."
    ),
    "NICHE_SPECIALIST": (
        "You manage a niche specialist restaurant.\n"
        "Target clients: Single archetype focus (most underserved).\n"
        "Price strategy: Archetype-optimal.\n"
        "Recipe focus: Archetype-specific prestige range, 4-6 dishes.\n"
        "Key principle: Dominate one client archetype completely."
    ),
    "SPEED_CONTENDER": (
        "You manage a speed-focused restaurant.\n"
        "Target clients: All archetypes, speed wins.\n"
        "Price strategy: Moderate.\n"
        "Recipe focus: Prestige 50-80, prep time <= 5s, fast recipes.\n"
        "Key principle: Maximize throughput within the serving window."
    ),
    "MARKET_ARBITRAGEUR": (
        "You manage a trade-focused restaurant.\n"
        "Target clients: Minimal serving, focus on ingredient trading.\n"
        "Price strategy: N/A.\n"
        "Key principle: Exploit ingredient price spreads."
    ),
}

# ── Archetype serving priority (lower = higher priority) ─────────
ARCHETYPE_PRIORITY = {
    "Astrobarone": 0,
    "Saggi del Cosmo": 1,
    "Famiglie Orbitali": 2,
    "Esploratore Galattico": 3,
}

# ── Polling / timing ─────────────────────────────────────────────
TRACKER_POLL_TIMEOUT = 5.0  # seconds
MEALS_POLL_INTERVAL = 0.3   # seconds between /meals polls during serving
