# Hackapizza 2.0 — Comprehensive Implementation Strategy

## Team SPAM! (ID: 17)

**Architecture**: Zone-Based Subagent System with Behavioral Embedding, ILP Positioning & Client Profiling  
**Framework**: datapizza-ai v0.0.9 (mandatory) + proposed kernel extensions  
**Inference**: Regolo.ai — `gpt-oss-120b` (reasoning), `gpt-oss-20b` (fast/parsing), `qwen3-vl-32b` (vision)

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Alignment with vectorization_strategy.md](#2-alignment-with-vectorization_strategymd)
3. [System Architecture Overview](#3-system-architecture-overview)
4. [Strategic Zones & Subagent Router](#4-strategic-zones--subagent-router)
5. [Client Profiling System](#5-client-profiling-system)
6. [Competitive Intelligence Pipeline](#6-competitive-intelligence-pipeline)
7. [Decision Engine — ILP per Zone](#7-decision-engine--ilp-per-zone)
8. [Deception & Defense Layer](#8-deception--defense-layer)
9. [Execution Engine — Serving Pipeline](#9-execution-engine--serving-pipeline)
10. [Data Architecture & Memory Systems](#10-data-architecture--memory-systems)
11. [Datapizza-AI Kernel Extensions](#11-datapizza-ai-kernel-extensions)
12. [Phase-by-Phase Action Matrix](#12-phase-by-phase-action-matrix)
13. [Causal Decision Chain](#13-causal-decision-chain)
14. [Implementation Roadmap](#14-implementation-roadmap)
15. [Technical Stack Summary](#15-technical-stack-summary)

---

## 1. Executive Summary

### The Thesis

Every other team will build either an "agent swarm" (slow, expensive, hard to debug) or a "single optimizer" (locally optimal, globally blind). Both share the same fatal flaw: **they only model themselves**.

We model the **entire competitive geometry** — every restaurant as a moving point in behavioral space — and use that map to:

1. **Find the unoccupied strategic gap** nobody else is standing in
2. **Predict competitor trajectories** one turn before they move
3. **Route our own strategy** through specialized subagents that each own a zone of the competitive landscape
4. **Profile every client archetype** with observable signals to maximize service accuracy
5. **Selectively share true information** to manufacture useful conflicts between competitors

The key principle: **LLMs extract structure, math makes decisions, code executes instantly.**

### What Makes This Different (Honestly)

After rigorous self-assessment, here's what's genuinely non-replicable vs. what every team will discover:

| Advantage                         | Replicable?                              | Why It Matters                                                   |
| --------------------------------- | ---------------------------------------- | ---------------------------------------------------------------- |
| ILP-optimal bidding               | Easy to replicate                        | Table stakes — but we do it _per zone_                           |
| Data accumulation across turns    | Time-locked                              | Early data = compounding advantage; late starters can't catch up |
| Execution speed in serving        | Hard to match with agent-heavy designs   | We never block on LLM during serving                             |
| Reputation compounding            | Requires early correct execution         | Turn 1–2 prestige investment pays off by turn 5+                 |
| Behavioral embedding + trajectory | Requires infrastructure most won't build | Not the deception — the _prediction_ is the weapon               |
| Zone-based subagent routing       | Unique architecture                      | Dynamic strategy switching that monolithic agents can't do       |

**Priority ranking**: (1) Execution speed, (2) SSE reliability, (3) Cross-turn data accumulation, (4) ILP positioning per zone, (5) Reputation compounding, (6) Orchestration/deception.

---

## 2. Alignment with vectorization_strategy.md

The existing [vectorization_strategy.md](vectorization_strategy.md) establishes the foundational concepts. This document **extends and integrates** it. Here's what changes:

### What Stays (Validated)

| Concept                                        | Status       | Notes                                   |
| ---------------------------------------------- | ------------ | --------------------------------------- |
| Behavioral embedding (14-feature vector)       | ✅ Keep      | Core innovation, well-designed          |
| PCA/UMAP for strategy space visualization      | ✅ Keep      | Useful for pitch + internal positioning |
| Trajectory prediction (velocity + momentum)    | ✅ Keep      | One-turn advance notice                 |
| Competitor cluster classification (5 types)    | ✅ Keep      | Maps directly to relational strategies  |
| Silent orchestration / selective truth         | ✅ Keep      | But deprioritized to #6                 |
| Recipe desirability matrix                     | ✅ Keep      | Drives menu composition per zone        |
| Prestige flywheel                              | ✅ Keep      | Core revenue loop                       |
| Ingredient criticality score                   | ✅ Keep      | Bidding + monopolization                |
| Temporal arc (Observe → Orchestrate → Extract) | ✅ Keep      | Governs persona scheduling              |
| ILP solver (scipy.optimize.milp)               | ✅ Keep base | But now zone-specific, not monolithic   |

### What's New (This Document Adds)

| Concept                         | Gap in Original              | Added Here                                    |
| ------------------------------- | ---------------------------- | --------------------------------------------- |
| **Strategic Zones**             | Monolithic strategy          | 5 zones with specialized subagents            |
| **SubagentRouter**              | No routing logic             | ILP-driven zone selection per turn            |
| **Client Profiling**            | Clients treated as black box | 4-archetype profiling with observable signals |
| **Two-Level Memory**            | No client memory             | GlobalClientLibrary + ZoneClientLibrary       |
| **DeceptionBandit**             | Deception is ad-hoc          | Thompson Sampling over deception arms         |
| **PseudoGAN**                   | No message quality scoring   | LLM generator + scorer discriminator          |
| **GroundTruthFirewall**         | No defense architecture      | Only server-signed GET data enters decisions  |
| **ReactiveEventBus**            | Basic SSE template dispatch  | Typed event bus with priority routing         |
| **Kernel Extensions**           | Framework used as-is         | 6 proposed extensions to datapizza-ai         |
| **Structured Serving Pipeline** | Mentioned but not designed   | Full client→dish→prepare→serve pipeline       |

### What Changes

| Original Concept                          | Change                                          | Reason                                       |
| ----------------------------------------- | ----------------------------------------------- | -------------------------------------------- |
| Single ILP per turn                       | → ILP per active zone                           | Zone constraints differ (premium vs. budget) |
| "Manufactured conflict" as primary weapon | → Deprioritized to #6                           | Deception is easily replicated; speed wins   |
| Static relational strategy                | → Updated per turn via DeceptionBandit          | Arms track which strategies actually work    |
| No client model                           | → ClientProfileMemory with 6 observable signals | Revenue depends on serving the right dish    |

---

## 3. System Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        REACTIVE EVENT BUS                               │
│  SSE Stream ─────────────────────────────────────────────────────────── │
│  │ game_started │ game_phase_changed │ client_spawned │ new_message │   │
│  │ preparation_complete │ message (broadcast) │ heartbeat │ game_reset│  │
│  └──────────────────────────┬───────────────────────────────────────── │
│                             │                                          │
│                    ┌────────▼────────┐                                  │
│                    │  Phase Router   │──── phase state machine          │
│                    └────────┬────────┘                                  │
│                             │                                          │
│  ┌──────────────────────────┼───────────────────────────────────┐      │
│  │                          │                                   │      │
│  ▼                          ▼                                   ▼      │
│ SPEAKING/WAITING          CLOSED_BID                        SERVING    │
│ ┌───────────────┐   ┌──────────────────┐  ┌────────────────────────┐  │
│ │ Intelligence  │   │  Bid Calculator  │  │  Serving Pipeline      │  │
│ │ Pipeline      │   │  (ILP Solver)    │  │  (Zero-LLM hot path)  │  │
│ │               │   │                  │  │                        │  │
│ │ ┌───────────┐ │   │  Zone-specific   │  │  Order Parser          │  │
│ │ │Competitor │ │   │  bid allocation  │  │  ↓                     │  │
│ │ │Tracker    │ │   │                  │  │  Dish Matcher (lookup) │  │
│ │ ├───────────┤ │   └──────────────────┘  │  ↓                     │  │
│ │ │Trajectory │ │                          │  Intolerance Check     │  │
│ │ │Predictor  │ │                          │  ↓                     │  │
│ │ ├───────────┤ │                          │  prepare_dish (MCP)    │  │
│ │ │Zone       │ │                          │  ↓                     │  │
│ │ │Classifier │ │                          │  serve_dish (MCP)      │  │
│ │ └───────────┘ │                          └────────────────────────┘  │
│ │               │                                                      │
│ │ ┌───────────┐ │                                                      │
│ │ │Diplomacy  │ │                                                      │
│ │ │Agent      │ │     ┌────────────────────────────────┐              │
│ │ │(Deception │ │     │     SUBAGENT ROUTER             │              │
│ │ │ Bandit)   │ │     │                                │              │
│ │ └───────────┘ │     │  ILP Zone Classifier           │              │
│ └───────────────┘     │  ↓                             │              │
│                       │  Active Zone Selection         │              │
│                       │  ↓                             │              │
│                       │  Subagent Dispatch             │              │
│                       │  (menu, pricing, bid targets)  │              │
│                       └────────────────────────────────┘              │
│                                                                        │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    MEMORY LAYER                                  │   │
│  │                                                                 │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌───────────────────────┐│   │
│  │  │ GameState    │  │ Competitor   │  │ Client Profile        ││   │
│  │  │ Memory       │  │ Memory       │  │ Memory                ││   │
│  │  │ (turns,      │  │ (embeddings, │  │ (Global + Zone libs)  ││   │
│  │  │  phases,     │  │  trajectories│  │                       ││   │
│  │  │  inventory)  │  │  , clusters) │  │                       ││   │
│  │  └──────────────┘  └──────────────┘  └───────────────────────┘│   │
│  │                                                                 │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌───────────────────────┐│   │
│  │  │ Event Log    │  │ Message Log  │  │ GroundTruth           ││   │
│  │  │ (JSONL       │  │ (sent +      │  │ Firewall              ││   │
│  │  │  append-only)│  │  received)   │  │ (GET-only decisions)  ││   │
│  │  └──────────────┘  └──────────────┘  └───────────────────────┘│   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```

### Key Design Principles

1. **LLMs are sensors, not actuators** — LLMs parse unstructured text (orders, messages). Math makes decisions. Code executes.
2. **No LLM in the serving hot path** — Order→dish mapping is pre-computed lookup. LLM only for genuinely ambiguous orders.
3. **Everything is event-sourced** — Every SSE event logged to JSONL. Full replay capability.
4. **Defense by architecture** — GroundTruthFirewall ensures strategic decisions use only server-signed GET data, never incoming messages.
5. **Zone-based modularity** — Each strategic zone has its own ILP constraints, client preferences, and menu composition.

---

## 4. Strategic Zones & Subagent Router

### Zone Definitions

Each zone represents a **distinct competitive position** in the behavioral embedding space. The SubagentRouter selects the active zone each turn based on ILP optimization.

| Zone                 | Target Archetype       | Price Strategy    | Prestige Target    | Menu Size                | When to Activate                                                         |
| -------------------- | ---------------------- | ----------------- | ------------------ | ------------------------ | ------------------------------------------------------------------------ |
| `PREMIUM_MONOPOLIST` | Saggi, Astrobaroni     | High ceiling      | ≥ 85               | Small (3–5 dishes)       | We hold critical high-Δ ingredients, competitors sparse in premium space |
| `BUDGET_OPPORTUNIST` | Esploratori, Famiglie  | Low-medium        | 23–60              | Large (6–10 dishes)      | Premium space is contested, budget gap exists, high volume available     |
| `NICHE_SPECIALIST`   | Single archetype focus | Archetype-optimal | Archetype-specific | Medium (4–6 dishes)      | One archetype significantly underserved by competitors                   |
| `SPEED_CONTENDER`    | All (speed wins)       | Moderate          | 50–80              | Medium, all fast recipes | Serving window is tight, throughput advantage matters most               |
| `MARKET_ARBITRAGEUR` | N/A (trade-focused)    | N/A               | N/A                | Minimal                  | Ingredient price spreads exist, competitor desperation detected          |

### SubagentRouter — ILP Zone Classification

Each turn (during `waiting` phase, after bids resolve), the router solves:

```python
# Zone selection as optimization problem
# Input: competitor positions, our inventory, client distribution, balance
# Output: which zone to activate this turn

def select_zone(game_state: GameState, competitor_map: CompetitorMap) -> Zone:
    """
    ILP that considers:
    1. Competitor density in each zone's target space (from embedding)
    2. Our ingredient inventory alignment with each zone's recipe pool
    3. Expected client distribution (from menu→archetype attraction model)
    4. Balance constraints (can we afford this zone's bidding strategy?)
    5. Reputation trajectory (are we positioned to attract the right clients?)
    """

    # Score each zone
    zone_scores = {}
    for zone in ZONES:
        competitor_penalty = count_competitors_in_zone(zone, competitor_map)
        inventory_fit = calculate_inventory_alignment(zone, game_state.inventory)
        revenue_potential = estimate_zone_revenue(zone, game_state)
        reputation_bonus = reputation_alignment(zone, game_state.reputation)

        zone_scores[zone] = (
            revenue_potential * 0.4 +
            inventory_fit * 0.3 -
            competitor_penalty * 0.2 +
            reputation_bonus * 0.1
        )

    return max(zone_scores, key=zone_scores.get)
```

### Subagent Implementation Pattern

Each zone maps to a datapizza-ai `Agent` with zone-specific configuration:

```python
from datapizza.agents import Agent
from datapizza.clients.openai_like import OpenAILikeClient
from datapizza.tools.mcp_client import MCPClient

# Each zone has its own agent with tailored system prompt
premium_agent = Agent(
    name="premium_monopolist",
    client=OpenAILikeClient(
        api_key=REGOLO_KEY,
        model="gpt-oss-120b",
        base_url="https://api.regolo.ai/v1",
        system_prompt=PREMIUM_SYSTEM_PROMPT,  # zone-specific instructions
    ),
    tools=mcp_tools + [zone_specific_tools],
    max_steps=5,
    terminate_on_text=True,
    planning_interval=0,  # no planning overhead
)

# Router dispatches to active zone's agent
class SubagentRouter:
    def __init__(self, zones: dict[str, Agent]):
        self.zones = zones
        self.active_zone: str = "SPEED_CONTENDER"  # default

    def route(self, game_state: GameState, competitor_map: CompetitorMap):
        self.active_zone = select_zone(game_state, competitor_map)
        return self.zones[self.active_zone]

    def get_active_agent(self) -> Agent:
        return self.zones[self.active_zone]
```

### Zone-Specific System Prompts

Each subagent receives a system prompt that defines:

- Target client archetype(s)
- Price ceiling/floor for menu items
- Recipe pool (filtered by prestige range)
- Bidding priorities (which ingredients matter for this zone)
- Risk tolerance (aggressive vs. conservative)

```python
PREMIUM_SYSTEM_PROMPT = """You are managing a premium galactic restaurant.
Target clients: Saggi del Cosmo, Astrobaroni.
Price strategy: High prices (near archetype ceiling).
Recipe focus: Prestige ≥ 85, prep time ≤ 6s preferred.
Bidding priority: High-Δ ingredients (Polvere di Crononite, Shard di Prisma Stellare,
Lacrime di Andromeda, Essenza di Tachioni).
Risk tolerance: Accept negative immediate margin if prestige gain > 5.
Key principle: Serve quality fast. Never miss a client."""

BUDGET_SYSTEM_PROMPT = """You are managing a high-volume budget restaurant.
Target clients: Esploratori Galattici, Famiglie Orbitali.
Price strategy: Low prices, high throughput.
Recipe focus: Prestige 23-60, prep time ≤ 5s, minimal ingredients.
Bidding priority: Common ingredients at lowest possible price.
Risk tolerance: Avoid all negative margins. Volume > prestige.
Key principle: Serve many clients fast. Throughput is revenue."""
```

---

## 5. Client Profiling System

### The Problem

The game gives us minimal client information upfront:

- `clientName` — archetype string
- `orderText` — natural language order
- `client_id` — unique identifier (for serve_dish)

But across turns we can **observe patterns** and build profiles:

### Observable Client Signals

| Signal                   | Source                             | How to Compute                          | What It Tells Us                         |
| ------------------------ | ---------------------------------- | --------------------------------------- | ---------------------------------------- |
| `archetype_distribution` | `client_spawned` events per turn   | Count per archetype / total clients     | Which archetypes our menu attracts       |
| `order_match_rate`       | Orders vs. menu items              | % of orders we could match              | Menu alignment with demand               |
| `intolerance_patterns`   | Failed serves (revenue = 0)        | Track which ingredients caused failures | Per-archetype intolerance map            |
| `price_acceptance`       | Revenue from served dishes         | Actual vs. menu price                   | Are we pricing correctly?                |
| `visit_trend`            | Clients per turn over time         | Slope of client count                   | Is our restaurant attracting more/fewer? |
| `prep_time_utilization`  | Dishes prepared vs. serving window | Total prep time / window duration       | Are we under/over-capacity?              |

### Two-Level Client Memory

```python
class ClientProfile:
    """Profile of a single client interaction."""
    archetype: str              # Esploratore, Astrobarone, Saggi, Famiglie
    order_text: str             # Raw order
    matched_dish: str | None    # What we matched it to
    served: bool                # Did we actually serve?
    revenue: float              # Payment received (0 if failed)
    intolerance_triggered: bool # Did an intolerance violation occur?
    prep_time_ms: int           # Actual prep time
    turn_id: int                # When this happened
    timestamp: str              # ISO timestamp

class GlobalClientLibrary:
    """Cross-turn, cross-zone aggregate client knowledge."""

    # Per-archetype statistics (updated every turn)
    archetype_stats: dict[str, ArchetypeStats]
    # ArchetypeStats contains:
    #   - avg_revenue_per_serve: float
    #   - intolerance_rate: float  (% of serves that triggered intolerance)
    #   - common_intolerances: list[str]  (ingredients that caused failures)
    #   - avg_prep_time_tolerance: float  (max prep time before they leave)
    #   - visit_frequency: float  (avg clients/turn of this archetype)
    #   - preferred_dishes: list[str]  (most-ordered dishes by this archetype)

    # Intolerance knowledge base (built empirically)
    known_intolerances: dict[str, set[str]]  # archetype → set of bad ingredients

    # Order pattern cache (for fast matching)
    order_to_dish_cache: dict[str, str]  # normalized_order → best_dish

    def update_from_turn(self, turn_data: list[ClientProfile]):
        """Aggregate new turn data into global library."""
        for profile in turn_data:
            stats = self.archetype_stats[profile.archetype]
            stats.update(profile)

            if profile.intolerance_triggered and profile.matched_dish:
                # Learn which ingredients this archetype can't eat
                dish_ingredients = get_recipe_ingredients(profile.matched_dish)
                self.known_intolerances[profile.archetype].update(
                    guess_intolerance_ingredient(dish_ingredients, profile)
                )

class ZoneClientLibrary:
    """Zone-specific client profile subset."""

    zone: str
    target_archetypes: list[str]

    # Filtered view of global library for this zone's target archetypes
    def get_relevant_profiles(self, global_lib: GlobalClientLibrary) -> dict:
        return {
            arch: global_lib.archetype_stats[arch]
            for arch in self.target_archetypes
        }

    # Zone-specific recipe recommendations
    def recommend_menu(self, inventory: dict, recipes: list) -> list:
        """Select recipes that best serve this zone's target archetypes."""
        scored = []
        for recipe in recipes:
            if not inventory_sufficient(recipe, inventory):
                continue

            archetype_fit = self.score_archetype_fit(recipe)
            intolerance_safety = self.score_intolerance_safety(recipe)
            throughput_value = 1.0 / recipe.prep_time_ms  # faster = better

            scored.append((recipe, archetype_fit * intolerance_safety * throughput_value))

        return sorted(scored, key=lambda x: x[1], reverse=True)
```

### Intolerance Detection Strategy

Since the game doesn't explicitly tell us what clients are intolerant to, we must learn empirically:

```python
class IntoleranceDetector:
    """
    Bayesian intolerance detection.

    When a serve fails (revenue = 0 + reputation loss), we know ONE of the
    ingredients in the served dish triggered an intolerance. We track suspicion
    scores per archetype×ingredient pair.
    """

    # suspicion[archetype][ingredient] = beta distribution (alpha, beta)
    suspicion: dict[str, dict[str, tuple[float, float]]]

    def record_success(self, archetype: str, ingredients: list[str]):
        """Dish served successfully — lower suspicion for all ingredients."""
        for ing in ingredients:
            a, b = self.suspicion[archetype].get(ing, (1.0, 1.0))
            self.suspicion[archetype][ing] = (a, b + 1)  # more evidence of safety

    def record_failure(self, archetype: str, ingredients: list[str]):
        """Dish serve failed — raise suspicion for all ingredients."""
        for ing in ingredients:
            a, b = self.suspicion[archetype].get(ing, (1.0, 1.0))
            self.suspicion[archetype][ing] = (a + 1, b)  # more evidence of danger

    def is_safe(self, archetype: str, ingredient: str, threshold: float = 0.3) -> bool:
        """Is this ingredient safe for this archetype? (Bayesian estimate)"""
        a, b = self.suspicion[archetype].get(ingredient, (1.0, 1.0))
        # Expected intolerance probability
        p_intolerant = a / (a + b)
        return p_intolerant < threshold

    def filter_safe_recipes(self, archetype: str, recipes: list) -> list:
        """Return only recipes whose ingredients are all safe for this archetype."""
        safe = []
        for recipe in recipes:
            if all(self.is_safe(archetype, ing) for ing in recipe.ingredients):
                safe.append(recipe)
        return safe
```

### Optimal Recipe Selection Per Archetype (From Data Analysis)

| Target Archetype          | Prestige | Max Prep Time | Ingredients | Price Strategy | Top Recipes                                        |
| ------------------------- | -------- | ------------- | ----------- | -------------- | -------------------------------------------------- |
| **Esploratore Galattico** | 23–50    | ≤ 5s          | 5 (minimal) | Low            | Fast, simple dishes                                |
| **Astrobarone**           | ≥ 80     | ≤ 6s          | 5–7         | High           | Sinfonia Temporale di Fenice... (95p, 4.05s, 5ing) |
| **Saggi del Cosmo**       | ≥ 85     | Any           | 5–9         | High           | Portale Cosmico: Sinfonia... (100p, 5.22s, 5ing)   |
| **Famiglie Orbitali**     | 60–80    | Any           | 5–7         | Medium         | Balanced prestige, fair price                      |

**Key statistical insight**: Prep time does NOT correlate with prestige (r = −0.12). S-tier recipes (90–100) average only 7.4s. This means premium service is inherently fast.

**High-Δ ingredients** (prestige boosters to prioritize):
| Ingredient | Prestige Δ | Statistical Significance |
|---|---|---|
| Polvere di Crononite | +9.9 | p = 0.00 |
| Shard di Prisma Stellare | +8.8 | p = 0.01 |
| Lacrime di Andromeda | +8.3 | p = 0.02 |
| Essenza di Tachioni | +6.0 | p = 0.04 |

---

## 6. Competitive Intelligence Pipeline

### Behavioral Embedding (From vectorization_strategy.md — Unchanged)

Each turn, for each restaurant, we observe and compute a 14-feature vector:

```python
restaurant_features = {
    # Auction behavior
    "bid_aggressiveness":   total_spent / balance,
    "bid_concentration":    gini_coefficient(bids_by_ingredient),
    "bid_consistency":      cosine_similarity(this_turn, last_turn),
    "bid_volume":           num_ingredients_bid_on,

    # Menu behavior
    "price_positioning":    avg_menu_price / market_avg_price,
    "menu_stability":       jaccard_similarity(this_menu, last_menu),
    "specialization_depth": 1 / num_dishes_on_menu,

    # Market behavior
    "market_activity":      trades_executed / total_turns,
    "buy_sell_ratio":       buys / (sells + 1),

    # Outcome signals
    "balance_growth_rate":  delta_balance / turns_elapsed,
    "client_diversity":     entropy(client_archetype_distribution),

    # Recipe & prestige signals
    "prestige_targeting":   avg_prestige_of_served_dishes,
    "recipe_complexity":    avg_ingredients_per_cooked_recipe,
    "prestige_consistency": std_dev(prestige_scores_over_turns),
}
```

After 3–4 turns → matrix `(n_restaurants × 14 × n_turns)` → PCA for visualization, UMAP for clustering.

### Competitor Cluster Classification (From vectorization_strategy.md — Unchanged)

```
CLUSTER                  RELATIONAL STRATEGY        ORCHESTRATION MOVE
──────────────────────────────────────────────────────────────────────
Stable Specialist        Coexist                    Reinforce their niche
Reactive Chaser          Generous Tit-for-Tat       Feed slightly wrong signals
Aggressive Hoarder       Targeted Spoiler           Bid-deny their top 2 items
Weak / Declining         Ignore                     Offer cheap alliance
Unclassified / New       Probe                      1 cooperative message, classify reply
```

### Trajectory Prediction (From vectorization_strategy.md — Enhanced)

```python
class TrajectoryPredictor:
    """Predict where each competitor will be next turn."""

    def __init__(self, momentum_factor: float = 0.7):
        self.momentum_factor = momentum_factor
        self.history: dict[int, list[np.ndarray]] = {}  # restaurant_id → list of feature vectors

    def update(self, restaurant_id: int, features: np.ndarray):
        if restaurant_id not in self.history:
            self.history[restaurant_id] = []
        self.history[restaurant_id].append(features)

    def predict_next(self, restaurant_id: int) -> np.ndarray:
        history = self.history[restaurant_id]
        if len(history) < 2:
            return history[-1]  # no velocity yet

        velocity = history[-1] - history[-2]
        # Recency-weighted momentum
        if len(history) >= 3:
            prev_velocity = history[-2] - history[-3]
            velocity = self.momentum_factor * velocity + (1 - self.momentum_factor) * prev_velocity

        return history[-1] + velocity

    def competitors_approaching_zone(self, zone_center: np.ndarray, threshold: float) -> list[int]:
        """Which competitors are moving toward a specific zone?"""
        approaching = []
        for rid, history in self.history.items():
            if rid == OUR_ID:
                continue
            predicted = self.predict_next(rid)
            current_dist = np.linalg.norm(history[-1] - zone_center)
            predicted_dist = np.linalg.norm(predicted - zone_center)
            if predicted_dist < current_dist and predicted_dist < threshold:
                approaching.append(rid)
        return approaching
```

### Intelligence Pipeline as DagPipeline

Using datapizza-ai's `DagPipeline` to wire the intelligence flow:

```python
from datapizza.pipeline import DagPipeline

intel_pipeline = DagPipeline()

# Modules
intel_pipeline.add_module("data_collector", DataCollectorModule())    # GET /restaurants, /bid_history, /market/entries
intel_pipeline.add_module("feature_extractor", FeatureExtractorModule())  # per-restaurant 14-feature vector
intel_pipeline.add_module("embedding", EmbeddingModule())             # PCA/UMAP projection
intel_pipeline.add_module("trajectory", TrajectoryModule())           # velocity + prediction
intel_pipeline.add_module("cluster", ClusterClassifierModule())       # 5-type classification
intel_pipeline.add_module("zone_selector", ZoneSelectorModule())      # ILP zone classification

# Connections
intel_pipeline.connect("data_collector", "feature_extractor")
intel_pipeline.connect("feature_extractor", "embedding")
intel_pipeline.connect("feature_extractor", "trajectory")
intel_pipeline.connect("embedding", "cluster")
intel_pipeline.connect("trajectory", "zone_selector")
intel_pipeline.connect("cluster", "zone_selector")

# Run at the start of each turn
result = intel_pipeline.run({
    "data_collector": {"turn_id": current_turn}
})
active_zone = result["zone_selector"]
```

---

## 7. Decision Engine — ILP per Zone

### The Revenue Equation

```
Revenue = Σ (price_i × served_i) − Σ (bid_cost_j) − Σ (market_cost_k)
```

Where:

- `price_i` = menu price of dish i
- `served_i` = 1 if dish i served successfully, 0 otherwise
- `bid_cost_j` = amount paid for ingredient j in auction
- `market_cost_k` = amount paid for ingredient k on secondary market

### ILP Formulation (Zone-Specific)

Each zone adds its own constraints to the base ILP:

```python
from scipy.optimize import milp, LinearConstraint, Bounds
import numpy as np

def solve_zone_ilp(zone: str, game_state: GameState, competitor_map: CompetitorMap) -> ZoneDecision:
    """
    Decision variables:
      x_i = quantity of ingredient i to bid on (integer)
      y_j = 1 if dish j on menu, 0 otherwise (binary)
      p_j = price of dish j (continuous, bounded)

    Objective: maximize expected_revenue - bid_costs

    Constraints (base):
      - Σ(x_i * bid_price_i) ≤ balance * spending_fraction
      - y_j = 1 ⟹ all ingredients for dish j available (inventory + bids)
      - p_j ∈ [archetype_floor, archetype_ceiling] for target archetype
      - prep_time(j) ≤ serving_window / expected_clients (throughput constraint)

    Zone-specific constraints:
      PREMIUM_MONOPOLIST:
        - prestige(j) ≥ 85 for all menu items
        - max 5 dishes on menu
        - bid priority on high-Δ ingredients

      BUDGET_OPPORTUNIST:
        - prestige(j) ≤ 60 for all menu items
        - min 6 dishes on menu
        - p_j ≤ market_avg * 0.8

      NICHE_SPECIALIST:
        - all dishes target same archetype
        - prestige range = archetype optimal range

      SPEED_CONTENDER:
        - prep_time(j) ≤ 5000ms for all dishes
        - maximize dish count within serving window

      MARKET_ARBITRAGEUR:
        - minimal menu (1-2 dishes)
        - maximize bid allocation for tradeable ingredients
    """

    # ... ILP setup code ...

    result = milp(
        c=-expected_revenue_vector,
        constraints=zone_constraints,
        integrality=integrality_vector,
        bounds=bounds
    )

    return ZoneDecision(
        bids=extract_bids(result),
        menu=extract_menu(result),
        prices=extract_prices(result)
    )
```

### Bid Price Computation

For each ingredient, we predict the competitor's maximum bid and bid just above:

```python
def compute_bid_price(ingredient: str, competitor_map: CompetitorMap, turn: int) -> float:
    """
    Bid = max(predicted_competitor_bids) + epsilon

    predicted_competitor_bids come from:
    - Historical bid data (GET /bid_history)
    - Weighted average with recency bias
    - Adjusted for trajectory (if competitor is becoming more aggressive on this ingredient)
    """
    historical_bids = get_bid_history(ingredient, turn)

    if not historical_bids:
        return BASE_BID_PRICE[ingredient]  # first turn: use recipe importance heuristic

    # Recency-weighted average of competitor bids
    weights = [0.5 ** (turn - t) for t in range(len(historical_bids))]
    predicted_max = np.average(
        [max(bids.values()) for bids in historical_bids],
        weights=weights
    )

    # Adjust for trajectory — if a Reactive Chaser is moving toward our ingredients
    trajectory_adjustment = 1.0
    for rid in competitor_map.reactive_chasers:
        if is_moving_toward_ingredient(rid, ingredient, competitor_map):
            trajectory_adjustment *= 1.15  # bid 15% higher

    return predicted_max * trajectory_adjustment + 1  # +1 epsilon
```

### Menu Pricing

```python
def compute_menu_price(dish: str, zone: str, game_state: GameState) -> float:
    """
    Price = archetype_ceiling × reputation_multiplier × zone_factor

    Constrained by:
    - Archetype willingness-to-pay ceiling
    - Zone pricing strategy
    - Competitor menu prices (from GET /restaurant/:id/menu)
    """
    archetype = get_target_archetype(zone)

    ARCHETYPE_CEILINGS = {
        "Esploratore Galattico": 50,
        "Astrobarone": 200,
        "Saggi del Cosmo": 250,
        "Famiglie Orbitali": 120,
    }

    base_price = ARCHETYPE_CEILINGS[archetype]

    # Reputation multiplier (higher reputation → can charge more)
    rep_mult = 1.0 + (game_state.reputation - 50) / 200  # normalized around 1.0

    # Zone factor
    ZONE_FACTORS = {
        "PREMIUM_MONOPOLIST": 0.95,    # near ceiling
        "BUDGET_OPPORTUNIST": 0.50,    # well below ceiling
        "NICHE_SPECIALIST": 0.80,      # moderate
        "SPEED_CONTENDER": 0.70,       # competitive
        "MARKET_ARBITRAGEUR": 0.60,    # minimal menu, low prices
    }

    return int(base_price * rep_mult * ZONE_FACTORS[zone])
```

---

## 8. Deception & Defense Layer

### GroundTruthFirewall (Defense)

The fundamental defense principle: **strategic decisions ONLY use data from server-signed GET responses, NEVER from incoming messages.**

```python
class GroundTruthFirewall:
    """
    Middleware that separates trusted data (GET responses) from untrusted data
    (incoming messages, market broadcasts).

    Pattern: every piece of data entering the decision engine carries a
    TrustLevel tag.
    """

    class TrustLevel:
        SERVER_SIGNED = "server"    # GET /restaurants, /bid_history, etc.
        SELF_GENERATED = "self"     # Our own calculations
        UNTRUSTED = "untrusted"     # Incoming messages, market broadcasts

    def validate_for_decisions(self, data: dict, trust_level: str) -> dict | None:
        """Only SERVER_SIGNED and SELF_GENERATED data passes through to ILP."""
        if trust_level == self.TrustLevel.UNTRUSTED:
            # Log for intelligence purposes but DO NOT use for decisions
            self.log_untrusted(data)
            return None
        return data

    def process_incoming_message(self, message: dict) -> dict:
        """
        Incoming messages are processed for intelligence but NEVER
        enter the decision engine directly.

        Instead, we:
        1. Log the message
        2. Compare claims against our own observations
        3. Update sender credibility score
        4. If claims are verifiable via GET, verify them
        """
        sender_id = message["senderId"]
        claim = message["text"]

        # Cross-reference against ground truth
        verifiable = self.extract_verifiable_claims(claim)
        for claim in verifiable:
            truth = self.verify_via_get(claim)
            if truth is not None:
                self.update_credibility(sender_id, claim, truth)

        return {
            "message": message,
            "trust_level": self.TrustLevel.UNTRUSTED,
            "sender_credibility": self.get_credibility(sender_id),
        }
```

### DeceptionBandit (Offense — Thompson Sampling)

We model deception strategies as arms of a multi-armed bandit:

```python
from scipy.stats import beta as beta_dist
import numpy as np

class DeceptionBandit:
    """
    Thompson Sampling bandit for selecting deception strategies.

    Arms represent different manipulation approaches.
    Reward = observable competitor behavior change in the desired direction.
    """

    ARMS = {
        "truthful_warning":     (1.0, 1.0),  # "heads up, X is bidding on Y"
        "inflated_intel":       (1.0, 1.0),  # "Recipe X has been amazing for us" (true but framed)
        "manufactured_scarcity":(1.0, 1.0),  # "We're stockpiling ingredient Z" (may be false)
        "alliance_offer":      (1.0, 1.0),  # "Want to split the premium market?"
        "silence":             (1.0, 1.0),  # Say nothing (baseline)
    }

    def __init__(self):
        self.arms = {name: list(prior) for name, prior in self.ARMS.items()}

    def select_arm(self) -> str:
        """Sample from posterior and pick the arm with highest sample."""
        samples = {
            name: beta_dist.rvs(a, b)
            for name, (a, b) in self.arms.items()
        }
        return max(samples, key=samples.get)

    def update(self, arm: str, reward: float):
        """
        reward = 1 if the target competitor changed behavior as intended
        reward = 0 if no observable effect
        reward = -1 if competitor did the opposite (they're onto us)
        """
        a, b = self.arms[arm]
        if reward > 0:
            self.arms[arm] = [a + 1, b]
        else:
            self.arms[arm] = [a, b + 1]

    def select_target(self, competitor_map: CompetitorMap) -> int:
        """
        Target selection based on competitor cluster:
        - Reactive Chasers: best targets (they respond to signals)
        - Aggressive Hoarders: worth trying to redirect
        - Stable Specialists: low-value targets (won't change)
        - Weak/Declining: don't waste messages
        """
        target_priority = (
            competitor_map.reactive_chasers +
            competitor_map.aggressive_hoarders
        )
        return target_priority[0] if target_priority else None
```

### PseudoGAN (Message Quality Optimization)

A two-LLM setup where one generates deceptive messages and the other scores them:

```python
class PseudoGAN:
    """
    Generator: gpt-oss-120b — crafts diplomatic messages
    Discriminator: gpt-oss-20b — scores whether the message would be
    believed by a rival LLM agent

    NOT a real GAN. No gradient-based training. Just iterative refinement.
    """

    def __init__(self, generator_client, discriminator_client):
        self.generator = generator_client  # gpt-oss-120b
        self.discriminator = discriminator_client  # gpt-oss-20b

    async def craft_message(
        self,
        target_cluster: str,
        desired_effect: str,
        context: str,
        max_iterations: int = 3
    ) -> str:
        best_message = None
        best_score = 0.0

        for i in range(max_iterations):
            # Generate candidate
            gen_prompt = f"""You are a restaurant manager in a competitive cooking game.
Craft a message to a {target_cluster} competitor to achieve: {desired_effect}
Context: {context}
{"Previous attempt scored " + str(best_score) + "/1.0. Make it more convincing." if best_message else ""}
Keep it under 200 characters. Be natural, not obviously manipulative."""

            candidate = (await self.generator.a_invoke(gen_prompt)).text

            # Score with discriminator
            disc_prompt = f"""You are an AI agent managing a restaurant. You received this message:
"{candidate}"
Score 0.0-1.0: how likely are you to change your strategy based on this?
Reply with just the number."""

            score_text = (await self.discriminator.a_invoke(disc_prompt)).text
            score = float(score_text.strip())

            if score > best_score:
                best_score = score
                best_message = candidate

            if score > 0.7:
                break  # good enough

        return best_message
```

---

## 9. Execution Engine — Serving Pipeline

### Design Principle: Zero-LLM Hot Path

During the serving phase, every millisecond counts. The serving pipeline uses NO LLM calls for the common case:

```python
class ServingPipeline:
    """
    Hot path: SSE event → dish match → prepare → serve
    Total latency target: <100ms before prepare_dish call
    """

    def __init__(self, menu: list, recipes: dict, intolerance_detector: IntoleranceDetector):
        self.menu = {item["name"].lower(): item for item in menu}
        self.recipes = recipes
        self.intolerance_detector = intolerance_detector

        # Pre-compute order→dish lookup table
        self.order_lookup = self._build_lookup()

        # Preparation queue
        self.prep_queue: asyncio.Queue = asyncio.Queue()
        self.preparing: dict[str, str] = {}  # dish_name → client_id

    def _build_lookup(self) -> dict[str, str]:
        """Pre-compute normalized order text → best menu dish mapping."""
        lookup = {}
        for dish_name in self.menu:
            # Multiple normalization variants
            normalized = dish_name.lower().strip()
            lookup[normalized] = dish_name
            # Without common prefixes
            for prefix in ["i'd like a ", "i'd like ", "vorrei ", "mi piacerebbe "]:
                lookup[prefix + normalized] = dish_name
        return lookup

    async def handle_client(self, client_name: str, order_text: str, client_id: str):
        """
        Called on client_spawned SSE event.

        Flow:
        1. Normalize order text
        2. Match to menu dish (lookup, then fuzzy, then LLM fallback)
        3. Check intolerance safety
        4. prepare_dish
        5. On preparation_complete → serve_dish
        """
        # Step 1: Normalize
        normalized = order_text.lower().strip()
        for prefix in ["i'd like a ", "i'd like "]:
            normalized = normalized.replace(prefix, "")

        # Step 2: Match dish
        dish = self._match_dish(normalized, client_name)
        if dish is None:
            return  # no match found, skip this client

        # Step 3: Intolerance check
        archetype = client_name
        if not self.intolerance_detector.filter_safe_recipes(
            archetype, [self.recipes[dish]]
        ):
            # This dish might trigger intolerance — find alternative
            dish = self._find_safe_alternative(archetype)
            if dish is None:
                return  # no safe dishes available

        # Step 4: Prepare
        self.preparing[dish] = client_id
        await self._mcp_prepare_dish(dish)

    async def handle_preparation_complete(self, dish_name: str):
        """Called on preparation_complete SSE event."""
        client_id = self.preparing.pop(dish_name, None)
        if client_id:
            await self._mcp_serve_dish(dish_name, client_id)

    def _match_dish(self, normalized_order: str, client_name: str) -> str | None:
        """
        Three-tier matching:
        1. Exact lookup (O(1), no LLM) — handles 90%+ of cases
        2. Fuzzy match (difflib, no LLM) — handles typos/variations
        3. LLM fallback (only for truly ambiguous orders) — <5% of cases
        """
        # Tier 1: Exact lookup
        if normalized_order in self.order_lookup:
            return self.order_lookup[normalized_order]

        # Tier 2: Fuzzy match
        from difflib import get_close_matches
        matches = get_close_matches(normalized_order, self.menu.keys(), n=1, cutoff=0.7)
        if matches:
            return self.menu[matches[0]]["name"]

        # Tier 3: LLM fallback (async, but we accept the latency hit for rare cases)
        # This is queued and handled asynchronously
        return None  # or await self._llm_match(normalized_order, client_name)

    def _find_safe_alternative(self, archetype: str) -> str | None:
        """Find the best safe menu dish for this archetype."""
        safe_dishes = self.intolerance_detector.filter_safe_recipes(
            archetype,
            [self.recipes[d] for d in self.menu]
        )
        if safe_dishes:
            # Pick the one with highest prestige (or fastest prep time for Esploratori)
            return max(safe_dishes, key=lambda r: r.prestige).name
        return None
```

### Serving Strategy Per Archetype

| Archetype                 | Priority   | Strategy                                                        |
| ------------------------- | ---------- | --------------------------------------------------------------- |
| **Astrobarone**           | 🔴 Highest | Serve first — highest revenue, least time tolerance             |
| **Saggi del Cosmo**       | 🟡 High    | Serve quality — they wait, so handle after Astrobaroni          |
| **Famiglie Orbitali**     | 🟢 Medium  | Serve balanced — good margin, time-tolerant                     |
| **Esploratore Galattico** | 🔵 Low     | Serve last — lowest revenue, but fast dishes so squeeze them in |

```python
class ClientPriorityQueue:
    """Priority queue for incoming clients during serving phase."""

    PRIORITY = {
        "Astrobarone": 0,        # highest priority (lowest number)
        "Saggi del Cosmo": 1,
        "Famiglie Orbitali": 2,
        "Esploratore Galattico": 3,
    }

    def __init__(self):
        self.queue: list[tuple[int, dict]] = []  # (priority, client_data)

    def add_client(self, client_data: dict):
        priority = self.PRIORITY.get(client_data["clientName"], 99)
        heapq.heappush(self.queue, (priority, client_data))

    def next_client(self) -> dict | None:
        if self.queue:
            _, client = heapq.heappop(self.queue)
            return client
        return None
```

---

## 10. Data Architecture & Memory Systems

### Event-Sourced Game State

All game data flows through an append-only event log:

```python
import json
from datetime import datetime

class EventLog:
    """Append-only JSONL event log for full game replay."""

    def __init__(self, filepath: str = "game_events.jsonl"):
        self.filepath = filepath

    def log(self, event_type: str, data: dict, trust_level: str = "server"):
        entry = {
            "ts": datetime.now().isoformat(),
            "type": event_type,
            "trust": trust_level,
            "data": data,
        }
        with open(self.filepath, "a") as f:
            f.write(json.dumps(entry) + "\n")

    def replay(self, event_type: str = None) -> list[dict]:
        """Replay events, optionally filtered by type."""
        events = []
        with open(self.filepath, "r") as f:
            for line in f:
                entry = json.loads(line)
                if event_type is None or entry["type"] == event_type:
                    events.append(entry)
        return events
```

### Memory Architecture

```
┌────────────────────────────────────────────────────────────────────┐
│                        MEMORY LAYER                                │
│                                                                    │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │  GameStateMemory (per-turn snapshot)                         │  │
│  │                                                             │  │
│  │  turn_id: int                                               │  │
│  │  phase: str                                                 │  │
│  │  balance: float                                             │  │
│  │  inventory: dict[str, int]                                  │  │
│  │  reputation: float                                          │  │
│  │  menu: list[dict]                                           │  │
│  │  clients_served: int                                        │  │
│  │  revenue_this_turn: float                                   │  │
│  └─────────────────────────────────────────────────────────────┘  │
│                                                                    │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │  CompetitorMemory (per-restaurant, cross-turn)              │  │
│  │                                                             │  │
│  │  restaurant_id: int → {                                     │  │
│  │    feature_history: list[np.ndarray]   # 14-dim vectors     │  │
│  │    cluster: str                        # current cluster    │  │
│  │    trajectory: np.ndarray              # predicted next pos │  │
│  │    credibility: float                  # message trust      │  │
│  │    menu_history: list[dict]            # what they served   │  │
│  │    bid_history: list[dict]             # what they bid      │  │
│  │    balance_history: list[float]        # their balance      │  │
│  │  }                                                          │  │
│  └─────────────────────────────────────────────────────────────┘  │
│                                                                    │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │  ClientProfileMemory (two-level)                            │  │
│  │                                                             │  │
│  │  GlobalClientLibrary:                                       │  │
│  │    archetype_stats: dict[str, ArchetypeStats]               │  │
│  │    known_intolerances: dict[str, set[str]]                  │  │
│  │    order_cache: dict[str, str]                              │  │
│  │                                                             │  │
│  │  ZoneClientLibrary (per zone):                              │  │
│  │    target_archetypes: list[str]                             │  │
│  │    zone_specific_recommendations: list[str]                 │  │
│  └─────────────────────────────────────────────────────────────┘  │
│                                                                    │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │  MessageMemory                                              │  │
│  │                                                             │  │
│  │  sent: list[dict]         # our outbox (no API — must log) │  │
│  │  received: list[dict]     # messages from competitors      │  │
│  │  broadcasts: list[dict]   # market broadcasts              │  │
│  └─────────────────────────────────────────────────────────────┘  │
│                                                                    │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │  EventLog (JSONL append-only)                               │  │
│  │                                                             │  │
│  │  Every SSE event + every GET response + every MCP call      │  │
│  │  Full replay capability for debugging and analysis          │  │
│  └─────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────┘
```

### End-of-Turn Snapshot (Polling)

At each turn's `stopped` phase, poll all GET endpoints to fill gaps:

```python
async def end_of_turn_snapshot(turn_id: int) -> dict:
    """Comprehensive data collection at end of each turn."""
    import aiohttp

    HEADERS = {"x-api-key": API_KEY}
    BASE = "https://hackapizza.datapizza.tech"

    async with aiohttp.ClientSession() as session:
        # Parallel GET requests
        tasks = {
            "our_state": session.get(f"{BASE}/restaurant/17", headers=HEADERS),
            "all_restaurants": session.get(f"{BASE}/restaurants", headers=HEADERS),
            "bids": session.get(f"{BASE}/bid_history?turn_id={turn_id}", headers=HEADERS),
            "market": session.get(f"{BASE}/market/entries", headers=HEADERS),
            "meals": session.get(f"{BASE}/meals?turn_id={turn_id}&restaurant_id=17", headers=HEADERS),
            "recipes": session.get(f"{BASE}/recipes", headers=HEADERS),
        }

        # Also get menus from all competitors
        for rid in range(1, 26):
            if rid != 17:
                tasks[f"menu_{rid}"] = session.get(
                    f"{BASE}/restaurant/{rid}/menu", headers=HEADERS
                )

        results = {}
        for key, coro in tasks.items():
            try:
                resp = await coro
                results[key] = await resp.json()
            except Exception:
                results[key] = None

        return results
```

### Using datapizza Memory for LLM Context

The framework's `Memory` class manages LLM conversation context, separate from game state:

```python
from datapizza.memory import Memory
from datapizza.type import ROLE, TextBlock

class AgentMemoryManager:
    """
    Manages the Memory objects for each subagent.

    Key insight: each zone's agent gets a DIFFERENT memory context
    containing only information relevant to its zone.
    """

    def __init__(self):
        self.memories: dict[str, Memory] = {
            zone: Memory() for zone in ZONES
        }

    def build_context_for_zone(self, zone: str, game_state: GameState) -> Memory:
        """Build a focused memory context for the active zone's agent."""
        mem = self.memories[zone]

        # Clear and rebuild with current context (keep it tight)
        mem.clear()

        # Add game state summary
        mem.add_turn(
            [TextBlock(content=f"""[GAME STATE] Turn {game_state.turn_id}
Balance: {game_state.balance} | Reputation: {game_state.reputation}
Inventory: {game_state.inventory}
Active zone: {zone}
Clients served this game: {game_state.total_clients_served}""")],
            role=ROLE.USER
        )

        # Add zone-specific context
        zone_context = self.get_zone_context(zone, game_state)
        mem.add_turn(
            [TextBlock(content=zone_context)],
            role=ROLE.USER
        )

        return mem
```

---

## 11. Datapizza-AI Kernel Extensions

These are proposed extensions to the datapizza-ai framework that would make it more suitable for competitive game scenarios. Each extension follows the framework's existing patterns and could be contributed back.

### Extension 1: `ReactiveEventBus` — Event-Driven Agent Activation

**Problem**: The framework's `Agent` is pull-based (you call `agent.run()`). The game is push-based (SSE events arrive asynchronously).

**Proposed Extension**: An event bus that connects SSE streams to agent invocations with typed routing.

```python
# Proposed: datapizza.events.ReactiveEventBus
from datapizza.agents import Agent
from typing import Callable, Any
import asyncio

class EventHandler:
    """Typed event handler with priority and filtering."""
    def __init__(self, event_type: str, handler: Callable, priority: int = 0,
                 filter_fn: Callable | None = None):
        self.event_type = event_type
        self.handler = handler
        self.priority = priority
        self.filter_fn = filter_fn

class ReactiveEventBus:
    """
    Event-driven agent activation layer.

    Extends the framework to support push-based architectures where
    external events (SSE, webhooks, message queues) trigger agent invocations.

    Usage:
        bus = ReactiveEventBus()
        bus.on("client_spawned", serving_agent, priority=0)
        bus.on("new_message", diplomacy_agent, priority=1)
        bus.on("game_phase_changed", phase_router, priority=0)

        # Connect to SSE stream
        await bus.connect_sse("https://server/events/17", headers={...})
    """

    def __init__(self):
        self.handlers: dict[str, list[EventHandler]] = {}
        self.middleware: list[Callable] = []

    def on(self, event_type: str, handler: Callable | Agent,
           priority: int = 0, filter_fn: Callable | None = None):
        """Register a handler for an event type."""
        if isinstance(handler, Agent):
            # Wrap agent in async invocation
            agent = handler
            async def agent_handler(data):
                return await agent.a_run(str(data))
            handler = agent_handler

        if event_type not in self.handlers:
            self.handlers[event_type] = []
        self.handlers[event_type].append(
            EventHandler(event_type, handler, priority, filter_fn)
        )
        # Sort by priority
        self.handlers[event_type].sort(key=lambda h: h.priority)

    def use(self, middleware: Callable):
        """Add middleware (e.g., GroundTruthFirewall, EventLog)."""
        self.middleware.append(middleware)

    async def emit(self, event_type: str, data: dict):
        """Dispatch an event through middleware then to handlers."""
        # Run through middleware chain
        for mw in self.middleware:
            data = await mw(event_type, data)
            if data is None:
                return  # middleware blocked the event

        # Dispatch to handlers
        for handler in self.handlers.get(event_type, []):
            if handler.filter_fn and not handler.filter_fn(data):
                continue
            try:
                await handler.handler(data)
            except Exception as e:
                print(f"Handler error for {event_type}: {e}")

    async def connect_sse(self, url: str, headers: dict):
        """Connect to an SSE stream and dispatch events."""
        import aiohttp

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as resp:
                async for line in resp.content:
                    line = line.decode().strip()
                    if line.startswith("data:"):
                        data = json.loads(line[5:])
                        event_type = data.get("type", "unknown")
                        await self.emit(event_type, data.get("data", {}))
```

**Value to datapizza-ai**: Enables event-driven architectures beyond request-response. Useful for any real-time application (chatbots with push notifications, IoT monitoring, game agents).

---

### Extension 2: `GameStateMemory` — Structured State Memory

**Problem**: The framework's `Memory` is a conversation buffer (turns of text). Game state is structured data (inventory, balance, reputation) that doesn't fit the conversation model.

**Proposed Extension**: A typed memory that stores structured state snapshots alongside conversation history.

```python
# Proposed: datapizza.memory.GameStateMemory
from datapizza.memory import Memory
from pydantic import BaseModel
from typing import Generic, TypeVar

T = TypeVar("T", bound=BaseModel)

class GameStateMemory(Memory, Generic[T]):
    """
    Memory that combines conversation history with structured state snapshots.

    Extends Memory to support:
    - Typed state snapshots (Pydantic models)
    - State diffing (what changed between turns)
    - Automatic context injection (state summary added to LLM context)

    Usage:
        class RestaurantState(BaseModel):
            turn_id: int
            balance: float
            inventory: dict[str, int]
            reputation: float

        memory = GameStateMemory[RestaurantState]()
        memory.update_state(RestaurantState(turn_id=1, balance=1000, ...))

        # State is automatically included in LLM context
        response = agent.run("What should I bid?", memory=memory)
    """

    def __init__(self):
        super().__init__()
        self.state_history: list[T] = []
        self.current_state: T | None = None

    def update_state(self, state: T):
        """Record a new state snapshot."""
        self.state_history.append(state)
        self.current_state = state

        # Auto-inject state summary into conversation context
        from datapizza.type import TextBlock, ROLE
        state_summary = f"[STATE UPDATE] {state.model_dump_json()}"
        self.add_turn([TextBlock(content=state_summary)], role=ROLE.USER)

    def state_diff(self, n_turns_back: int = 1) -> dict:
        """What changed in the last N turns?"""
        if len(self.state_history) < n_turns_back + 1:
            return {}

        old = self.state_history[-(n_turns_back + 1)]
        new = self.state_history[-1]

        diff = {}
        for field in old.model_fields:
            old_val = getattr(old, field)
            new_val = getattr(new, field)
            if old_val != new_val:
                diff[field] = {"old": old_val, "new": new_val}
        return diff

    def trend(self, field: str, window: int = 5) -> list:
        """Get the trend of a numeric field over the last N states."""
        values = []
        for state in self.state_history[-window:]:
            values.append(getattr(state, field, None))
        return values
```

**Value to datapizza-ai**: Any agent application that needs structured state alongside conversation history (game agents, workflow agents, monitoring agents).

---

### Extension 3: `CompetitorMemory` — Multi-Entity Tracking Memory

**Problem**: The framework has no built-in way to track multiple external entities (competitors, other users, market participants) across time.

**Proposed Extension**: A memory specialized for tracking multiple entities with per-entity feature vectors and history.

```python
# Proposed: datapizza.memory.EntityTrackingMemory
from datapizza.memory import Memory
import numpy as np

class EntityTrackingMemory(Memory):
    """
    Memory specialized for tracking multiple external entities across time.

    Each entity has:
    - Feature vector history (for embedding/clustering)
    - Classification (cluster assignment)
    - Predicted trajectory
    - Interaction history

    Usage:
        memory = EntityTrackingMemory(feature_dim=14)
        memory.update_entity(entity_id=5, features=np.array([...]))
        memory.classify_entity(entity_id=5, cluster="aggressive_hoarder")
        trajectory = memory.predict_trajectory(entity_id=5)
    """

    def __init__(self, feature_dim: int = 14):
        super().__init__()
        self.feature_dim = feature_dim
        self.entities: dict[int, EntityProfile] = {}

    def update_entity(self, entity_id: int, features: np.ndarray, metadata: dict = None):
        if entity_id not in self.entities:
            self.entities[entity_id] = EntityProfile(entity_id, self.feature_dim)
        self.entities[entity_id].add_observation(features, metadata)

    def classify_entity(self, entity_id: int, cluster: str):
        if entity_id in self.entities:
            self.entities[entity_id].cluster = cluster

    def predict_trajectory(self, entity_id: int, momentum: float = 0.7) -> np.ndarray:
        return self.entities[entity_id].predict_next(momentum)

    def get_entities_in_cluster(self, cluster: str) -> list[int]:
        return [eid for eid, e in self.entities.items() if e.cluster == cluster]

    def get_approaching_entities(self, target: np.ndarray, threshold: float) -> list[int]:
        """Which entities are moving toward a target position?"""
        approaching = []
        for eid, entity in self.entities.items():
            if len(entity.feature_history) < 2:
                continue
            current_dist = np.linalg.norm(entity.feature_history[-1] - target)
            predicted = entity.predict_next()
            predicted_dist = np.linalg.norm(predicted - target)
            if predicted_dist < current_dist and predicted_dist < threshold:
                approaching.append(eid)
        return approaching

class EntityProfile:
    def __init__(self, entity_id: int, feature_dim: int):
        self.entity_id = entity_id
        self.feature_history: list[np.ndarray] = []
        self.cluster: str = "unclassified"
        self.metadata_history: list[dict] = []

    def add_observation(self, features: np.ndarray, metadata: dict = None):
        self.feature_history.append(features)
        self.metadata_history.append(metadata or {})

    def predict_next(self, momentum: float = 0.7) -> np.ndarray:
        if len(self.feature_history) < 2:
            return self.feature_history[-1]
        velocity = self.feature_history[-1] - self.feature_history[-2]
        return self.feature_history[-1] + velocity * momentum
```

**Value to datapizza-ai**: Multi-agent systems, competitive intelligence, any scenario where an agent needs to track and predict external entity behavior.

---

### Extension 4: `StructuredEventBus` — Typed Event Middleware

**Problem**: The framework doesn't have event middleware for processing SSE/webhook events before they reach agents.

**Proposed Extension**: Middleware chain for event processing — filtering, transformation, logging, trust tagging.

```python
# Proposed: datapizza.events.StructuredEventBus
# (simplified version of ReactiveEventBus focused on middleware)

from typing import Callable, Awaitable

Middleware = Callable[[str, dict], Awaitable[dict | None]]

class StructuredEventBus:
    """
    Typed event processing with middleware chain.

    Middleware functions can:
    - Transform event data
    - Block events (return None)
    - Add metadata (trust levels, timestamps)
    - Log events

    Usage:
        bus = StructuredEventBus()

        # Add middleware
        bus.use(event_logger)           # logs all events
        bus.use(trust_tagger)           # adds trust_level to data
        bus.use(ground_truth_firewall)  # blocks untrusted data from decisions

        # Register handlers
        bus.on("client_spawned", handle_client)
    """
    pass  # Implementation same as ReactiveEventBus above
```

---

### Extension 5: Custom `@tool` Definitions for Game Actions

**Problem**: MCP tools are generic. We want typed, validated game-specific tools.

**Proposed Extension**: Strongly-typed tool wrappers for common game actions.

```python
from datapizza.tools import tool
from pydantic import BaseModel
import aiohttp

class BidItem(BaseModel):
    ingredient: str
    bid: float
    quantity: int

@tool
async def submit_bids(bids: list[BidItem]) -> str:
    """Submit ingredient bids for the closed bid phase.

    Args:
        bids: List of bid items with ingredient name, bid amount, and quantity.

    Returns:
        Confirmation or error message from the game server.
    """
    payload = {
        "jsonrpc": "2.0", "id": 1, "method": "tools/call",
        "params": {
            "name": "closed_bid",
            "arguments": {"bids": [b.model_dump() for b in bids]}
        }
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(MCP_URL, json=payload, headers=HEADERS) as resp:
            result = await resp.json()
            return result.get("result", {}).get("content", [{}])[0].get("text", "OK")

@tool
async def set_menu(items: list[dict]) -> str:
    """Set the restaurant menu with dish names and prices.

    Args:
        items: List of menu items, each with 'name' (str) and 'price' (int).

    Returns:
        Confirmation or error message.
    """
    # ... MCP call implementation ...
    pass

@tool
async def analyze_competitors() -> str:
    """Fetch and analyze all competitor restaurant states.

    Returns:
        Summary of competitor positions, balances, and menus.
    """
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{BASE_URL}/restaurants", headers=HEADERS) as resp:
            data = await resp.json()

    summary_lines = []
    for r in data:
        summary_lines.append(
            f"Team {r['id']} ({r['name']}): balance={r['balance']}, "
            f"rep={r['reputation']}, open={r['isOpen']}, "
            f"menu_items={len(r.get('menu', []))}"
        )
    return "\n".join(summary_lines)
```

---

### Extension 6: `DagPipeline` for Intelligence Pipeline

**Problem**: The intelligence flow (data collection → feature extraction → embedding → clustering → zone selection) is a DAG that should use the framework's pipeline abstraction.

**Proposed Extension**: Custom `Module` implementations that plug into `DagPipeline`.

```python
from datapizza.core.module import Module

class DataCollectorModule(Module):
    """Collects game data from all GET endpoints."""

    async def process(self, input_data: dict) -> dict:
        turn_id = input_data.get("turn_id", 0)
        return await end_of_turn_snapshot(turn_id)

class FeatureExtractorModule(Module):
    """Extracts 14-dim feature vector per restaurant."""

    async def process(self, input_data: dict) -> dict:
        restaurants = input_data.get("all_restaurants", [])
        bids = input_data.get("bids", [])

        features = {}
        for r in restaurants:
            features[r["id"]] = extract_features(r, bids)

        return {"features": features}

class ClusterClassifierModule(Module):
    """Classifies restaurants into behavioral clusters."""

    async def process(self, input_data: dict) -> dict:
        embeddings = input_data.get("embeddings", {})

        clusters = {}
        for rid, emb in embeddings.items():
            clusters[rid] = classify_cluster(emb)

        return {"clusters": clusters}

# Wire them into a DagPipeline
pipeline = DagPipeline()
pipeline.add_module("collector", DataCollectorModule())
pipeline.add_module("features", FeatureExtractorModule())
pipeline.add_module("clusters", ClusterClassifierModule())
pipeline.connect("collector", "features")
pipeline.connect("features", "clusters")
```

---

## 12. Phase-by-Phase Action Matrix

### Phase: `game_started`

| Action                | Component        | Details                                          |
| --------------------- | ---------------- | ------------------------------------------------ |
| Initialize game state | GameStateMemory  | Reset turn counter, load persisted state         |
| Connect SSE           | ReactiveEventBus | Start listening at `/events/17`                  |
| Fetch recipes         | DataCollector    | `GET /recipes` → cache locally                   |
| Fetch all restaurants | DataCollector    | `GET /restaurants` → initial competitor snapshot |

### Phase: `speaking`

| Action                    | Component           | Details                                                                 |
| ------------------------- | ------------------- | ----------------------------------------------------------------------- |
| Run intelligence pipeline | DagPipeline         | Fetch competitors, compute embeddings, classify clusters                |
| Select active zone        | SubagentRouter      | ILP zone classification based on competitor positions                   |
| Set menu                  | Active Subagent     | Zone-appropriate dishes + prices via `save_menu`                        |
| Diplomacy                 | DiplomacyAgent      | DeceptionBandit selects arm → PseudoGAN crafts message → `send_message` |
| Process incoming messages | GroundTruthFirewall | Log, verify claims, update credibility                                  |

### Phase: `closed_bid`

| Action                | Component       | Details                                       |
| --------------------- | --------------- | --------------------------------------------- |
| Compute optimal bids  | ILP Solver      | Zone-specific bid allocation via `closed_bid` |
| Update menu if needed | Active Subagent | Adjust based on pre-bid analysis              |
| Monitor market        | MarketMonitor   | Check `GET /market/entries` for arbitrage     |

### Phase: `waiting`

| Action                     | Component         | Details                                                                                 |
| -------------------------- | ----------------- | --------------------------------------------------------------------------------------- |
| Evaluate bid results       | GameStateMemory   | `GET /restaurant/17` → check inventory                                                  |
| Adjust menu to inventory   | Active Subagent   | Remove dishes we can't cook, adjust prices                                              |
| Market operations          | MarketArbitrageur | Buy missing ingredients, sell surplus via `create_market_entry` / `execute_transaction` |
| Pre-compute serving lookup | ServingPipeline   | Build order→dish lookup table from current menu                                         |
| Open restaurant            | MCP               | `update_restaurant_is_open(is_open=true)`                                               |

### Phase: `serving`

| Action                        | Component           | Details                                                        |
| ----------------------------- | ------------------- | -------------------------------------------------------------- |
| Handle `client_spawned`       | ServingPipeline     | Parse order → match dish → intolerance check → `prepare_dish`  |
| Handle `preparation_complete` | ServingPipeline     | `serve_dish` to waiting client                                 |
| Priority queue                | ClientPriorityQueue | Astrobaroni first, then Saggi, then Famiglie, then Esploratori |
| Track outcomes                | ClientProfileMemory | Record success/failure per serve for intolerance learning      |

### Phase: `stopped`

| Action                        | Component           | Details                                 |
| ----------------------------- | ------------------- | --------------------------------------- |
| End-of-turn snapshot          | DataCollector       | Poll all GET endpoints                  |
| Update all memories           | Memory Layer        | GameState, Competitor, ClientProfile    |
| Update behavioral embedding   | CompetitorMemory    | New feature vectors for all restaurants |
| Update trajectory predictions | TrajectoryPredictor | Velocity + momentum for next turn       |
| Update intolerance model      | IntoleranceDetector | Bayesian update from serve outcomes     |
| Persist state                 | EventLog            | Save everything to JSONL                |
| Log to monitoring             | ContextTracing      | datapizza-ai tracing integration        |

---

## 13. Causal Decision Chain

The complete causal chain from game objective to every strategic decision:

```
OBJECTIVE: Maximize final balance
    │
    ├── Revenue = Σ(price × served) − Σ(bid_costs) − Σ(market_costs)
    │
    ├──► WHICH CLIENTS TO TARGET?
    │    │
    │    ├── Archetype analysis (4 types with known behaviors)
    │    ├── Menu→archetype attraction model
    │    ├── Current reputation level (determines accessible archetypes)
    │    └── Zone-specific targeting
    │         │
    │         └──► WHICH ZONE TO ACTIVATE?
    │              │
    │              ├── Competitor density in each zone (from embedding)
    │              ├── Inventory alignment with zone recipes
    │              ├── Revenue potential per zone
    │              └── Reputation trajectory alignment
    │
    ├──► WHICH RECIPES TO PUT ON MENU?
    │    │
    │    ├── Recipe pool filtered by zone (prestige range)
    │    ├── Ingredient availability (inventory + expected bid wins)
    │    ├── Intolerance safety (Bayesian model)
    │    ├── Prep time (throughput constraint)
    │    └── Ingredient criticality (can we monopolize?)
    │
    ├──► HOW MUCH TO BID?
    │    │
    │    ├── Predicted competitor max bids (recency-weighted history)
    │    ├── Trajectory adjustment (reactive chasers moving our way?)
    │    ├── Ingredient criticality for our zone's recipes
    │    ├── Balance constraint (can't spend more than we have)
    │    └── Future value (prestige flywheel: accept negative margin if prestige gain > X)
    │
    ├──► HOW TO PRICE MENU ITEMS?
    │    │
    │    ├── Archetype willingness-to-pay ceiling
    │    ├── Reputation multiplier
    │    ├── Zone pricing factor
    │    └── Competitor menu prices (undercut or premium?)
    │
    ├──► HOW TO SERVE EACH CLIENT?
    │    │
    │    ├── Order text → dish match (lookup, fuzzy, LLM fallback)
    │    ├── Intolerance check (Bayesian safety filter)
    │    ├── Priority queue (Astrobaroni first)
    │    └── Safe alternative selection if primary dish is risky
    │
    └──► MARKET OPERATIONS (FALLBACK)
         │
         ├── Missing ingredients → buy from market (marginal analysis)
         ├── Surplus ingredients → sell before expiry
         └── Arbitrage if price spread exists between buy/sell listings
```

---

## 14. Implementation Roadmap

### Priority 1 — Core Loop (Must Have for Game Start)

| #   | Task                                                         | Time Est. | Dependencies |
| --- | ------------------------------------------------------------ | --------- | ------------ |
| 1.1 | SSE connection + event dispatch                              | 1h        | None         |
| 1.2 | MCP client setup (datapizza MCPClient)                       | 30m       | None         |
| 1.3 | Basic serving pipeline (order→match→prepare→serve)           | 2h        | 1.1, 1.2     |
| 1.4 | Menu setting (hardcoded initial menu)                        | 30m       | 1.2          |
| 1.5 | Basic bid submission (equal split across needed ingredients) | 1h        | 1.2          |
| 1.6 | Event logging (JSONL)                                        | 30m       | 1.1          |

**Milestone**: Can participate in a game turn, serve clients, generate revenue.

### Priority 2 — Intelligence Layer (Competitive Advantage)

| #   | Task                                          | Time Est. | Dependencies |
| --- | --------------------------------------------- | --------- | ------------ |
| 2.1 | Data collector (end-of-turn snapshot polling) | 1h        | 1.6          |
| 2.2 | Competitor feature extraction (14-dim vector) | 2h        | 2.1          |
| 2.3 | Behavioral embedding (PCA/UMAP)               | 1h        | 2.2          |
| 2.4 | Cluster classification (5 types)              | 1h        | 2.3          |
| 2.5 | Trajectory prediction                         | 1h        | 2.2          |
| 2.6 | ILP bid optimization                          | 2h        | 2.2          |
| 2.7 | ILP menu optimization (zone-specific)         | 2h        | 2.4          |

**Milestone**: Optimal bidding and menu based on competitor analysis.

### Priority 3 — Client Profiling (Revenue Optimization)

| #   | Task                                            | Time Est. | Dependencies |
| --- | ----------------------------------------------- | --------- | ------------ |
| 3.1 | Client profile tracking (GlobalClientLibrary)   | 1h        | 1.3          |
| 3.2 | Intolerance detection (Bayesian model)          | 1.5h      | 3.1          |
| 3.3 | Client priority queue (archetype-based serving) | 30m       | 1.3          |
| 3.4 | Zone-specific client recommendations            | 1h        | 2.4, 3.1     |

**Milestone**: Safe, prioritized, archetype-aware serving.

### Priority 4 — Zone-Based Subagent System (Architecture)

| #   | Task                                   | Time Est. | Dependencies |
| --- | -------------------------------------- | --------- | ------------ |
| 4.1 | Zone definitions + subagent prompts    | 1h        | None         |
| 4.2 | SubagentRouter with ILP zone selection | 2h        | 2.4, 2.7     |
| 4.3 | Per-zone Memory contexts               | 1h        | 4.1          |
| 4.4 | Dynamic zone switching between turns   | 1h        | 4.2, 4.3     |

**Milestone**: System dynamically switches strategy based on competitive landscape.

### Priority 5 — Orchestration (Deception Layer)

| #   | Task                                    | Time Est. | Dependencies |
| --- | --------------------------------------- | --------- | ------------ |
| 5.1 | Diplomacy agent (basic message sending) | 1h        | 1.2          |
| 5.2 | DeceptionBandit (Thompson Sampling)     | 1.5h      | 2.4, 5.1     |
| 5.3 | PseudoGAN (message quality scoring)     | 1.5h      | 5.1          |
| 5.4 | GroundTruthFirewall (defense)           | 1h        | 2.1          |

**Milestone**: Sophisticated diplomacy with automated message crafting and defense.

### Priority 6 — Polish & Visualization

| #   | Task                                     | Time Est. | Dependencies |
| --- | ---------------------------------------- | --------- | ------------ |
| 6.1 | Live 2D scatter plot (matplotlib/plotly) | 2h        | 2.3          |
| 6.2 | Trajectory trails + collision arrows     | 1h        | 2.5, 6.1     |
| 6.3 | Monitoring integration (ContextTracing)  | 1h        | All          |
| 6.4 | Pitch slides preparation                 | 2h        | 6.1          |

---

## 15. Technical Stack Summary

| Component                | Technology                                              | Why                                    |
| ------------------------ | ------------------------------------------------------- | -------------------------------------- |
| **Framework**            | datapizza-ai v0.0.9                                     | Mandatory                              |
| **LLM (reasoning)**      | Regolo.ai `gpt-oss-120b` via `OpenAILikeClient`         | Primary model for subagents            |
| **LLM (fast/parsing)**   | Regolo.ai `gpt-oss-20b` via `OpenAILikeClient`          | Order parsing, PseudoGAN discriminator |
| **Behavioral embedding** | numpy + sklearn PCA/UMAP                                | Fast, local, no API calls              |
| **ILP solver**           | scipy.optimize.milp                                     | Exact optimal solution in <1s          |
| **Bandit**               | scipy.stats.beta (Thompson Sampling)                    | Deception arm selection                |
| **Competitor modeling**  | numpy weighted statistics                               | Simple, interpretable                  |
| **Event bus**            | Custom ReactiveEventBus + aiohttp SSE                   | Async event dispatch                   |
| **Game communication**   | SSE listener + MCP JSON-RPC via aiohttp                 | As required by spec                    |
| **Data storage**         | JSONL files + in-memory dicts                           | Simple, fast, debuggable               |
| **Monitoring**           | datapizza.tracing.ContextTracing + Datapizza Monitoring | Built-in observability                 |
| **Visualization**        | matplotlib / plotly                                     | Pitch presentation                     |

---

## Appendix A: Key Constants

```python
# Team
TEAM_ID = 17
TEAM_NAME = "SPAM!"
API_KEY = "dTpZhKpZ02-4ac2be8821b52df78bf06070"

# Server
BASE_URL = "https://hackapizza.datapizza.tech"
SSE_URL = f"{BASE_URL}/events/{TEAM_ID}"
MCP_URL = f"{BASE_URL}/mcp"

# LLM
REGOLO_BASE_URL = "https://api.regolo.ai/v1"
REGOLO_API_KEY = os.getenv("REGOLO_API_KEY")
PRIMARY_MODEL = "gpt-oss-120b"
FAST_MODEL = "gpt-oss-20b"
VISION_MODEL = "qwen3-vl-32b"

# Headers
HEADERS = {
    "x-api-key": API_KEY,
    "Content-Type": "application/json",
}

# Zones
ZONES = [
    "PREMIUM_MONOPOLIST",
    "BUDGET_OPPORTUNIST",
    "NICHE_SPECIALIST",
    "SPEED_CONTENDER",
    "MARKET_ARBITRAGEUR",
]

# Archetype price ceilings (estimated)
ARCHETYPE_CEILINGS = {
    "Esploratore Galattico": 50,
    "Astrobarone": 200,
    "Saggi del Cosmo": 250,
    "Famiglie Orbitali": 120,
}

# High-Δ ingredients
HIGH_DELTA_INGREDIENTS = [
    ("Polvere di Crononite", 9.9),
    ("Shard di Prisma Stellare", 8.8),
    ("Lacrime di Andromeda", 8.3),
    ("Essenza di Tachioni", 6.0),
]
```

## Appendix B: File Structure (Proposed)

```
SPAM/
├── _docs/
│   ├── Hackapizza_instructions.md
│   ├── api_reference.md
│   ├── vectorization_strategy.md
│   ├── implementation_strategy.md      ← THIS FILE
│   └── customers_info/
│       ├── clients_comprehensive_report.md
│       └── dialogue_retrieval_report.md
├── templates/
│   └── client_template.py
├── Datapizza_docs/
│   └── ...
├── src/
│   ├── main.py                         # Entry point: SSE + event bus
│   ├── config.py                       # Constants, API keys
│   ├── event_bus.py                    # ReactiveEventBus
│   ├── phase_router.py                 # Phase state machine
│   ├── serving/
│   │   ├── pipeline.py                 # ServingPipeline
│   │   ├── order_matcher.py            # 3-tier dish matching
│   │   ├── priority_queue.py           # ClientPriorityQueue
│   │   └── intolerance.py              # IntoleranceDetector
│   ├── intelligence/
│   │   ├── data_collector.py           # GET endpoint polling
│   │   ├── feature_extractor.py        # 14-dim feature vector
│   │   ├── embedding.py                # PCA/UMAP
│   │   ├── trajectory.py               # TrajectoryPredictor
│   │   ├── cluster.py                  # Competitor classification
│   │   └── pipeline.py                 # DagPipeline wiring
│   ├── decision/
│   │   ├── ilp_solver.py               # ILP bid/menu optimization
│   │   ├── zone_selector.py            # ILP zone classification
│   │   ├── subagent_router.py          # SubagentRouter
│   │   └── pricing.py                  # Menu pricing logic
│   ├── diplomacy/
│   │   ├── deception_bandit.py         # Thompson Sampling
│   │   ├── pseudo_gan.py               # Message quality optimization
│   │   ├── firewall.py                 # GroundTruthFirewall
│   │   └── agent.py                    # DiplomacyAgent
│   ├── memory/
│   │   ├── game_state.py               # GameStateMemory
│   │   ├── competitor.py               # CompetitorMemory
│   │   ├── client_profile.py           # ClientProfileMemory
│   │   ├── message_log.py              # MessageMemory
│   │   └── event_log.py                # JSONL EventLog
│   └── visualization/
│       └── scatter.py                  # Live 2D scatter plot
└── tests/
    └── ...
```

---

_This document supersedes vectorization_strategy.md as the active implementation plan. The vectorization document remains valid for its core concepts (behavioral embedding, trajectory prediction, silent orchestration) which are incorporated here without modification._
