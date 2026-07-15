---
name: pytcr-bulk-gene-motifs
description: Analyze V/D/J gene usage (heatmaps, clustered heatmaps, V-J Sankey diagrams) and CDR3 amino-acid/nucleotide motif enrichment in bulk TCR-Seq repertoires with pyTCR. Use after pytcr-bulk-data-loading, once the standardized repertoire table (df) is available.
---

# Bulk Gene Usage and Motif Analysis

Run this after `pytcr-bulk-data-loading`, once `df` has the standard pyTCR columns. This skill covers two of pyTCR's six analysis types: gene usage analysis and motif analysis (Peng et al. 2022, Table 1).

## Setup

```python
import pandas as pd
import seaborn as sns
from matplotlib import pyplot as plt
```

Code below reuses `group_cols`, the list of metadata columns from `pytcr-bulk-data-loading` (e.g. `["hospitalized"]`, or `[]` if none).

---

## 1. Gene usage analysis

### 1a. Weighted V gene usage

"Weighted" means usage is summed by clonotype frequency (as opposed to unweighted, which sums by clonotype count — not covered by the reference implementation, but follows the same pattern substituting `#count` for `freq`). Excludes ambiguous V-gene calls (`unknown`, `or`, multi-gene calls containing `/`):

```python
def gene_usage(df, gene_col="v", group_cols=None):
    group_cols = group_cols or []
    df_usage = df.groupby(["sample", gene_col] + group_cols, as_index=False)["freq"].sum().rename(columns={"freq": "frequency"})
    for pattern in ["unknown", "or", "/"]:
        df_usage = df_usage[~df_usage[gene_col].str.contains(pattern, regex=False)]
    return df_usage

df_v_usage = gene_usage(df, gene_col="v", group_cols=group_cols)
```

Same function works for D (`gene_col="d"`) and J (`gene_col="j"`) gene usage.

### 1b. Heatmap

```python
def plot_gene_usage_heatmap(df_usage, gene_col, title):
    sns.set_style("white")
    sns.set_context("talk")
    plt.figure(figsize=(20, 20))

    pivoted = df_usage.pivot(index=gene_col, columns="sample", values="frequency").fillna(0)
    ax = sns.heatmap(pivoted, cmap="coolwarm", cbar_kws={"label": f"{gene_col.upper()} gene frequency"})
    ax.set_xlabel("Sample", fontsize=30)
    ax.set_ylabel(f"{gene_col.upper()} gene", fontsize=30)
    plt.xticks(fontsize=20)
    plt.yticks(fontsize=20)
    plt.title(title, fontsize=30)
    ax.figure.axes[-1].yaxis.label.set_size(25)
    bottom, top = ax.get_ylim()
    ax.set_ylim(bottom + 0.5, top - 0.5)
    sns.despine()
    return ax

plot_gene_usage_heatmap(df_v_usage, "v", "V gene weighted usage")
```

### 1c. Hierarchically-clustered heatmap

Same data, clustered by similarity across samples and genes:

```python
def plot_gene_usage_clustermap(df_usage, gene_col, title):
    sns.set_style("white")
    sns.set_context("talk")

    pivoted = pd.pivot_table(df_usage, values="frequency", index=[gene_col], columns="sample").fillna(0)
    g = sns.clustermap(pivoted, cmap="coolwarm", vmin=0, vmax=1, figsize=(20, 20), cbar_pos=(0.02, 0.8, 0.03, 0.2))
    plt.setp(g.ax_heatmap.xaxis.get_majorticklabels(), fontsize=20)
    plt.setp(g.ax_heatmap.yaxis.get_majorticklabels(), fontsize=20)
    g.ax_heatmap.set_xlabel("Sample", fontsize=30)
    g.ax_heatmap.set_ylabel(f"{gene_col.upper()} gene", fontsize=30)
    g.fig.suptitle(title, fontsize=30)
    sns.despine()
    return g

plot_gene_usage_clustermap(df_v_usage, "v", "V gene weighted usage")
```

### 1d. V-J combination Sankey diagram

Visualizes, for one sample, how V genes pair with J genes (edge width ∝ combined clonotype frequency). Requires `holoviews` with the `bokeh` backend (`pip install holoviews bokeh`). Alleles are stripped from gene names (e.g. `TRBV20-1` → `TRBV20`) so the diagram groups by gene, not allele:

```python
import holoviews as hv
hv.extension("bokeh", "matplotlib")

def build_vj_sankey_data(df_sample):
    df_sample = df_sample[df_sample["v"] != "unknown"].copy()
    df_sample["v"] = df_sample["v"].replace(r"\-.*$", "", regex=True)
    df_sample["j"] = df_sample["j"].replace(r"\-.*$", "", regex=True)
    df_sankey = (
        df_sample.groupby(["v", "j"])["freq"].sum().reset_index()
        .rename(columns={"v": "source", "j": "target", "freq": "value"})
    )
    return df_sankey[df_sankey["value"] > 0]

df_sankey = build_vj_sankey_data(df[df["sample"] == "<sample_name>"])
graph = hv.Sankey(df_sankey)
graph.opts(
    cmap="Category10", label_position="left", edge_line_width=1, edge_color="source",
    label_text_font_size="16pt", width=1024, height=2048, bgcolor="snow",
    node_alpha=1.0, node_width=40, node_sort=True, show_values=False,
)
hv.save(graph, "<output_path>", fmt="html")
graph
```

---

## 2. Motif analysis

### 2a. Amino-acid spectratype

Frequency of clonotypes by CDR3 amino-acid length, per sample:

```python
df["aa_length"] = df["cdr3aa"].str.len()
df_aa_spectratype = df.groupby(["sample", "aa_length"] + group_cols, as_index=False)["freq"].sum().rename(columns={"freq": "spectratype"})
```

Visualize with the `plot_metric_by_group` helper from `pytcr-bulk-repertoire-metrics` (e.g. plot `aa_length` at each sample's peak spectratype value), or as a bar/line plot of `spectratype` vs. `aa_length` per sample/group.

### 2b. K-mer motif counting

Counts every overlapping length-`k` substring across a sample's CDR3 sequences. The same algorithm applies to amino-acid and nucleotide sequences — only the input column changes:

```python
def count_kmer_motifs(k, sequences):
    counts = {}
    for seq in sequences:
        for i in range(len(seq) - k + 1):
            motif = seq[i:i + k]
            counts[motif] = counts.get(motif, 0) + 1
    return counts

def motif_counts_by_sample(df, seq_col, k, group_cols=None):
    group_cols = group_cols or []
    rows = []
    for sample, df_sample in df.groupby("sample"):
        counts = count_kmer_motifs(k, df_sample[seq_col])
        df_counts = pd.DataFrame(counts.items(), columns=["motif", "count"])
        df_counts["sample"] = sample
        for col in group_cols:
            df_counts[col] = df_sample[col].iloc[0]
        rows.append(df_counts)
    return pd.concat(rows, ignore_index=True)

df_aa_motifs = motif_counts_by_sample(df, "cdr3aa", k=6, group_cols=group_cols)
df_nt_motifs = motif_counts_by_sample(df, "cdr3nt", k=6, group_cols=group_cols)
```

### 2c. Filter to enriched motifs

Restrict to motifs above a count threshold that also recur across multiple samples within a group — otherwise every rare motif shows up and the plot is unreadable. Thresholds are dataset-dependent; the paper used `min_count=9999` for amino-acid motifs (k=6) and `min_count=150000` for nucleotide motifs (k=6) on the COVID19-BWNW dataset, both with `min_samples=2`:

```python
def filter_enriched_motifs(df_motifs, min_count, min_samples, group_col):
    df_filtered = df_motifs[df_motifs["count"] > min_count]
    presence = df_filtered.groupby([group_col, "motif"], sort=False).size().reset_index(name="number_of_samples")
    presence = presence[presence["number_of_samples"] > min_samples]
    return pd.merge(df_filtered, presence, on=[group_col, "motif"])

df_aa_enriched = filter_enriched_motifs(df_aa_motifs, min_count=9999, min_samples=2, group_col="<group_col>")
df_nt_enriched = filter_enriched_motifs(df_nt_motifs, min_count=150000, min_samples=2, group_col="<group_col>")
```

### 2d. Visualize

```python
def plot_motif_counts(df_enriched, group_col, xlabel):
    sns.set_style("white")
    sns.set_context("talk")
    fig, ax = plt.subplots(figsize=(8, 5))
    sns.stripplot(data=df_enriched, x="motif", y="count", hue=group_col, dodge=True, size=6, linewidth=1, ax=ax)
    ax.set_xlabel(xlabel, fontsize=20)
    ax.set_ylabel("Count", fontsize=20)
    plt.xticks(fontsize=18, rotation=90)
    plt.yticks(fontsize=18)
    plt.setp(ax.get_legend().get_texts(), fontsize="20")
    plt.setp(ax.get_legend().get_title(), fontsize="20")
    sns.despine()
    return ax

plot_motif_counts(df_aa_enriched, "<group_col>", "Amino acid motif")
plot_motif_counts(df_nt_enriched, "<group_col>", "Nucleotide motif")
```

---

## Post-analysis

With gene usage and motifs characterized, the natural next step is:

- **Cross-sample overlap analysis**: `pytcr-bulk-repertoire-overlap`
