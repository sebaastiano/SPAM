#!/usr/bin/env python3
# type: ignore
"""
Hackapizza 2.0 — Comprehensive Statistical & Correlational Analysis of Game Data.
Generates graphs + a markdown report in the statistics/ folder.
"""

import json
import os
import urllib.request
from collections import Counter
from itertools import combinations

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd
import seaborn as sns
from scipy import stats

# ── Config ──────────────────────────────────────────────────────────────────
API_KEY = "dTpZhKpZ02-4ac2be8821b52df78bf06070"
BASE_URL = "https://hackapizza.datapizza.tech"
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)))
IMG_DIR = os.path.join(OUT_DIR, "graphs")
os.makedirs(IMG_DIR, exist_ok=True)

sns.set_theme(style="whitegrid", palette="viridis", font_scale=1.15)
plt.rcParams.update({
    "figure.dpi": 200,
    "savefig.dpi": 200,
    "savefig.bbox": "tight",
    "axes.titlesize": 13,
    "axes.labelsize": 11,
    "font.size": 10,
})

# ── Fetch data ──────────────────────────────────────────────────────────────
def fetch(endpoint):
    req = urllib.request.Request(f"{BASE_URL}{endpoint}", headers={"x-api-key": API_KEY})
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode())

print("Fetching recipes…")
recipes_raw = fetch("/recipes")
print(f"  → {len(recipes_raw)} recipes")

# ── Build DataFrame ─────────────────────────────────────────────────────────
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

# Unique ingredient list & frequency
all_ing_names = [ing for row in df["ingredient_names"] for ing in row]
ing_freq = Counter(all_ing_names)
ing_freq_df = pd.DataFrame(ing_freq.items(), columns=["ingredient", "count"]).sort_values("count", ascending=False).reset_index(drop=True)

# ── Markdown report builder ─────────────────────────────────────────────────
md = []
md.append("# Hackapizza 2.0 — Statistical Analysis\n")
md.append(f"**Dataset:** {len(df)} recipes, {len(ing_freq)} unique ingredients\n")
md.append("---\n")

# ══════════════════════════════════════════════════════════════════════════════
#  1. DESCRIPTIVE STATISTICS
# ══════════════════════════════════════════════════════════════════════════════
md.append("## 1. Descriptive Statistics\n")

desc = df[["prestige", "prep_s", "n_ingredients"]].describe().round(2)
md.append("### Core Metrics\n")
md.append(desc.to_markdown())
md.append("")

# Prestige distribution
md.append("\n### Prestige Distribution\n")
fig, axes = plt.subplots(1, 3, figsize=(18, 5))
# Histogram
axes[0].hist(df["prestige"], bins=16, edgecolor="white", color=sns.color_palette()[0], alpha=0.8)
axes[0].set_xlabel("Prestige")
axes[0].set_ylabel("Count")
axes[0].set_title("Prestige Distribution (Histogram)")
axes[0].axvline(df["prestige"].mean(), color="red", ls="--", lw=2, label=f"Mean = {df['prestige'].mean():.1f}")
axes[0].axvline(df["prestige"].median(), color="orange", ls="--", lw=2, label=f"Median = {df['prestige'].median():.1f}")
axes[0].set_xlim(df["prestige"].min() - 3, df["prestige"].max() + 3)
axes[0].legend(fontsize=9)
# KDE
sns.kdeplot(df["prestige"], ax=axes[1], fill=True, color=sns.color_palette()[0], alpha=0.5, linewidth=2)
axes[1].axvline(df["prestige"].mean(), color="red", ls="--", lw=2, label=f"Mean = {df['prestige'].mean():.1f}")
axes[1].set_xlabel("Prestige")
axes[1].set_title("Prestige Distribution (KDE)")
axes[1].set_xlim(df["prestige"].min() - 5, df["prestige"].max() + 5)
axes[1].legend(fontsize=9)
# Box + strip
sns.boxplot(x=df["prestige"], ax=axes[2], color=sns.color_palette()[1], width=0.4)
sns.stripplot(x=df["prestige"], ax=axes[2], color="black", alpha=0.15, size=3, jitter=0.25)
axes[2].set_title("Prestige Distribution (Box + Points)")
axes[2].set_xlabel("Prestige")
plt.tight_layout()
fig.savefig(os.path.join(IMG_DIR, "01_prestige_distribution.png"))
plt.close(fig)
md.append("![Prestige Distribution](graphs/01_prestige_distribution.png)\n")

# Prep time distribution
md.append("### Preparation Time Distribution\n")
fig, axes = plt.subplots(1, 3, figsize=(18, 5))
# Histogram with tight x-range
axes[0].hist(df["prep_s"], bins=30, edgecolor="white", color=sns.color_palette()[2], alpha=0.8)
axes[0].set_xlabel("Preparation Time (s)")
axes[0].set_ylabel("Count")
axes[0].set_title("Preparation Time Distribution (Histogram)")
axes[0].axvline(df["prep_s"].mean(), color="red", ls="--", lw=2, label=f"Mean = {df['prep_s'].mean():.1f}s")
axes[0].axvline(df["prep_s"].median(), color="orange", ls="--", lw=2, label=f"Median = {df['prep_s'].median():.1f}s")
axes[0].set_xlim(df["prep_s"].min() - 0.5, df["prep_s"].max() + 0.5)
axes[0].legend(fontsize=9)
# KDE
sns.kdeplot(df["prep_s"], ax=axes[1], fill=True, color=sns.color_palette()[2], alpha=0.5, linewidth=2)
axes[1].axvline(df["prep_s"].mean(), color="red", ls="--", lw=2, label=f"Mean = {df['prep_s'].mean():.1f}s")
axes[1].set_xlabel("Preparation Time (s)")
axes[1].set_title("Preparation Time Distribution (KDE)")
axes[1].set_xlim(df["prep_s"].min() - 1, df["prep_s"].max() + 1)
axes[1].legend(fontsize=9)
# Box + strip
sns.boxplot(x=df["prep_s"], ax=axes[2], color=sns.color_palette()[3], width=0.4)
sns.stripplot(x=df["prep_s"], ax=axes[2], color="black", alpha=0.15, size=3, jitter=0.25)
axes[2].set_title("Preparation Time (Box + Points)")
axes[2].set_xlabel("Preparation Time (s)")
plt.tight_layout()
fig.savefig(os.path.join(IMG_DIR, "02_prep_time_distribution.png"))
plt.close(fig)
md.append("![Prep Time Distribution](graphs/02_prep_time_distribution.png)\n")

# Ingredient count distribution
md.append("### Ingredient Count Distribution\n")
fig, ax = plt.subplots(figsize=(10, 5))
ing_counts = df["n_ingredients"].value_counts().sort_index()
ax.bar(list(ing_counts.index), list(ing_counts.values), edgecolor="white", color=sns.color_palette()[4])
ax.set_xlabel("Number of Ingredients")
ax.set_ylabel("Number of Recipes")
ax.set_title("Recipes by Ingredient Count")
ax.xaxis.set_major_locator(mticker.MaxNLocator(integer=True))
for idx_val, cnt_val in zip(ing_counts.index, ing_counts.values):
    ax.text(idx_val, int(cnt_val) + 0.5, str(cnt_val), ha="center", fontsize=9)
fig.savefig(os.path.join(IMG_DIR, "03_ingredient_count_distribution.png"))
plt.close(fig)
md.append("![Ingredient Count Distribution](graphs/03_ingredient_count_distribution.png)\n")

# ══════════════════════════════════════════════════════════════════════════════
#  2. CORRELATIONAL ANALYSIS
# ══════════════════════════════════════════════════════════════════════════════
md.append("## 2. Correlational Analysis\n")

# 2a. Number of ingredients vs prestige
md.append("### 2a. Number of Ingredients vs Prestige\n")
r_val, p_val = stats.pearsonr(df["n_ingredients"], df["prestige"])
rho, rho_p = stats.spearmanr(df["n_ingredients"], df["prestige"])
md.append(f"- **Pearson r** = {r_val:.4f} (p = {p_val:.4e})")
md.append(f"- **Spearman ρ** = {rho:.4f} (p = {rho_p:.4e})")
md.append("")

fig, ax = plt.subplots(figsize=(10, 7))
# Add jitter to discrete x-axis for visibility
jitter_x = df["n_ingredients"] + np.random.uniform(-0.25, 0.25, len(df))
ax.scatter(jitter_x, df["prestige"], alpha=0.45, s=35, c=df["prestige"], cmap="viridis", edgecolors="white", linewidth=0.3)
sns.regplot(x="n_ingredients", y="prestige", data=df, ax=ax, scatter=False, line_kws={"color": "red", "lw": 2})
ax.set_xlabel("Number of Ingredients")
ax.set_ylabel("Prestige")
ax.set_title(f"Ingredients vs Prestige (Pearson r={r_val:.3f}, p={p_val:.3e})")
ax.set_ylim(df["prestige"].min() - 5, df["prestige"].max() + 5)
ax.xaxis.set_major_locator(mticker.MaxNLocator(integer=True))
fig.savefig(os.path.join(IMG_DIR, "04_ingredients_vs_prestige.png"))
plt.close(fig)
md.append("![Ingredients vs Prestige](graphs/04_ingredients_vs_prestige.png)\n")

# Mean prestige per ingredient count
grp = df.groupby("n_ingredients")["prestige"].agg(["mean", "median", "std", "count"]).round(2)
md.append("#### Mean Prestige by Ingredient Count\n")
md.append(grp.to_markdown())
md.append("")

fig, ax = plt.subplots(figsize=(10, 6))
ax.bar(grp.index, grp["mean"], yerr=grp["std"], capsize=4, edgecolor="white", color=sns.color_palette()[0], alpha=0.85)
ax.set_xlabel("Number of Ingredients")
ax.set_ylabel("Mean Prestige")
ax.set_title("Mean Prestige by Ingredient Count (with std dev)")
ax.xaxis.set_major_locator(mticker.MaxNLocator(integer=True))
# Zoom y-axis to show variation clearly
y_min = max(0, (grp["mean"] - grp["std"]).min() - 10)
y_max = (grp["mean"] + grp["std"]).max() + 10
ax.set_ylim(y_min, y_max)
for x_val, m_val, c_val in zip(grp.index, grp["mean"], grp["count"]):
    ax.text(x_val, m_val + grp.loc[x_val, "std"] + 1.5, f"n={int(c_val)}", ha="center", fontsize=8, color="gray")
fig.savefig(os.path.join(IMG_DIR, "05_mean_prestige_by_ing_count.png"))
plt.close(fig)
md.append("![Mean Prestige by Ingredient Count](graphs/05_mean_prestige_by_ing_count.png)\n")

# 2b. Preparation time vs prestige
md.append("### 2b. Preparation Time vs Prestige\n")
r_val2, p_val2 = stats.pearsonr(df["prep_s"], df["prestige"])
rho2, rho_p2 = stats.spearmanr(df["prep_s"], df["prestige"])
md.append(f"- **Pearson r** = {r_val2:.4f} (p = {p_val2:.4e})")
md.append(f"- **Spearman ρ** = {rho2:.4f} (p = {rho_p2:.4e})")
md.append("")

fig, ax = plt.subplots(figsize=(10, 7))
ax.scatter(df["prep_s"], df["prestige"], alpha=0.45, s=35, c=df["prestige"], cmap="viridis", edgecolors="white", linewidth=0.3)
sns.regplot(x="prep_s", y="prestige", data=df, ax=ax, scatter=False, line_kws={"color": "red", "lw": 2})
ax.set_xlabel("Preparation Time (s)")
ax.set_ylabel("Prestige")
ax.set_title(f"Prep Time vs Prestige (Pearson r={r_val2:.3f}, p={p_val2:.3e})")
ax.set_xlim(df["prep_s"].min() - 0.5, df["prep_s"].max() + 0.5)
ax.set_ylim(df["prestige"].min() - 5, df["prestige"].max() + 5)
fig.savefig(os.path.join(IMG_DIR, "06_prep_time_vs_prestige.png"))
plt.close(fig)
md.append("![Prep Time vs Prestige](graphs/06_prep_time_vs_prestige.png)\n")

# 2c. Preparation time vs number of ingredients
md.append("### 2c. Preparation Time vs Number of Ingredients\n")
r_val3, p_val3 = stats.pearsonr(df["prep_s"], df["n_ingredients"])
rho3, rho_p3 = stats.spearmanr(df["prep_s"], df["n_ingredients"])
md.append(f"- **Pearson r** = {r_val3:.4f} (p = {p_val3:.4e})")
md.append(f"- **Spearman ρ** = {rho3:.4f} (p = {rho_p3:.4e})")
md.append("")

fig, ax = plt.subplots(figsize=(10, 7))
jitter_y = df["n_ingredients"] + np.random.uniform(-0.25, 0.25, len(df))
ax.scatter(df["prep_s"], jitter_y, alpha=0.45, s=35, c=df["prestige"], cmap="viridis", edgecolors="white", linewidth=0.3)
sns.regplot(x="prep_s", y="n_ingredients", data=df, ax=ax, scatter=False, line_kws={"color": "red", "lw": 2})
ax.set_xlabel("Preparation Time (s)")
ax.set_ylabel("Number of Ingredients")
ax.set_title(f"Prep Time vs Ingredients (Pearson r={r_val3:.3f}, p={p_val3:.3e})")
ax.set_xlim(df["prep_s"].min() - 0.5, df["prep_s"].max() + 0.5)
plt.colorbar(ax.collections[0], ax=ax, label="Prestige")
fig.savefig(os.path.join(IMG_DIR, "07_prep_time_vs_ingredients.png"))
plt.close(fig)
md.append("![Prep Time vs Ingredients](graphs/07_prep_time_vs_ingredients.png)\n")

# 2d. Full correlation matrix
md.append("### 2d. Correlation Matrix\n")
corr_df = df[["prestige", "prep_s", "n_ingredients"]].rename(columns={
    "prestige": "Prestige", "prep_s": "Prep Time (s)", "n_ingredients": "# Ingredients"
})
corr_matrix = corr_df.corr().round(4)
md.append(corr_matrix.to_markdown())
md.append("")

fig, ax = plt.subplots(figsize=(8, 7))
sns.heatmap(corr_matrix, annot=True, cmap="RdYlGn", center=0, vmin=-1, vmax=1, ax=ax, fmt=".3f",
            linewidths=2, annot_kws={"size": 14, "weight": "bold"}, square=True)
ax.set_title("Correlation Matrix", fontsize=14, pad=15)
plt.xticks(fontsize=10)
plt.yticks(fontsize=10)
fig.savefig(os.path.join(IMG_DIR, "08_correlation_matrix.png"))
plt.close(fig)
md.append("![Correlation Matrix](graphs/08_correlation_matrix.png)\n")

# ══════════════════════════════════════════════════════════════════════════════
#  3. INGREDIENT ANALYSIS
# ══════════════════════════════════════════════════════════════════════════════
md.append("## 3. Ingredient Analysis\n")

# 3a. Top ingredients by frequency
md.append("### 3a. Ingredient Frequency (Top 30)\n")
top30 = ing_freq_df.head(30)
fig, ax = plt.subplots(figsize=(14, 10))
bars = ax.barh(top30["ingredient"][::-1], top30["count"][::-1], color=sns.color_palette("viridis", 30), edgecolor="white", linewidth=0.5)
ax.set_xlabel("Number of Recipes", fontsize=11)
ax.set_title("Top 30 Most Common Ingredients", fontsize=13)
max_count = top30["count"].max()
ax.set_xlim(0, max_count * 1.12)
for bar, val in zip(bars, top30["count"][::-1]):
    ax.text(bar.get_width() + max_count * 0.01, bar.get_y() + bar.get_height()/2, str(val), va="center", fontsize=9, fontweight="bold")
plt.tight_layout()
fig.savefig(os.path.join(IMG_DIR, "09_ingredient_frequency_top30.png"))
plt.close(fig)
md.append("![Ingredient Frequency](graphs/09_ingredient_frequency_top30.png)\n")

# 3b. Ingredient impact on prestige
md.append("### 3b. Ingredient Impact on Prestige\n")
md.append("Mean prestige of recipes containing each ingredient vs. recipes without it.\n")

ing_impact = []
for ing in ing_freq:
    has_ing = df[[ing in s for s in df["ingredient_names"]]]["prestige"]
    no_ing = df[[ing not in s for s in df["ingredient_names"]]]["prestige"]
    if len(has_ing) >= 5:  # only consider ingredients appearing in 5+ recipes
        t_stat, t_p = stats.ttest_ind(has_ing, no_ing, equal_var=False)
        ing_impact.append({
            "ingredient": ing,
            "mean_with": has_ing.mean(),
            "mean_without": no_ing.mean(),
            "delta": has_ing.mean() - no_ing.mean(),
            "count": len(has_ing),
            "t_stat": t_stat,
            "p_value": t_p,
        })

impact_df = pd.DataFrame(ing_impact).sort_values("delta", ascending=False).reset_index(drop=True)
impact_df_round = impact_df.round(2)
md.append("\n#### Ingredients Ranked by Prestige Impact (Δ = mean_with - mean_without)\n")
md.append(impact_df_round[["ingredient", "mean_with", "mean_without", "delta", "count", "p_value"]].to_markdown(index=False))
md.append("")

# Plot top 15 positive and bottom 15 negative impact
fig, ax = plt.subplots(figsize=(14, 12))
top_impact = pd.concat([impact_df.head(15), impact_df.tail(15)]).drop_duplicates()
top_impact = top_impact.sort_values("delta")
colors = ["#d32f2f" if d < 0 else "#388e3c" for d in top_impact["delta"]]
ax.barh(top_impact["ingredient"], top_impact["delta"], color=colors, edgecolor="white", linewidth=0.5)
ax.axvline(0, color="black", linewidth=1.2)
ax.set_xlabel("Δ Prestige (mean with - mean without)", fontsize=11)
ax.set_title("Ingredient Impact on Prestige\n(Top 15 positive + Top 15 negative)", fontsize=13)
# Add value labels
for idx_row, row_data in top_impact.iterrows():
    d = row_data["delta"]
    ax.text(d + (0.3 if d >= 0 else -0.3), row_data["ingredient"], f"{d:+.1f}",
            va="center", ha="left" if d >= 0 else "right", fontsize=8, fontweight="bold")
plt.tight_layout()
fig.savefig(os.path.join(IMG_DIR, "10_ingredient_prestige_impact.png"))
plt.close(fig)
md.append("![Ingredient Prestige Impact](graphs/10_ingredient_prestige_impact.png)\n")

# 3c. Ingredient co-occurrence
md.append("### 3c. Ingredient Co-occurrence Analysis\n")
md.append("Which ingredient pairs appear together most often?\n")

pair_counter = Counter()
for ing_set in df["ingredient_names"]:
    for pair in combinations(sorted(ing_set), 2):
        pair_counter[pair] += 1

top_pairs = pair_counter.most_common(25)
pair_df = pd.DataFrame(top_pairs, columns=["pair", "count"])
pair_df["ingredient_1"] = pair_df["pair"].apply(lambda x: x[0])
pair_df["ingredient_2"] = pair_df["pair"].apply(lambda x: x[1])

md.append("#### Top 25 Ingredient Pairs\n")
md.append("| # | Ingredient 1 | Ingredient 2 | Co-occurrences |")
md.append("|---|-------------|-------------|----------------|")
for idx, row in pair_df.iterrows():
    md.append(f"| {int(idx)+1} | {row['ingredient_1']} | {row['ingredient_2']} | {row['count']} |")  # type: ignore[arg-type]
md.append("")

# Co-occurrence heatmap for top 20 ingredients
top20_ings = ing_freq_df.head(20)["ingredient"].tolist()
cooc_matrix = pd.DataFrame(0, index=top20_ings, columns=top20_ings, dtype=int)
for ing_set in df["ingredient_names"]:
    present = [i for i in top20_ings if i in ing_set]
    for a, b in combinations(present, 2):
        cooc_matrix.at[a, b] = cooc_matrix.at[a, b] + 1  # type: ignore[operator]
        cooc_matrix.at[b, a] = cooc_matrix.at[b, a] + 1  # type: ignore[operator]

fig, ax = plt.subplots(figsize=(16, 14))
sns.heatmap(cooc_matrix, annot=True, fmt="d", cmap="YlOrRd", ax=ax, linewidths=0.5)
ax.set_title("Ingredient Co-occurrence Matrix (Top 20 Ingredients)")
plt.xticks(rotation=45, ha="right", fontsize=8)
plt.yticks(fontsize=8)
plt.tight_layout()
fig.savefig(os.path.join(IMG_DIR, "11_ingredient_cooccurrence_heatmap.png"))
plt.close(fig)
md.append("![Ingredient Co-occurrence](graphs/11_ingredient_cooccurrence_heatmap.png)\n")

# ══════════════════════════════════════════════════════════════════════════════
#  4. PRESTIGE TIER ANALYSIS
# ══════════════════════════════════════════════════════════════════════════════
md.append("## 4. Prestige Tier Analysis\n")

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
    mean_ingredients=("n_ingredients", "mean"),
    mean_prep_s=("prep_s", "mean"),
).round(2).reindex(tier_order)

md.append("### Tier Breakdown\n")
md.append(tier_stats.to_markdown())
md.append("")

fig, axes = plt.subplots(1, 3, figsize=(18, 7))
tier_colors = sns.color_palette("RdYlGn_r", len(tier_order))

# Count by tier
tier_counts = df["tier"].value_counts().reindex(tier_order)
axes[0].bar(tier_order, tier_counts.values, color=tier_colors, edgecolor="white")
axes[0].set_title("Recipes per Tier")
axes[0].set_ylabel("Count")
axes[0].tick_params(axis="x", rotation=30)
for xi, vi in enumerate(tier_counts.values):
    axes[0].text(xi, vi + 0.8, str(vi), ha="center", fontsize=10, fontweight="bold")

# Mean ingredients by tier — zoomed y-axis
ing_vals = tier_stats["mean_ingredients"]
axes[1].bar(tier_order, ing_vals, color=tier_colors, edgecolor="white")
axes[1].set_title("Mean Ingredients per Tier")
axes[1].set_ylabel("Avg # Ingredients")
axes[1].tick_params(axis="x", rotation=30)
y_pad = (ing_vals.max() - ing_vals.min()) * 0.3
axes[1].set_ylim(max(0, ing_vals.min() - y_pad - 1), ing_vals.max() + y_pad)
for xi, vi in enumerate(ing_vals):
    axes[1].text(xi, vi + 0.08, f"{vi:.1f}", ha="center", fontsize=10, fontweight="bold")

# Mean prep time by tier — zoomed y-axis
prep_vals = tier_stats["mean_prep_s"]
axes[2].bar(tier_order, prep_vals, color=tier_colors, edgecolor="white")
axes[2].set_title("Mean Prep Time per Tier")
axes[2].set_ylabel("Avg Prep Time (s)")
axes[2].tick_params(axis="x", rotation=30)
y_pad2 = (prep_vals.max() - prep_vals.min()) * 0.3
axes[2].set_ylim(max(0, prep_vals.min() - y_pad2 - 1), prep_vals.max() + y_pad2)
for xi, vi in enumerate(prep_vals):
    axes[2].text(xi, vi + 0.05, f"{vi:.1f}", ha="center", fontsize=10, fontweight="bold")

plt.tight_layout()
fig.savefig(os.path.join(IMG_DIR, "12_tier_comparison.png"))
plt.close(fig)
md.append("![Tier Comparison](graphs/12_tier_comparison.png)\n")

# Ingredient distribution violin plot by tier
md.append("### Ingredient Count by Tier (Violin Plot)\n")
fig, ax = plt.subplots(figsize=(12, 6))
sns.violinplot(x="tier", y="n_ingredients", data=df, order=tier_order, ax=ax, inner="box", palette="RdYlGn_r")
ax.set_xlabel("Tier")
ax.set_ylabel("Number of Ingredients")
ax.set_title("Ingredient Count Distribution by Prestige Tier")
fig.savefig(os.path.join(IMG_DIR, "13_ingredients_by_tier_violin.png"))
plt.close(fig)
md.append("![Ingredients by Tier Violin](graphs/13_ingredients_by_tier_violin.png)\n")

# ══════════════════════════════════════════════════════════════════════════════
#  5. INGREDIENT-SPECIFIC PRESTIGE ANALYSIS
# ══════════════════════════════════════════════════════════════════════════════
md.append("## 5. Ingredient Presence in Top-Tier Recipes\n")
md.append("How often does each ingredient appear in S-tier (prestige ≥ 90) vs overall?\n")

s_tier = df[df["prestige"] >= 90]
s_tier_ings = Counter([ing for s in s_tier["ingredient_names"] for ing in s])
s_tier_total = len(s_tier)

enrichment = []
for ing, count_in_s in s_tier_ings.items():
    total_count = ing_freq[ing]
    pct_in_s = count_in_s / s_tier_total * 100
    pct_overall = total_count / len(df) * 100
    enrichment.append({
        "ingredient": ing,
        "s_tier_count": count_in_s,
        "total_count": total_count,
        "pct_in_s_tier": round(pct_in_s, 1),
        "pct_overall": round(pct_overall, 1),
        "enrichment_ratio": round(pct_in_s / pct_overall, 2) if pct_overall > 0 else 0,
    })

enrich_df = pd.DataFrame(enrichment).sort_values("enrichment_ratio", ascending=False).reset_index(drop=True)
md.append("\n#### Ingredient Enrichment in S-Tier Recipes\n")
md.append("Enrichment ratio > 1 means the ingredient is *over-represented* in top recipes.\n")
md.append(enrich_df.to_markdown(index=False))
md.append("")

fig, ax = plt.subplots(figsize=(14, 8))
enrich_plot = enrich_df[enrich_df["s_tier_count"] >= 2].head(25).sort_values("enrichment_ratio")
colors = ["#388e3c" if e >= 1 else "#d32f2f" for e in enrich_plot["enrichment_ratio"]]
ax.barh(enrich_plot["ingredient"], enrich_plot["enrichment_ratio"], color=colors)
ax.axvline(1, color="black", linewidth=0.8, linestyle="--", label="Baseline (1.0)")
ax.set_xlabel("Enrichment Ratio (>1 = over-represented in S-tier)")
ax.set_title("Ingredient Enrichment in S-Tier Recipes (≥2 appearances)")
ax.legend()
plt.tight_layout()
fig.savefig(os.path.join(IMG_DIR, "14_s_tier_ingredient_enrichment.png"))
plt.close(fig)
md.append("![S-Tier Enrichment](graphs/14_s_tier_ingredient_enrichment.png)\n")

# ══════════════════════════════════════════════════════════════════════════════
#  6. PRESTIGE EFFICIENCY ANALYSIS
# ══════════════════════════════════════════════════════════════════════════════
md.append("## 6. Prestige Efficiency Analysis\n")
md.append("Which recipes give the most prestige per ingredient? Per second of prep time?\n")

df["prestige_per_ing"] = (df["prestige"] / df["n_ingredients"]).round(2)
df["prestige_per_sec"] = (df["prestige"] / df["prep_s"]).round(2)

md.append("\n### Top 20 Recipes by Prestige per Ingredient\n")
top_eff_ing = df.nlargest(20, "prestige_per_ing")[["name", "prestige", "n_ingredients", "prestige_per_ing", "prep_s"]]
md.append(top_eff_ing.to_markdown(index=False))
md.append("")

md.append("\n### Top 20 Recipes by Prestige per Second\n")
top_eff_time = df.nlargest(20, "prestige_per_sec")[["name", "prestige", "prep_s", "prestige_per_sec", "n_ingredients"]]
md.append(top_eff_time.to_markdown(index=False))
md.append("")

fig, axes = plt.subplots(1, 2, figsize=(16, 7))
jitter_x2 = df["n_ingredients"] + np.random.uniform(-0.2, 0.2, len(df))
sc0 = axes[0].scatter(jitter_x2, df["prestige_per_ing"], alpha=0.55, s=40, c=df["prestige"], cmap="viridis", edgecolors="white", linewidth=0.3)
axes[0].set_xlabel("Number of Ingredients")
axes[0].set_ylabel("Prestige / Ingredient")
axes[0].set_title("Prestige Efficiency vs Ingredient Count")
axes[0].xaxis.set_major_locator(mticker.MaxNLocator(integer=True))
plt.colorbar(sc0, ax=axes[0], label="Prestige")

sc1 = axes[1].scatter(df["prep_s"], df["prestige_per_sec"], alpha=0.55, s=40, c=df["prestige"], cmap="viridis", edgecolors="white", linewidth=0.3)
axes[1].set_xlabel("Preparation Time (s)")
axes[1].set_ylabel("Prestige / Second")
axes[1].set_title("Prestige Efficiency vs Prep Time")
plt.colorbar(sc1, ax=axes[1], label="Prestige")

plt.tight_layout()
fig.savefig(os.path.join(IMG_DIR, "15_prestige_efficiency.png"))
plt.close(fig)
md.append("![Prestige Efficiency](graphs/15_prestige_efficiency.png)\n")

# ══════════════════════════════════════════════════════════════════════════════
#  7. PAIRPLOT & JOINT DISTRIBUTIONS
# ══════════════════════════════════════════════════════════════════════════════
md.append("## 7. Joint Distribution Plot\n")
fig = sns.pairplot(df[["prestige", "prep_s", "n_ingredients"]].rename(columns={
    "prestige": "Prestige", "prep_s": "Prep Time (s)", "n_ingredients": "# Ingredients"
}), diag_kind="kde", plot_kws={"alpha": 0.4, "s": 20})
fig.savefig(os.path.join(IMG_DIR, "16_pairplot.png"))
plt.close(fig.figure)
md.append("![Pairplot](graphs/16_pairplot.png)\n")

# ══════════════════════════════════════════════════════════════════════════════
#  8. STRATEGIC SUMMARY
# ══════════════════════════════════════════════════════════════════════════════
md.append("## 8. Strategic Summary & Key Findings\n")

md.append("### Key Correlations\n")
md.append(f"| Relationship | Pearson r | p-value | Interpretation |")
md.append(f"|-------------|-----------|---------|----------------|")
def _interpret(r_val: float) -> str:
    return "Weak" if abs(r_val) < 0.3 else "Moderate" if abs(r_val) < 0.6 else "Strong"

corr_ip = stats.pearsonr(df["n_ingredients"], df["prestige"])
corr_tp = stats.pearsonr(df["prep_s"], df["prestige"])
corr_ti = stats.pearsonr(df["prep_s"], df["n_ingredients"])
r_ip, p_ip = corr_ip.statistic, corr_ip.pvalue
r_tp, p_tp = corr_tp.statistic, corr_tp.pvalue
r_ti, p_ti = corr_ti.statistic, corr_ti.pvalue
md.append(f"| # Ingredients → Prestige | {r_ip:.4f} | {p_ip:.4e} | {_interpret(r_ip)} |")
md.append(f"| Prep Time → Prestige | {r_tp:.4f} | {p_tp:.4e} | {_interpret(r_tp)} |")
md.append(f"| Prep Time → # Ingredients | {r_ti:.4f} | {p_ti:.4e} | {_interpret(r_ti)} |")
md.append("")

# Best "bang for buck" recipes: high prestige, low ingredients
md.append("### Best Value Recipes (Prestige ≥ 85, Ingredients ≤ 6)\n")
best_value = df[(df["prestige"] >= 85) & (df["n_ingredients"] <= 6)].sort_values("prestige", ascending=False)
if len(best_value) > 0:
    md.append(best_value[["name", "prestige", "n_ingredients", "prep_s", "prestige_per_ing"]].to_markdown(index=False))
else:
    md.append("*No recipes match these criteria.*")
md.append("")

md.append("---\n")
md.append("*Generated automatically from live game server data.*\n")

# ── Write report ────────────────────────────────────────────────────────────
report_path = os.path.join(OUT_DIR, "analysis_report.md")
with open(report_path, "w", encoding="utf-8") as f:
    f.write("\n".join(md))

print(f"\n✅ Report written to: {report_path}")
print(f"✅ {len(os.listdir(IMG_DIR))} graphs saved to: {IMG_DIR}/")
