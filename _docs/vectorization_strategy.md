# Hackapizza 2.0 — Strategy Document
## *Behavioral Embedding, Competitive Geometry & Silent Orchestration*

---

## The Core Idea in One Sentence

> While every other team asks *"how do I optimize my restaurant?"*, we ask *"what is the geometry of this competition?"* — then we occupy the space nobody else is standing in, and quietly move everyone else like pieces on a board.

---

## The Problem With Every Other Approach

Most teams will converge on one of two paths:

**Path A — The Agent Swarm**: multiple LLM agents reasoning about bids, menus, clients, diplomacy. Expensive, slow, hard to debug under time pressure, and every agent is guessing.

**Path B — The Optimizer**: one big loop trying to maximize revenue each turn in isolation. Locally optimal, globally blind.

Both approaches share the same fatal flaw: **they only model themselves**. They treat other restaurants as background noise. They never ask what the competitive landscape looks like as a whole, or where within it the real opportunity lives.

We do something fundamentally different.

The key principle: **LLMs extract structure, math makes decisions, code executes instantly — and intelligence about competitors becomes a weapon we use against them.**

---

## Behavioral Embedding (The Core Innovation)

This is what makes our approach genuinely different.

### The Insight

Every restaurant's behavior across turns — what they bid, how much, what menu they set, which clients they target, how they react to market changes — is not a random sequence of actions. It is a **projection of an underlying strategy vector**.

We recover that vector. We map every restaurant into a shared **behavioral space**. We find where we should be standing — and we learn enough about everyone else to move them.

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
    "client_diversity":     entropy(client_archetype_distribution),

    # Recipe & prestige signals (from extracted game statistics)
    "prestige_targeting":   avg_prestige_of_served_dishes,
    "recipe_complexity":    avg_ingredients_per_cooked_recipe,
    "prestige_consistency": std_dev(prestige_scores_over_turns)
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

And crucially: **we know what every other restaurant will do before they do it.** That prediction is not just for us. It becomes a diplomatic weapon.

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

## The Silent Orchestration Layer

This is the layer nobody will have. It is the direct consequence of having the embedding — and it is the most powerful thing in our entire system.

### The Core Idea

We can predict what every restaurant will do next turn with reasonable accuracy. That prediction is **privately valuable to other restaurants**. We can sell it, trade it, or weaponize it — selectively, surgically, and without ever revealing that we have a model.

We are not just a restaurant. We are the **hidden conductor** of the entire competitive ecosystem.

### Concrete Mechanic: Manufactured Conflict

Our embedding tells us:
- Restaurant B is a Reactive Chaser — they're moving toward the premium ingredient cluster
- Restaurant A is a Stable Specialist — they've been quietly monopolizing truffle for 3 turns
- These two are about to collide in the auction next turn

We send a message to Restaurant A during speaking phase:

> *"Hey, just a heads up — we've been watching the market and it looks like someone is moving aggressively into premium ingredients this turn. Might be worth bidding a bit higher than usual to protect your position."*

Restaurant A bids higher on truffle. Restaurant B hits unexpected resistance, loses the bid, pays more than planned, or abandons the ingredient entirely. The collision we predicted becomes a collision we engineered — **without fingerprints**.

We didn't lie. We didn't inject. We shared a true observation, selectively, at the right moment, to the right recipient.

### The Strategy Selection Matrix

Different restaurants deserve different relational strategies simultaneously. The embedding tells us which cluster each competitor belongs to — and that determines how we interact with them.

```
COMPETITOR CLUSTER          RELATIONAL STRATEGY        ORCHESTRATION MOVE
──────────────────────────────────────────────────────────────────────────
Stable Specialist           Coexist                    Share intel that
  → committed to a niche,   → silent truce, don't      reinforces their
    predictable, low threat   touch their ingredients   existing position

Reactive Chaser             Generous Tit for Tat       Feed them slightly
  → copies whatever works   → cooperate openly,        wrong signals about
                              retaliate if they enter   where the value is
                              our niche

Aggressive Hoarder          Targeted Spoiler           Tell their rivals
  → bids everything,        → bid to deny their        what they're doing
    starves others            top 2 critical items      (selectively true)

Weak / Declining            Ignore                     Optionally: offer
  → low balance, losing     → not a threat             them a real deal,
    trajectory                                          lock in their loyalty
                                                        cheaply as an ally

Unclassified / New          Probe                      Send one cooperative
  → insufficient data       → observe reaction,        message, classify
                              classify from response    from how they reply
```

This policy updates **every turn** as trajectories evolve. A Reactive Chaser who stops reacting becomes a Stable Specialist. An Aggressive Hoarder who runs low on balance becomes ignorable. The system is always current.

### Conditional Revelation — Selective Truth as a Weapon

The most subtle and powerful tool. During speaking phase we **selectively reveal partial true information** to specific competitors based on what benefits us.

Example: we know from the embedding that Restaurant B is a Reactive Chaser. We know from our recipe analysis that high-prestige Recipe X requires ingredient Y which is currently undervalued in the auction — because competitors haven't mapped the prestige payoff yet.

We tell Restaurant B: *"we've been getting great results with Recipe X this turn."*

Restaurant B starts bidding on ingredient Y. This does two things simultaneously:
- It **validates our strategy** — if they succeed, the prestige signal was real
- It **drives up the price** of Y for any future latecomers trying to copy us, while we already have supply locked in

We've used another team as a market signal amplifier. They think they received useful intelligence. They did — but timed and framed entirely for our benefit.

### The Alliance Network

Over multiple turns we maintain a **soft alliance** with 1-2 stable, non-threatening restaurants. We share genuine intelligence with them — things we'd give up anyway. In return:

- They act as an early warning system for aggressive moves we might miss
- They give us diplomatic cover — if we appear to have allies, aggressive teams factor that in
- In the final turns, if we're leading, a coordinated signal from both of us can flood a third restaurant's auction space and protect our position

The alliance is real. The information sharing is real. But the structure of who we share with and what we share is **entirely calculated**.

---

## Iterated Game Strategy — The Temporal Dimension

The relational strategies above are **what** we play. The iterated game framework tells us **when** to shift.

### Why Classic Strategies Don't Quite Fit

Tit for Tat, Grim Trigger, Pavlov — these were designed for bilateral repeated games. We have a multiplayer game with asymmetric information, limited turns, and a behavioral embedding that changes what "cooperation" means turn to turn.

The classic strategies give us a starting point. Our embedding gives us the ability to **apply the right one to the right opponent at the right time**.

### The Temporal Arc

```
TURN 1–2:   OBSERVATION MODE
            Minimal bids, appear non-threatening
            Build embedding, classify all competitors
            Probe unclassified restaurants with one cooperative message
            Identify undervalued high-prestige recipes
            Assign initial relational strategy per restaurant

TURN 3–N:   ORCHESTRATION MODE
            Execute relational strategies per competitor cluster
            Feed manufactured intel to trigger useful conflicts
            Position quietly in the embedding gap
            Monopolize key ingredients
            Serve consistently, compound reputation

FINAL TURNS: EXTRACTION MODE (Backward Induction)
            No future to protect — all restraint drops
            Grim Trigger on anyone threatening our gap
            Full resource extraction
            If leading: defensive coexistence, protect position
            If trailing: pure spoiler against the leader,
                         use alliance to flood their auction space
```

The shift from Orchestration to Extraction mode is **not arbitrary**. It is triggered by a threshold: when `turns_remaining * expected_margin_per_turn < cost_of_cooperation`, defection becomes dominant. The system calculates this automatically.

---

## Recipe & Prestige Statistics — The Data Advantage

The game statistics we extracted give us an edge no other team has built into their model.

### The Recipe Desirability Matrix

Not all recipes are equal. We score each one:

```python
recipe_score = (
    prestige_weight      * prestige_score           +  # revenue potential
    complexity_penalty   * num_ingredients_required  -  # execution risk
    competition_penalty  * num_teams_likely_cooking  -  # how contested
    scarcity_penalty     * ingredient_rarity_avg       # sourcing difficulty
)
```

The sweet spot: **high prestige, ingredients currently undervalued in auction.** This gap exists because competitors haven't mapped prestige payoffs to ingredient requirements. We have. We exploit this asymmetry before they close it.

### The Prestige Flywheel — Early Investment Dominates

Most teams optimize turn-by-turn margin. This is accounting. We do finance.

Prestige compounds into reputation. Reputation attracts higher-paying archetypes. Higher-paying archetypes generate more balance. More balance means more aggressive bidding power. More bidding power means better ingredients. Better ingredients mean higher prestige dishes.

```python
# naive: maximize this turn's revenue
value = price - ingredient_cost

# ours: maximize discounted future revenue stream
value = price - ingredient_cost + sum(
    prestige_gain * reputation_multiplier(turn) * expected_revenue_per_turn
    for turn in remaining_turns
)
```

This means in turns 1–2 we are willing to **pay above-market prices for high-prestige ingredients** even when immediate margin is negative. The trajectory value of the reputation gain dominates. By turn 5 we are serving clients others cannot attract.

### Ingredient Criticality Score

Used both for our own bidding strategy and for identifying which ingredients to monopolize or weaponize in orchestration:

```python
criticality_score = (
    (recipes_requiring_it / total_recipes) *
    (1 / market_quantity_available) *
    (1 / num_substitute_ingredients) *
    (avg_prestige_of_recipes_requiring_it / max_prestige)
)
```

Top 1–2 ingredients by criticality: **monopolize**. Become the infrastructure. Sell surplus on the market at a premium. Other restaurants either buy from us or can't cook their best dishes.

Second tier ingredients: **bid precisely** — just above predicted competitor max, no more.

Everything else: **ignore or use as decoy bids** to corrupt competitor models of us.

---

## Execution Engine

Once strategy is set, execution is pure deterministic code. No LLMs, no latency, no reasoning errors.

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

result = milp(
    c=-expected_revenue_vector,
    constraints=ingredient_constraints,
    integrality=integrality_vector,
    bounds=bounds
)
```

### Serving Pipeline

Client arrives → perception agent parses order (async, structured JSON out) → ILP lookup table finds optimal dish → `prepare_dish` → `serve_dish`.

The entire pipeline runs in milliseconds. No LLM blocking the serving phase. We never miss a client because we were waiting for a response.

---

## Reputation as a Compounding Asset

Reputation is not a soft metric. It is a **revenue multiplier** that compounds across turns.

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
Better ingredients → higher prestige dishes
        ↓
        (loop)
```

**Non-negotiables:**
- Never violate intolerance constraints. The client parser agent handles this.
- Consistent menu positioning — don't randomly shift archetype targeting
- Speed of service — never block on LLM during serving phase

---

## The Live Visualization

During the pitch we show this running live: a 2D scatter plot where every restaurant is a moving dot with a trajectory trail, and our restaurant is visibly occupying the strategic gap the others left open — with arrows showing the manufactured conflicts we triggered.

```
  ·  ·                        ·
        ●─────────→  restaurant_A
              ↑  collision engineered here
        ●─────→  restaurant_B

                                        ●  restaurant_D

                         ○  ← US
                    (we were never in the collision)
```

The dots move in real time as turns progress. You can see:
- Competitors clustering around the same contested region
- Manufactured conflicts between restaurants we predicted and triggered
- Our trajectory quietly finding the open space
- Competitors chasing where we were while we're already somewhere else

**This image alone communicates the strategy faster than any slide.**

---

## What This Gives Us

| Capability | How | Advantage |
|---|---|---|
| Predict competitor bids | Bid history + weighted average model | Win ingredients cheaply |
| Find strategic gaps | PCA/UMAP embedding | Own unclaimed market space |
| Optimal resource allocation | ILP solver | Mathematically provable optimality |
| Instant client serving | Pure code execution | Never miss a client |
| Long-term planning | Trajectory prediction + backward induction | Always one step ahead |
| Monopolization | Ingredient criticality scoring | Become infrastructure |
| Silent orchestration | Selective intel sharing via diplomacy agent | Move competitors without touching them |
| Prestige compounding | Recipe desirability matrix + future value model | Attract clients others can't reach |
| Manufactured conflict | Trajectory prediction → targeted messages | Remove threats before they materialize |

---

## Technical Stack Summary

| Component | Technology | Why |
|---|---|---|
| Perception agents | `datapizza-ai` + `gpt-oss-120b` | Structured extraction, small focused prompts |
| Behavioral embedding | `numpy` + `sklearn` PCA/UMAP | Fast, local, no API calls |
| ILP solver | `scipy.optimize.milp` | Exact optimal solution in <1s |
| Competitor modeling | `numpy` weighted statistics | Simple, interpretable, effective |
| Orchestration engine | Pure Python + diplomacy agent | Surgical message targeting |
| Execution engine | Pure Python | Zero latency, zero failure modes |
| Live visualization | `matplotlib` / `plotly` | Real-time scatter with trajectories + conflict arrows |
| Game communication | SSE listener + MCP tools | As required by the challenge spec |

---

## The Pitch — 2 Minutes

> "Every team built agents to play the game. We built a system to understand the game as a whole — and then reshape it.
>
> We embedded every restaurant's behavior into a vector space. Not just where they are, but where they're going. That map gave us two things: the gap nobody was standing in, and the ability to predict every competitor's next move before they made it.
>
> We went to the gap. Quietly. Our ILP solver positioned us there, our bid calculator won critical ingredients for just above what competitors would pay, and our serving engine handled every client in milliseconds.
>
> But the embedding gave us something else. We knew that Restaurant B was about to collide with Restaurant A over premium ingredients. So we told Restaurant A — truthfully — to watch out. They bid higher. Restaurant B hit a wall they didn't expect. We were never involved.
>
> We did this systematically. Not deception. Selective truth, surgically timed, based on trajectory predictions the other teams didn't know we had.
>
> [show live visualization]
>
> Every dot is a restaurant. Every trail is their strategy. The arrows are conflicts we manufactured. The circle is us — in the gap, watching it all unfold.
>
> We didn't compete. We conducted."

---

## Why This Wins

**Technically**: long-term planning, memory management, efficient tool use, async event handling, inter-agent communication — every evaluation criterion addressed by design.

**Strategically**: we're not playing the game everyone else is playing. We're modeling the entire competitive system, finding the gap, and moving the other pieces.

**In the pitch**: the visualization makes the insight immediately visceral. The collision arrows make the orchestration layer tangible. You don't explain it — you show it happening in real time.

> *"We didn't optimize our restaurant. We optimized the entire competitive landscape — and then found the one place in it where nobody could touch us."*