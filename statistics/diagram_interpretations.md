# Diagram Interpretations — Hackapizza 2.0 Statistical Analysis

This document provides a detailed interpretation of each of the 16 diagrams generated from the analysis of 287 recipes and 62 unique ingredients.

---

## 01 — Prestige Distribution

![Prestige Distribution](graphs/01_prestige_distribution.png)

**What it shows:** Three views of the same data — a histogram, a kernel density estimate (KDE), and a box-and-whisker plot with individual data points — for the prestige scores of all 287 recipes.

**Interpretation:**

- The distribution is roughly **unimodal and slightly right-skewed**, centered around a mean of ~62.8 and a median of 62. The mean and median being almost identical confirms near-symmetry with a slight lean toward higher values.
- The histogram reveals a broad plateau between ~35 and ~80. There is no sharp peak: recipes are spread relatively evenly across the mid-range, with thinning tails below 30 and above 90.
- The KDE smooths out binning artifacts and shows the underlying shape more clearly — a wide bell with slightly heavier density in the 40–75 band.
- The box plot shows the IQR spans from 50 to 75 (a 25-point range), meaning **half of all recipes fall within that band**. The whiskers extend to 23 and 100, confirming the full range.
- **Strategic takeaway:** Prestige is widely distributed, and truly elite recipes (≥90) are rare (only 19 out of 287 = 6.6%). Getting consistently high-prestige meals on the menu requires deliberate ingredient selection, not random sampling.

---

## 02 — Preparation Time Distribution

![Prep Time Distribution](graphs/02_prep_time_distribution.png)

**What it shows:** Histogram, KDE, and box plot for preparation times (in seconds) across all recipes.

**Interpretation:**

- Preparation times range from ~3s to ~15s with a mean of 9.0s and a standard deviation of 3.48s.
- The histogram and KDE show that prep times are spread roughly **uniformly** across the range, without a strong single mode — there are roughly equal counts at most integer-second values from 3 to 15.
- The box plot confirms the IQR runs from 6s to 12s, with the median at 9s sitting right in the center.
- There is no obvious bimodal structure (e.g., "quick dishes" vs "slow dishes"): the dataset is continuous across the range.
- **Strategic takeaway:** Preparation time is a real constraint during the serving phase. Faster dishes (≤5s) let you serve more clients per round. Since prep time has no strong positive correlation with prestige (see Diagram 06), **prioritizing faster recipes doesn't sacrifice quality**.

---

## 03 — Ingredient Count Distribution

![Ingredient Count Distribution](graphs/03_ingredient_count_distribution.png)

**What it shows:** A bar chart showing the number of recipes for each possible ingredient count (5 through 11).

**Interpretation:**

- The most common ingredient count is **5** (75 recipes, 26%) followed by **6** (66 recipes, 23%). Together, 5–6 ingredient recipes account for nearly half the dataset.
- The count drops progressively: 7 (51), 8 (41), 9 (31), 10 (19), 11 (4).
- The distribution is **right-skewed** — simpler recipes are more common than complex ones.
- **Strategic takeaway:** Fewer ingredients means fewer items to bid on and acquire. Since 5-ingredient recipes can reach prestige 100 (see the efficiency analysis), complexity is not required for excellence. Prefer economical recipes during bidding.

---

## 04 — Number of Ingredients vs Prestige (Scatter)

![Ingredients vs Prestige](graphs/04_ingredients_vs_prestige.png)

**What it shows:** A scatter plot of ingredient count (x, jittered for visibility) against prestige (y), color-coded by prestige, with a linear regression line.

**Interpretation:**

- The Pearson r = 0.17 (p = 0.004) indicates a **statistically significant but very weak positive correlation**: more ingredients → slightly higher prestige on average.
- The scatter shows enormous variance at every ingredient count. At n=5, prestige ranges from 23 to 100. At n=10, it ranges from ~30 to ~95. The regression line is nearly flat.
- The color gradient (dark = low prestige, bright = high prestige) is scattered randomly across all x-values, reinforcing that ingredient count is a poor predictor of quality.
- **Strategic takeaway:** Do NOT assume more-complex recipes are better. The identity of ingredients matters far more than the quantity. Focus bidding strategy on acquiring the *right* ingredients, not the *most*.

---

## 05 — Mean Prestige by Ingredient Count (Bar with Std Dev)

![Mean Prestige by Ingredient Count](graphs/05_mean_prestige_by_ing_count.png)

**What it shows:** Bar chart of mean prestige at each ingredient count, with standard deviation error bars and sample sizes (n=...).

**Interpretation:**

- Mean prestige rises gently from ~59 (at 5 ingredients) to a peak of ~70 (at 9 ingredients), then drops back to ~63–65 at 10–11.
- The error bars are large at every count (±15–18 points), completely overlapping across all groups. This confirms the weak correlation: the differences in means are dwarfed by within-group spread.
- The peak at 9 is based on only 31 recipes, and at 11 there are only 4 — small samples make those estimates less reliable.
- **Strategic takeaway:** The "sweet spot" around 9 ingredients is suggestive but not reliable. The variance within each group is so high that ingredient count alone is not a useful decision variable. Again, **which** ingredients you have determines prestige, not how many.

---

## 06 — Preparation Time vs Prestige (Scatter)

![Prep Time vs Prestige](graphs/06_prep_time_vs_prestige.png)

**What it shows:** Scatter plot of prep time (x) versus prestige (y), with regression line and color coding.

**Interpretation:**

- Pearson r = −0.12 (p = 0.038): a **weak but significant negative correlation**. Faster dishes have slightly higher prestige on average.
- The regression line has a faint negative slope, but the scatter cloud is dense and uniformly spread — prestige 100 appears at ~5s, while prestige 23 appears at various prep times too.
- The key insight is that prep time does NOT positively correlate with quality. If anything, the slight negative trend means the best recipes tend to be faster.
- **Strategic takeaway:** This is good news for gameplay. Elite recipes don't require long cook times, so you can **serve more high-prestige meals per round** without a speed-quality tradeoff.

---

## 07 — Preparation Time vs Number of Ingredients (Scatter)

![Prep Time vs Ingredients](graphs/07_prep_time_vs_ingredients.png)

**What it shows:** Scatter plot of prep time (x) versus ingredient count (y, jittered), with prestige colorbar and regression line.

**Interpretation:**

- Pearson r = 0.10 (p = 0.097): **not statistically significant** at α=0.05. Prep time and ingredient count are essentially independent.
- The scatter is a uniform cloud with no visible pattern. Recipes with 5 ingredients can take 3s or 15s; same for recipes with 10.
- The prestige color is randomly distributed across the plane, confirming no three-way interaction between prep time, ingredient count, and prestige.
- **Strategic takeaway:** You don't need to anticipate that complex recipes take longer. All three core variables (prestige, prep time, ingredient count) are nearly orthogonal — strategy should optimise each dimension independently.

---

## 08 — Correlation Matrix (Heatmap)

![Correlation Matrix](graphs/08_correlation_matrix.png)

**What it shows:** A 3×3 Pearson correlation heatmap for Prestige, Prep Time, and Number of Ingredients.

**Interpretation:**

- Off-diagonal values are all weak: +0.170 (Ingredients↔Prestige), −0.122 (Prep Time↔Prestige), +0.098 (Prep Time↔Ingredients).
- The green-red color scale makes it immediately visible: no strong green or red cells appear off-diagonal. Everything is pale/near-white.
- This single diagram summarizes the core finding of the correlational analysis: **the three numeric recipe variables are nearly uncorrelated**.
- **Strategic takeaway:** Recipe prestige cannot be predicted from prep time or ingredient count. This implies prestige is driven by **ingredient identity and combination**, which is exactly what the ingredient-specific analyses (Diagrams 09–14) investigate.

---

## 09 — Ingredient Frequency (Top 30)

![Ingredient Frequency](graphs/09_ingredient_frequency_top30.png)

**What it shows:** Horizontal bar chart of the 30 most common ingredients, ranked by how many of the 287 recipes include them.

**Interpretation:**

- **Carne di Balena spaziale** is the most common ingredient (65 recipes, 22.6%), followed by **Carne di Kraken** (62) and **Pane di Luce** (61).
- There is a gradual frequency decline — no sharp cliff. The top 5 are in 50+ recipes each; the bottom of the top 30 are still in 20+ recipes.
- Common meats (Balena, Kraken, Drago, Xenodonte, Mucca) and starches (Pane di Luce, Pane degli Abissi, Riso di Cassandra, Amido di Stellarion) dominate the top ranks.
- More "exotic" ingredients like Polvere di Crononite, Lacrime di Andromeda, or Shard di Prisma Stellare appear less frequently (~24–28 recipes).
- **Strategic takeaway:** High-frequency ingredients will likely appear on the market more often and face higher bidding competition. Rare ingredients with high prestige impact (see Diagram 10) may be undervalued in auctions — they're the bargains to target.

---

## 10 — Ingredient Prestige Impact (Δ Prestige)

![Ingredient Prestige Impact](graphs/10_ingredient_prestige_impact.png)

**What it shows:** A horizontal diverging bar chart of the top 15 positive-impact and top 15 negative-impact ingredients. For each ingredient, Δ = mean prestige of recipes that contain it minus mean prestige of recipes that don't contain it.

**Interpretation:**

- **Top positive impact:** Polvere di Crononite (+9.9), Shard di Prisma Stellare (+8.8), Lacrime di Andromeda (+8.3). Recipes containing these tend to score ~8–10 points higher in prestige than those without.
- **Top negative impact:** Salsa Szechuan (−9.1), Cristalli di Nebulite (−7.3), Pane di Luce (−4.3). These appear disproportionately in lower-prestige recipes.
- The green bars (positive Δ) indicate "prestige-boosting" ingredients. The red bars (negative Δ) indicate "prestige-dragging" ingredients.
- Importantly, only a few ingredients have statistically significant (p < 0.05) deltas: Polvere di Crononite, Shard di Prisma Stellare, Lacrime di Andromeda, Essenza di Tachioni, and Salsa Szechuan. The rest are trends, not certainties.
- **Strategic takeaway:** This is the most actionable diagram for bidding strategy. **Prioritize acquiring positive-Δ ingredients** (especially the top 3–5 with significant p-values). **Avoid overpaying for negative-Δ ingredients** like Salsa Szechuan or Pane di Luce unless needed for a specific high-prestige recipe.

---

## 11 — Ingredient Co-occurrence Heatmap

![Ingredient Co-occurrence](graphs/11_ingredient_cooccurrence_heatmap.png)

**What it shows:** A 20×20 heatmap showing how often the top 20 most common ingredients appear together in the same recipe. Darker/warmer cells indicate more frequent co-occurrence.

**Interpretation:**

- The hottest cells are Carne di Balena spaziale + Pane di Luce (19 co-occurrences), followed by Carne di Drago + Pane di Luce (18) and Carne di Kraken + Pane di Luce (18). **Pane di Luce acts as a universal companion** to many meat proteins.
- Meats co-occur heavily with each other (Balena + Kraken = 16, Balena + Fibra di Sintetex = 17), suggesting many multi-meat recipes.
- Some pairs have very low co-occurrence (1–3), even among these top-20 ingredients, which means certain combination slots are unexplored.
- **Strategic takeaway:** Co-occurrence patterns reveal common recipe "archetypes." If you acquire one ingredient from a heavily co-occurring pair, you'll likely need the partner too. Plan bids for ingredient clusters, not isolated items. Also note: Pane di Luce is extremely common but has negative prestige impact — it's a filler ingredient in many mediocre recipes.

---

## 12 — Prestige Tier Comparison

![Tier Comparison](graphs/12_tier_comparison.png)

**What it shows:** Three side-by-side bar charts comparing the six prestige tiers (S through E) on: recipe count, mean ingredient count, and mean prep time.

**Interpretation:**

- **Recipe count (left):** The distribution is roughly bell-shaped centered on tiers C–D–E. Tier E (<50) has the most recipes (66), while S-tier (90–100) has the fewest (19). The mid-range is crowded.
- **Mean ingredients (center):** S-tier averages 7.53 ingredients, while E-tier averages 6.11. The difference is modest (~1.4 ingredients) and non-monotonic — A and B both sit at 7.0. This confirms that ingredient count is a weak differentiator.
- **Mean prep time (right):** Counter-intuitively, **S-tier has the shortest average prep time (7.4s)** while D-tier has the longest (10.1s). This echoes the negative correlation from Diagram 06 — the best recipes tend to cook faster.
- **Strategic takeaway:** Elite recipes require slightly more ingredients on average but cook faster. The combination "more ingredients + less time" means S-tier recipes are **ingredient-intensive but time-efficient** — exactly the profile you want during serving phases.

---

## 13 — Ingredient Count by Tier (Violin Plot)

![Ingredients by Tier Violin](graphs/13_ingredients_by_tier_violin.png)

**What it shows:** Violin plots showing the full distribution of ingredient counts within each prestige tier, with inner box plots for quartiles.

**Interpretation:**

- All tiers have broadly similar distributions, with most density in the 5–8 range. This reaffirms the weak relationship between ingredient count and prestige.
- The S-tier violin is slightly wider at 5 and 7–8, suggesting a bimodal pattern: some S-tier recipes are very lean (5 ingredients) while others are moderately complex (8–9).
- E-tier is the tallest violin around 5, confirming that the lowest-prestige recipes tend to be simpler.
- The overlap between all violins is massive — you cannot visually separate tiers by ingredient count.
- **Strategic takeaway:** There is no "right" number of ingredients for high prestige. The S-tier bimodality suggests two archetypes of elite recipes: minimalist (5 ingredients, carefully chosen) and moderately complex (7–9 ingredients). Both can reach ≥90 prestige if the ingredient composition is correct.

---

## 14 — S-Tier Ingredient Enrichment

![S-Tier Enrichment](graphs/14_s_tier_ingredient_enrichment.png)

**What it shows:** Horizontal bar chart showing the enrichment ratio of each ingredient in S-tier recipes. Enrichment ratio = (% of S-tier recipes containing the ingredient) / (% of all recipes containing it). Values >1.0 (green) mean over-represented; <1.0 (red) mean under-represented. Only ingredients appearing ≥2 times in S-tier are shown.

**Interpretation:**

- **Most enriched:** Polvere di Stelle and Lacrime di Andromeda (enrichment ratio ~3.2×): they appear in S-tier recipes about 3 times more often than their base rate across all recipes would predict.
- **Other strong signals:** Frammenti di Supernova (~2.4×), Essenza di Vuoto (~2.1×), and Carne di Mucca (~2.0×) are also heavily enriched.
- Below the 1.0 baseline (red bars), ingredients like Carne di Drago (~0.56×), Radici di Singolarità (~0.34×), and Fusilli del Vento (~0.39×) are strongly depleted — they appear much less often in S-tier recipes than expected.
- Cross-referencing with Diagram 10 (prestige impact): the enriched ingredients here largely overlap with the positive-Δ group. This provides independent confirmation from two different statistical lenses.
- **Strategic takeaway:** This is the second critical bidding guide. The enrichment ratio tells you which ingredients are *disproportionately present* in the best recipes. **Polvere di Stelle, Lacrime di Andromeda, Frammenti di Supernova, and Essenza di Vuoto** are the strongest S-tier markers. Acquiring these should be a top bidding priority.

---

## 15 — Prestige Efficiency (Scatter)

![Prestige Efficiency](graphs/15_prestige_efficiency.png)

**What it shows:** Two scatter plots side by side. Left: prestige-per-ingredient vs ingredient count. Right: prestige-per-second vs prep time. Both are color-coded by absolute prestige.

**Interpretation:**

- **Left panel (prestige/ingredient):** A clear inverse pattern — recipes with fewer ingredients yield dramatically more prestige per ingredient. The 5-ingredient cluster reaches up to 20 prestige/ingredient, while 10–11 ingredient recipes top out around 9–10. This is a mathematical consequence (dividing by a smaller number), but the key insight is that the *highest absolute prestige* (brightest dots) also appears in the low-ingredient zone.
- **Right panel (prestige/second):** A similar inverse pattern — short prep times yield the highest prestige-per-second. Recipes under 5s can deliver 19–25 prestige/second. The bright dots (high absolute prestige) cluster in the lower-left region, confirming that the most efficient recipes are both fast and prestigious.
- The top-right of both panels is empty: no recipes are simultaneously slow/complex AND highly efficient.
- **Strategic takeaway:** The most efficient recipes (highest prestige per unit of resource) are **lean and fast**. In a competitive serving round, these recipes let you maximize total prestige output. The Top 20 tables in the analysis report list the specific recipes to target.

---

## 16 — Pairplot (Joint Distribution)

![Pairplot](graphs/16_pairplot.png)

**What it shows:** A 3×3 matrix of pairwise scatter plots (off-diagonal) and KDE density plots (diagonal) for Prestige, Prep Time, and # Ingredients.

**Interpretation:**

- **Diagonal (KDE):** Prestige is roughly bell-shaped; Prep Time has a flatter/more uniform distribution; # Ingredients is right-skewed with a peak at 5.
- **Off-diagonal (scatters):** All three pairwise scatter plots show diffuse, cloud-like patterns with no visible linear or nonlinear trends. This is the multivariate version of the weak correlations shown in Diagram 08.
- The Prestige × Prep Time cloud (top-center and center-left) has a very faint negative tilt, consistent with r = −0.12.
- The Prestige × # Ingredients cloud (top-right and bottom-left) has a very faint positive tilt, consistent with r = +0.17.
- The Prep Time × # Ingredients cloud (center-right and bottom-center) is essentially circular — no relationship.
- **Strategic takeaway:** This diagram confirms the holistic picture: these three variables are independently distributed. No hidden nonlinear structure exists that wasn't already captured by the Pearson and Spearman coefficients. **Recipe prestige is driven by ingredient identity, not by prep time or ingredient count.**

---

## Summary of Key Strategic Insights

| Insight | Supporting Diagrams |
|---|---|
| Prestige is driven by **which** ingredients, not how many | 04, 05, 07, 08, 13, 16 |
| Faster preparation does NOT reduce prestige — if anything the opposite | 06, 08, 12, 15 |
| S-tier recipes use slightly more ingredients but cook faster | 12, 13 |
| Polvere di Crononite, Lacrime di Andromeda, Shard di Prisma Stellare are the top prestige-boosting ingredients | 10, 14 |
| Salsa Szechuan, Cristalli di Nebulite, Pane di Luce are the top prestige-dragging ingredients | 10, 14 |
| High-frequency ingredients face more auction competition | 09, 11 |
| The best strategy targets lean, fast, high-prestige recipes (5–6 ingredients, <6s prep time) | 03, 12, 15 |
| Rare ingredients with high enrichment ratios are the smartest bids | 09, 10, 14 |
