# Business Trajectory — Hackapizza 2.0

**Team:** SPAM! (ID 17)  
**Starting Balance:** 1000  
**Competitors:** 24 other restaurants  
**Game Window:** ~5–7 min per turn, variable number of turns  

---

## 0. Core Financial Constraints

| Constraint | Value | Source |
|---|---|---|
| Starting balance | 1000 | game_data_reference |
| Ingredients expire every turn | 100% loss | Hackapizza instructions §6 |
| Blind auction | No price discovery until after bid | §2.2 |
| Market entries expire every turn | Cannot stockpile across turns | §9 |
| Menu can be set in speaking/closed_bid/waiting | Not during serving | Phase matrix |
| Preparation + serving only during serving phase | ~5–7 min window | §2.4 |
| Balance is the sole win metric | Maximize end-of-game balance | §11 |
| 25 restaurants competing for same ingredient pool | | game_data_reference |
| 287 recipes available to all teams equally | No exclusive access | |

### Revenue Formula (per turn)

$$\text{Turn Profit} = \sum_{i} \text{price}_i \cdot \mathbb{1}[\text{served}_i] - \sum_{j} \text{bid\_cost}_j$$

Where:
- Revenue only from **successfully served** dishes (correct recipe, no intolerance violation)
- Unsold ingredients = sunk cost (they expire)
- Failed serves (wrong dish, intolerance) = zero revenue + wasted ingredients

---

## 1. Recipe Pool Segmentation

Based on our statistical analysis, we segment the 287 recipes into operational tiers:

### 1.1 Premium Core (15 recipes) — The Profit Engine

Recipes with **prestige ≥ 85**, **≤ 6 ingredients**, and **prep time ≤ 7s**. These are lean, fast, and elite.

| Recipe | Prestige | # Ing | Prep (s) | P/Ing | P/Sec |
|---|---|---|---|---|---|
| Portale Cosmico: Sinfonia di Gnocchi del Crepuscolo… | 100 | 5 | 5.2 | 20.0 | 19.1 |
| Sinfonia Temporale di Fenice e Xenodonte… | 95 | 5 | 4.0 | 19.0 | 23.5 |
| Più-dimensionale Sinfonia di Sapori… | 95 | 6 | 4.8 | 15.8 | 19.6 |
| Sinfonia Quantica dell'Oceano Interstellare | 94 | 6 | 4.0 | 15.7 | 23.5 |
| Sinfonia Celeste dell'Equilibrio Temporale | 92 | 6 | 9.4 | 15.3 | 9.8 |
| Sinfonia di Multiverso: La Danza degli Elementi | 90 | 5 | 5.6 | 18.0 | 16.2 |
| Sinfonia Aromatica del Multiverso | 89 | 5 | 6.7 | 17.8 | 13.4 |
| Viaggio Cosmico nel Multiverso | 89 | 5 | 6.9 | 17.8 | 13.0 |
| Sinfonia Celestiale di Gnocchi del Crepuscolo | 88 | 6 | 4.5 | 14.7 | 19.7 |
| Galassia nel Piatto: Sinfonia di Sapori e Dimensioni | 87 | 6 | 9.8 | 14.5 | 8.8 |
| Piastrella Celestiale di Gnocchi del Crepuscolo… | 86 | 5 | 10.8 | 17.2 | 7.9 |
| Sinfonia del Multiverso Calante | 85 | 5 | 4.0 | 17.0 | 21.4 |
| Sinfonia Cosmica di Terracotta | 85 | 5 | 6.8 | 17.0 | 12.5 |
| Sinfonia Cosmica di Andromeda | 85 | 5 | 9.2 | 17.0 | 9.2 |
| Sinfonia Cosmica all'Alba di Fenice | 85 | 6 | 13.9 | 14.2 | 6.1 |

**Key property:** All 15 recipes require only 5–6 ingredients. Average prep = 7.0s. 5 of them prep in under 5s.

### 1.2 Speed Tier (20 recipes) — Throughput Maximizers

All recipes with **prep time ≤ 5s** (regardless of prestige). For high-volume turns where serving speed matters most.

- These range from prestige 25 to 100.
- Average prestige ~73, but the fast + high-prestige overlap with Premium Core.
- Use these when the serving window is short and client volume is high.

### 1.3 Budget Tier (66 recipes) — Volume Play

Recipes with **prestige < 50** and **≤ 6 ingredients**. Cheap to produce, easily replaceable.

- Target: Esploratori Galattici and Famiglie Orbitali (price-sensitive).
- Low bid cost because ingredients are common (high-frequency ingredients dominate here).
- Risk: low margin per dish, requires volume.

### 1.4 Mid-Range (remaining ~186 recipes) — Fallback Pool

Prestige 50–84, variable complexity. Used opportunistically when premium ingredients are unavailable.

---

## 2. Client Archetype Economics

| Archetype | Time Tolerance | Budget | Quality Need | Optimal Strategy |
|---|---|---|---|---|
| 🚀 Esploratore Galattico | Low (rush) | Low | Low | Cheap + fast dishes, volume pricing |
| 💰 Astrobarone | Very low (rush) | High | High | Premium + fast, high price |
| 🔭 Saggi del Cosmo | High (patient) | High | Very high | Ultra-premium, top price |
| 👨‍👩‍👧‍👦 Famiglie Orbitali | High (patient) | Medium | Medium | Balanced quality/price |

### Revenue Potential per Archetype (estimated)

| Archetype | Price Range Estimate | Prestige Requirement | Speed Requirement | Revenue/Dish |
|---|---|---|---|---|
| Esploratore | Low (budget) | Any | Fast (<5s) | Low |
| Astrobarone | High (premium) | ≥ 70 | Fast (<5s) | High |
| Saggi | Very high | ≥ 85 | Any | Very high |
| Famiglie | Medium | 50–80 | Any | Medium |

**The critical insight:** Astrobaroni and Saggi are the most profitable client archetypes. Our Premium Core recipes serve exactly these segments. Famiglie are solid margin. Esploratori are margin-negative unless we run very lean.

---

## 3. Bidding Economics

### 3.1 Ingredient Demand Model

There are **62 unique ingredients** shared across **25 restaurants**. Each turn, all 25 restaurants bid for the same limited pool.

**Expected competition level per ingredient:**

| Ingredient Type | Frequency (recipes) | Expected Bidders | Bid Strategy |
|---|---|---|---|
| Common staples (Carne di Balena, Pane di Luce, Carne di Kraken) | 60+ recipes | High (15–25 teams) | Bid conservatively — everyone wants them, price wars erode margin |
| Mid-frequency (Riso di Cassandra, Uova di Fenice, Teste di Idra) | 40–55 recipes | Medium (10–15 teams) | Moderate bids — good availability, reasonable prices |
| Rare prestige-boosters (Polvere di Crononite, Lacrime di Andromeda, Shard di Prisma Stellare) | 24–28 recipes | Low–medium (5–12 teams) | **Bid aggressively** — fewer competitors, high prestige payoff |
| Very rare (Cioccorane, Spore Quantiche, Frutti del Diavolo) | 1–21 recipes | Low (2–8 teams) | Situational — only bid if targeted recipe requires it |

### 3.2 Optimal Bid Budget Per Turn

With 1000 starting balance and ingredients expiring every turn, we must budget each turn as a self-contained P&L:

$$\text{Max Bid Budget} = \text{Balance} \times \text{BidRatio}$$

| Game Phase | BidRatio | Reasoning |
|---|---|---|
| Turn 1–2 (learning) | 15–20% | Uncertain pricing, test the market |
| Turn 3–5 (growth) | 25–35% | Better price models, compound reputation |
| Turn 6+ (extraction) | 20–30% | Stable strategy, optimize margins |
| Low balance (<300) | 10–15% | Survival mode — minimal bids, high-margin only |
| High balance (>2000) | 30–40% | Can afford to dominate auctions |

### 3.3 Expected Ingredient Cost Model

In a 25-restaurant blind auction, expected prices depend on competition. Without historical data (first-turn cold start), estimate:

| Ingredient Rarity | Expected Cost per Unit (Turn 1) | Subsequent Turns |
|---|---|---|
| Common (>50 recipes) | 10–30 | Adjust from bid_history |
| Medium (25–50 recipes) | 20–50 | Adjust from bid_history |
| Rare (<25 recipes) | 30–80 | Adjust from bid_history |

**After Turn 1:** Use `GET /bid_history` to calibrate. Real price discovery replaces estimates.

---

## 4. Turn-by-Turn Financial Trajectory

### Assumptions

- Average ~3–8 clients per turn per restaurant (unknown, must be discovered)
- Serving window ~5–7 minutes (~300–420 seconds)
- Each dish takes 3–15s to prepare (avg 9s)
- **Maximum dishes per turn** = serving_window / avg_prep_time ≈ 300/9 ≈ **33 dishes** (theoretical max), realistically **8–20 dishes** accounting for order processing

### Phase 1: Learning (Turns 1–2)

**Objective:** Survive, learn prices, calibrate client model.

| Parameter | Value | Reasoning |
|---|---|---|
| Bid budget | 150–200 (15–20% of 1000) | Conservative, preserve capital |
| Target recipes | 3–5 mid-range (prestige 60–80) | Low risk, decent margin |
| Menu size | 4–6 dishes | Moderate variety, attract mixed clientele |
| Pricing | Moderate (aim for 2–3× ingredient cost) | Test market acceptance |
| Expected revenue | 100–300 per turn | Low volume while calibrating |
| Expected profit | −50 to +150 per turn | Break-even is success |
| End-of-phase balance | 900–1200 | Survive with data |

**Key actions:**
1. Bid on **common + some rare ingredients** to test both price curves
2. Set a balanced menu (mix of prestige tiers)
3. Track every client archetype, order pattern, and bid result
4. Use `bid_history` after Turn 1 to calibrate Turn 2 bids
5. Do NOT close the restaurant — reputation building starts now

### Phase 2: Growth (Turns 3–5)

**Objective:** Compound reputation, establish premium positioning.

| Parameter | Value | Reasoning |
|---|---|---|
| Bid budget | 250–400 (25–35% of balance) | Aggressive acquisition of premium ingredients |
| Target recipes | Shift toward Premium Core (prestige ≥85) | Reputation flywheel |
| Menu size | 4–8 dishes (skewed premium) | Attract Saggi + Astrobaroni |
| Pricing | High for premium, moderate for filler | Maximize per-dish margin |
| Expected revenue | 300–600 per turn | Growing client base |
| Expected profit | +100 to +300 per turn | Clear positive trajectory |
| End-of-phase balance | 1200–2500 | Compounding |

**Key actions:**
1. **Prioritize high-Δ ingredients** (Polvere di Crononite, Lacrime di Andromeda, Shard di Prisma Stellare)
2. Bid aggressively on rare ingredients (fewer competitors → better ROI)
3. Shift menu toward 85+ prestige dishes
4. Price premium dishes at maximum the market will bear
5. Start using competitor intelligence (what are others bidding on?)
6. Build intolerance knowledge base from any failed serves

### Phase 3: Extraction (Turns 6+)

**Objective:** Maximize profit with established position and data advantage.

| Parameter | Value | Reasoning |
|---|---|---|
| Bid budget | 20–30% of balance | Optimized spending, known prices |
| Target recipes | Premium Core (fast + high prestige) | Maximum throughput × prestige |
| Menu size | 3–5 premium dishes | Focused, all serveable |
| Pricing | Maximum per archetype | Full margin extraction |
| Expected revenue | 400–800+ per turn | Mature operation |
| Expected profit | +200 to +500 per turn | Peak efficiency |
| End-of-phase balance | Growing steadily | Compound advantage |

**Key actions:**
1. Surgical bidding — only bid on exactly what you need for planned dishes
2. Use market (inter-restaurant trading) to acquire missing ingredients cheaply
3. Sell surplus ingredients to competitors (revenue + deny resources)
4. Close restaurant temporarily if ingredient supply is bad (protect reputation)
5. Focus on speed: fastest-prep premium dishes first

---

## 5. Financial Projections (3 Scenarios)

### Scenario A: Conservative (Pessimistic)

Low client volume, high ingredient competition, some failed serves.

| Turn | Bid Cost | Revenue | Profit | Balance |
|---|---|---|---|---|
| 1 | 150 | 100 | −50 | 950 |
| 2 | 150 | 150 | 0 | 950 |
| 3 | 200 | 250 | +50 | 1000 |
| 4 | 200 | 300 | +100 | 1100 |
| 5 | 250 | 350 | +100 | 1200 |
| 6 | 250 | 400 | +150 | 1350 |
| 7 | 250 | 400 | +150 | 1500 |
| 8 | 250 | 450 | +200 | 1700 |
| 9 | 300 | 500 | +200 | 1900 |
| 10 | 300 | 500 | +200 | 2100 |
| **Total** | **2300** | **3400** | **+1100** | **2100** |

### Scenario B: Expected (Base Case)

Moderate client volume, reasonable ingredient prices, learning curve in turns 1–2.

| Turn | Bid Cost | Revenue | Profit | Balance |
|---|---|---|---|---|
| 1 | 180 | 200 | +20 | 1020 |
| 2 | 200 | 300 | +100 | 1120 |
| 3 | 280 | 450 | +170 | 1290 |
| 4 | 320 | 550 | +230 | 1520 |
| 5 | 380 | 650 | +270 | 1790 |
| 6 | 400 | 700 | +300 | 2090 |
| 7 | 420 | 750 | +330 | 2420 |
| 8 | 450 | 800 | +350 | 2770 |
| 9 | 450 | 800 | +350 | 3120 |
| 10 | 450 | 800 | +350 | 3470 |
| **Total** | **3530** | **6000** | **+2470** | **3470** |

### Scenario C: Optimistic

High client volume, good ingredient availability, quick calibration.

| Turn | Bid Cost | Revenue | Profit | Balance |
|---|---|---|---|---|
| 1 | 200 | 350 | +150 | 1150 |
| 2 | 250 | 500 | +250 | 1400 |
| 3 | 350 | 700 | +350 | 1750 |
| 4 | 400 | 850 | +450 | 2200 |
| 5 | 500 | 1000 | +500 | 2700 |
| 6 | 550 | 1100 | +550 | 3250 |
| 7 | 600 | 1200 | +600 | 3850 |
| 8 | 600 | 1200 | +600 | 4450 |
| 9 | 600 | 1200 | +600 | 5050 |
| 10 | 600 | 1200 | +600 | 5650 |
| **Total** | **4650** | **9300** | **+4650** | **5650** |

---

## 6. Breakeven Analysis

### Per-Turn Breakeven

$$\text{Breakeven} = \frac{\text{Total Bid Cost}}{\text{Avg Price per Dish}}$$

If we bid 250 per turn and price dishes at 80 on average:
$$\text{Breakeven} = 250 / 80 \approx 3.1 \text{ dishes}$$

**Serving ≥ 4 dishes per turn guarantees profitability.** With a 5-minute serving window and fast premium dishes (4–7s prep), we can prepare **40–75 dishes** in theory. Even at 25% efficiency (order parsing overhead, wait times), that's **10–18 served dishes** — well above breakeven.

### Survival Threshold

If balance drops below **200**, switch to pure survival mode:
- Bid only on the cheapest common ingredients
- Serve only budget dishes to Esploratori/Famiglie
- Use market to sell any ingredients for cash
- Never close (need reputation recovery)

---

## 7. Menu Pricing Strategy

### Pricing by Client Archetype

| Archetype | Willingness to Pay | Our Price | Prestige Served | Margin |
|---|---|---|---|---|
| Saggi del Cosmo | Very high | 120–200 | ≥ 85 | Very high |
| Astrobarone | High | 80–150 | ≥ 70 | High |
| Famiglie Orbitali | Medium | 40–80 | 50–80 | Medium |
| Esploratore Galattico | Low | 20–40 | Any | Thin |

### Dynamic Pricing Rules

1. **Premium dishes (≥85 prestige):** Price at 100–200. These attract Saggi & Astrobaroni.
2. **Mid-range dishes (60–84 prestige):** Price at 50–100. Balanced clientele.
3. **Budget dishes (<60 prestige):** Price at 20–50. Volume play for Esploratori.
4. **After Turn 3:** Increase premium prices by 10–20% if reputation is growing.
5. **If client volume drops:** Lower all prices by 10–15% to attract more traffic.

### Menu Composition (Target)

| Phase | Premium (≥85) | Mid-Range (60–84) | Budget (<60) |
|---|---|---|---|
| Turns 1–2 | 1–2 dishes | 2–3 dishes | 1–2 dishes |
| Turns 3–5 | 3–4 dishes | 1–2 dishes | 0–1 dishes |
| Turns 6+ | 3–5 dishes | 0–1 dishes | 0 dishes |

---

## 8. Ingredient Bidding Priority Matrix

Based on prestige impact (Diagram 10) and S-tier enrichment (Diagram 14):

### Tier 1 — Always Bid (High-Δ, High Enrichment)

These ingredients appear in our Premium Core recipes and have proven prestige impact.

| Ingredient | Δ Prestige | S-Tier Enrichment | p-value | Strategy |
|---|---|---|---|---|
| Polvere di Crononite | +9.93 | 1.74× | 0.003 | **Bid aggressively** — strongest signal |
| Shard di Prisma Stellare | +8.84 | 1.89× | 0.010 | **Bid aggressively** |
| Lacrime di Andromeda | +8.28 | 3.24× | 0.015 | **Bid aggressively** — highest enrichment |
| Essenza di Tachioni | +6.04 | 0.49× | 0.040 | **Bid moderately** — significant but lower enrichment |
| Polvere di Stelle | +4.84 | 3.24× | 0.200 | **Bid moderately** — high enrichment, borderline significance |

### Tier 2 — Bid if Affordable (Supporting Ingredients)

| Ingredient | Δ Prestige | Role |
|---|---|---|
| Gnocchi del Crepuscolo | +5.05 | Key in top recipe (Portale Cosmico, prestige 100) |
| Uova di Fenice | +3.61 | Common in S-tier, 1.43× enrichment |
| Teste di Idra | +4.32 | High frequency (56 recipes), versatile |
| Riso di Cassandra | +3.68 | 1.93× enrichment, appears in many premium combos |
| Carne di Mucca | +3.40 | 1.97× enrichment, surprisingly strong signal |

### Tier 3 — Avoid Unless Needed

| Ingredient | Δ Prestige | Risk |
|---|---|---|
| Salsa Szechuan | −9.14 | Strongest negative signal (p = 0.01) |
| Cristalli di Nebulite | −7.29 | Strong negative (p = 0.08) |
| Pane di Luce | −4.31 | Very common but associated with low-prestige recipes |
| Lattuga Namecciana | −3.59 | Negative, ubiquitous in budget dishes |
| Nettare di Sirena | −3.54 | Negative delta |

---

## 9. Competitive Positioning

### Market Structure (25 restaurants)

All 25 teams start identical (balance 1000, reputation 100). Differentiation happens through:
1. **Menu composition** (what you choose to serve)
2. **Pricing** (how much you charge)
3. **Bid strategy** (what ingredients you acquire)
4. **Speed** (how fast you serve during serving phase)

### Expected Competitor Archetypes

| Strategy | Expected # Teams | Our Response |
|---|---|---|
| Premium-only | 3–5 | Compete on speed + ingredient access |
| Budget/volume | 5–8 | Ignore — let them fight over common ingredients |
| Jack-of-all-trades | 8–12 | Their diluted strategy won't match our focus |
| No strategy / manual | 3–5 | Free market share |
| Sophisticated (like us) | 2–4 | Monitor via bid_history, adjust bids |

### Our Competitive Edge (by priority)

1. **Execution speed in serving:** Zero-LLM hot path means we serve faster than agent-heavy competitors
2. **Bid calibration from Turn 2+:** Using bid_history for real-time price optimization
3. **Focused ingredient acquisition:** We bid on 8–12 specific ingredients, not everything
4. **Data accumulation:** Every turn builds our client profile + competitor model
5. **Reputation compounding:** Early prestige investment pays off multiplicatively

---

## 10. Risk Matrix & Contingency Plans

| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| All bids lose (outbid on everything) | Low–Medium | High | Fall back to market trading; buy from other restaurants |
| Client sends ambiguous order | High | Medium | Pre-compute fuzzy text→recipe lookup; fallback to highest-prestige available |
| Intolerance violation (serve wrong dish) | Medium | High | Build intolerance DB from failures; err toward known-safe dishes |
| SSE connection drops | Low | Very High | Auto-reconnect with exponential backoff; state recovery from GET endpoints |
| Balance below 200 | Low | High | Survival mode: minimal bids, budget menu, sell surplus |
| Most teams pursue premium strategy | Medium | Medium | Shift to Speed Contender zone — win on throughput, not prestige |
| Rate limiting (429 errors) | Medium | Medium | Pre-compute all decisions; batch MCP calls; avoid polling loops |
| Unexpected game reset | Low | Low | All state recoverable from GET endpoints; no permanent damage |

---

## 11. Key Performance Indicators (per Turn)

| KPI | Target (Turns 1–2) | Target (Turns 3–5) | Target (Turns 6+) |
|---|---|---|---|
| Dishes served | ≥ 3 | ≥ 6 | ≥ 8 |
| Serve success rate | ≥ 70% | ≥ 85% | ≥ 90% |
| Avg dish prestige | ≥ 55 | ≥ 70 | ≥ 80 |
| Bid win rate | ≥ 40% | ≥ 60% | ≥ 70% |
| Turn profit | ≥ 0 | ≥ +100 | ≥ +200 |
| Ingredient utilization | ≥ 50% | ≥ 75% | ≥ 85% |
| Client satisfaction (no intolerance) | ≥ 90% | ≥ 95% | ≥ 98% |

---

## 12. Decision Flowchart (Per Turn)

```
Start of Turn
│
├── SPEAKING PHASE
│   ├── GET /restaurants → update competitor state
│   ├── GET /bid_history (prev turn) → update price model
│   ├── Compute zone selection (ILP)
│   ├── Select target recipes for this turn
│   ├── Set menu (save_menu MCP call)
│   ├── Open restaurant (update_restaurant_is_open → true)
│   └── Optional: send_message for diplomacy
│
├── CLOSED BID PHASE
│   ├── Compute optimal bids for target ingredients
│   │   ├── Budget = balance × BidRatio
│   │   ├── Allocate across ingredients by priority tier
│   │   └── cap each bid at max_acceptable_price from price model
│   └── Submit bids (closed_bid MCP call)
│
├── WAITING PHASE
│   ├── GET /restaurant/17 → check inventory (what we won)
│   ├── Recalculate menu based on actual inventory
│   ├── Update menu if needed (save_menu)
│   ├── Check market for missing ingredients (GET /market/entries)
│   ├── Buy from market if profitable (execute_transaction)
│   └── Sell surplus on market (create_market_entry)
│
├── SERVING PHASE
│   ├── Listen for client_spawned SSE events
│   ├── For each client:
│   │   ├── Parse orderText → match to menu item (pre-computed lookup)
│   │   ├── Check intolerance DB → skip if risky
│   │   ├── prepare_dish (MCP call)
│   │   ├── Wait for preparation_complete SSE event
│   │   ├── GET /meals → obtain client_id
│   │   └── serve_dish (MCP call)
│   ├── If ingredient supply running low → close restaurant
│   └── Log all client data for next-turn learning
│
└── STOPPED PHASE
    ├── Log final turn state
    ├── Update all models (competitor, client, price)
    └── Prepare for next turn
```

---

## 13. Summary — The SPAM! Trajectory

| Dimension | Phase 1 (Turns 1–2) | Phase 2 (Turns 3–5) | Phase 3 (Turns 6+) |
|---|---|---|---|
| **Posture** | Learn & survive | Grow & compound | Extract & dominate |
| **Menu** | Balanced (mixed tiers) | Premium-heavy | Premium-exclusive |
| **Bidding** | Conservative & broad | Aggressive on rare | Surgical & optimized |
| **Pricing** | Moderate | High on premium | Maximum extraction |
| **Target clients** | All archetypes | Saggi + Astrobaroni | Saggi + Astrobaroni |
| **Bid budget %** | 15–20% | 25–35% | 20–30% |
| **Expected balance** | 900–1200 | 1200–2500 | 2500+ (compounding) |
| **Risk tolerance** | Low | Medium–High | Medium |

**The thesis in one sentence:** Start conservative, learn fast, shift to premium once calibrated, then compound reputation and pricing power to maximize terminal balance.

---

*Derived from 287-recipe statistical analysis, 62-ingredient prestige/enrichment model, and full game constraint set.*
