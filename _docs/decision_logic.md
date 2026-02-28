# SPAM! — Decision Logic Reference

All thresholds, formulas, and conditions that determine every decision the bot makes.

---

## Table of Contents
1. [Turn Flow & Phase Lifecycle](#1-turn-flow--phase-lifecycle)
2. [Skill System & Execution Order](#2-skill-system--execution-order)
3. [Intelligence Pipeline](#3-intelligence-pipeline)
4. [Zone Selection](#4-zone-selection)
5. [Menu Planning (ILP)](#5-menu-planning-ilp)
6. [Bid Prices](#6-bid-prices)
7. [Menu Prices](#7-menu-prices)
8. [Market Operations](#8-market-operations)
9. [Serving Pipeline](#9-serving-pipeline)
10. [Order Matching](#10-order-matching)
11. [Diplomacy](#11-diplomacy)
12. [Strategy Inference (Competitors)](#12-strategy-inference-competitors)
13. [Threat & Opportunity Levels](#13-threat--opportunity-levels)
14. [Constants Reference](#14-constants-reference)

---

## 1. Turn Flow & Phase Lifecycle

### Phase Order
```
game_started → speaking → closed_bid → waiting → serving → stopped → (repeat)
```

### Phase Durations (estimated, updated from observations, rolling avg of last 10)
| Phase | Default estimate |
|---|---|
| speaking | 90 s |
| closed_bid | 45 s |
| waiting | 45 s |
| serving | 150 s |
| stopped | 30 s |

### turn_id Protection
SSE `game_phase_changed` events frequently carry `turn_id=0`, which would regress state and cause `/meals?turn_id=0` → 400 errors.

**Rule:**
```
turn_id = raw_turn  if (raw_turn is not None and raw_turn > 0)
        else current_turn  (keep existing)
```
`game_started` also rejects `turn_id=0`, falling back to `max(current_turn + 1, 1)`.

### Mid-turn Entry Detection
If the **first phase received** is not `speaking`, we joined mid-turn:
- `is_mid_turn_entry = True`
- `skipped_phases = PHASE_ORDER[:idx_of_current_phase]`
- Different skill set runs (see §2)

---

## 2. Skill System & Execution Order

Skills sorted by **priority (lower = runs first)**. Dependencies enforced.

### Normal Phase → Skills

| Phase | Skills (in priority order) |
|---|---|
| `speaking` | `intelligence_scan` → `zone_selection` → `menu_planning` → `menu_save` → `diplomacy_send` → `market_ops` |
| `closed_bid` | `bid_compute` → `bid_submit` → `menu_save` → `market_ops` |
| `waiting` | `inventory_verify` → `menu_planning` → `menu_save` → `market_ops` → `restaurant_open` → `serving_prep` |
| `serving` | `serving_monitor` → `close_decision` |
| `stopped` | `end_turn_snapshot` → `info_gather` |

### Mid-turn Catchup Skills

| Entry Phase | Skills run |
|---|---|
| `speaking` | Full speaking pipeline (nothing missed) |
| `closed_bid` | `quick_intelligence` → `zone_selection` → `menu_planning` → `menu_save` → `bid_compute` → `bid_submit` → `market_ops` |
| `waiting` | `quick_intelligence` → `zone_selection` → `inventory_verify` → `menu_planning` → `menu_save` → `market_ops` → `restaurant_open` → `serving_prep` |
| `serving` | `serving_readiness_check` → `emergency_menu` → `restaurant_open` → `serving_prep` → `close_decision` |
| `stopped` | `end_turn_snapshot` → `info_gather` |

### Skill Dependency Rules
A skill is **skipped** if any of its `requires_skills` have not yet run in the current turn. For example, `bid_submit` requires `bid_compute`.

### `spending_fraction` (budget committed to bids)
| Phase | Value |
|---|---|
| `speaking` or `closed_bid` | `0.4` (40% of balance) |
| `waiting` or `serving` | `0.0` (no new bids possible) |

---

## 3. Intelligence Pipeline

**8-module DAG pipeline**, runs once per turn in the `speaking` phase.

```
DataCollector → StateBuilder → FeatureExtractor → StrategyInferrer
     → Embedding → Trajectory → Cluster → BriefingGenerator
```

### Data Sources
1. TrackerBridge → `GET /api/all_restaurants`, `/api/bid_history`, `/api/market`, `/api/meals` (Flask sidecar on port 5555, polls game server every 5s)
2. Fallback: direct game server API polling if tracker unreachable

### 14-Dimensional Feature Vector (per competitor)
Used for clustering and trajectory prediction. Captures:
- Normalised balance
- Balance delta
- Menu price relative to global average
- Menu size
- Bid activity
- Reputation delta
- Is-open flag
- Total bid spend
- Market activity (buys/sells)
- Consecutive loss streak
- Strategy class (one-hot signals)

---

## 4. Zone Selection

### Fast Path — Monopoly
```
if active_competitors == 0:
    → PREMIUM_MONOPOLIST  (no scoring needed)
```
Where `active_competitors = count(briefings where is_active=True AND menu_size > 0)`.

### Scored Path (competition exists)

```
score = revenue_potential × 0.4
      + inventory_fit     × 0.3
      - competitor_penalty × 0.2
      + reputation_bonus  × 0.1
      + monopoly_bonus
```

**`revenue_potential`**
```
avg_ceiling   = mean(ARCHETYPE_CEILINGS[arch] for arch in zone_targets)
rep_factor    = min(1.0, reputation / 100)
budget_factor = min(1.0, balance / 5000)
revenue_potential = (avg_ceiling / 250) × rep_factor × budget_factor
```

**`inventory_fit`**
```
eligible = recipes where prestige in ZONE_PRESTIGE_RANGE[zone]
cookable_score  = (# fully cookable) / len(eligible)   (weight 0.6)
partial_score   = mean(have/needed for top 10 eligible) (weight 0.4)
inventory_fit   = cookable_score × 0.6 + partial_score × 0.4
```

**`competitor_penalty`**
```
# count competitors whose strategy or menu_price matches this zone
penalty = matching_competitors / total_competitors
# Special: PREMIUM_MONOPOLIST zone gets +0.5 per competitor with avg_price > 150
# BUDGET_OPPORTUNIST zone gets +0.5 per competitor with avg_price < 80
```

**`reputation_bonus`**
| Zone | Formula |
|---|---|
| PREMIUM_MONOPOLIST | `min(1.0, reputation / 100)` |
| BUDGET_OPPORTUNIST | `0.7` (flat) |
| SPEED_CONTENDER | `0.6` (flat) |
| others | `min(1.0, (reputation + 20) / 100)` |

**`monopoly_bonus`** (only when `active_competitors ≤ 2`)
```
PREMIUM_MONOPOLIST: 0.3 × (1 - active_competitors / 5)
NICHE_SPECIALIST:   0.15 × (1 - active_competitors / 5)
others:             0.0
```

### Zone Constraints (used by ILP)
| Zone | Prestige range | Menu size (min/max) | Max prep time |
|---|---|---|---|
| PREMIUM_MONOPOLIST | 85–100 | 3–5 | 7.0 s |
| BUDGET_OPPORTUNIST | 23–60 | 6–10 | 6.0 s |
| NICHE_SPECIALIST | 50–100 | 4–6 | 10.0 s |
| SPEED_CONTENDER | 50–80 | 4–8 | 5.0 s |
| MARKET_ARBITRAGEUR | 23–100 | 1–2 | 15.0 s |

### Zone Target Archetypes
| Zone | Targets |
|---|---|
| PREMIUM_MONOPOLIST | Saggi del Cosmo, Astrobarone |
| BUDGET_OPPORTUNIST | Esploratore Galattico, Famiglie Orbitali |
| NICHE_SPECIALIST | determined at runtime |
| SPEED_CONTENDER | all archetypes |
| MARKET_ARBITRAGEUR | none (market-focused) |

---

## 5. Menu Planning (ILP)

### MILP Formulation
Decision variables: `y_j ∈ {0,1}` (include recipe j), `x_i ∈ ℤ≥0` (bid qty for ingredient i)

```
Minimise:  -Σ(revenue_j × y_j) + Σ(bid_price_i × x_i)

Subject to:
  C1: menu_min ≤ Σ y_j ≤ menu_max                         (zone menu size)
  C2: Σ(need_ij × y_j) - x_i ≤ inventory_i  ∀ ingredient  (supply coverage)
  C3: Σ(bid_price_i × x_i) ≤ balance × spending_fraction  (budget cap)
```

`expected_revenue = (Σ revenue_j × y_j) × 0.7` (30% margin of safety on fill rate)

### Greedy Fallback (MILP infeasible or error)
Recipes scored and ranked, then greedily allocated within budget:

```
prestige_score  = prestige / 100           (weight 0.30)
speed_score     = max(0, 1 - prep_time/15) (weight 0.25)
inventory_score = have / needed            (weight 0.25)
delta_bonus     = 0.1 × (# high-Δ ingredients in recipe)  (weight 0.10)
competition_penalty = Σ(demand_forecast[ing] × 0.01)       (weight −0.10)

total_score = prestige×0.3 + speed×0.25 + inventory×0.25
            + delta_bonus×0.1 - competition_penalty×0.1
```

### Zone Fallback (waiting phase, empty menu)
If primary zone yields empty menu in `waiting` phase (can't bid anymore), tries fallback zones in order: `SPEED_CONTENDER → BUDGET_OPPORTUNIST → NICHE_SPECIALIST → MARKET_ARBITRAGEUR`.

---

## 6. Bid Prices

### With no competitor wanting the ingredient

```
if active_competitors == 0:
    bid = 10  (absolute minimum — monopoly)
elif ingredient not in any competitor's top_bid_ingredients:
    bid = 15  if ingredient is HIGH_DELTA else 10
```

### With competitor wanting the ingredient

```
for each active competitor c wanting this ingredient:
    est_bid = c.predicted_bid_spend / len(c.top_bid_ingredients)
    if c.strategy == "AGGRESSIVE_HOARDER": est_bid × 1.30
    if c.strategy == "REACTIVE_CHASER":   est_bid × 1.15
    if c.strategy == "DECLINING":          est_bid × 0.70

demand_multiplier = 1.0 + min(demand_forecast[ingredient] / 20, 0.30)
bid = int(max(predicted_competitor_bids) × demand_multiplier) + 1
```

### HIGH_DELTA ingredients (from statistical analysis)
| Ingredient | Δ prestige |
|---|---|
| Polvere di Crononite | +9.93 |
| Shard di Prisma Stellare | +8.84 |
| Lacrime di Andromeda | +8.28 |
| Essenza di Tachioni | +6.04 |

### NEGATIVE_DELTA ingredients (avoid in premium!)
| Ingredient | Δ prestige |
|---|---|
| Salsa Szechuan | −9.14 |
| Cristalli di Nebulite | −7.29 |

---

## 7. Menu Prices

### Formula
```
base_ceiling   = ARCHETYPE_CEILINGS[primary_archetype_for_zone]
rep_mult       = 1.0 + (reputation - 50) / 200
prestige_mult  = 1.0 + (recipe.prestige - 50) / 200

# Competition-dependent zone factor:
if active_competitors == 0:
    zone_factor = 1.0          (monopoly — full ceiling, no discount)
else:
    zone_factor = ZONE_PRICE_FACTORS[zone]

price = int(base_ceiling × rep_mult × zone_factor × prestige_mult)
price = clamp(price, 10, int(base_ceiling × 1.30))
```

### Zone Price Factors (applied only when competitors exist)
| Zone | Factor |
|---|---|
| PREMIUM_MONOPOLIST | 0.95 |
| BUDGET_OPPORTUNIST | 0.50 |
| NICHE_SPECIALIST | 0.80 |
| SPEED_CONTENDER | 0.70 |
| MARKET_ARBITRAGEUR | 0.60 |

### Archetype Price Ceilings
| Archetype | Ceiling |
|---|---|
| Saggi del Cosmo | 250 |
| Astrobarone | 200 |
| Famiglie Orbitali | 120 |
| Esploratore Galattico | 50 |

### Competitive Adjustment (when active competitors exist)
```
avg_competitor_price = mean(c.menu_price_avg for active competitors)

PREMIUM_MONOPOLIST: price = max(price, int(avg × 1.05))   (stay premium)
BUDGET_OPPORTUNIST: price = min(price, int(avg × 0.90))   (undercut)
others: unchanged
```

### Example — PREMIUM_MONOPOLIST, reputation=100, prestige=80, no competition
```
base = 250 (Saggi del Cosmo ceiling)
rep_mult = 1.0 + (100-50)/200 = 1.25
zone_factor = 1.0 (monopoly)
prestige_mult = 1.0 + (80-50)/200 = 1.15
price = int(250 × 1.25 × 1.0 × 1.15) = 359
capped at 250 × 1.30 = 325  → price = 325
```

---

## 8. Market Operations

Runs in `speaking` and (as catchup) in `closed_bid` and `waiting`.

### Competition Level
```
competition_level = min(1.0, active_competitors / 5.0)
# 0.0 = monopoly, 1.0 = 5+ active competitors
```

### BUY logic
For each ingredient the menu **needs** but inventory is short:
```
deficit = needed_qty - inventory_qty
if deficit > 0:
    base_price = 10
    if competitor briefings available:
        intel_price = compute_bid_price(ingredient, briefings, demand_forecast)
        buy_price = int(base_price + (intel_price - base_price) × competition_level)
    else:
        buy_price = base_price
    buy_price = clamp(buy_price, 10, 100)
    → create_market_entry(BUY, ingredient, deficit, buy_price)
```

### SELL logic
For each ingredient we have that **no menu recipe** uses:
```
sell_price = max(15, int(30 × (1 + competition_level)))
→ create_market_entry(SELL, ingredient, qty, sell_price)
```

---

## 9. Serving Pipeline

### Poll-driven design
- Main loop polls `GET /meals?turn_id={turn_id}` on a fixed interval  
- `client_spawned` SSE event triggers an **immediate** extra poll (after 0.3 s propagation delay)
- Fall-through: polls fire on `POLL_INTERVAL = 1.5 s` regardless

### Per-client serving flow
```
1. Match orderText → dish  (OrderMatcher, see §10)
2. Intolerance check       (best-effort, archetype "unknown")
   → if unsafe: try any other cookable dish
3. Ingredient availability check (_can_cook)
   → if can't cook main dish: fallback to any cookable dish
   → if nothing cookable: close restaurant
4. Commit ingredients      (BEFORE prepare_dish, prevents double-commit)
5. MCP: prepare_dish(dish_name)
6. On preparation_complete SSE: MCP: serve_dish(dish_name, client_id)
```

### MCP Retry Policy
```
MAX_MCP_RETRIES = 3
MCP_RETRY_BASE_DELAY = 0.3 s   (exponential back-off × attempt)
```

### Preparation Timeout (watchdog)
```
timeout = prep_time × PREP_TIMEOUT_MULTIPLIER + PREP_TIMEOUT_BUFFER
        = prep_time × 2.5 + 5.0 seconds
```
Timed-out preparations release committed ingredients back.

### Overflow / Auto-close
When no dish can be prepared from remaining inventory → `close_restaurant()` immediately.

### Error back-off
After `5` consecutive `/meals` 400/500 errors → sleep 10 s before retrying.

---

## 10. Order Matching

Three-tier with no LLM — 90%+ hit rate expected.

| Tier | Method | Threshold |
|---|---|---|
| 1 | Exact normalized lookup (pre-built dictionary with prefix variants) | exact |
| 2 | Fuzzy (`difflib.get_close_matches`) | cutoff 0.70, then 0.55 |
| 3a | Substring: dish name ⊂ order OR order ⊂ dish name | exact substring |
| 3b | Token overlap: `\|order_tokens ∩ dish_tokens\| / \|dish_tokens\|` | ≥ 0.40 |
| fallback | Any cookable dish from current inventory | always |

**Normalisation before matching:** lowercase → strip common Italian/English prefixes (`"vorrei"`, `"i'd like"`, `"please give me"`, etc.) and suffixes (`"please"`, `"per favore"`, `"grazie"`, `.`, `!`).

---

## 11. Diplomacy

### Skip conditions (return immediately, no messages)
```
if competitor_briefings is empty:           → skip (no intel yet)
if ALL competitors have strategy=DORMANT:   → skip (no one to target)
```

### Target selection — `DeceptionBandit.select_target_and_strategy`

For each non-DORMANT competitor:
```
if opportunity_level > 0.3:   → select arm (Thompson Sampling) → craft deception
elif threat_level > 0.5:      → build threat response
```

**Fallback** (when no competitor passes thresholds): send a `price_anchoring` message to the highest-scoring candidate (score = `opportunity + threat × 0.7`). Always send at least one message when competitors exist.

Max messages per turn: **3** (top-3 by priority).

### Arm selection — Thompson Sampling
Each competitor × arm has `[alpha, beta]` priors (start at `[1.0, 1.0]` = uniform).  
Each arm: sample from `Beta(alpha, beta)` → pick arm with highest sample.  

Reward update after next turn:
```
reward > 0  → alpha += 1  (success)
reward = 0  → beta  += 1  (no effect)
```

### Arms
| Arm | Desired effect |
|---|---|
| `ingredient_misdirect` | competitor bids away from their top ingredient |
| `manufactured_scarcity` | competitor overbids on a vulnerable ingredient |
| `price_anchoring` | competitor raises their menu prices |
| `alliance_offer` | offered to declining teams for cooperation |
| `truthful_warning` | build credibility by sharing verifiable info |
| `inflated_intel` | redirect demand with false "hot recipe" signal |
| `silence` | do nothing (returns None, excluded from actions) |

### Reward Measurement (post-turn)
Compares pre/post competitor state from tracker:
| Desired effect | Reward condition |
|---|---|
| `bid_away_from_ingredient` | target's bid ingredients shrunk |
| `raise_prices` | target's avg menu price increased by ≥ 5% |
| `overbid_on_ingredient` | target's total bid spend increased by ≥ 15% |
| `alliance_cooperation` | target has market sells (they traded) |

---

## 12. Strategy Inference (Competitors)

Highest-confidence hypothesis wins. Rules evaluated in order:

| Strategy | Conditions | Confidence |
|---|---|---|
| `PREMIUM_MONOPOLIST` | avg_price > 150 AND menu_size ≤ 5 | `min(0.9, avg_price/250)` |
| `BUDGET_OPPORTUNIST` | avg_price < 100 AND menu_size ≥ 6 | `min(0.85, menu_size/15)` |
| `AGGRESSIVE_HOARDER` | recent_bid_spend (last 2 turns) > balance × 0.3 | `min(0.8, bid_spend/balance)` |
| `MARKET_ARBITRAGEUR` | market_entries > 3 AND menu_size ≤ 2 | `0.7` (flat) |
| `REACTIVE_CHASER` | menu_change_rate (across history) ≥ 0.6 | `min(0.75, rate)` |
| `DECLINING` | balance_delta < 0 AND reputation_delta ≤ 0 for ≥ 2 consecutive turns | `min(0.9, consecutive_losses × 0.3)` |
| `DORMANT` | NOT is_open AND menu_size == 0 AND balance ≥ 7500 | `0.95` |
| `UNCLASSIFIED` | none of the above | `0.0` |

### Cluster strategies and responses
| Strategy | Our response |
|---|---|
| STABLE_SPECIALIST | Coexist — reinforce their niche |
| REACTIVE_CHASER | Generous Tit-for-Tat — feed slightly wrong signals |
| AGGRESSIVE_HOARDER | Targeted Spoiler — bid-deny their top 2 items |
| DECLINING | Ignore — offer cheap alliance |
| DORMANT | Monitor only |
| UNCLASSIFIED | Probe — 1 cooperative message, classify reply |

---

## 13. Threat & Opportunity Levels

Computed by `AdvancedTrajectoryPredictor` for each competitor.

### Threat Level
```
threat = 0.0
if balance > 7000: threat += 0.2
if balance > 5000: threat += 0.1   (only one of these applies)
if len(predicted_bids) > 5: threat += 0.3 else threat += 0.1
if reputation > 90: threat += 0.1
threat += 0.1  (menu overlap placeholder)
threat = min(1.0, threat)
```

Max reachable: `0.2 + 0.3 + 0.1 + 0.1 = 0.7` (rich, many bids, high rep)

### Opportunity Level
```
opportunity = 0.0
if len(history) >= 2 and balance_delta < -200: opportunity += 0.3
if balance < 4000:                              opportunity += 0.2
if reputation < 80:                             opportunity += 0.2
if strategy == "REACTIVE_CHASER":               opportunity += 0.3
opportunity = min(1.0, opportunity)
```

Max reachable: `0.3 + 0.2 + 0.2 + 0.3 = 1.0`

### Trajectory Prediction
Feature-space momentum (level 1):
```
velocity = features[-1] - features[-2]
if len >= 3:
    prev_velocity = features[-2] - features[-3]
    velocity = 0.7 × velocity + 0.3 × prev_velocity   (momentum_factor=0.7)
predicted = features[-1] + velocity
```

Balance prediction (level 2): Exponential weighted mean of last 5 balance deltas  
(weights: `0.5^(n-1-i)` for position i).

---

## 14. Constants Reference

### Bid prices — base fallback (when tracker unavailable)
| Ingredient | Base bid |
|---|---|
| Polvere di Crononite | 60 |
| Shard di Prisma Stellare | 55 |
| Lacrime di Andromeda | 50 |
| Essenza di Tachioni | 45 |
| Frutti del Diavolo | 40 |
| Gnocchi del Crepuscolo | 35 |
| Polvere di Stelle | 35 |
| (all others) | 20 |

### Poll & timing constants
| Constant | Value |
|---|---|
| `POLL_INTERVAL` | 1.5 s (serving /meals poll) |
| `POLL_TRIGGER_DELAY` | 0.3 s (wait after client_spawned) |
| `PREP_TIMEOUT_MULTIPLIER` | 2.5 × prep_time |
| `PREP_TIMEOUT_BUFFER` | 5.0 s |
| `MAX_MCP_RETRIES` | 3 |
| `MCP_RETRY_BASE_DELAY` | 0.3 s |
| `MAX_CONSECUTIVE_ERRORS` | 5 (then back off to 10 s) |
| Tracker poll interval | 5 s (Flask sidecar) |

### Model routing
| Usage | Model |
|---|---|
| Primary (diplomacy messages, complex decisions) | `gpt-oss-120b` |
| Fast (lightweight/quick decisions) | `gpt-oss-20b` |
| Vision | `qwen3-vl-32b` |
