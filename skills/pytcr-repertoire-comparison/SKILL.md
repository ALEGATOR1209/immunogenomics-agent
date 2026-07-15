---
name: pytcr-repertoire-comparison
description: Compare adaptive immune receptor repertoires across samples in a scirpy MuData object — clonotype overlap matrices, Jaccard-distance heatmaps with hierarchical clustering, and pairwise sample scatterplots. Use after pytcr-clonotype-clustering, once clonotype IDs and a sample-identifying column exist in mdata.obs.
---

# Comparing Repertoires

Run this after `pytcr-clonotype-clustering`, once `mdata.obs["airr:clone_id"]` and a sample-identifying column (e.g. `"gex:sample"`) exist. This skill covers repertoire similarity and overlap between samples or sample groups — useful for pinpointing shared clonotype groups and quantifying how similar two repertoires are.

## Setup

```python
import scirpy as ir
```

---

## 1. Compute repertoire overlap

`ir.tl.repertoire_overlap` builds a matrix of clonotype abundance per sample (or other grouping), plus a Jaccard distance matrix between samples and the linkage from hierarchical clustering on that distance matrix.

Replace `<group_col>` with the column identifying samples/groups to compare (e.g. `"gex:sample"`):

```python
df, dst, lk = ir.tl.repertoire_overlap(mdata, "<group_col>", inplace=False)
df.head()
```

- `df` — clonotype × sample abundance matrix
- `dst` — Jaccard distance matrix between samples
- `lk` — hierarchical clustering linkage of `dst`

Use `inplace=False` to get the matrices back directly rather than storing them in `mdata.uns`.

## 2. Heatmap of sample similarity

Visualize `dst` as a heatmap, with samples reordered by the hierarchical clustering. `heatmap_cats` overlays additional categorical annotations (e.g. patient, tissue source) alongside the sample axis to help interpret clusters:

```python
_ = ir.pl.repertoire_overlap(
    mdata,
    "<group_col>",
    heatmap_cats=["<patient_col>", "<source_col>"],
    yticklabels=True,
    xticklabels=True,
)
```

Samples that cluster together share more clonotypes — e.g. samples from the same patient or tissue type typically cluster more tightly than samples across patients.

## 3. Pairwise sample scatterplot

Compare two specific samples directly: each point is a clonotype, positioned by its abundance in each of the two samples, with point size proportional to the number of cells at that coordinate. Replace `<sample_a>`/`<sample_b>` with values from `<group_col>`:

```python
ir.pl.repertoire_overlap(mdata, "<group_col>", pair_to_plot=["<sample_a>", "<sample_b>"], fig_kws={"dpi": 120})
```

Points off the diagonal represent clonotypes with skewed abundance between the two samples; points near the top-right represent clonotypes strongly shared by both.

---

## Post-analysis

Natural next steps once repertoire similarity is characterized:

- **Integrating gene expression**: clonotype modularity, clonotype imbalance among cell clusters, marker genes in top clonotypes
- **Epitope database query**: `ir.pp.ir_dist` + `ir.tl.ir_query` + `ir.tl.ir_query_annotate`
