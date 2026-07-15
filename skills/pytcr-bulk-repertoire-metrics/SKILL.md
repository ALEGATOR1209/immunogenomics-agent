---
name: pytcr-bulk-repertoire-metrics
description: Compute and visualize per-sample bulk TCR-Seq repertoire metrics with pyTCR — basic counts, clonality (clonal proportion, relative-abundance clonotype groups), and diversity indices (Shannon-Wiener, Simpson, D50, Chao1, Gini). Use after pytcr-bulk-data-loading, once the standardized repertoire table (df) is available.
---

# Bulk Repertoire Metrics: Basic, Clonality, Diversity

Run this after `pytcr-bulk-data-loading`, once `df` has the standard pyTCR columns (`sample`, `freq`, `#count`, `cdr3aa`, `cdr3nt`, `v`, `d`, `j`, `count`, `clonotype_count`, plus any metadata columns). This skill covers three of pyTCR's six analysis types: basic analysis, clonality analysis, and diversity analysis (Peng et al. 2022, Table 1).

## Setup

```python
import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib import pyplot as plt
```

Code below reuses `group_cols`, the list of metadata columns to group/compare by (e.g. `["hospitalized"]`, or `[]` if none) — the same list passed to `pytcr-bulk-data-loading`, Step 4.

---

## 1. Basic analysis

Read count and clonotype count per sample were already computed during loading (`pytcr-bulk-data-loading`, Step 4) and live in the `count` and `clonotype_count` columns. A one-row-per-sample summary:

```python
df_basic = df[["sample"] + group_cols + ["count", "clonotype_count"]].drop_duplicates()
```

> The paper's Table 1 also defines mean/geometric-mean clonotype frequency, mean CDR3-nt length, convergence, and nucleotide-level spectratype as basic-analysis metrics. Those aren't covered here — the reference implementation only computes read count and clonotype count as usable per-sample summaries; the rest are formulas in the paper without a working reference implementation to port faithfully.

---

## 2. Visualizing a metric across sample groups

Most metrics below end up as one value per `sample` (optionally grouped by a metadata column, e.g. `hospitalized`) and get compared across groups. Rather than repeating plotting code per metric, use one helper supporting all seven plot types pyTCR offers:

```python
_PLOT_FNS = {
    "violin": sns.violinplot, "strip": sns.stripplot, "swarm": sns.swarmplot,
    "box": sns.boxplot, "boxen": sns.boxenplot, "point": sns.pointplot, "bar": sns.barplot,
}

def plot_metric_by_group(df_metric, metric_col, group_col, plot_type="box", ylabel=None, group_labels=None, overlay_strip=False):
    sns.set_style("white")
    sns.set_context("talk")
    fig, ax = plt.subplots(figsize=(5, 5))
    _PLOT_FNS[plot_type](x=group_col, y=metric_col, data=df_metric, ax=ax)
    if overlay_strip:
        sns.stripplot(x=group_col, y=metric_col, data=df_metric, s=6, dodge=True, linewidth=1, ax=ax)
    ax.set_xlabel(None)
    ax.set_ylabel(ylabel or metric_col, fontsize=20)
    if group_labels:
        ax.set_xticklabels(group_labels)
    plt.xticks(fontsize=20)
    plt.yticks(fontsize=20)
    sns.despine()
    return ax
```

`plot_type` is one of `violin`, `strip`, `swarm`, `box`, `boxen`, `point`, `bar`. `overlay_strip=True` reproduces the paper's Figure 1A style (box plot + strip plot overlay).

```python
plot_metric_by_group(df_basic, "clonotype_count", "<group_col>", plot_type="box", ylabel="Number of clonotypes", overlay_strip=True)
```

---

## 3. Clonality analysis

Clonality assesses how evenly reads are distributed across clonotypes in a sample.

### 3a. Clonal proportion

The number of top clonotypes (by frequency) needed to reach a given cumulative share of reads — smaller means the repertoire is more dominated by a few large clones. `threshold` is fully customizable (the paper uses 10%):

```python
def clonal_proportion(df, threshold=0.1, group_cols=None):
    group_cols = group_cols or []
    rows = []
    for sample, df_sample in df.groupby("sample"):
        df_sorted = df_sample.sort_values("freq", ascending=False).reset_index(drop=True)
        accum_freq = df_sorted["freq"].cumsum()
        n_clonotypes = int((accum_freq <= threshold).sum())
        if n_clonotypes == 0:
            continue  # even the single largest clonotype already exceeds the threshold
        row = {"sample": sample, "clonal_proportion": n_clonotypes}
        for col in group_cols:
            row[col] = df_sorted[col].iloc[0]
        rows.append(row)
    return pd.DataFrame(rows)

df_clonal_proportion = clonal_proportion(df, threshold=0.1, group_cols=group_cols)
plot_metric_by_group(df_clonal_proportion, "clonal_proportion", "<group_col>", plot_type="violin", ylabel="Clonal proportion (10%)")
```

### 3b. Relative abundance by clonotype size group

Buckets clonotypes into frequency-based size classes and shows, per sample, how much of the repertoire (by cumulative frequency) each class accounts for. Default bucket edges match the paper (hyperexpanded/large/medium/small/rare); pass your own `bins`/`labels` to customize — the paper explicitly calls out that these thresholds should be user-adjustable:

```python
def clonotype_size_group(freq, bins=(0, 1e-5, 1e-4, 1e-3, 1e-2, 1), labels=("Rare", "Small", "Medium", "Large", "Hyperexpanded")):
    return pd.cut(freq, bins=bins, labels=labels)

df["clonotype_group"] = clonotype_size_group(df["freq"])
df_relative_abundance = df.groupby(["sample", "clonotype_group"], observed=True)["freq"].sum().reset_index()
```

Stacked bar plot, one bar per sample:

```python
def plot_stacked_clonotype_groups(df_relative_abundance, value_col, label_order, ylabel):
    sns.set_style("white")
    sns.set_context("talk")
    ax = df_relative_abundance.groupby(["sample", "clonotype_group"], observed=True)[value_col].sum().unstack()[label_order].plot(kind="bar", stacked=True)
    plt.legend(title="Clonotype groups", ncol=len(label_order), loc="upper right", bbox_to_anchor=(0.85, 1.1), handletextpad=0.1, prop={"size": 20})
    ax.set_xlabel("Sample", fontsize=20)
    ax.set_ylabel(ylabel, fontsize=20)
    plt.xticks(fontsize=20)
    plt.yticks(fontsize=20)
    plt.gcf().set_size_inches(20, 10)
    sns.despine()
    return ax

plot_stacked_clonotype_groups(df_relative_abundance, "freq", ["Hyperexpanded", "Large", "Medium", "Small", "Rare"], "Clonotype frequency")
```

The same pattern also works restricted to the top-N or bottom-N clonotypes by frequency (the paper illustrates this on the top 100 and rare 100, bucketed by read count rather than frequency). The two ends of the repertoire use different bucket resolutions — the rare end needs finer bins since read counts cluster near 1:

```python
def top_or_rare_by_read_count(df, n=100, top=True, bins=None, labels=None):
    if top:
        bins = bins or (1, 10, 100, 1000, 5000)
        labels = labels or ("1-10", "11-100", "101-1000", "1001-5000")
    else:
        bins = bins or (0, 1, 3, 10, 30, 100, 200)
        labels = labels or ("1", "2-3", "4-10", "11-30", "31-100", "101-200")

    df_subset = (
        df.sort_values(["sample", "freq"]).groupby("sample").tail(n)
        if top else
        df.sort_values(["sample", "freq"]).groupby("sample").head(n)
    )
    df_subset = df_subset.copy()
    df_subset["reads_group"] = pd.cut(df_subset["#count"], bins=bins, labels=labels)
    return df_subset

df_top100 = top_or_rare_by_read_count(df, n=100, top=True)
plot_stacked_clonotype_groups(df_top100.rename(columns={"reads_group": "clonotype_group"}), "#count", list(df_top100["reads_group"].cat.categories), "Clonotype count")

df_rare100 = top_or_rare_by_read_count(df, n=100, top=False)
```

---

## 4. Diversity analysis

All indices are computed per sample from the `freq` column. High Shannon-Wiener, low normalized Shannon-Wiener, high inverse Simpson, high Gini Simpson, high Chao1, and high Gini coefficient all indicate *high* clonal diversity.

```python
def diversity_metrics(df, group_cols=None):
    group_cols = group_cols or []
    keys = ["sample"] + group_cols

    df = df.copy()
    df["_shannon_term"] = -(df["freq"] * np.log(df["freq"]))
    df["_simpson_term"] = df["freq"] ** 2

    agg = df.groupby(keys).agg(
        shannon_index=("_shannon_term", "sum"),
        simpson_index=("_simpson_term", "sum"),
        clonotype_count=("freq", "size"),
    ).reset_index()

    agg["shannon_wiener_index"] = np.exp(agg["shannon_index"])
    agg["normalized_shannon_wiener_index"] = agg["shannon_index"] / np.log(agg["clonotype_count"])
    agg["inverse_simpson_index"] = 1 / agg["simpson_index"]
    agg["gini_simpson_index"] = 1 - agg["simpson_index"]

    d50_rows, chao1_rows = [], []
    for sample, df_sample in df.groupby("sample"):
        d50_rows.append({"sample": sample, "D50_index": _d50(df_sample)})
        chao1, chao1_sd = _chao1(df_sample)
        chao1_rows.append({"sample": sample, "chao1": chao1, "chao1_SD": chao1_sd})
    df_d50 = pd.DataFrame(d50_rows)
    df_chao1 = pd.DataFrame(chao1_rows)
    df_gini = df.groupby("sample").agg(gini_coefficient=("freq", _gini)).reset_index()

    result = agg.merge(df_d50, on="sample").merge(df_chao1, on="sample").merge(df_gini, on="sample")
    return result.drop(columns=["shannon_index", "simpson_index"])


def _d50(df_sample):
    df_sorted = df_sample.sort_values("freq", ascending=False).reset_index(drop=True)
    accum_freq = df_sorted["freq"].cumsum()
    n_to_reach_half = int((accum_freq < 0.5).sum()) + 1
    return n_to_reach_half / len(df_sorted) * 100


def _chao1(df_sample):
    s = len(df_sample)
    f1 = (df_sample["#count"] == 1).sum()
    f2 = (df_sample["#count"] == 2).sum()
    chao1 = s + (f1 * (f1 - 1)) / (2 * (f2 + 1))
    chao1_sd = (f2 * (0.5 * (f1 / f2) ** 2 + (f1 / f2) ** 3 + 0.25 * (f1 / f2) ** 4)) ** 0.5 if f2 else np.nan
    return chao1, chao1_sd


def _gini(freq_values):
    sorted_values = np.sort(freq_values.to_numpy())
    height, area = 0.0, 0.0
    for value in sorted_values:
        height += value
        area += height - value / 2.0
    fair_area = height * len(sorted_values) / 2.0
    return (fair_area - area) / fair_area


df_diversity_metrics = diversity_metrics(df, group_cols=group_cols)
```

- **Shannon-Wiener index** (`shannon_wiener_index`) / **normalized Shannon-Wiener index** — normalized divides by `log(clonotype_count)`, making it comparable across samples with different numbers of clonotypes.
- **Inverse Simpson index** / **Gini Simpson index** — both derived from the Simpson index `D = Σ pᵢ²`.
- **D50 index** — percentage of clonotypes needed to account for ≥50% of reads.
- **Chao1 estimate** (+ SD) — richness estimator from singleton/doubleton clonotype counts (`#count == 1` / `== 2`); undefined (`NaN`) if a sample has no doubletons.
- **Gini coefficient** — inequality of the frequency distribution (0 = perfectly even, 1 = maximally uneven).

Visualize any of them with the same helper from Section 2:

```python
plot_metric_by_group(df_diversity_metrics, "normalized_shannon_wiener_index", "<group_col>", plot_type="violin", ylabel="Normalized Shannon Wiener index")
```

---

## Post-analysis

With basic, clonality, and diversity metrics computed, the natural next steps are:

- **Gene usage and motif analysis**: `pytcr-bulk-gene-motifs`
- **Cross-sample overlap analysis**: `pytcr-bulk-repertoire-overlap`
