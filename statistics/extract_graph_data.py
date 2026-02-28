# type: ignore
"""Extract raw data behind all 16 graphs into a Markdown file for agent consumption."""

import json
import os
import urllib.request
from collections import Counter
from itertools import combinations

import numpy as np
import pandas as pd
from scipy import stats

# ── Config (same as run_analysis.py) ──
API_KEY = "dTpZhKpZ02-4ac2be8821b52df78bf06070"
BASE_URL = "https://hackapizza.datapizza.tech"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "graph_data.md")

def fetch(endpoint):
    req = urllib.request.Request(f"{BASE_URL}{endpoint}", headers={"x-api-key": API_KEY})
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode())

# ── Fetch recipes ──
print("Fetching recipes…")
recipes_raw = fetch("/recipes")
print(f"  → {len(recipes_raw)} recipes")

# ── Build DataFrame (same logic as run_analysis.py) ──
rows = []
for r in recipes_raw:
    ings = r.get("ingredients", {})
    rows.append({
        "name": r["name"],
        "prestige": r["prestige"],
        "prep_ms": r["preparationTimeMs"],
        "prep_s": r["preparationTimeMs"] / 1000,
        "n_ingredients": len(ings),
        "ingredients": ings,
        "ingredient_names": set(ings.keys()),
    })
df = pd.DataFrame(rows)

# Ingredient frequency
all_ings = [ing for s in df["ingredient_names"] for ing in s]
ing_freq = Counter(all_ings)
ing_freq_df = pd.DataFrame(ing_freq.items(), columns=["ingredient", "count"]).sort_values("count", ascending=False).reset_index(drop=True)

md = []
md.append("# Graph Data Reference — Hackapizza 2.0\n")
md.append("This file contains the raw tabular data behind each of the 16 diagrams,")
md.append("so that AI agents can read and reason about the data without needing to view images.\n")
md.append(f"**Dataset:** {len(df)} recipes, {len(ing_freq)} unique ingredients\n")
md.append("---\n")

# ════════════════════════════════════════════════════════════════════
# 01 — Prestige Distribution
# ════════════════════════════════════════════════════════════════════
md.append("## 01 — Prestige Distribution\n")
desc = df["prestige"].describe().round(2)
md.append("### Summary Statistics\n")
md.append(f"| Stat | Value |")
md.append(f"|------|-------|")
for k, v in desc.items():
    md.append(f"| {k} | {v} |")
md.append("")

# Histogram bins
counts_01, edges_01 = np.histogram(df["prestige"], bins=16)
md.append("### Histogram Bins (16 bins)\n")
md.append("| Bin Range | Count |")
md.append("|-----------|-------|")
for i in range(len(counts_01)):
    md.append(f"| {edges_01[i]:.1f} – {edges_01[i+1]:.1f} | {counts_01[i]} |")
md.append("")

# ════════════════════════════════════════════════════════════════════
# 02 — Preparation Time Distribution
# ════════════════════════════════════════════════════════════════════
md.append("## 02 — Preparation Time Distribution\n")
desc2 = df["prep_s"].describe().round(2)
md.append("### Summary Statistics\n")
md.append(f"| Stat | Value |")
md.append(f"|------|-------|")
for k, v in desc2.items():
    md.append(f"| {k} | {v} |")
md.append("")

counts_02, edges_02 = np.histogram(df["prep_s"], bins=30)
md.append("### Histogram Bins (30 bins)\n")
md.append("| Bin Range (s) | Count |")
md.append("|---------------|-------|")
for i in range(len(counts_02)):
    md.append(f"| {edges_02[i]:.2f} – {edges_02[i+1]:.2f} | {counts_02[i]} |")
md.append("")

# ════════════════════════════════════════════════════════════════════
# 03 — Ingredient Count Distribution
# ════════════════════════════════════════════════════════════════════
md.append("## 03 — Ingredient Count Distribution\n")
ing_counts = df["n_ingredients"].value_counts().sort_index()
md.append("| # Ingredients | # Recipes | % of Total |")
md.append("|---------------|-----------|------------|")
for n, c in ing_counts.items():
    md.append(f"| {n} | {c} | {c/len(df)*100:.1f}% |")
md.append("")

# ════════════════════════════════════════════════════════════════════
# 04 — Number of Ingredients vs Prestige
# ════════════════════════════════════════════════════════════════════
md.append("## 04 — Number of Ingredients vs Prestige (Scatter Data)\n")
r_val, p_val = stats.pearsonr(df["n_ingredients"], df["prestige"])
rho, rho_p = stats.spearmanr(df["n_ingredients"], df["prestige"])
md.append(f"- **Pearson r** = {r_val:.4f} (p = {p_val:.4e})")
md.append(f"- **Spearman ρ** = {rho:.4f} (p = {rho_p:.4e})\n")

md.append("### Per-Recipe Data (n_ingredients, prestige)\n")
md.append("| Recipe | # Ing | Prestige |")
md.append("|--------|-------|----------|")
for _, row in df.sort_values(["n_ingredients", "prestige"], ascending=[True, False]).iterrows():
    md.append(f"| {row['name'][:80]} | {row['n_ingredients']} | {row['prestige']} |")
md.append("")

# ════════════════════════════════════════════════════════════════════
# 05 — Mean Prestige by Ingredient Count
# ════════════════════════════════════════════════════════════════════
md.append("## 05 — Mean Prestige by Ingredient Count\n")
grp = df.groupby("n_ingredients")["prestige"].agg(["mean", "median", "std", "count", "min", "max"]).round(2)
md.append(grp.to_markdown())
md.append("")

# ════════════════════════════════════════════════════════════════════
# 06 — Prep Time vs Prestige
# ════════════════════════════════════════════════════════════════════
md.append("## 06 — Preparation Time vs Prestige\n")
r2, p2 = stats.pearsonr(df["prep_s"], df["prestige"])
rho2, rp2 = stats.spearmanr(df["prep_s"], df["prestige"])
md.append(f"- **Pearson r** = {r2:.4f} (p = {p2:.4e})")
md.append(f"- **Spearman ρ** = {rho2:.4f} (p = {rp2:.4e})\n")

md.append("### Per-Recipe Data (prep_s, prestige)\n")
md.append("| Recipe | Prep (s) | Prestige |")
md.append("|--------|----------|----------|")
for _, row in df.sort_values(["prep_s", "prestige"], ascending=[True, False]).iterrows():
    md.append(f"| {row['name'][:80]} | {row['prep_s']:.3f} | {row['prestige']} |")
md.append("")

# ════════════════════════════════════════════════════════════════════
# 07 — Prep Time vs Number of Ingredients
# ════════════════════════════════════════════════════════════════════
md.append("## 07 — Preparation Time vs Number of Ingredients\n")
r3, p3 = stats.pearsonr(df["prep_s"], df["n_ingredients"])
rho3, rp3 = stats.spearmanr(df["prep_s"], df["n_ingredients"])
md.append(f"- **Pearson r** = {r3:.4f} (p = {p3:.4e})")
md.append(f"- **Spearman ρ** = {rho3:.4f} (p = {rp3:.4e})\n")

md.append("### Mean Prep Time by Ingredient Count\n")
grp_prep = df.groupby("n_ingredients")["prep_s"].agg(["mean", "median", "std", "count"]).round(2)
md.append(grp_prep.to_markdown())
md.append("")

# ════════════════════════════════════════════════════════════════════
# 08 — Correlation Matrix
# ════════════════════════════════════════════════════════════════════
md.append("## 08 — Correlation Matrix\n")
corr_df = df[["prestige", "prep_s", "n_ingredients"]].rename(columns={
    "prestige": "Prestige", "prep_s": "Prep Time (s)", "n_ingredients": "# Ingredients"
})
md.append("### Pearson Correlation\n")
md.append(corr_df.corr().round(4).to_markdown())
md.append("")
md.append("### Spearman Correlation\n")
md.append(corr_df.corr(method="spearman").round(4).to_markdown())
md.append("")

# ════════════════════════════════════════════════════════════════════
# 09 — Ingredient Frequency (Top 30)
# ════════════════════════════════════════════════════════════════════
md.append("## 09 — Ingredient Frequency (All 62 Ingredients)\n")
md.append("| Rank | Ingredient | Count | % of Recipes |")
md.append("|------|-----------|-------|-------------|")
for i, (_, row) in enumerate(ing_freq_df.iterrows(), 1):
    md.append(f"| {i} | {row['ingredient']} | {row['count']} | {row['count']/len(df)*100:.1f}% |")
md.append("")

# ════════════════════════════════════════════════════════════════════
# 10 — Ingredient Prestige Impact
# ════════════════════════════════════════════════════════════════════
md.append("## 10 — Ingredient Prestige Impact (Δ Prestige)\n")
ing_impact = []
for ing in ing_freq:
    has = df[[ing in s for s in df["ingredient_names"]]]["prestige"]
    no = df[[ing not in s for s in df["ingredient_names"]]]["prestige"]
    if len(has) >= 5:
        t_stat, t_p = stats.ttest_ind(has, no, equal_var=False)
        ing_impact.append({
            "ingredient": ing,
            "mean_with": round(has.mean(), 2),
            "mean_without": round(no.mean(), 2),
            "delta": round(has.mean() - no.mean(), 2),
            "count": len(has),
            "p_value": round(t_p, 4),
            "significant": "Yes" if t_p < 0.05 else "No",
        })
impact_df = pd.DataFrame(ing_impact).sort_values("delta", ascending=False).reset_index(drop=True)

md.append("| Ingredient | Mean With | Mean Without | Δ | Count | p-value | Significant (p<0.05) |")
md.append("|-----------|-----------|-------------|---|-------|---------|---------------------|")
for _, row in impact_df.iterrows():
    md.append(f"| {row['ingredient']} | {row['mean_with']} | {row['mean_without']} | {row['delta']:+.2f} | {row['count']} | {row['p_value']} | {row['significant']} |")
md.append("")

# ════════════════════════════════════════════════════════════════════
# 11 — Ingredient Co-occurrence Heatmap (Top 20)
# ════════════════════════════════════════════════════════════════════
md.append("## 11 — Ingredient Co-occurrence Matrix (Top 20 Ingredients)\n")
top20 = ing_freq_df.head(20)["ingredient"].tolist()
cooc = pd.DataFrame(0, index=top20, columns=top20, dtype=int)
for s in df["ingredient_names"]:
    present = [i for i in top20 if i in s]
    for a, b in combinations(present, 2):
        cooc.at[a, b] += 1
        cooc.at[b, a] += 1

md.append(cooc.to_markdown())
md.append("")

md.append("### Top 30 Co-occurring Pairs\n")
pair_counter = Counter()
for s in df["ingredient_names"]:
    for pair in combinations(sorted(s), 2):
        pair_counter[pair] += 1
top_pairs = pair_counter.most_common(30)
md.append("| Rank | Ingredient 1 | Ingredient 2 | Co-occurrences |")
md.append("|------|-------------|-------------|----------------|")
for i, (pair, cnt) in enumerate(top_pairs, 1):
    md.append(f"| {i} | {pair[0]} | {pair[1]} | {cnt} |")
md.append("")

# ════════════════════════════════════════════════════════════════════
# 12 — Prestige Tier Comparison
# ════════════════════════════════════════════════════════════════════
md.append("## 12 — Prestige Tier Comparison\n")
def tier_label(p):
    if p >= 90: return "S (90-100)"
    if p >= 80: return "A (80-89)"
    if p >= 70: return "B (70-79)"
    if p >= 60: return "C (60-69)"
    if p >= 50: return "D (50-59)"
    return "E (<50)"

df["tier"] = df["prestige"].apply(tier_label)
tier_order = ["S (90-100)", "A (80-89)", "B (70-79)", "C (60-69)", "D (50-59)", "E (<50)"]

tier_stats = df.groupby("tier").agg(
    count=("prestige", "count"),
    mean_prestige=("prestige", "mean"),
    std_prestige=("prestige", "std"),
    mean_ingredients=("n_ingredients", "mean"),
    std_ingredients=("n_ingredients", "std"),
    mean_prep_s=("prep_s", "mean"),
    std_prep_s=("prep_s", "std"),
    min_prestige=("prestige", "min"),
    max_prestige=("prestige", "max"),
).round(2).reindex(tier_order)
md.append(tier_stats.to_markdown())
md.append("")

# ════════════════════════════════════════════════════════════════════
# 13 — Ingredient Count by Tier (Violin)
# ════════════════════════════════════════════════════════════════════
md.append("## 13 — Ingredient Count by Tier (Violin Plot Data)\n")
md.append("### Quantiles of # Ingredients per Tier\n")
for tier in tier_order:
    sub = df[df["tier"] == tier]["n_ingredients"]
    md.append(f"**{tier}** (n={len(sub)})")
    md.append(f"- Min: {sub.min()}, Q1: {sub.quantile(0.25):.1f}, Median: {sub.median():.1f}, Q3: {sub.quantile(0.75):.1f}, Max: {sub.max()}")
    vc = sub.value_counts().sort_index()
    md.append(f"- Distribution: {', '.join(f'{k} ing → {v} recipes' for k, v in vc.items())}")
    md.append("")

# ════════════════════════════════════════════════════════════════════
# 14 — S-Tier Ingredient Enrichment
# ════════════════════════════════════════════════════════════════════
md.append("## 14 — S-Tier Ingredient Enrichment\n")
s_tier = df[df["prestige"] >= 90]
s_tier_ings = Counter([ing for s in s_tier["ingredient_names"] for ing in s])
s_total = len(s_tier)

enrichment = []
for ing, cnt_s in s_tier_ings.items():
    total = ing_freq[ing]
    pct_s = cnt_s / s_total * 100
    pct_all = total / len(df) * 100
    enrichment.append({
        "ingredient": ing,
        "s_tier_count": cnt_s,
        "total_count": total,
        "pct_in_s_tier": round(pct_s, 1),
        "pct_overall": round(pct_all, 1),
        "enrichment_ratio": round(pct_s / pct_all, 2) if pct_all > 0 else 0,
    })
enrich_df = pd.DataFrame(enrichment).sort_values("enrichment_ratio", ascending=False).reset_index(drop=True)

md.append(f"S-tier recipes: {s_total} (prestige ≥ 90)\n")
md.append("| Ingredient | S-Tier Count | Total Count | % in S-Tier | % Overall | Enrichment Ratio |")
md.append("|-----------|-------------|-------------|-------------|-----------|-----------------|")
for _, row in enrich_df.iterrows():
    md.append(f"| {row['ingredient']} | {row['s_tier_count']} | {row['total_count']} | {row['pct_in_s_tier']}% | {row['pct_overall']}% | {row['enrichment_ratio']}× |")
md.append("")

# Ingredients with 0 appearances in S-tier
absent = [ing for ing in ing_freq if ing not in s_tier_ings]
if absent:
    md.append("### Ingredients ABSENT from all S-Tier Recipes\n")
    md.append("| Ingredient | Total Count |")
    md.append("|-----------|-------------|")
    for ing in sorted(absent, key=lambda x: -ing_freq[x]):
        md.append(f"| {ing} | {ing_freq[ing]} |")
    md.append("")

# ════════════════════════════════════════════════════════════════════
# 15 — Prestige Efficiency
# ════════════════════════════════════════════════════════════════════
md.append("## 15 — Prestige Efficiency\n")
df["prestige_per_ing"] = (df["prestige"] / df["n_ingredients"]).round(2)
df["prestige_per_sec"] = (df["prestige"] / df["prep_s"]).round(2)

md.append("### All Recipes Ranked by Prestige per Ingredient\n")
eff = df.sort_values("prestige_per_ing", ascending=False)[["name", "prestige", "n_ingredients", "prestige_per_ing", "prep_s", "prestige_per_sec"]]
md.append("| Recipe | Prestige | # Ing | Prestige/Ing | Prep (s) | Prestige/Sec |")
md.append("|--------|----------|-------|-------------|----------|-------------|")
for _, row in eff.iterrows():
    md.append(f"| {row['name'][:80]} | {row['prestige']} | {row['n_ingredients']} | {row['prestige_per_ing']} | {row['prep_s']:.3f} | {row['prestige_per_sec']} |")
md.append("")

md.append("### All Recipes Ranked by Prestige per Second\n")
eff2 = df.sort_values("prestige_per_sec", ascending=False)[["name", "prestige", "prep_s", "prestige_per_sec", "n_ingredients", "prestige_per_ing"]]
md.append("| Recipe | Prestige | Prep (s) | Prestige/Sec | # Ing | Prestige/Ing |")
md.append("|--------|----------|----------|-------------|-------|-------------|")
for _, row in eff2.iterrows():
    md.append(f"| {row['name'][:80]} | {row['prestige']} | {row['prep_s']:.3f} | {row['prestige_per_sec']} | {row['n_ingredients']} | {row['prestige_per_ing']} |")
md.append("")

# ════════════════════════════════════════════════════════════════════
# 16 — Pairplot (Joint Distribution)
# ════════════════════════════════════════════════════════════════════
md.append("## 16 — Pairplot / Joint Distribution Summary\n")
md.append("The pairplot visualises pairwise scatter + KDE for the 3 numeric variables.\n")
md.append("### Full Descriptive Statistics\n")
full_desc = df[["prestige", "prep_s", "n_ingredients"]].describe().round(3)
md.append(full_desc.to_markdown())
md.append("")
md.append("### Pearson Correlations (repeated for completeness)\n")
md.append(corr_df.corr().round(4).to_markdown())
md.append("")
md.append("### Spearman Correlations\n")
md.append(corr_df.corr(method="spearman").round(4).to_markdown())
md.append("")

# ════════════════════════════════════════════════════════════════════
# Write
# ════════════════════════════════════════════════════════════════════
with open(OUT, "w") as f:
    f.write("\n".join(md) + "\n")

print(f"✅ Written {len(md)} lines to {OUT}")
