---
name: pytcr-repertoire-comparison
description: Compare adaptive immune receptor repertoires across samples in a scirpy MuData object — clonotype overlap matrices, Jaccard-distance heatmaps with hierarchical clustering, and pairwise sample scatterplots. Use after pytcr-clonotype-clustering, once clonotype IDs and a sample-identifying column exist in mdata.obs.
---

# Comparing Repertoires

Run this after `pytcr-clonotype-clustering`, once `mdata.obs["airr:clone_id"]` and a sample-identifying column (e.g. `"gex:sample"`) exist. Every `.pl.*` call below has a no-plot, data-only alternative next to it — for agents that can't process images.

## Setup

```python
import pandas as pd
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

- `df` — sample × clonotype abundance matrix (`df.index` gives the sample labels, in the same order as `dst`/`lk`)
- `dst` — condensed Jaccard distance array between samples (`scipy.spatial.distance.pdist` output — not a labeled matrix; pair with `df.index` and `squareform` to get named pairwise distances, see Section 2)
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

Samples that cluster together share more clonotypes (e.g. same-patient/tissue samples typically cluster tighter than cross-patient ones).

> **No-plot alternative:** read `dst`/`lk` (from Section 1) directly instead of the heatmap's colors/dendrogram order — named pairwise distances, or explicit per-sample cluster labels cut from the linkage.
> ```python
> from scipy.spatial.distance import squareform
>
> dist_df = pd.DataFrame(squareform(dst), index=df.index, columns=df.index)
> dist_df.stack().loc[lambda s: s > 0].sort_values()  # smallest distances = most similar sample pairs
>
> from scipy.cluster.hierarchy import fcluster
> cluster_labels = pd.Series(fcluster(lk, t=<threshold>, criterion="distance"), index=df.index)  # explicit group per sample
> ```

## 3. Pairwise sample scatterplot

Compare two specific samples directly: each point is a clonotype, positioned by its abundance in each of the two samples, with point size proportional to the number of cells at that coordinate. Replace `<sample_a>`/`<sample_b>` with values from `<group_col>`:

```python
ir.pl.repertoire_overlap(mdata, "<group_col>", pair_to_plot=["<sample_a>", "<sample_b>"], fig_kws={"dpi": 120})
```

Points off the diagonal represent clonotypes with skewed abundance between the two samples; points near the top-right represent clonotypes strongly shared by both.

> **No-plot alternative:** the same per-clonotype abundances the scatterplot draws from, plus the single overlap-distance number for the pair — both read straight out of Section 1's `df`/`dst` (`df`'s rows are samples, columns are clonotypes).
> ```python
> pair_abundance = df.loc[["<sample_a>", "<sample_b>"], :].T  # clonotype rows, one column per sample
> pair_abundance.loc[(pair_abundance != 0).all(axis=1)]  # clonotypes present in both samples
>
> from scipy.spatial.distance import squareform
> pd.DataFrame(squareform(dst), index=df.index, columns=df.index).loc["<sample_a>", "<sample_b>"]  # overlap distance
> ```

---

## Post-analysis

Natural next steps: GEX integration (clonotype modularity/imbalance across clusters, marker genes in top clonotypes) or epitope database query (`ir.pp.ir_dist` + `ir.tl.ir_query` + `ir.tl.ir_query_annotate`).
