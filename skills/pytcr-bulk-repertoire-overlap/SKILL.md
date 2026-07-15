---
name: pytcr-bulk-repertoire-overlap
description: Compare clonotype repertoires pairwise across many bulk TCR-Seq samples with pyTCR — Jaccard index, overlap coefficient, Morisita-Horn index, Tversky index, cosine similarity, Pearson correlation, relative overlap diversity, geometric-mean overlap frequencies, and Jensen-Shannon divergence of V-gene usage, each as a sample-by-sample heatmap. Use after pytcr-bulk-data-loading, once the standardized repertoire table (df) has 2+ samples.
---

# Bulk Repertoire Overlap Analysis

Run this after `pytcr-bulk-data-loading`, once `df` has the standard pyTCR columns and contains **at least two samples**. This skill covers pyTCR's overlap analysis (Peng et al. 2022, Table 1) — a comprehensive set of indices for comparing clonotype composition between every pair of samples. Unlike single-file tools that only accept one sample per file, this works directly on a `df` with any number of samples already combined (see `pytcr-bulk-data-loading`, Step 3).

## Setup

```python
import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib import pyplot as plt
from scipy.spatial.distance import cosine
```

---

## 1. Prepare pairwise overlap data

Every index below compares two samples' clonotypes, identified by exact match on CDR3 nucleotide sequence, CDR3 amino-acid sequence, and V/D/J genes. This step is shared across all indices: it self-joins the repertoire on those five columns to find every clonotype present in more than one sample, then indexes the result by sample pair for fast lookup — the same hash-join strategy the paper describes for its overlap-analysis performance.

```python
def prepare_overlap_data(df):
    df = df.copy()
    # keep only the first gene call when multiple were reported (e.g. "TRBV12-3/12-4")
    for col in ("v", "j"):
        df[col] = df[col].str.replace(r",.*", "", regex=True)

    sample_names = list(df["sample"].drop_duplicates())
    samples = {name: df[df["sample"] == name] for name in sample_names}

    df_compare = pd.merge(df, df, on=["cdr3nt", "cdr3aa", "v", "d", "j"], suffixes=["_1", "_2"])
    df_compare = df_compare[df_compare["sample_1"] != df_compare["sample_2"]]
    df_compare["#count_1**2"] = df_compare["#count_1"] ** 2
    df_compare["#count_2**2"] = df_compare["#count_2"] ** 2
    df_compare["#count_1*2"] = df_compare["#count_1"] * df_compare["#count_2"]

    df_overlaps = {}
    for i, sample1 in enumerate(sample_names):
        mask1 = df_compare["sample_1"] == sample1
        for sample2 in sample_names[i + 1:]:
            mask2 = df_compare["sample_2"] == sample2
            df_overlaps[f"{sample1}:{sample2}"] = df_compare.loc[mask1 & mask2]

    return sample_names, samples, df_overlaps

sample_names, samples, df_overlaps = prepare_overlap_data(df)
```

> This self-join is O(samples²) in the number of overlapping clonotypes, so it can get expensive with many samples or very deep repertoires — this matches the cost profile the paper itself reports for overlap analysis (its slowest analysis type, though still faster than VDJtools/Immunarch at the same task).

---

## 2. Compute an index across all sample pairs

Each overlap index reduces to: take two samples' clonotype tables plus their overlap subset, return one number. A single driver runs any such function over every sample pair and returns a long-format table (both `(s1, s2)` and `(s2, s1)` rows, matching how the source heatmaps are built):

```python
def compute_pairwise_index(sample_names, samples, df_overlaps, metric_fn, value_col):
    rows = []
    for i, sample1 in enumerate(sample_names):
        df_sample1 = samples[sample1]
        for sample2 in sample_names[i + 1:]:
            df_sample2 = samples[sample2]
            df_overlap = df_overlaps[f"{sample1}:{sample2}"]
            value = metric_fn(df_sample1, df_sample2, df_overlap)
            rows.append({"sample_1": sample1, "sample_2": sample2, value_col: value})
            rows.append({"sample_1": sample2, "sample_2": sample1, value_col: value})
    return pd.DataFrame(rows)
```

And a shared heatmap plotter:

```python
def plot_overlap_heatmap(df_index, value_col, label):
    sns.set_style("white")
    sns.set_context("talk")
    plt.figure(figsize=(20, 20))

    df_index = df_index.copy()
    df_index[value_col] = df_index[value_col].astype(float)
    pivoted = df_index.pivot(index="sample_2", columns="sample_1", values=value_col)

    ax = sns.heatmap(pivoted, cmap="coolwarm", xticklabels=False, yticklabels=False, cbar_kws={"label": label})
    ax.figure.axes[-1].yaxis.label.set_size(30)
    ax.set_xlabel("Samples", fontsize=30)
    ax.set_ylabel("Samples", fontsize=30)
    cbar = ax.collections[0].colorbar
    cbar.ax.tick_params(labelsize=25)
    bottom, top = ax.get_ylim()
    ax.set_ylim(bottom + 0.5, top - 0.5)
    sns.despine()
    return ax
```

---

## 3. Overlap indices

Each metric function below plugs into `compute_pairwise_index`.

```python
def jaccard_index(df_s1, df_s2, df_overlap):
    n_overlap = len(df_overlap)
    return n_overlap / (len(df_s1) + len(df_s2) - n_overlap)

def overlap_coefficient(df_s1, df_s2, df_overlap):
    return len(df_overlap) / min(len(df_s1), len(df_s2))

def morisita_horn_index(df_s1, df_s2, df_overlap):
    sum1, sum2 = df_s1["#count"].sum(), df_s2["#count"].sum()
    sum_sq1 = df_overlap["#count_1**2"].sum()
    sum_sq2 = df_overlap["#count_2**2"].sum()
    sum_cross = df_overlap["#count_1*2"].sum()
    denom = ((sum_sq1 / sum1 ** 2) + (sum_sq2 / sum2 ** 2)) * sum1 * sum2
    return (2 * sum_cross) / denom

def tversky_index(df_s1, df_s2, df_overlap, alpha=0.5, beta=0.5):
    both = len(df_overlap)
    only1, only2 = len(df_s1) - both, len(df_s2) - both
    return both / (both + alpha * only1 + beta * only2)

def cosine_similarity_index(df_s1, df_s2, df_overlap):
    return 1 - cosine(df_overlap["freq_1"], df_overlap["freq_2"])

def pearson_correlation(df_s1, df_s2, df_overlap, value_col="#count"):
    return df_overlap[f"{value_col}_1"].corr(df_overlap[f"{value_col}_2"])

def relative_overlap_diversity(df_s1, df_s2, df_overlap):
    return len(df_overlap) / (len(df_s1) * len(df_s2))

def geometric_mean_relative_overlap_frequency(df_s1, df_s2, df_overlap):
    return (df_overlap["freq_1"].sum() * df_overlap["freq_2"].sum()) ** 0.5

def clonotype_wise_geometric_mean_frequency(df_s1, df_s2, df_overlap):
    return ((df_overlap["freq_1"] * df_overlap["freq_2"]) ** 0.5).sum()
```

- **Jaccard index** — clonotypes in both samples ÷ clonotypes in either sample.
- **Overlap coefficient** — clonotypes in both ÷ size of the *smaller* sample. (The published notebook has a variable-binding bug here that used the wrong sample's size as the denominator in some pairs; `min(len(df_s1), len(df_s2))` is the correct, order-independent form and is what's used above.)
- **Morisita-Horn index** — abundance-weighted overlap using squared read counts.
- **Tversky index** — with `alpha=beta=0.5` this is the Sørensen–Dice coefficient.
- **Cosine similarity** — cosine of the two samples' frequency vectors over the overlapping clonotypes.
- **Pearson correlation** — pass `value_col="#count"` or `value_col="freq"` for the two variants the paper reports.
- **Relative overlap diversity** — overlap size normalized by the product of both sample sizes.
- **Geometric mean of relative overlap frequencies** — geometric mean of each sample's total frequency mass contributed by overlapping clonotypes.
- **Clonotype-wise sum of geometric mean frequencies** — per-clonotype geometric mean of the two frequencies, summed over the overlap.

```python
df_jaccard = compute_pairwise_index(sample_names, samples, df_overlaps, jaccard_index, "jaccard_index")
df_overlap_coef = compute_pairwise_index(sample_names, samples, df_overlaps, overlap_coefficient, "overlap_coefficient")
df_morisita_horn = compute_pairwise_index(sample_names, samples, df_overlaps, morisita_horn_index, "morisita_horn_index")
df_tversky = compute_pairwise_index(sample_names, samples, df_overlaps, tversky_index, "tversky_index")
df_cosine = compute_pairwise_index(sample_names, samples, df_overlaps, cosine_similarity_index, "cosine_similarity")
df_pearson_count = compute_pairwise_index(sample_names, samples, df_overlaps, lambda s1, s2, o: pearson_correlation(s1, s2, o, "#count"), "pearson_correlation")
df_pearson_freq = compute_pairwise_index(sample_names, samples, df_overlaps, lambda s1, s2, o: pearson_correlation(s1, s2, o, "freq"), "pearson_correlation")
df_rel_overlap_div = compute_pairwise_index(sample_names, samples, df_overlaps, relative_overlap_diversity, "relative_overlap_diversity")
df_geo_mean_overlap = compute_pairwise_index(sample_names, samples, df_overlaps, geometric_mean_relative_overlap_frequency, "geometric_mean_of_relative_overlap_frequencies")
df_clonotype_geo_mean = compute_pairwise_index(sample_names, samples, df_overlaps, clonotype_wise_geometric_mean_frequency, "clonotype_wise_sum_of_geometric_mean_frequencies")

plot_overlap_heatmap(df_jaccard, "jaccard_index", "Jaccard index")
```

---

## 4. Jensen-Shannon divergence of V-gene usage

Unlike the indices above, this compares samples by their **V-gene usage distribution**, not exact clonotype overlap — so it uses a separate driver over `samples` directly rather than `df_overlaps`:

```python
def kl_divergence(p, q):
    return -np.sum(p * np.log2(q / p))

def js_divergence(p, q):
    m = 0.5 * (p + q)
    return 0.5 * kl_divergence(p, m) + 0.5 * kl_divergence(q, m)

def jensen_shannon_v_usage(sample_names, samples):
    rows = []
    for i, sample1 in enumerate(sample_names):
        v_usage_1 = samples[sample1].groupby("v")["freq"].sum().reset_index(name="sumfreq_1")
        for sample2 in sample_names[i + 1:]:
            v_usage_2 = samples[sample2].groupby("v")["freq"].sum().reset_index(name="sumfreq_2")
            merged = pd.merge(v_usage_1, v_usage_2, on="v")
            value = js_divergence(merged[["sumfreq_1"]].to_numpy(), merged[["sumfreq_2"]].to_numpy())
            rows.append({"sample_1": sample1, "sample_2": sample2, "jensen_shannon_divergence": value})
            rows.append({"sample_1": sample2, "sample_2": sample1, "jensen_shannon_divergence": value})
    return pd.DataFrame(rows)

df_jsd = jensen_shannon_v_usage(sample_names, samples)
plot_overlap_heatmap(df_jsd, "jensen_shannon_divergence", "Jensen-Shannon divergence")
```

Only V genes present in *both* samples (the inner join on `"v"`) contribute to the divergence — genes unique to one sample are dropped rather than treated as zero-frequency, matching the reference notebook.

---

## Post-analysis

Overlap analysis is typically the last step in a bulk pyTCR workflow, after:

- **Basic / clonality / diversity metrics**: `pytcr-bulk-repertoire-metrics`
- **Gene usage and motif analysis**: `pytcr-bulk-gene-motifs`
