# Hackapizza 2.0 — Strategy Document
## *Behavioral Embedding & Competitive Geometry*

---

## The Core Idea in One Sentence

> While every other team asks *"how do I optimize my restaurant?"*, we ask *"what is the geometry of this competition?"* — then we occupy the space nobody else is standing in.

---

## The Problem With Every Other Approach

Most teams will converge on one of two paths:

**Path A — The Agent Swarm**: multiple LLM agents reasoning about bids, menus, clients, diplomacy. Expensive, slow, hard to debug under time pressure, and every agent is guessing.

**Path B — The Optimizer**: one big loop trying to maximize revenue each turn in isolation. Locally optimal, globally blind.

Both approaches share the same fatal flaw: **they only model themselves**. They treat other restaurants as background noise. They never ask what the competitive landscape looks like as a whole, or where within it the real opportunity lives.

We do something fundamentally different.


The key principle: **LLMs extract structure, math makes decisions, code executes instantly.**


## Behavioral Embedding (The Core Innovation)

This is what makes our approach genuinely different.

### The Insight

Every restaurant's behavior across turns — what they bid, how much, what menu they set, which clients they target, how they react to market changes — is not a random sequence of actions. It is a **projection of an underlying strategy vector**.

We recover that vector. We map every restaurant into a shared **behavioral space**. We find where we should be standing.

### Building the Feature Vector

Each turn, for each restaurant, we observe:

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
    "client_diversity":     entropy(client_archetype_distribution)
}
```

After 3–4 turns we have a matrix of shape `(n_restaurants × n_features × n_turns)`. We reduce this to 2D using **PCA** for the live visualization and **UMAP** for the internal clustering.

### The Strategy Space Map

```
        HIGH PRICE POSITIONING
               │
    ┌──────────┼──────────────────────┐
    │          │                      │
    │  [Sage   │    [Premium          │
    │  Chasers]│    Generalists]      │
    │    ●     │       ●   ●          │
    │          │                      │
────┼──────────┼──────────────────────┼────
SPEC│          │            DIVERSIFIED│
    │          │    ← YOU →           │
    │          │        ○             │
    │          │   (unoccupied gap)   │
    │  [Budget │    [Volume           │
    │  Racers] │    Players]          │
    │   ● ●    │        ●             │
    └──────────┼──────────────────────┘
               │
        LOW PRICE POSITIONING
```

The unoccupied region is not random. It represents a **viable strategy that nobody has claimed yet**. The ILP positions us there.

### Trajectory Analysis — Predict Before They Move

Static position tells us where everyone is. **Trajectory tells us where they're going.**

```python
# Each restaurant has a velocity vector in strategy space
velocity = current_position - previous_position

# Fit momentum model with recency weighting
predicted_position = current_position + velocity * momentum_factor

# If competitor is moving toward our region → preemptively shift
# If competitor is moving away → the gap is opening, exploit it
```

This gives us **one full turn of advance notice** on competitor strategy shifts. We're not reacting — we're already there.

### The Feedback Loop

```
Observe competitor behavior
        ↓
Update embedding + trajectories
        ↓
ILP finds unoccupied viable region
        ↓
We position there
        ↓
Competitors observe us and react
        ↓
They move toward where we were
        ↓
We've already moved to the next gap
        ↓
        (repeat)
```

We are always one step ahead because we are modeling the **space**, not the game.

---

## Layer 3 — Execution Engine

Once the strategy is set, execution is pure deterministic code. No LLMs, no latency, no reasoning errors.

### The ILP Solver

Each turn we solve an Integer Linear Program in under 1 second:

**Decision variables:**
- How many units of each ingredient to bid on
- Which dishes to put on the menu and at what price
- Which dish to assign to each arriving client archetype

**Objective:** maximize expected revenue this turn while maintaining strategic position in the embedding space

**Constraints:**
- Cannot spend more than current balance
- Cannot cook a dish without required ingredients
- Cannot serve a dish that violates client intolerances
- Cooking time must fit within serving window
- Ingredient quantities bounded by auction outcome

```python
from scipy.optimize import milp, LinearConstraint, Bounds

# solve in milliseconds
result = milp(
    c=-expected_revenue_vector,    # maximize revenue
    constraints=ingredient_constraints,
    integrality=integrality_vector,
    bounds=bounds
)
```

### Auction Strategy — The Bid Calculator

The blind auction is a **repeated incomplete information game**. After each turn bid history is public. We exploit this.

For each ingredient we need:
```python
# Predict what competitors will bid based on their history
predicted_competitor_max = weighted_average(
    competitor_bid_history[ingredient],
    recency_weight=0.65
)

# Bid just above their predicted max — win cheaply
if ingredient in critical_ingredients:
    our_bid = predicted_competitor_max + epsilon       # must win
else:
    our_bid = predicted_competitor_max * 0.85          # okay to lose
```

**Monopolization logic:** for ingredients with high criticality score (required by many recipes, scarce, non-substitutable) we bid to monopolize, then sell surplus on the market at a premium. We become the infrastructure other restaurants depend on.

```python
criticality_score = (
    (recipes_requiring_it / total_recipes) *
    (1 / market_quantity_available) *
    (1 / num_substitute_ingredients)
)

# Top 1-2 ingredients by criticality → monopolize
# Everything else → bid only what we need
```

### Serving Pipeline

Client arrives → perception agent parses order (async) → ILP lookup table finds optimal dish → `prepare_dish` → `serve_dish`.

The entire pipeline runs in milliseconds. No LLM blocking the serving phase. We never miss a client because we were waiting for a response.

---

## Temporal Strategy — Backward Induction

Most agents play as if the game is infinite. Ours knows it is **finite** and plays accordingly.

```
TURN 1–2:   Observation mode
            Minimal bids, gather data, build competitor models
            Appear non-threatening, let patterns emerge

TURN 3–N:   Embedding active
            Find the gap, position quietly
            Monopolize key ingredients
            Serve consistently, build reputation

FINAL TURNS: Backward induction kicks in
            No future to protect → maximize extraction
            Use accumulated competitor intelligence for
            perfectly timed aggressive moves
```

This is the **centipede game solution**: we know exactly when to stop cooperating because we've solved the game from the end state backward.

---

## Reputation as a Compounding Asset

Reputation is not a soft metric. It is a **revenue multiplier** that compounds across turns.

The trust flywheel:
```
Serve correctly + consistently
        ↓
Reputation increases
        ↓
Better client archetypes arrive (Astrobarons, Sages)
        ↓
Higher revenue per client served
        ↓
More balance → more aggressive bidding power
        ↓
Better ingredients → better dishes
        ↓
        (loop)
```

**Non-negotiables for reputation:**
- Never violate intolerance constraints. Ever. The client parser agent handles this.
- Consistent menu positioning — don't change archetype targeting randomly
- Speed of service — never block on LLM during serving phase

---

## The Live Visualization

During the pitch we show this running live: a 2D scatter plot where every restaurant is a moving dot with a trajectory trail, and our restaurant is visibly occupying the strategic gap the others left open.

```
  ·  ·                        ·
        ●  restaurant_A
                    ●  restaurant_C
                                        ●  restaurant_D
              ●  restaurant_B

                         ○  ← US
                    (the gap)
```

The dots move in real time as turns progress. You can see:
- Competitors clustering around the same contested region
- Our trajectory quietly finding the open space
- Competitors eventually noticing and moving toward where we *were*

**This image alone communicates the strategy faster than any slide.**

---

## What This Gives Us

| Capability | How | Advantage |
|---|---|---|
| Predict competitor bids | Bid history + weighted average model | Win ingredients cheaply |
| Find strategic gaps | PCA/UMAP embedding of all restaurants | Own unclaimed market space |
| Optimal resource allocation | ILP solver | Mathematically provable turn-level optimality |
| Instant client serving | Pure code execution | Never miss a client |
| Long-term planning | Trajectory prediction + backward induction | Always one step ahead |
| Monopolization | Ingredient criticality scoring | Become infrastructure, not just a restaurant |

---

## The Pitch — 2 Minutes

> "Every team built agents to play the game. We built a system to understand the game as a whole.
>
> We embedded every restaurant's behavior into a vector space — tracking not just what they do, but the trajectory of where they're going. That map told us something simple: there was a region of viable strategy that nobody occupied.
>
> So we went there. Quietly. While everyone else fought over the same contested resources, our ILP solver positioned us in the gap, our bid calculator won critical ingredients for just above what competitors predicted to pay, and our serving engine handled every client in milliseconds — no LLMs blocking the pipeline.
>
> The result is a system that doesn't compete. It finds where competition isn't happening, and owns that space.
>
> [show live visualization]
>
> Every dot is a restaurant. Every trail is their strategy evolution. The circle is us. Notice where we are."

---

## Technical Stack Summary

| Component | Technology | Why |
|---|---|---|
| Perception agents | `datapizza-ai` + `gpt-oss-120b` | Structured extraction, small focused prompts |
| Behavioral embedding | `numpy` + `sklearn` PCA/UMAP | Fast, local, no API calls |
| ILP solver | `scipy.optimize.milp` | Exact optimal solution in <1s |
| Competitor modeling | `numpy` weighted statistics | Simple, interpretable, effective |
| Execution engine | Pure Python | Zero latency, zero failure modes |
| Live visualization | `matplotlib` / `plotly` | Real-time scatter with trajectories |
| Game communication | SSE listener + MCP tools | As required by the challenge spec |

---

## Why This Wins

**Technically**: long-term planning, memory management, efficient tool use, async event handling — every evaluation criterion is addressed by design, not by accident.

**Strategically**: we're not playing the game everyone else is playing. We're modeling the game they're all playing and finding the space they collectively leave open.

**In the pitch**: the visualization makes the insight immediately visceral. You don't have to explain it — you show it.

> *"We didn't optimize our restaurant. We optimized our position in the competitive landscape."*