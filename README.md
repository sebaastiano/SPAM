# SPAM!

Autonomous agent system for a competitive restaurant simulation game. Each turn the system reasons about zone placement, menu composition, ingredient bidding, pricing, and diplomatic manipulation.

---

## Core Strategies

### 1. LLM Strategic Planner (`src/decision/strategy_agent.py`)

A `gpt-oss-120b`-powered **StrategyAgent** acts as the turn brain. It produces a structured `TurnStrategy` JSON before any skill runs, setting parameters for every downstream module: which zone to target, how aggressively to bid, what price multiplier to apply, and which diplomatic posture to take.

### 2. Zone-Based Decision Routing (`src/decision/subagent_router.py`, `zone_selector.py`)

The market is segmented into strategic zones (e.g. `DIVERSIFIED`, `PREMIUM`, `BUDGET`). An algorithmic heuristic picks the zone; the StrategyAgent can override it when confidence ≥ 0.5. Each zone maps to a dedicated `datapizza` Agent with a tailored system prompt.

### 3. ILP Menu & Bid Optimizer (`src/decision/ilp_solver.py`)

Integer Linear Programming solves menu composition and ingredient bid allocation under budget and prep-time constraints, guided by the StrategyAgent's `bid_aggressiveness` and `menu_*` parameters.

### 4. Dynamic Pricing (`src/decision/pricing.py`)

Prices are computed per recipe based on competitor observations, then multiplied by the strategy agent's `price_adjustment_factor`. Undercutting mode is toggled by the agent.

### 5. Competitive Intelligence Pipeline (`src/intelligence/`)

A `DagPipeline` DAG runs every turn:

```
DataCollector → StateBuilder → FeatureExtractor → StrategyInferrer
→ Embedding → TrajectoryPredictor → ClusterClassifier → BriefingGenerator
```

- **StrategyInferrer** classifies each competitor into archetypes: `PREMIUM_MONOPOLIST`, `BUDGET_OPPORTUNIST`, `AGGRESSIVE_HOARDER`, `MARKET_ARBITRAGEUR`, `REACTIVE_CHASER`, `DECLINING_PASSIVE`, `DORMANT`.
- **TrajectoryPredictor** forecasts competitor behavior over the next few turns.
- **VectorStore** holds competitor embeddings for similarity search and clustering.

### 6. Deception Bandit (`src/diplomacy/deception_bandit.py`)

**Thompson Sampling** (Beta priors, per-competitor) selects from 7 manipulation arms:
`truthful_warning` · `inflated_intel` · `manufactured_scarcity` · `ingredient_misdirect` · `alliance_offer` · `price_anchoring` · `silence`

Rewards are measured by observable competitor state changes (bid shifts, menu price changes) tracked across turns.

### 7. Pseudo-GAN Message Crafter (`src/diplomacy/pseudo_gan.py`)

A generator (`gpt-oss-120b`) drafts diplomatic messages in Italian; a discriminator (`gpt-oss-20b`) scores believability. The loop refines up to 3 iterations until score > 0.7. Messages are grounded in real tracker intel to maximize credibility.

### 8. Ground Truth Firewall (`src/diplomacy/firewall.py`)

Incoming competitor messages are filtered and cross-checked against observed game state to prevent our own agent from acting on manipulated intel.
