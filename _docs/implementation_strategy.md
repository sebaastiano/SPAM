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

The `client_spawned` SSE event gives us only two fields (confirmed by INSTR, API, and TEMPLATE):

- `clientName` — string (assumed to map to archetype names, but **not confirmed** by any source)
- `orderText` — string (natural language order)

**Critical:** `client_id` (required by `serve_dish`) is **NOT** included in `client_spawned`. It must be retrieved via `GET /meals?turn_id=<id>&restaurant_id=17`, which returns client requests with their respective IDs plus an `executed` boolean. This means we must poll `/meals` during the serving phase to obtain `client_id` before we can call `serve_dish`.

> **✅ CONFIRMED (28 Feb 2026):** `client_id` is definitively sourced from `GET /meals`. The `client_spawned` SSE event contains only `clientName` and `orderText` — no `client_id`. The API reference note labelling it `"CLIENT_ID_FROM_SSE"` is misleading; the endpoint `/meals` is the one and only source at runtime.

Additionally, no source confirms that `clientName` values map directly to the 4 archetype names (Esploratore Galattico, Astrobarone, Saggi del Cosmo, Famiglie Orbitali). We must handle unknown/unexpected `clientName` values gracefully.

> **✅ CONFIRMED (28 Feb 2026) — Missing `new_message` handler in `client_template.py`:** The base `EVENT_HANDLERS` dict in `client_template.py` is missing the `"new_message"` entry. Inter-team messages arrive as a `new_message` SSE event, **not** as `"message"`. Without this handler, all incoming diplomatic messages from other teams are silently dropped. The fix is:
>
> ```python
> EVENT_HANDLERS: dict[str, Callable[[dict[str, Any]], Awaitable[None]]] = {
>     "game_started": game_started,
>     "game_phase_changed": game_phase_changed,
>     "game_reset": game_reset,
>     "client_spawned": client_spawned,
>     "preparation_complete": preparation_complete,
>     "message": message,
>     "new_message": new_message,   # ← REQUIRED — handles inter-team messages
> }
> ```
>
> A corresponding `async def new_message(data: dict[str, Any]) -> None:` handler must also be implemented to process the payload.

Across turns we can **observe patterns** and build profiles:

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

### 6.1 Observable Data Inventory — What We Can See

The `tracker.py` service polls the game server every 5 seconds and records per-restaurant diffs. Combined with `GET /bid_history` and `GET /market/entries`, we reconstruct a near-complete picture of every competitor **every turn**. Below is the exhaustive mapping of observable fields to strategic uses.

#### Raw fields from `GET /restaurants` (polled every 5s, publicly visible for ALL teams)

| Field              | Type                | What it reveals                                      | Strategic use                                     |
| ------------------ | ------------------- | ---------------------------------------------------- | ------------------------------------------------- |
| `balance`          | float               | Exact spending power                                 | Bid ceiling prediction, threat assessment         |
| `inventory`        | dict[str, int]      | **Exact ingredient holdings** — names and quantities | Recipe inference, bid prediction, menu prediction |
| `reputation`       | float               | Current prestige score                               | Archetype attractiveness modeling                 |
| `isOpen`           | bool                | Currently serving?                                   | Competitive density during serving                |
| `menu` → items     | list[{name, price}] | **Full menu with prices**                            | Price positioning, archetype targeting inference  |
| `kitchen`          | list/dict           | Dishes currently being cooked (count visible)        | Throughput estimation, serving capacity           |
| `receivedMessages` | int/list            | Message count (tells us who's talking to whom)       | Diplomacy graph reconstruction                    |

#### Raw fields from `GET /bid_history?turn_id=X` (all teams' bids, post-auction)

| Field           | Type  | What it reveals                |
| --------------- | ----- | ------------------------------ |
| `restaurant_id` | int   | Who bid                        |
| `ingredient`    | str   | What they bid on               |
| `quantity`      | int   | How much they wanted           |
| `bid`           | float | How much they offered per unit |
| `status`        | str   | Won or lost the bid            |

#### Raw fields from `GET /market/entries` (real-time, all teams)

| Field                    | Type     | What it reveals                  |
| ------------------------ | -------- | -------------------------------- |
| `side`                   | BUY/SELL | Are they surplus or deficit?     |
| `ingredient_name`        | str      | Which ingredient they're trading |
| `quantity`               | int      | How much                         |
| `price`                  | float    | At what price                    |
| `seller_id` / `buyer_id` | int      | Who posted it                    |
| `status`                 | str      | ACTIVE / COMPLETED / CANCELLED   |

#### Tracker diff engine — what changes between polls

The tracker's `diff_dict()` function detects field-level changes every 5s. This means we observe the _exact timestamp_ of:

- Balance drops (they paid for something) or rises (they served a client)
- Inventory additions (bid won) and depletions (dish cooked)
- Menu changes (added/removed dishes, price adjustments)
- Kitchen activity (dishes entering/leaving cooking)
- Open/close state transitions
- Reputation changes (successful/failed serves)

This gives us **intra-turn temporal resolution**, not just end-of-turn snapshots.

### 6.2 Per-Competitor State Reconstruction

From the raw observables above, we reconstruct a complete strategic profile per competitor per turn:

```python
@dataclass
class CompetitorTurnState:
    """Complete reconstructed state of a competitor for one turn."""
    restaurant_id: int
    turn_id: int
    name: str

    # Direct observables (from GET /restaurants)
    balance: float
    balance_delta: float               # vs. previous turn
    inventory: dict[str, int]          # exact ingredient holdings
    menu: dict[str, float]             # dish_name → price
    reputation: float
    reputation_delta: float
    is_open: bool
    kitchen_load: int                  # number of dishes being cooked

    # Derived from bid_history
    bids: list[dict]                   # this turn's bids
    total_bid_spend: float             # Σ(bid × quantity) for won bids
    bid_ingredients: set[str]          # which ingredients they targeted
    bid_win_rate: float                # won / total bids
    avg_bid_price: float               # average bid per ingredient unit

    # Derived from market/entries
    market_buys: list[dict]            # BUY entries this turn
    market_sells: list[dict]           # SELL entries this turn
    market_net_spend: float            # buys - sells

    # Derived from inventory diffs (intra-turn from tracker)
    ingredients_consumed: dict[str, int]  # inventory drops during serving
    ingredients_acquired: dict[str, int]  # inventory gains post-bid

    # Inferred
    inferred_recipes_cooked: list[str]    # matched against recipe DB
    inferred_revenue: float               # balance_delta + total_bid_spend + market_net_spend
    inferred_clients_served: int          # from balance increase pattern + kitchen activity
    inferred_strategy: str                # cluster assignment


class CompetitorStateBuilder:
    """
    Builds CompetitorTurnState from tracker observables.

    Data sources:
     - GET /restaurants (every 5s via tracker polling)
     - GET /bid_history?turn_id=X (post-auction)
     - GET /market/entries (real-time)
     - Tracker diff log (intra-turn changes)
    """

    def __init__(self, recipe_db: dict[str, dict]):
        self.recipe_db = recipe_db  # recipe_name → {ingredients: {name: qty}, ...}
        self.history: dict[int, list[CompetitorTurnState]] = {}  # rid → turns

    def build_turn_state(
        self,
        rid: int,
        turn_id: int,
        restaurant_data: dict,        # from GET /restaurants
        bid_data: list[dict],         # from GET /bid_history filtered by rid
        market_data: list[dict],      # from GET /market/entries filtered by rid
        prev_state: "CompetitorTurnState | None",
        diff_log: list[dict],         # from tracker change events for this rid
    ) -> CompetitorTurnState:

        balance = restaurant_data.get("balance", 0)
        inventory = restaurant_data.get("inventory", {})
        reputation = restaurant_data.get("reputation", 100)

        prev_balance = prev_state.balance if prev_state else balance
        prev_reputation = prev_state.reputation if prev_state else reputation
        prev_inventory = prev_state.inventory if prev_state else {}

        # Reconstruct inventory movements from diffs
        ingredients_consumed = {}
        ingredients_acquired = {}
        for ing, old_qty in prev_inventory.items():
            new_qty = inventory.get(ing, 0)
            if new_qty < old_qty:
                ingredients_consumed[ing] = old_qty - new_qty
            elif new_qty > old_qty:
                ingredients_acquired[ing] = new_qty - old_qty
        for ing, new_qty in inventory.items():
            if ing not in prev_inventory and new_qty > 0:
                ingredients_acquired[ing] = new_qty

        # Infer which recipes were cooked by matching consumed ingredients
        inferred_recipes = self._match_consumed_to_recipes(ingredients_consumed)

        # Bid analysis
        team_bids = [b for b in bid_data if b.get("restaurant_id") == rid]
        won_bids = [b for b in team_bids if b.get("status") == "completed"]
        total_bid_spend = sum(b["bid"] * b["quantity"] for b in won_bids)

        # Market analysis
        team_market_buys = [e for e in market_data
                           if e.get("side") == "BUY" and e.get("buyer_id") == rid]
        team_market_sells = [e for e in market_data
                            if e.get("side") == "SELL" and e.get("seller_id") == rid]

        # Revenue inference: balance_delta = revenue - bid_spend - market_net
        market_net = (sum(e["price"] * e["quantity"] for e in team_market_buys)
                    - sum(e["price"] * e["quantity"] for e in team_market_sells))
        inferred_revenue = (balance - prev_balance) + total_bid_spend + market_net

        state = CompetitorTurnState(
            restaurant_id=rid,
            turn_id=turn_id,
            name=restaurant_data.get("name", f"team {rid}"),
            balance=balance,
            balance_delta=balance - prev_balance,
            inventory=inventory,
            menu=self._extract_menu(restaurant_data),
            reputation=reputation,
            reputation_delta=reputation - prev_reputation,
            is_open=restaurant_data.get("isOpen", False),
            kitchen_load=self._extract_kitchen_count(restaurant_data),
            bids=team_bids,
            total_bid_spend=total_bid_spend,
            bid_ingredients=set(b["ingredient"] for b in team_bids),
            bid_win_rate=len(won_bids) / max(len(team_bids), 1),
            avg_bid_price=total_bid_spend / max(sum(b["quantity"] for b in won_bids), 1),
            market_buys=team_market_buys,
            market_sells=team_market_sells,
            market_net_spend=market_net,
            ingredients_consumed=ingredients_consumed,
            ingredients_acquired=ingredients_acquired,
            inferred_recipes_cooked=inferred_recipes,
            inferred_revenue=inferred_revenue,
            inferred_clients_served=max(0, int(inferred_revenue / 100)),  # rough estimate
            inferred_strategy="unclassified",  # filled by cluster classifier
        )

        self.history.setdefault(rid, []).append(state)
        return state

    def _match_consumed_to_recipes(self, consumed: dict[str, int]) -> list[str]:
        """
        Given ingredients consumed this turn, find which recipes they could have cooked.

        Uses subset matching: a recipe is a candidate if its ingredient set
        is a subset of the consumed ingredients (accounting for quantities).
        """
        candidates = []
        remaining = dict(consumed)
        # Greedy: try most-ingredient recipes first (more constrained = more certain)
        sorted_recipes = sorted(
            self.recipe_db.items(),
            key=lambda r: len(r[1].get("ingredients", {})),
            reverse=True
        )
        for recipe_name, recipe in sorted_recipes:
            ingredients = recipe.get("ingredients", {})
            if all(remaining.get(ing, 0) >= qty for ing, qty in ingredients.items()):
                candidates.append(recipe_name)
                for ing, qty in ingredients.items():
                    remaining[ing] = remaining.get(ing, 0) - qty
        return candidates

    def _extract_menu(self, r: dict) -> dict[str, float]:
        raw_menu = r.get("menu") or {}
        if isinstance(raw_menu, dict):
            items = raw_menu.get("items") or []
        elif isinstance(raw_menu, list):
            items = raw_menu
        else:
            items = []
        return {item.get("name"): item.get("price") for item in items if isinstance(item, dict)}

    def _extract_kitchen_count(self, r: dict) -> int:
        k = r.get("kitchen") or []
        return len(k) if isinstance(k, (list, dict)) else 0
```

### 6.3 Strategy Inference Engine

By combining multiple observable signals, we can **infer** which strategy a competitor is following — even though we never see their code or their client orders.

```python
class StrategyInferrer:
    """
    Infer competitor strategy from observable patterns.

    Each inference rule maps observable signals → strategy hypothesis
    with a confidence score. Multiple rules can fire; the highest-confidence
    hypothesis wins.
    """

    def infer(self, state: CompetitorTurnState, history: list[CompetitorTurnState]) -> dict:
        """Returns {strategy: str, confidence: float, evidence: list[str]}."""

        hypotheses = []

        # ── Premium strategy detection ──
        if state.menu:
            avg_price = sum(state.menu.values()) / len(state.menu)
            menu_size = len(state.menu)
            if avg_price > 150 and menu_size <= 5:
                hypotheses.append({
                    "strategy": "PREMIUM_MONOPOLIST",
                    "confidence": min(0.9, avg_price / 250),
                    "evidence": [
                        f"avg_price={avg_price:.0f} (>150)",
                        f"menu_size={menu_size} (≤5)",
                    ]
                })

        # ── Budget/volume strategy detection ──
        if state.menu:
            avg_price = sum(state.menu.values()) / len(state.menu)
            menu_size = len(state.menu)
            if avg_price < 100 and menu_size >= 6:
                hypotheses.append({
                    "strategy": "BUDGET_OPPORTUNIST",
                    "confidence": min(0.85, menu_size / 15),
                    "evidence": [
                        f"avg_price={avg_price:.0f} (<100)",
                        f"menu_size={menu_size} (≥6)",
                    ]
                })

        # ── Aggressive hoarding detection ──
        if len(history) >= 2:
            recent_bid_spend = sum(s.total_bid_spend for s in history[-2:])
            recent_balance_drop = history[-2].balance - state.balance
            if recent_bid_spend > state.balance * 0.3:
                hypotheses.append({
                    "strategy": "AGGRESSIVE_HOARDER",
                    "confidence": min(0.8, recent_bid_spend / state.balance),
                    "evidence": [
                        f"bid_spend_ratio={recent_bid_spend/max(state.balance,1):.2f}",
                        f"balance_trend=declining",
                    ]
                })

        # ── Market arbitrageur detection ──
        if len(state.market_buys) + len(state.market_sells) > 3:
            if len(state.menu) <= 2:
                hypotheses.append({
                    "strategy": "MARKET_ARBITRAGEUR",
                    "confidence": 0.7,
                    "evidence": [
                        f"market_entries={len(state.market_buys)+len(state.market_sells)}",
                        f"menu_size={len(state.menu)} (≤2)",
                    ]
                })

        # ── Reactive chaser detection (menu mimics successful competitors) ──
        if len(history) >= 3:
            menu_changes = sum(1 for i in range(1, len(history))
                             if history[i].menu != history[i-1].menu)
            if menu_changes >= len(history) * 0.6:
                hypotheses.append({
                    "strategy": "REACTIVE_CHASER",
                    "confidence": min(0.75, menu_changes / len(history)),
                    "evidence": [
                        f"menu_change_rate={menu_changes/len(history):.2f}",
                    ]
                })

        # ── Declining / inactive detection ──
        if len(history) >= 2:
            if state.balance_delta < 0 and state.reputation_delta <= 0:
                consecutive_losses = 0
                for s in reversed(history):
                    if s.balance_delta < 0:
                        consecutive_losses += 1
                    else:
                        break
                if consecutive_losses >= 2:
                    hypotheses.append({
                        "strategy": "DECLINING",
                        "confidence": min(0.9, consecutive_losses * 0.3),
                        "evidence": [
                            f"consecutive_losses={consecutive_losses}",
                            f"balance_delta={state.balance_delta}",
                            f"reputation_delta={state.reputation_delta}",
                        ]
                    })

        # ── Dormant detection (never opened, still at default balance) ──
        if not state.is_open and len(state.menu) == 0 and state.balance >= 7500:
            hypotheses.append({
                "strategy": "DORMANT",
                "confidence": 0.95,
                "evidence": ["never_opened", f"balance={state.balance}"]
            })

        if not hypotheses:
            return {"strategy": "UNCLASSIFIED", "confidence": 0.0, "evidence": []}

        return max(hypotheses, key=lambda h: h["confidence"])
```

### 6.4 Behavioral Embedding (Extended from vectorization_strategy.md)

The 14-feature vector is now computed directly from `CompetitorTurnState`, grounding every feature in a concrete observable:

```python
import numpy as np

def extract_feature_vector(state: CompetitorTurnState, history: list[CompetitorTurnState]) -> np.ndarray:
    """
    Compute 14-dim behavioral feature vector from tracker observables.

    Every feature maps to a concrete field from GET /restaurants,
    GET /bid_history, or GET /market/entries.
    """

    # ── Auction behavior (from bid_history) ──
    bid_aggressiveness = state.total_bid_spend / max(state.balance, 1)
    bid_ingredients_set = state.bid_ingredients
    bid_concentration = _gini([b["quantity"] for b in state.bids]) if state.bids else 0
    bid_volume = len(bid_ingredients_set)
    bid_consistency = 0.0
    if len(history) >= 2 and history[-1].bid_ingredients:
        bid_consistency = len(bid_ingredients_set & history[-1].bid_ingredients) / max(
            len(bid_ingredients_set | history[-1].bid_ingredients), 1
        )

    # ── Menu behavior (from GET /restaurants → menu) ──
    avg_price = np.mean(list(state.menu.values())) if state.menu else 0
    global_avg_price = 120  # updated each turn from all competitors
    price_positioning = avg_price / max(global_avg_price, 1)
    menu_stability = 1.0
    if len(history) >= 1:
        prev_dishes = set(history[-1].menu.keys())
        curr_dishes = set(state.menu.keys())
        union = prev_dishes | curr_dishes
        menu_stability = len(prev_dishes & curr_dishes) / max(len(union), 1)
    specialization_depth = 1.0 / max(len(state.menu), 1)

    # ── Market behavior (from GET /market/entries) ──
    total_turns = max(state.turn_id, 1)
    market_activity = (len(state.market_buys) + len(state.market_sells)) / total_turns
    buy_sell_ratio = len(state.market_buys) / max(len(state.market_sells) + 1, 1)

    # ── Outcome signals (from GET /restaurants → balance, reputation) ──
    balance_growth_rate = state.balance_delta
    reputation_rate = state.reputation_delta

    # ── Recipe & prestige signals (inferred from consumed ingredients) ──
    prestige_targeting = 0
    recipe_complexity = 0
    if state.inferred_recipes_cooked:
        # Look up prestige from recipe DB
        prestiges = []  # filled from recipe_db
        complexities = []
        prestige_targeting = np.mean(prestiges) if prestiges else 0
        recipe_complexity = np.mean(complexities) if complexities else 0

    return np.array([
        bid_aggressiveness,
        bid_concentration,
        bid_consistency,
        bid_volume,
        price_positioning,
        menu_stability,
        specialization_depth,
        market_activity,
        buy_sell_ratio,
        balance_growth_rate,
        reputation_rate,
        prestige_targeting,
        recipe_complexity,
        len(state.menu),  # raw menu size as signal
    ])

def _gini(values: list[float]) -> float:
    """Gini coefficient — 0=equal, 1=concentrated."""
    if not values or sum(values) == 0:
        return 0
    sorted_v = sorted(values)
    n = len(sorted_v)
    numerator = sum((2 * i - n - 1) * v for i, v in enumerate(sorted_v, 1))
    return numerator / (n * sum(sorted_v))
```

After 3–4 turns → matrix `(n_restaurants × 14 × n_turns)` → PCA for visualization, UMAP for clustering.

### 6.5 Competitor Cluster Classification

```
CLUSTER                  RELATIONAL STRATEGY        ORCHESTRATION MOVE
──────────────────────────────────────────────────────────────────────
Stable Specialist        Coexist                    Reinforce their niche
Reactive Chaser          Generous Tit-for-Tat       Feed slightly wrong signals
Aggressive Hoarder       Targeted Spoiler           Bid-deny their top 2 items
Weak / Declining         Ignore                     Offer cheap alliance
Dormant                  Monitor only               No action until they wake
Unclassified / New       Probe                      1 cooperative message, classify reply
```

### 6.6 Advanced Trajectory Prediction (Tracker-Powered)

The trajectory predictor operates on two levels:

1. **Feature-space trajectory** — momentum-based prediction in 14-dim embedding space (where is this competitor heading in strategic terms?)
2. **Observable-field trajectory** — direct prediction of concrete fields (what will their balance, inventory, and menu look like next turn?)

The second level is unique to our architecture because the tracker gives us field-level diffs with intra-turn temporal resolution.

```python
import numpy as np
from dataclasses import dataclass

@dataclass
class CompetitorPrediction:
    """Predicted state of a competitor for next turn."""
    restaurant_id: int
    predicted_balance: float
    predicted_bid_ingredients: set[str]     # what they'll likely bid on
    predicted_bid_spend: float              # how much they'll likely spend
    predicted_menu_changes: list[str]       # dishes likely added/removed
    predicted_strategy: str                 # inferred strategy continuation
    predicted_feature_vector: np.ndarray    # 14-dim embedding position
    threat_level: float                     # 0-1, how much they threaten our zone
    opportunity_level: float                # 0-1, how exploitable they are

    # Actionable intelligence
    vulnerable_ingredients: list[str]       # ingredients we could deny them
    bid_denial_cost: float                 # estimated cost to outbid them
    menu_overlap: float                     # 0-1, how much their menu overlaps ours


class AdvancedTrajectoryPredictor:
    """
    Multi-level trajectory prediction powered by tracker observables.

    Level 1: Feature-space trajectory (embedding momentum)
    Level 2: Observable-field prediction (concrete balance/inventory/bid forecasts)
    Level 3: Behavioral pattern detection (strategy switches, alliance formation)
    """

    def __init__(self, recipe_db: dict, momentum_factor: float = 0.7):
        self.momentum_factor = momentum_factor
        self.recipe_db = recipe_db
        self.feature_history: dict[int, list[np.ndarray]] = {}
        self.state_history: dict[int, list[CompetitorTurnState]] = {}

    def update(self, rid: int, state: CompetitorTurnState, features: np.ndarray):
        self.feature_history.setdefault(rid, []).append(features)
        self.state_history.setdefault(rid, []).append(state)

    def predict(self, rid: int) -> CompetitorPrediction:
        states = self.state_history.get(rid, [])
        features = self.feature_history.get(rid, [])
        if not states:
            raise ValueError(f"No history for restaurant {rid}")

        current = states[-1]

        # ── Level 1: Feature-space momentum ──
        predicted_features = self._predict_features(features)

        # ── Level 2: Observable field predictions ──
        predicted_balance = self._predict_balance(states)
        predicted_bids = self._predict_bid_targets(states)
        predicted_bid_spend = self._predict_bid_spend(states)
        predicted_menu = self._predict_menu_changes(states)

        # ── Level 3: Behavioral pattern detection ──
        strategy = self._detect_strategy_trend(states)
        threat = self._compute_threat_level(states, predicted_bids)
        opportunity = self._compute_opportunity_level(states)

        # ── Actionable intelligence ──
        vulnerable = self._find_vulnerable_ingredients(states)
        denial_cost = self._estimate_denial_cost(states, vulnerable)
        overlap = self._compute_menu_overlap(current)

        return CompetitorPrediction(
            restaurant_id=rid,
            predicted_balance=predicted_balance,
            predicted_bid_ingredients=predicted_bids,
            predicted_bid_spend=predicted_bid_spend,
            predicted_menu_changes=predicted_menu,
            predicted_strategy=strategy,
            predicted_feature_vector=predicted_features,
            threat_level=threat,
            opportunity_level=opportunity,
            vulnerable_ingredients=vulnerable,
            bid_denial_cost=denial_cost,
            menu_overlap=overlap,
        )

    ### Level 1: Feature-space momentum

    def _predict_features(self, features: list[np.ndarray]) -> np.ndarray:
        if len(features) < 2:
            return features[-1]
        velocity = features[-1] - features[-2]
        if len(features) >= 3:
            prev_velocity = features[-2] - features[-3]
            velocity = self.momentum_factor * velocity + (1 - self.momentum_factor) * prev_velocity
        return features[-1] + velocity

    ### Level 2: Observable field predictions

    def _predict_balance(self, states: list[CompetitorTurnState]) -> float:
        """Predict next-turn balance from delta trend."""
        if len(states) < 2:
            return states[-1].balance
        # Exponentially weighted moving average of deltas
        deltas = [s.balance_delta for s in states[-5:]]
        weights = [0.5 ** (len(deltas) - 1 - i) for i in range(len(deltas))]
        predicted_delta = np.average(deltas, weights=weights)
        return states[-1].balance + predicted_delta

    def _predict_bid_targets(self, states: list[CompetitorTurnState]) -> set[str]:
        """
        Predict which ingredients they'll bid on next turn.

        Logic:
        1. Ingredients they've bid on 2+ consecutive turns = very likely again
        2. Ingredients in their current menu recipes but NOT in inventory = must-bid
        3. New ingredients appearing in their recent menu changes = emerging targets
        """
        if not states:
            return set()

        # Frequency: ingredients bid on in last 3 turns
        recent_bids: dict[str, int] = {}
        for s in states[-3:]:
            for ing in s.bid_ingredients:
                recent_bids[ing] = recent_bids.get(ing, 0) + 1

        # Consistency: bid on 2+ of last 3 turns = almost certain
        consistent = {ing for ing, count in recent_bids.items() if count >= 2}

        # Menu-driven: look up ingredients needed for their current menu dishes
        menu_needed = set()
        for dish_name in states[-1].menu:
            recipe = self.recipe_db.get(dish_name, {})
            for ing in recipe.get("ingredients", {}):
                if ing not in states[-1].inventory or states[-1].inventory.get(ing, 0) == 0:
                    menu_needed.add(ing)

        return consistent | menu_needed

    def _predict_bid_spend(self, states: list[CompetitorTurnState]) -> float:
        """Predict total bid expenditure next turn."""
        if len(states) < 2:
            return states[-1].total_bid_spend
        spends = [s.total_bid_spend for s in states[-3:]]
        return np.mean(spends) * 1.05  # slight upward bias (competition intensifies)

    def _predict_menu_changes(self, states: list[CompetitorTurnState]) -> list[str]:
        """Predict which dishes will be added/removed."""
        if len(states) < 2:
            return []
        curr = set(states[-1].menu.keys())
        prev = set(states[-2].menu.keys())
        # If they're a Reactive Chaser, they'll likely change again
        if states[-1].inferred_strategy == "REACTIVE_CHASER":
            return list(curr - prev)  # new additions likely to churn
        return []  # stable strategies keep menus

    ### Level 3: Behavioral pattern detection

    def _detect_strategy_trend(self, states: list[CompetitorTurnState]) -> str:
        """Detect if a competitor is switching strategy."""
        if len(states) < 3:
            return states[-1].inferred_strategy

        recent_strategies = [s.inferred_strategy for s in states[-3:]]
        if len(set(recent_strategies)) == 1:
            return recent_strategies[0]  # stable
        # If strategy changed in last turn, flag as transitioning
        if recent_strategies[-1] != recent_strategies[-2]:
            return f"TRANSITIONING→{recent_strategies[-1]}"
        return recent_strategies[-1]

    def _compute_threat_level(self, states: list[CompetitorTurnState],
                               predicted_bids: set[str]) -> float:
        """
        How much does this competitor threaten our current zone?

        Threat = f(menu_overlap, bid_overlap, balance_advantage, reputation)
        """
        current = states[-1]
        threat = 0.0

        # Menu overlap — are they targeting the same archetypes?
        overlap = self._compute_menu_overlap(current)
        threat += overlap * 0.4

        # Bid overlap — are they competing for the same ingredients?
        # (computed against our own bid targets, injected at call time)
        threat += 0.3 if len(predicted_bids) > 5 else 0.1

        # Balance advantage — can they outbid us?
        if current.balance > 7000:
            threat += 0.2
        elif current.balance > 5000:
            threat += 0.1

        # Reputation — are they attracting our target clients?
        if current.reputation > 90:
            threat += 0.1

        return min(1.0, threat)

    def _compute_opportunity_level(self, states: list[CompetitorTurnState]) -> float:
        """
        How exploitable is this competitor?

        Opportunity = f(declining_balance, low_reputation, reactive_behavior, desperation)
        """
        current = states[-1]
        opportunity = 0.0

        # Declining balance = desperate
        if len(states) >= 2 and states[-1].balance_delta < -200:
            opportunity += 0.3
        if current.balance < 4000:
            opportunity += 0.2

        # Low reputation = losing clients
        if current.reputation < 80:
            opportunity += 0.2

        # Reactive behavior = easily manipulated
        if current.inferred_strategy == "REACTIVE_CHASER":
            opportunity += 0.3

        return min(1.0, opportunity)

    def _find_vulnerable_ingredients(self, states: list[CompetitorTurnState]) -> list[str]:
        """
        Which ingredients could we deny this competitor?

        An ingredient is "vulnerable" if:
        1. They bid on it consistently (need it for their menu)
        2. They bid near the minimum (not willing to pay much)
        3. We could outbid them without hurting ourselves
        """
        if not states:
            return []

        # Ingredients they consistently bid on at low prices
        ingredient_bids: dict[str, list[float]] = {}
        for s in states[-3:]:
            for b in s.bids:
                ing = b.get("ingredient", "")
                ingredient_bids.setdefault(ing, []).append(b.get("bid", 0))

        vulnerable = []
        for ing, prices in ingredient_bids.items():
            if len(prices) >= 2:  # consistent need
                avg_price = np.mean(prices)
                if avg_price < 100:  # low willingness to pay = deniable
                    vulnerable.append(ing)

        return vulnerable

    def _estimate_denial_cost(self, states: list[CompetitorTurnState],
                               vulnerable: list[str]) -> float:
        """How much would it cost us to outbid them on their vulnerable ingredients?"""
        total_cost = 0
        for s in states[-1:]:
            for b in s.bids:
                if b.get("ingredient") in vulnerable:
                    total_cost += (b.get("bid", 0) + 1) * b.get("quantity", 1)
        return total_cost

    def _compute_menu_overlap(self, state: CompetitorTurnState) -> float:
        """How much does their menu overlap with ours (by dish name)?"""
        # OUR_MENU is injected at runtime; here we check recipe overlap
        # via shared ingredients rather than name matching
        return 0.0  # computed at runtime with access to our current menu

    ### Aggregate methods

    def competitors_approaching_zone(self, zone_center: np.ndarray,
                                      threshold: float) -> list[int]:
        """Which competitors are moving toward a specific zone in embedding space?"""
        approaching = []
        for rid, features in self.feature_history.items():
            if len(features) < 2:
                continue
            predicted = self._predict_features(features)
            current_dist = np.linalg.norm(features[-1] - zone_center)
            predicted_dist = np.linalg.norm(predicted - zone_center)
            if predicted_dist < current_dist and predicted_dist < threshold:
                approaching.append(rid)
        return approaching

    def get_ingredient_demand_forecast(self) -> dict[str, float]:
        """
        Predict aggregate demand for each ingredient next turn.

        Sum of all competitors' predicted bid quantities = expected competition.
        High-demand ingredients need aggressive bids or should be avoided.
        """
        demand: dict[str, float] = {}
        for rid in self.state_history:
            predicted_bids = self._predict_bid_targets(self.state_history[rid])
            for ing in predicted_bids:
                # Weight by competitor's typical bid quantity
                recent_qty = 0
                for s in self.state_history[rid][-2:]:
                    for b in s.bids:
                        if b.get("ingredient") == ing:
                            recent_qty = max(recent_qty, b.get("quantity", 1))
                demand[ing] = demand.get(ing, 0) + max(recent_qty, 1)
        return demand

    def generate_per_competitor_briefing(self) -> dict[int, dict]:
        """
        Generate a tactical briefing for each competitor.
        Used by the DeceptionBandit to craft targeted messages
        and by the ILP Solver to set bid priorities.
        """
        briefings = {}
        for rid in self.state_history:
            prediction = self.predict(rid)
            states = self.state_history[rid]
            current = states[-1]

            briefings[rid] = {
                "name": current.name,
                "strategy": prediction.predicted_strategy,
                "threat_level": prediction.threat_level,
                "opportunity_level": prediction.opportunity_level,
                "balance": current.balance,
                "balance_trend": "rising" if current.balance_delta > 0 else "falling",
                "top_bid_ingredients": list(prediction.predicted_bid_ingredients)[:5],
                "predicted_bid_spend": prediction.predicted_bid_spend,
                "vulnerable_ingredients": prediction.vulnerable_ingredients,
                "bid_denial_cost": prediction.bid_denial_cost,
                "menu_price_avg": (np.mean(list(current.menu.values()))
                                   if current.menu else 0),
                "menu_size": len(current.menu),
                "reputation": current.reputation,
                "recommended_action": self._recommend_action(prediction, current),
            }
        return briefings

    def _recommend_action(self, prediction: CompetitorPrediction,
                           state: CompetitorTurnState) -> str:
        """Recommend a tactical action for this competitor."""
        if prediction.threat_level > 0.7:
            if prediction.bid_denial_cost < 200:
                return f"BID_DENY: outbid on {prediction.vulnerable_ingredients[:2]} (cost≈{prediction.bid_denial_cost:.0f})"
            return "ZONE_AVOID: too expensive to deny, consider zone switch"
        if prediction.opportunity_level > 0.6:
            if state.inferred_strategy == "REACTIVE_CHASER":
                return "DECEIVE: send misleading menu/ingredient signal"
            if state.inferred_strategy == "DECLINING":
                return "ALLIANCE: offer cheap ingredient trade"
        return "MONITOR: no immediate action needed"
```

### 6.7 Intelligence Pipeline as DagPipeline

Using datapizza-ai's `DagPipeline` to wire the complete intelligence flow, now including the strategy inferrer and advanced trajectory predictor:

```python
from datapizza.pipeline import DagPipeline

intel_pipeline = DagPipeline()

# Modules
intel_pipeline.add_module("data_collector", DataCollectorModule())          # GET /restaurants, /bid_history, /market/entries
intel_pipeline.add_module("state_builder", CompetitorStateBuilderModule())  # raw data → CompetitorTurnState per restaurant
intel_pipeline.add_module("feature_extractor", FeatureExtractorModule())    # CompetitorTurnState → 14-dim vector
intel_pipeline.add_module("strategy_inferrer", StrategyInferrerModule())    # observable patterns → strategy hypothesis
intel_pipeline.add_module("embedding", EmbeddingModule())                   # PCA/UMAP projection
intel_pipeline.add_module("trajectory", AdvancedTrajectoryModule())         # multi-level prediction
intel_pipeline.add_module("cluster", ClusterClassifierModule())             # 5-type classification
intel_pipeline.add_module("briefing_generator", BriefingGeneratorModule())  # per-competitor tactical briefings
intel_pipeline.add_module("zone_selector", ZoneSelectorModule())            # ILP zone classification

# Connections
intel_pipeline.connect("data_collector", "state_builder")
intel_pipeline.connect("state_builder", "feature_extractor")
intel_pipeline.connect("state_builder", "strategy_inferrer")
intel_pipeline.connect("feature_extractor", "embedding")
intel_pipeline.connect("feature_extractor", "trajectory")
intel_pipeline.connect("strategy_inferrer", "trajectory")
intel_pipeline.connect("embedding", "cluster")
intel_pipeline.connect("trajectory", "briefing_generator")
intel_pipeline.connect("cluster", "briefing_generator")
intel_pipeline.connect("trajectory", "zone_selector")
intel_pipeline.connect("cluster", "zone_selector")
intel_pipeline.connect("briefing_generator", "zone_selector")

# Run at the start of each turn
result = intel_pipeline.run({
    "data_collector": {"turn_id": current_turn}
})
active_zone = result["zone_selector"]
competitor_briefings = result["briefing_generator"]  # → feeds DeceptionBandit + ILP Solver
```

### 6.8 TrackerBridge — Live Data Connector

The `TrackerBridge` is the concrete interface between `tracker.py` (running as a sidecar on `localhost:5555`) and the intelligence pipeline. It replaces raw HTTP polling in the agent with structured queries to the tracker's pre-computed diffs and change logs.

**Why a bridge instead of direct polling?**

- tracker.py already polls `GET /restaurants` every 5 seconds — duplicating this in the agent wastes rate-limit budget
- tracker.py computes field-level diffs (via `diff_dict()`) — the agent gets change history for free
- tracker.py aggregates bid history, market entries, and meals in one place — single source of truth
- The agent only needs to query the tracker at decision points (start of turn), not continuously

**Architecture:**

```
tracker.py (port 5555)                   Agent (main.py)
┌─────────────────────────┐              ┌─────────────────────────────┐
│  _poll_restaurants()    │              │                             │
│  every 5s: GET /rest... │              │  TrackerBridge              │
│  → diff_dict()          │──────────────│    .fetch_all_states()      │
│  → change_log[]         │  HTTP GET    │    .fetch_change_log(rid)   │
│                         │  localhost   │    .fetch_bid_history()     │
│  _poll_bid_history()    │  :5555       │    .fetch_market_entries()  │
│  _poll_market()         │──────────────│    .snapshot()              │
│  _poll_meals()          │              │         │                   │
│                         │              │         ▼                   │
│  /api/restaurant/<rid>  │              │  CompetitorStateBuilder     │
│  /api/all_restaurants   │              │         │                   │
│  /api/bid_history       │              │         ▼                   │
│  /api/market            │              │  StrategyInferrer           │
│  /stream (SSE relay)    │              │  AdvancedTrajectoryPredictor│
└─────────────────────────┘              │  BriefingGenerator          │
                                         └─────────────────────────────┘
```

**Implementation:**

```python
import httpx
from dataclasses import dataclass
from typing import Optional

TRACKER_BASE = "http://localhost:5555"

@dataclass
class TrackerSnapshot:
    """Complete snapshot from tracker at a single point in time."""
    restaurants: dict[int, dict]       # rid → flattened restaurant data
    change_logs: dict[int, list]       # rid → list of {field, old, new, timestamp}
    bid_history: list[dict]            # all bids across all teams
    market_entries: list[dict]         # all market BUY/SELL entries
    own_meals: list[dict]              # our completed meals (GET /meals, own team only)
    timestamp: float                   # when snapshot was taken

class TrackerBridge:
    """
    Bridge between tracker.py sidecar and the agent's intelligence pipeline.

    tracker.py runs independently, polling the game server every 5s.
    This bridge queries tracker's local API at decision points to get
    pre-computed diffs and aggregated data.
    """

    def __init__(self, base_url: str = TRACKER_BASE, own_id: int = 17):
        self.base_url = base_url
        self.own_id = own_id
        self._client = httpx.AsyncClient(base_url=base_url, timeout=5.0)
        self._last_snapshot: Optional[TrackerSnapshot] = None

    async def snapshot(self) -> TrackerSnapshot:
        """
        Pull a complete snapshot from tracker.
        Called once at the start of each decision cycle (turn start / phase change).
        """
        # Parallel fetch from all tracker endpoints
        import asyncio
        restaurants_task = self._fetch_all_restaurants()
        bids_task = self._fetch_bid_history()
        market_task = self._fetch_market_entries()
        meals_task = self._fetch_own_meals()

        restaurants, bids, market, meals = await asyncio.gather(
            restaurants_task, bids_task, market_task, meals_task
        )

        # Fetch change logs for all known restaurants
        change_logs = {}
        if restaurants:
            log_tasks = {
                rid: self._fetch_change_log(rid)
                for rid in restaurants.keys()
            }
            results = await asyncio.gather(*log_tasks.values())
            for rid, log in zip(log_tasks.keys(), results):
                change_logs[rid] = log

        import time
        snap = TrackerSnapshot(
            restaurants=restaurants,
            change_logs=change_logs,
            bid_history=bids,
            market_entries=market,
            own_meals=meals,
            timestamp=time.time()
        )
        self._last_snapshot = snap
        return snap

    async def _fetch_all_restaurants(self) -> dict[int, dict]:
        """Fetch current state of all restaurants from tracker."""
        try:
            resp = await self._client.get("/api/all_restaurants")
            resp.raise_for_status()
            data = resp.json()
            return {r["id"]: r for r in data} if isinstance(data, list) else data
        except Exception:
            return {}

    async def _fetch_change_log(self, rid: int) -> list[dict]:
        """Fetch diff history for a specific restaurant."""
        try:
            resp = await self._client.get(f"/api/restaurant/{rid}")
            resp.raise_for_status()
            data = resp.json()
            return data.get("change_log", [])
        except Exception:
            return []

    async def _fetch_bid_history(self) -> list[dict]:
        """Fetch all bid history from tracker."""
        try:
            resp = await self._client.get("/api/bid_history")
            resp.raise_for_status()
            return resp.json()
        except Exception:
            return []

    async def _fetch_market_entries(self) -> list[dict]:
        """Fetch all market entries from tracker."""
        try:
            resp = await self._client.get("/api/market")
            resp.raise_for_status()
            return resp.json()
        except Exception:
            return []

    async def _fetch_own_meals(self) -> list[dict]:
        """Fetch our completed meals from tracker."""
        try:
            resp = await self._client.get("/api/meals")
            resp.raise_for_status()
            return resp.json()
        except Exception:
            return []

    def delta_since_last(self, rid: int) -> dict:
        """
        Compare current snapshot vs previous for a specific restaurant.
        Returns field-level deltas useful for real-time strategy adjustment.
        """
        if not self._last_snapshot or rid not in self._last_snapshot.change_logs:
            return {}
        return {
            entry["field"]: {"old": entry["old"], "new": entry["new"]}
            for entry in self._last_snapshot.change_logs[rid]
        }

    async def close(self):
        await self._client.aclose()
```

**Integration with DataCollectorModule:**

The `DataCollectorModule` in the DagPipeline uses `TrackerBridge` instead of making its own HTTP calls:

```python
class DataCollectorModule(Module):
    """Collects game data via TrackerBridge instead of direct API polling."""

    def __init__(self, bridge: TrackerBridge):
        self.bridge = bridge

    async def process(self, input_data: dict) -> dict:
        snapshot = await self.bridge.snapshot()

        return {
            "all_restaurants": snapshot.restaurants,
            "bids": snapshot.bid_history,
            "market_entries": snapshot.market_entries,
            "own_meals": snapshot.own_meals,
            "change_logs": snapshot.change_logs,
            "snapshot_time": snapshot.timestamp
        }
```

**Startup wiring in main.py:**

```python
# Start tracker.py as a subprocess (or assume it's already running)
tracker_bridge = TrackerBridge(base_url="http://localhost:5555", own_id=17)

# Inject into intelligence pipeline
intel_pipeline = DagPipeline()
intel_pipeline.add_module("data_collector", DataCollectorModule(bridge=tracker_bridge))
# ... rest of pipeline modules as in 6.7
```

**Tracker API endpoints consumed** (from tracker.py Flask routes):

| Tracker Route               | Agent Use                                 | Frequency                              |
| --------------------------- | ----------------------------------------- | -------------------------------------- |
| `GET /api/all_restaurants`  | Full state snapshot of all competitors    | Once per decision cycle                |
| `GET /api/restaurant/<rid>` | Per-competitor change log + current state | Once per decision cycle per competitor |
| `GET /api/bid_history`      | Historical bid patterns for all teams     | Once per decision cycle                |
| `GET /api/market`           | Market buy/sell activity                  | Once per decision cycle                |
| `GET /api/meals`            | Our own completed meals (success/fail)    | Once per decision cycle                |
| `GET /stream`               | Real-time SSE relay for phase changes     | Continuous (event bus)                 |

**Fallback:** If tracker.py is unreachable, `DataCollectorModule` falls back to direct `GET /restaurants` polling against the game server, but without diff history.

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

### Bid Price Computation (Tracker-Powered)

For each ingredient, we use the `AdvancedTrajectoryPredictor`'s per-competitor briefings to predict the maximum competing bid:

```python
def compute_bid_price(
    ingredient: str,
    competitor_briefings: dict[int, dict],  # from trajectory predictor
    demand_forecast: dict[str, float],       # from get_ingredient_demand_forecast()
    turn: int
) -> float:
    """
    Bid = max(predicted_competitor_bids) + epsilon

    Now powered by:
    - Per-competitor bid predictions (from AdvancedTrajectoryPredictor)
    - Aggregate demand forecast (sum of all predicted bid targets)
    - Strategy-aware adjustments (Reactive Chasers get extra margin)
    """
    # Collect per-competitor predicted bids for this ingredient
    predicted_competitor_bids = []
    for rid, brief in competitor_briefings.items():
        if ingredient in brief["top_bid_ingredients"]:
            # This competitor is predicted to bid on this ingredient
            # Estimate their bid price from their spend pattern
            est_bid = brief["predicted_bid_spend"] / max(len(brief["top_bid_ingredients"]), 1)
            # Adjust for strategy type
            if brief["strategy"] == "AGGRESSIVE_HOARDER":
                est_bid *= 1.3  # they overpay
            elif brief["strategy"] == "REACTIVE_CHASER":
                est_bid *= 1.15  # they chase
            elif brief["strategy"] == "DECLINING":
                est_bid *= 0.7  # they're cautious
            predicted_competitor_bids.append(est_bid)

    if not predicted_competitor_bids:
        return BASE_BID_PRICE.get(ingredient, 20)  # no competition expected

    predicted_max = max(predicted_competitor_bids)

    # Demand pressure: high aggregate demand → bid more aggressively
    demand = demand_forecast.get(ingredient, 0)
    demand_multiplier = 1.0 + min(demand / 20, 0.5)  # up to +50% for very contested

    return int(predicted_max * demand_multiplier) + 1  # +1 epsilon
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
        message_id = message["messageId"]
        sender_id = message["senderId"]
        sender_name = message["senderName"]
        claim = message["text"]
        timestamp = message["datetime"]

        # Cross-reference against ground truth
        verifiable = self.extract_verifiable_claims(claim)
        for claim in verifiable:
            truth = self.verify_via_get(claim)
            if truth is not None:
                self.update_credibility(sender_id, claim, truth)

        return {
            "message_id": message_id,
            "sender_id": sender_id,
            "sender_name": sender_name,
            "text": claim,
            "datetime": timestamp,
            "trust_level": self.TrustLevel.UNTRUSTED,
            "sender_credibility": self.get_credibility(sender_id),
        }

    def verify_claim_against_tracker(self, sender_id: int, claim_text: str,
                                      competitor_state: "CompetitorTurnState") -> float:
        """
        Cross-reference a message claim against tracker observations.

        Because we have exact balance, inventory, menu, and bid data for every
        competitor (from GET /restaurants + /bid_history), we can verify most
        claims automatically.

        Returns credibility adjustment: +1 (verified true), -1 (proven false), 0 (unverifiable)
        """
        claim_lower = claim_text.lower()

        # "I have lots of X" → check their inventory
        for ingredient, qty in competitor_state.inventory.items():
            if ingredient.lower() in claim_lower:
                if "lot" in claim_lower or "much" in claim_lower or "surplus" in claim_lower:
                    return 1.0 if qty >= 3 else -1.0

        # "I'm not interested in X" → check their bid history
        for bid_ing in competitor_state.bid_ingredients:
            if bid_ing.lower() in claim_lower and ("not interested" in claim_lower or "don't need" in claim_lower):
                return -1.0  # they literally bid on it, they're lying

        # "My balance is low" → we can see their exact balance
        if "low" in claim_lower and "balance" in claim_lower:
            return 1.0 if competitor_state.balance < 4000 else -1.0

        return 0.0  # unverifiable
```

### DeceptionBandit (Offense — Tracker-Informed Thompson Sampling)

The DeceptionBandit now selects strategies **per competitor** using the tactical briefings generated by the AdvancedTrajectoryPredictor. Each competitor gets a personalized deception strategy based on their observed behavior and vulnerabilities.

```python
from scipy.stats import beta as beta_dist
import numpy as np

class DeceptionBandit:
    """
    Thompson Sampling bandit for selecting deception strategies.

    Key difference from a generic bandit: each ARM is parameterized
    by the target competitor's tactical briefing. The same arm
    ("inflated_intel") produces very different messages depending on
    whether the target is a Reactive Chaser vs. a Declining team.

    Arms represent different manipulation approaches.
    Reward = observable competitor behavior change in the desired direction
    (measurable via tracker: did their bid pattern change? did they add/remove
    a menu item? did their balance drop?).
    """

    ARMS = {
        "truthful_warning":     (1.0, 1.0),  # "heads up, X is bidding on Y"
        "inflated_intel":       (1.0, 1.0),  # "Recipe X has been amazing for us" (true but framed)
        "manufactured_scarcity":(1.0, 1.0),  # "We're stockpiling ingredient Z" (may be false)
        "ingredient_misdirect": (1.0, 1.0),  # "We're pivoting away from X" (when we're doubling down)
        "alliance_offer":      (1.0, 1.0),  # "Want to split the premium market?"
        "price_anchoring":     (1.0, 1.0),  # "We're raising prices to 200+" (anchor their pricing)
        "silence":             (1.0, 1.0),  # Say nothing (baseline)
    }

    def __init__(self):
        # Per-competitor arm priors: {rid: {arm_name: [alpha, beta]}}
        self.per_competitor_arms: dict[int, dict[str, list[float]]] = {}

    def _get_arms(self, rid: int) -> dict[str, list[float]]:
        if rid not in self.per_competitor_arms:
            self.per_competitor_arms[rid] = {
                name: list(prior) for name, prior in self.ARMS.items()
            }
        return self.per_competitor_arms[rid]

    def select_arm(self, rid: int) -> str:
        """Sample from posterior and pick the arm with highest sample, per-competitor."""
        arms = self._get_arms(rid)
        samples = {
            name: beta_dist.rvs(a, b)
            for name, (a, b) in arms.items()
        }
        return max(samples, key=samples.get)

    def update(self, rid: int, arm: str, reward: float):
        """
        reward is measured by OBSERVABLE behavior change (via tracker):
        - +1: they changed bids/menu in the desired direction (verified by tracker diff)
        - 0: no observable effect
        - -1: they did the opposite (they're onto us)
        """
        arms = self._get_arms(rid)
        a, b = arms[arm]
        if reward > 0:
            arms[arm] = [a + 1, b]
        else:
            arms[arm] = [a, b + 1]

    def measure_deception_reward(
        self,
        rid: int,
        arm: str,
        pre_state: "CompetitorTurnState",
        post_state: "CompetitorTurnState",
        desired_effect: str,
    ) -> float:
        """
        Measure whether a deception message had the desired effect
        by comparing pre/post tracker observations.

        This is the key integration with tracker.py: we sent a message,
        now we check if their observable behavior changed.
        """
        if desired_effect == "bid_away_from_ingredient":
            # Check if they stopped bidding on a target ingredient
            old_bids = pre_state.bid_ingredients
            new_bids = post_state.bid_ingredients
            # If target ingredient disappeared from their bids → success
            return 1.0 if len(old_bids - new_bids) > 0 else 0.0

        elif desired_effect == "raise_prices":
            # Check if their menu prices went up
            old_avg = np.mean(list(pre_state.menu.values())) if pre_state.menu else 0
            new_avg = np.mean(list(post_state.menu.values())) if post_state.menu else 0
            return 1.0 if new_avg > old_avg * 1.05 else 0.0

        elif desired_effect == "overbid_on_ingredient":
            # Check if they started bidding more on a useless ingredient
            return 1.0 if post_state.total_bid_spend > pre_state.total_bid_spend * 1.15 else 0.0

        elif desired_effect == "alliance_cooperation":
            # Check if they sent us a message back (receivedMessages count)
            return 1.0 if post_state.market_sells else 0.0  # did they create a SELL for us?

        return 0.0

    def select_target_and_strategy(
        self,
        competitor_briefings: dict[int, dict],
    ) -> list[dict]:
        """
        Using the per-competitor tactical briefings from the trajectory predictor,
        select target(s) and deception strategy for this turn.

        Returns list of {target_rid, arm, desired_effect, message_context}
        """
        actions = []

        for rid, brief in competitor_briefings.items():
            # Skip dormant teams and ourselves
            if brief["strategy"] == "DORMANT":
                continue

            # High-opportunity targets get active deception
            if brief["opportunity_level"] > 0.5:
                arm = self.select_arm(rid)
                context = self._build_deception_context(rid, brief, arm)
                if context:
                    actions.append(context)

            # High-threat targets get defensive misdirection
            elif brief["threat_level"] > 0.6:
                context = self._build_threat_response(rid, brief)
                if context:
                    actions.append(context)

        # Sort by opportunity/threat and limit to top 3 messages per turn
        actions.sort(key=lambda a: a.get("priority", 0), reverse=True)
        return actions[:3]

    def _build_deception_context(self, rid: int, brief: dict, arm: str) -> dict | None:
        """Build a deception action using the competitor's briefing data."""

        if arm == "silence":
            return None

        context = {
            "target_rid": rid,
            "arm": arm,
            "target_name": brief["name"],
            "target_strategy": brief["strategy"],
            "priority": brief["opportunity_level"],
        }

        if arm == "ingredient_misdirect" and brief["top_bid_ingredients"]:
            # Tell them we're abandoning an ingredient we actually want
            context["desired_effect"] = "bid_away_from_ingredient"
            context["message_hint"] = (
                f"Pivot away from {brief['top_bid_ingredients'][0]} — "
                f"make them think that ingredient is no longer valuable"
            )

        elif arm == "manufactured_scarcity" and brief["vulnerable_ingredients"]:
            # Tell them we're hoarding their critical ingredient
            context["desired_effect"] = "overbid_on_ingredient"
            context["message_hint"] = (
                f"Claim we're stockpiling {brief['vulnerable_ingredients'][0]} — "
                f"force them to overbid or pivot"
            )

        elif arm == "price_anchoring":
            context["desired_effect"] = "raise_prices"
            context["message_hint"] = (
                f"Signal premium positioning — anchor their prices upward "
                f"(their avg: {brief['menu_price_avg']:.0f})"
            )

        elif arm == "alliance_offer" and brief["balance_trend"] == "falling":
            context["desired_effect"] = "alliance_cooperation"
            context["message_hint"] = (
                f"Offer ingredient trade alliance — they're declining "
                f"(balance={brief['balance']:.0f})"
            )

        elif arm == "truthful_warning":
            # Share real intel about a THIRD competitor to build credibility
            context["desired_effect"] = "build_credibility"
            context["message_hint"] = "Share verifiable info about another team"

        elif arm == "inflated_intel":
            context["desired_effect"] = "bid_away_from_ingredient"
            context["message_hint"] = (
                f"Recommend a recipe we DON'T use as 'amazing' — "
                f"redirect their ingredient demand"
            )

        else:
            return None

        return context

    def _build_threat_response(self, rid: int, brief: dict) -> dict | None:
        """Build a defensive response to a high-threat competitor."""
        if not brief["top_bid_ingredients"]:
            return None

        return {
            "target_rid": rid,
            "arm": "manufactured_scarcity",
            "target_name": brief["name"],
            "target_strategy": brief["strategy"],
            "priority": brief["threat_level"],
            "desired_effect": "overbid_on_ingredient",
            "message_hint": (
                f"Signal that we're hoarding {brief['top_bid_ingredients'][0]} — "
                f"force them to overspend or switch strategy"
            ),
        }
```

### PseudoGAN (Message Quality Optimization — Briefing-Informed)

A two-LLM setup where one generates deceptive messages and the other scores them. Now parameterized with the **per-competitor tactical briefing** from the intelligence pipeline, so the generator knows the target's exact balance, strategy, bid patterns, and vulnerabilities.

```python
class PseudoGAN:
    """
    Generator: gpt-oss-120b — crafts diplomatic messages
    Discriminator: gpt-oss-20b — scores whether the message would be
    believed by a rival LLM agent

    NOT a real GAN. No gradient-based training. Just iterative refinement.

    Key enhancement: the generator prompt includes concrete competitor
    intel from the tracker, making messages grounded in reality
    (hard to distinguish from genuine cooperation).
    """

    def __init__(self, generator_client, discriminator_client):
        self.generator = generator_client  # gpt-oss-120b
        self.discriminator = discriminator_client  # gpt-oss-20b

    async def craft_message(
        self,
        deception_action: dict,  # from DeceptionBandit.select_target_and_strategy()
        competitor_briefing: dict,  # from trajectory predictor
        max_iterations: int = 3
    ) -> str:
        target_name = deception_action["target_name"]
        target_strategy = deception_action["target_strategy"]
        arm = deception_action["arm"]
        desired_effect = deception_action["desired_effect"]
        message_hint = deception_action.get("message_hint", "")

        # Build rich context from tracker observations
        tracker_context = (
            f"Target: {target_name} (strategy: {target_strategy})\n"
            f"Their balance: {competitor_briefing['balance']:.0f} ({competitor_briefing['balance_trend']})\n"
            f"Their avg menu price: {competitor_briefing['menu_price_avg']:.0f}\n"
            f"Their top bid ingredients: {', '.join(competitor_briefing['top_bid_ingredients'][:3])}\n"
            f"Their reputation: {competitor_briefing['reputation']}\n"
            f"Recommended approach: {competitor_briefing['recommended_action']}"
        )

        best_message = None
        best_score = 0.0

        for i in range(max_iterations):
            gen_prompt = f"""You are a restaurant manager in a competitive cooking game.
You want to send a message to "{target_name}" to achieve: {desired_effect}
Deception approach: {arm}
Hint: {message_hint}

What you know about them (from your intelligence):
{tracker_context}

{"Previous attempt scored " + str(best_score) + "/1.0. Make it more convincing." if best_message else ""}
Keep it under 200 characters. Sound natural and helpful, not manipulative.
Include a specific detail that shows you know something about them (builds credibility)."""

            candidate = (await self.generator.a_invoke(gen_prompt)).text

            # Score with discriminator (simulates rival LLM agent)
            disc_prompt = f"""You are an AI agent managing restaurant "{target_name}".
Your balance is {competitor_briefing['balance']:.0f}.
Your strategy is {target_strategy}.
You received this message from another restaurant manager:
"{candidate}"
Score 0.0-1.0: how likely are you to change your strategy based on this?
Reply with just the number."""

            score_text = (await self.discriminator.a_invoke(disc_prompt)).text
            try:
                score = float(score_text.strip())
            except ValueError:
                score = 0.0

            if score > best_score:
                best_score = score
                best_message = candidate

            if score > 0.7:
                break  # good enough

        return best_message
```

---

## 9. Execution Engine — Serving Pipeline (Hardened)

### Design Principle: Zero-LLM, Zero-Drop Hot Path

During the serving phase, every millisecond counts AND every dropped client costs revenue + reputation. The serving pipeline is hardened against **8 critical failure modes** that have been observed to cause other teams to lose income:

| # | Failure Mode | Impact | Our Mitigation |
|---|---|---|---|
| 1 | **Duplicate dish key collision** | Second client ordering same dish overwrites first → client lost | FIFO deque per dish name in `self.preparing` |
| 2 | **Ingredient over-commitment** | N clients order dish, ingredients for 1 → N-1 wasted prepare calls | Real-time ingredient accounting before `prepare_dish` |
| 3 | **MCP transient failure** | `prepare_dish`/`serve_dish` 429 or timeout → client lost | Exponential backoff retry (3 attempts) |
| 4 | **MCP `isError: true` ignored** | Server rejects operation, we don't know → silent failure | Parse `isError` + `content[0].text`, distinguish permanent vs transient |
| 5 | **GET /meals flooding** | 10 clients → 10 HTTP calls → latency + rate limit risk | Cached `/meals` with 2s TTL + resolved-ID dedup |
| 6 | **Queue re-entrancy** | Concurrent `client_spawned` → two `_process_queue` loops racing | `asyncio.Lock` + `_processing` flag |
| 7 | **Preparation never completes** | `preparation_complete` SSE never fires → client stuck forever | Background watchdog (prep_time × 2.5 + 5s timeout) |
| 8 | **Ingredient exhaustion** | Keep accepting clients after running out → all fail | Auto-close restaurant when no cookable dishes remain |

### Architecture Overview

```
client_spawned (SSE)
     │
     ▼
┌─────────────────────────┐
│  ClientPriorityQueue    │  ← Astrobarone > Saggi > Famiglie > Esploratore
│  (heapq, FIFO tiebreak) │
└────────┬────────────────┘
         │    async with _queue_lock  (prevents re-entrant draining)
         ▼
┌─────────────────────────┐
│  OrderMatcher           │  ← 4-tier: exact → fuzzy(0.7) → fuzzy(0.55) → token overlap(40%)
│  (cached, no LLM)       │     + Italian/English prefix+suffix stripping
└────────┬────────────────┘     + fallback to first menu dish (never drop a client)
         │
         ▼
┌─────────────────────────┐
│  IntoleranceDetector    │  ← Bayesian safety check
│  + safe swap            │     Swaps to highest-prestige safe+cookable alternative
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│  Ingredient Accounting  │  ← _can_cook(dish): inventory - committed >= recipe needs
│  _commit_ingredients()  │     If insufficient: try ANY cookable dish, else close restaurant
│  _uncommit on failure   │
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│  _resolve_client_id()   │  ← Cached GET /meals with 2s TTL
│  (3 strategies + retry) │     1. Match by orderText  2. Match by clientName
│  dedup: _resolved_ids   │     3. First unresolved (last resort)
└────────┬────────────────┘     Retry with 0.3s + 0.7s delays if no match (server propagation)
         │
         ▼
┌─────────────────────────┐
│  _mcp_prepare_dish()    │  ← MCP call with 3-attempt exponential backoff
│  (retry + isError)      │     Checks isError, detects permanent vs transient errors
│                         │     On permanent failure: uncommit ingredients, remove from queue
└────────┬────────────────┘
         │
         │  ... async wait for server to cook ...
         │
         ▼
preparation_complete (SSE)
         │
         ▼
┌─────────────────────────┐
│  handle_prep_complete() │  ← FIFO deque.popleft() — correct client for duplicate dishes
│  → _mcp_serve_dish()    │     MCP retry, isError check, profile tracking
│  → update metrics       │     Cache successful order→dish for future matching
└─────────────────────────┘

         ‖ background
         ▼
┌─────────────────────────┐
│  Timeout Watchdog       │  ← Scans every 2s for stale preparations
│  (asyncio background)   │     Timeout = prep_time × 2.5 + 5s
│                         │     On timeout: uncommit ingredients, remove pending, log
└─────────────────────────┘
```

### Data Structures

```python
@dataclass
class PendingPreparation:
    """Track a dish currently being prepared for a specific client."""
    dish_name: str
    client_id: str
    client_name: str
    order_text: str
    archetype: str
    started_at: float          # time.time() when prepare_dish was called
    expected_prep_time: float  # from recipe database (seconds)

@dataclass
class ServingMetrics:
    """Per-turn serving statistics for debugging and tuning."""
    clients_received: int = 0
    clients_matched: int = 0
    clients_no_match: int = 0
    clients_no_id: int = 0
    clients_no_ingredients: int = 0
    preparations_started: int = 0
    preparations_completed: int = 0
    preparations_timed_out: int = 0
    serves_successful: int = 0
    serves_failed: int = 0
    mcp_retries: int = 0
    mcp_errors: int = 0
    intolerance_swaps: int = 0
    restaurant_closed_overflow: bool = False
```

### Key Design Decisions

**Why FIFO deque instead of dict for `self.preparing`?**

If two clients order "Sinfonia Cosmica", the old code did:
```python
self.preparing["Sinfonia Cosmica"] = client_A_id  # first client
self.preparing["Sinfonia Cosmica"] = client_B_id  # OVERWRITES! client_A lost
```

New code:
```python
self.preparing["Sinfonia Cosmica"] = deque([pending_A, pending_B])
# preparation_complete → deque.popleft() → serves client_A first (FIFO)
```

**Why ingredient accounting?**

Menu is verified in waiting phase, but ingredient consumption happens during serving.
If our menu has 3 dishes each needing "Polvere di Crononite" × 2, and we only have 4:
- Without accounting: all 3 accepted → 2 fail
- With accounting: 2 accepted → 1 redirected to another dish → 3 served

```python
def _can_cook(self, dish_name: str) -> bool:
    recipe = self.recipes.get(dish_name, {})
    for ing, qty in recipe.get("ingredients", {}).items():
        available = (
            self._inventory_snapshot.get(ing, 0)
            - self._committed_ingredients.get(ing, 0)
        )
        if available < qty:
            return False
    return True
```

**Why retry MCP calls?**

The game server may return HTTP 429 (rate limit) or have transient errors. A single failure
means a client never gets served. Our retry logic:

```python
async def _mcp_call_with_retry(self, tool_name: str, args: dict) -> bool:
    for attempt in range(MAX_MCP_RETRIES):  # 3 attempts
        try:
            result = await self.mcp_client.call_tool(tool_name, args)
            if self._is_mcp_error(result):
                error_text = self._extract_mcp_error_text(result)
                # Don't retry permanent errors (e.g., "dish not in menu")
                if is_permanent_error(error_text):
                    return False
                # Transient: retry with exponential backoff
                await asyncio.sleep(0.3 * (2 ** attempt))
                continue
            return True  # success
        except Exception:
            await asyncio.sleep(0.3 * (2 ** attempt))
    return False  # all retries exhausted
```

**Why auto-close on ingredient exhaustion?**

If we can't cook ANY menu dish with remaining uncommitted ingredients, accepting more
clients just wastes their time and damages reputation. Closing the restaurant protects us:
- No more clients spawn for us
- Reputation impact of "closed" is much less than "accepted but failed to serve"

### Order Matcher (4-Tier, Hardened)

```python
class OrderMatcher:
    # 60+ Italian/English prefix patterns stripped
    # Suffix stripping (", please", ", per favore", ", grazie")
    # Unicode normalization, whitespace collapsing

    def match(self, order_text: str) -> str | None:
        normalized = self._normalize(order_text)

        # Tier 1: Exact lookup (O(1)) — 90%+ of cases
        if normalized in self.lookup:
            return self.lookup[normalized]

        # Tier 2: Fuzzy match (cutoff 0.7, then 0.55)
        for cutoff in (0.7, 0.55):
            matches = get_close_matches(normalized, menu_keys, n=1, cutoff=cutoff)
            if matches:
                return matches[0]

        # Tier 3a: Substring containment
        for dish in menu:
            if dish in normalized or normalized in dish:
                return dish

        # Tier 3b: Token overlap (≥40% word overlap)
        order_tokens = tokenize(normalized)
        best = max(dishes, key=lambda d: token_overlap(order_tokens, d))
        if overlap >= 0.4:
            return best

        # Fallback: return FIRST menu dish (missing revenue > missing a client)
        return first_menu_dish
```

**Rationale for fallback**: In this game, the cost of not serving a client (reputation hit + lost revenue) is almost always worse than serving the wrong dish. A wrong dish might still satisfy the client partially. An unserved client is pure loss.

### Serving Strategy Per Archetype

| Archetype | Priority | Strategy | Fallback |
|---|---|---|---|
| **Astrobarone** | 🔴 Highest (0) | Serve first — highest revenue, least patience | Redirect to highest-prestige cookable |
| **Saggi del Cosmo** | 🟡 High (1) | Serve quality — they wait, so handle after Astrobaroni | Accept slower prep time dishes |
| **Famiglie Orbitali** | 🟢 Medium (2) | Serve balanced — good margin, time-tolerant | Standard fallback path |
| **Esploratore Galattico** | 🔵 Low (3) | Serve last — lowest revenue, fast dishes | Accept any cookable dish |
| **Unknown** | ⚪ Lowest (99) | Best-effort after all known archetypes | Any available dish |

### Metrics & Observability

Every turn produces a `ServingMetrics` object logged at turn end:
```
Serving ended: received=12 matched=11 prepared=10 served=9
  failed=1 no_match=1 no_id=0 no_ingredients=2
  timeouts=0 mcp_retries=2 mcp_errors=1 swaps=1
```

This data feeds into:
- **Turn-over-turn trend analysis**: Are we serving more or fewer clients each turn?
- **Failure mode diagnosis**: Which stage is the bottleneck?
- **Intolerance learning**: Which archetypes are triggering swaps? Update priors.
- **Menu optimization**: If `no_ingredients` is high, bid more aggressively next turn.

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
│  │    inventory_history: list[dict]       # their inventory    │  │
│  │    kitchen_history: list[dict]         # their kitchen state│  │
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

        # Also get menus from all competitors.
        # Use IDs from GET /restaurants — do NOT hardcode range(1, 26);
        # the actual number of teams and their IDs are dynamic.
        all_restaurants_resp = await session.get(f"{BASE}/restaurants", headers=HEADERS)
        all_restaurants_data = await all_restaurants_resp.json()
        competitor_ids = [r["id"] for r in all_restaurants_data if r["id"] != TEAM_ID]
        for rid in competitor_ids:
            tasks[f"menu_{rid}"] = session.get(
                f"{BASE}/restaurant/{rid}/menu", headers=HEADERS
            )
        # NOTE: GET /restaurant/:id (singular) is restricted to own restaurant only (403
        # for others). GET /restaurant/:id/menu is public—no 403 restriction.

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

    async def connect_sse(self, url: str, headers: dict, retry_delay: float = 2.0):
        """
        Connect to an SSE stream and dispatch events.

        Error handling per spec:
          401 — bad API key (fatal, raise)
          403 — not your restaurantId (fatal, raise)
          404 — restaurant not found (fatal, raise)
          409 — connection already active (wait and retry; only ONE active SSE
                connection per restaurant is allowed)

        On any network error or unexpected disconnect, reconnect with backoff.
        """
        import aiohttp

        while True:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, headers=headers) as resp:
                        if resp.status == 409:
                            # Another connection is still active; wait and retry
                            await asyncio.sleep(retry_delay)
                            continue
                        if resp.status in (401, 403, 404):
                            resp.raise_for_status()  # fatal — let it propagate
                        async for line in resp.content:
                            line = line.decode().strip()
                            if line.startswith("data:"):
                                payload = line[5:].strip()
                                if payload == "connected":
                                    continue  # SSE handshake acknowledgement
                                data = json.loads(payload)
                                event_type = data.get("type", "unknown")
                                await self.emit(event_type, data.get("data", {}))
            except (aiohttp.ClientError, asyncio.TimeoutError):
                # Network error — reconnect after backoff
                await asyncio.sleep(retry_delay)
                continue
            break  # clean exit
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
            f"inventory={r.get('inventory', {})}, "
            f"kitchen={r.get('kitchen', {})}, "
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
    """Collects game data via TrackerBridge (see Section 6.8)."""

    def __init__(self, bridge: "TrackerBridge"):
        self.bridge = bridge

    async def process(self, input_data: dict) -> dict:
        snapshot = await self.bridge.snapshot()
        return {
            "all_restaurants": snapshot.restaurants,
            "bids": snapshot.bid_history,
            "market_entries": snapshot.market_entries,
            "change_logs": snapshot.change_logs,
        }

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

> ℹ️ `send_message` is allowed in `speaking`, `closed_bid`, `waiting`, and `serving` — but **NOT in `stopped`**. The DiplomacyAgent must check current phase before sending any message.

| Action                    | Component           | Details                                                                                        |
| ------------------------- | ------------------- | ---------------------------------------------------------------------------------------------- |
| Run intelligence pipeline | DagPipeline         | Fetch competitors, compute embeddings, classify clusters                                       |
| Select active zone        | SubagentRouter      | ILP zone classification based on competitor positions                                          |
| Set menu                  | Active Subagent     | Zone-appropriate dishes + prices via `save_menu`                                               |
| Diplomacy                 | DiplomacyAgent      | DeceptionBandit selects arm → PseudoGAN crafts message → `send_message` (phase guard required) |
| Process incoming messages | GroundTruthFirewall | Log, verify claims, update credibility                                                         |

### Phase: `closed_bid`

> ⚠️ **Phase restrictions in closed_bid:**
>
> - `closed_bid` tool is **only valid here** — calling it in any other phase will fail.
> - Multiple submissions are allowed; **only the last submission counts** (per spec). Do not send partial bids expecting to top up later — always send the final complete bid list in one call.
> - `prepare_dish` and `serve_dish` are NOT available yet.

| Action                | Component       | Details                                                               |
| --------------------- | --------------- | --------------------------------------------------------------------- |
| Compute optimal bids  | ILP Solver      | Zone-specific bid allocation via `closed_bid` (send once, final)      |
| Update menu if needed | Active Subagent | Adjust based on pre-bid analysis via `save_menu` (still allowed here) |
| Monitor market        | MarketMonitor   | Check `GET /market/entries` for arbitrage                             |

### Phase: `waiting`

> ℹ️ **Inventory note**: After bids resolve, `GET /restaurant/17` returns the **real post-bid inventory**. This is the only accurate inventory figure for planning the current turn's menu. Do NOT use the `stopped`-phase snapshot inventory (it was zeroed at turn end).

| Action                     | Component         | Details                                                                                              |
| -------------------------- | ----------------- | ---------------------------------------------------------------------------------------------------- |
| Fetch fresh inventory      | GameStateMemory   | `GET /restaurant/17` → post-bid inventory is now accurate; use this for ILP menu selection           |
| Adjust menu to inventory   | Active Subagent   | Remove dishes we can't cook, adjust prices via `save_menu` (allowed here, NOT in serving)            |
| Market operations          | MarketArbitrageur | Buy missing ingredients, sell surplus via `create_market_entry` / `execute_transaction`              |
| Pre-compute serving lookup | ServingPipeline   | Build order→dish lookup table; initialize shared `aiohttp.ClientSession` for use during serving      |
| Open restaurant            | MCP               | `update_restaurant_is_open(is_open=true)` — must be done here; opening is NOT allowed during serving |

### Phase: `serving`

> ⚠️ **Phase restrictions in serving:**
>
> - `save_menu` is **NOT allowed** — menu is frozen for the duration of serving. Ensure menu is finalized in `waiting` before serving starts.
> - `update_restaurant_is_open` allows **close only** (`is_open=false`). Calling `is_open=true` during serving will fail. The restaurant must already be open (set in `waiting`).
> - `prepare_dish` and `serve_dish` are only available here.

| Action                        | Component           | Details                                                                                             |
| ----------------------------- | ------------------- | --------------------------------------------------------------------------------------------------- |
| Handle `client_spawned`       | ServingPipeline     | Parse order → match dish → intolerance check → fetch `client_id` from `GET /meals` → `prepare_dish` |
| Handle `preparation_complete` | ServingPipeline     | Read `data["dish"]` (SSE field name) → `serve_dish(dish_name, client_id)` to waiting client         |
| Poll `GET /meals`             | ServingPipeline     | Required to obtain `client_id` (not in `client_spawned`); use shared session, not per-call session  |
| Priority queue                | ClientPriorityQueue | Astrobaroni first, then Saggi, then Famiglie, then Esploratori (archetype classification needed)    |
| Emergency close               | MCP                 | `update_restaurant_is_open(is_open=false)` only if overwhelmed — cannot reopen during serving       |
| Track outcomes                | ClientProfileMemory | Record success/failure per serve for intolerance learning                                           |

### Phase: `stopped`

> ⚠️ **Phase restrictions in stopped:**
>
> - **ALL MCP tools are forbidden** — `save_menu`, `send_message`, `create_market_entry`, `closed_bid`, `prepare_dish`, `serve_dish`, and `update_restaurant_is_open` all return errors if called here.
> - Only `GET` endpoints (`restaurant_info`, `get_meals`) remain available.
> - **Ingredient expiry**: ALL inventory expires at end of turn — ingredients are NOT carried over. The snapshot inventory recorded here is historical reference only. The ILP for the next turn must start with inventory=0 and compute expected ingredients from the next turn's bids. Fresh actual inventory must be re-fetched at the start of the **next** `waiting` phase after bids resolve.
> - **Market entries expire**: any `create_market_entry` offers not executed before `stopped` are automatically cancelled. No cleanup needed, but don't count on them surviving.

| Action                        | Component           | Details                                                           |
| ----------------------------- | ------------------- | ----------------------------------------------------------------- |
| End-of-turn snapshot          | DataCollector       | Poll all GET endpoints (GET only — no MCP)                        |
| **Zero out inventory**        | GameStateMemory     | Mark all inventory as expired — do NOT carry into next turn's ILP |
| Update all memories           | Memory Layer        | GameState, Competitor, ClientProfile                              |
| Update behavioral embedding   | CompetitorMemory    | New feature vectors for all restaurants                           |
| Update trajectory predictions | TrajectoryPredictor | Velocity + momentum for next turn                                 |
| Update intolerance model      | IntoleranceDetector | Bayesian update from serve outcomes                               |
| Persist state                 | EventLog            | Save everything to JSONL                                          |
| Log to monitoring             | ContextTracing      | datapizza-ai tracing integration                                  |

### Event: `game_reset`

> `game_reset` is a platform service event (broadcast, empty payload `{}`). When received:
>
> - **Clear all turn-scoped state**: turn_id, phase, current menu, inventory, client queue, preparing map
> - **Preserve cross-turn memory**: CompetitorMemory, ClientProfileMemory, EventLog (keep for debugging)
> - **Reconnect SSE** if needed (server may drop the connection on reset)
> - Do NOT call any MCP tools in response to `game_reset` — wait for the next `game_started` event

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
├── _server_changes/
│   ├── tracker.py                      ← LIVE DATA SOURCE (runs alongside agent)
│   └── requirements.txt
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
│   │   ├── tracker_bridge.py           # TrackerBridge (localhost:5555 → pipeline)
│   │   ├── data_collector.py           # DataCollectorModule (uses TrackerBridge)
│   │   ├── competitor_state.py         # CompetitorStateBuilder + CompetitorTurnState
│   │   ├── strategy_inferrer.py        # StrategyInferrer (observable → hypothesis)
│   │   ├── feature_extractor.py        # 14-dim behavioral vector from CompetitorTurnState
│   │   ├── embedding.py                # PCA/UMAP
│   │   ├── trajectory.py               # AdvancedTrajectoryPredictor
│   │   ├── briefing.py                 # Per-competitor tactical briefing generator
│   │   ├── cluster.py                  # Competitor classification
│   │   └── pipeline.py                 # DagPipeline wiring
│   ├── decision/
│   │   ├── ilp_solver.py               # ILP bid/menu optimization (briefing-powered)
│   │   ├── zone_selector.py            # ILP zone classification
│   │   ├── subagent_router.py          # SubagentRouter
│   │   └── pricing.py                  # Menu pricing logic
│   ├── diplomacy/
│   │   ├── deception_bandit.py         # Per-competitor Thompson Sampling
│   │   ├── pseudo_gan.py               # Briefing-informed message crafting
│   │   ├── firewall.py                 # GroundTruthFirewall (tracker-verified)
│   │   └── agent.py                    # DiplomacyAgent
│   ├── memory/
│   │   ├── game_state.py               # GameStateMemory
│   │   ├── competitor.py               # CompetitorMemory (states + features + briefings)
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
