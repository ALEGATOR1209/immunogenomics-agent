---
name: pytcr-gex-integration
description: Integrate gene expression (GEX) data with immune-receptor clonotypes in a scirpy MuData object — clonotype modularity, clonotype imbalance between cell clusters, repertoire overlap between cell types, and marker-gene / differential-expression analysis of top clonotypes. Use after pytcr-clonotype-clustering and pytcr-clonotype-analysis, once clonotype IDs, a GEX embedding, and cell-type cluster annotations exist in mdata.
---

# Integrating Gene Expression Data

Run this after `pytcr-clonotype-clustering` and `pytcr-clonotype-analysis`, once `mdata["gex"]` has a computed embedding/clustering (e.g. `gex:umap`, `gex:cluster`) and `mdata.obs` has clonotype IDs. Cross-modality analyses combining transcriptomics with receptor identity. Every `.pl.*` call below has a no-plot, data-only alternative next to it — for agents that can't process images.

## Setup

```python
import muon as mu
import pandas as pd
import scanpy as sc
import scirpy as ir
from cycler import cycler
from matplotlib import cm as mpl_cm
from matplotlib import pyplot as plt
```

---

## 1. Clonotype modularity

Clonotype modularity flags clonotypes (or clusters) whose cells are transcriptionally *more similar to each other than expected by chance* — the log2 fold change of cell-cell neighborhood-graph edges within the clonotype vs. a random background model. A high score means a consistent molecular phenotype.

### 1a. Compute

Replace `<cc_col>` with the clonotype (or clonotype cluster) column to score, e.g. `"airr:cc_aa_tcrdist"`:

```python
ir.tl.clonotype_modularity(mdata, target_col="<cc_col>")
```

Adds `mdata.obs["airr:clonotype_modularity"]`.

### 1b. Visualize

On the GEX embedding:

```python
mu.pl.embedding(mdata, basis="gex:umap", color="airr:clonotype_modularity")
```

On the clonotype network (see `pytcr-clonotype-clustering`, Step 4):

```python
_ = ir.pl.clonotype_network(mdata, color="clonotype_modularity", label_fontsize=9, panel_size=(6, 6), base_size=20)
```

As a one-sided volcano plot (modularity score vs. FDR):

```python
ir.pl.clonotype_modularity(mdata, base_size=20)
```

> **No-plot alternative:** none of these three plots are needed to rank or threshold clonotypes by modularity — the score and its FDR are already plain `obs` columns from Step 1a. See 1c below for the ranking snippet; the FDR sits alongside it in `mdata.obs["airr:clonotype_modularity_fdr"]`.
> ```python
> mdata.obs.set_index("<cc_col>")[["airr:clonotype_modularity", "airr:clonotype_modularity_fdr"]].drop_duplicates().sort_values("airr:clonotype_modularity", ascending=False)
> ```

### 1c. Inspect top-scoring clonotypes

Extract the N clonotypes with the highest modularity:

```python
clonotypes_top_modularity = list(
    mdata.obs.set_index("<cc_col>")["airr:clonotype_modularity"]
    .sort_values(ascending=False)
    .index.unique()
    .values[:2]
)
```

Highlight them on the embedding to check whether they localize to a specific transcriptional cluster:

```python
mu.pl.embedding(
    mdata,
    basis="gex:umap",
    color="<cc_col>",
    groups=clonotypes_top_modularity,
    palette=cycler(color=mpl_cm.Dark2_r.colors),
)
```

> **No-plot alternative:** the same localization question — do these clonotypes concentrate in one transcriptional cluster — as a cross-tab.
> ```python
> pd.crosstab(mdata.obs["<cc_col>"], mdata.obs["<cluster_col>"]).loc[clonotypes_top_modularity]
> ```

### 1d. Differential expression of top clonotypes vs. the rest

`sc.tl.rank_genes_groups` doesn't understand `MuData`, so temporarily attach the clonotype column to the GEX `AnnData` with `ir.get.obs_context`:

```python
with ir.get.obs_context(mdata["gex"], {"cc_aa_tcrdist": mdata.obs["<cc_col>"]}) as tmp_ad:
    sc.tl.rank_genes_groups(tmp_ad, "cc_aa_tcrdist", groups=clonotypes_top_modularity, reference="rest", method="wilcoxon")
    fig, axs = plt.subplots(1, 2, figsize=(8, 4))
    for ct, ax in zip(clonotypes_top_modularity, axs, strict=False):
        sc.pl.rank_genes_groups_violin(tmp_ad, groups=[ct], n_genes=15, ax=ax, show=False, strip=False)
```

> **No-plot alternative:** per-gene scores/fold-changes/adjusted p-values as a DataFrame — the sign of `logfoldchanges` says up or down, no violin shape-reading needed.
> ```python
> for ct in clonotypes_top_modularity:
>     df = sc.get.rank_genes_groups_df(tmp_ad, group=ct)
>     print(ct, df.head(15))  # or df.set_index("names").loc["<gene>", "logfoldchanges"] for one gene
> ```

---

## 2. Clonotype imbalance among cell clusters

`ir.tl.clonotype_imbalance` finds clonotypes that are differentially distributed between two cell-type groups (e.g. two GEX clusters), using per-sample replicates to test significance.

Replace `<sample_col>` with the sample-identifying column, `<cluster_col>` with the cell-type column, and `<case_label>`/`<control_label>` with the two categories to compare:

```python
freq, stat = ir.tl.clonotype_imbalance(
    mdata,
    replicate_col="<sample_col>",
    groupby="<cluster_col>",
    case_label="<case_label>",
    control_label="<control_label>",
    inplace=False,
)
top_differential_clonotypes = stat["clone_id"].tolist()[:3]
```

Visualize the cluster assignment against the top differential clonotypes to confirm enrichment in one cluster over the other:

```python
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4), gridspec_kw={"wspace": 0.6})
mu.pl.embedding(mdata, basis="gex:umap", color="<cluster_col>", ax=ax1, show=False)
mu.pl.embedding(
    mdata,
    basis="gex:umap",
    color="airr:clone_id",
    groups=top_differential_clonotypes,
    ax=ax2,
    size=[80 if c in top_differential_clonotypes else 30 for c in mdata.obs["airr:clone_id"][mdata.mod["gex"].obs_names]],
    palette=cycler(color=mpl_cm.Dark2_r.colors),
)
```

> **No-plot alternative:** the enrichment answer already lives in `stat` from the `ir.tl.clonotype_imbalance` call above — no embedding needed to confirm it.
> ```python
> stat[["clone_id", "pval", "logFC"]].head()
> ```
> `freq` (the other return value) holds per-sample abundance if a numeric cross-check against a specific sample/cluster is needed.

---

## 3. Repertoire overlap of cell types

The same `ir.pl.repertoire_overlap` used for cross-sample comparison (see `pytcr-repertoire-comparison`) can compare cell types/clusters instead — pass the cell-type column as the grouping and the two labels of interest:

```python
_ = ir.pl.repertoire_overlap(mdata, "<cluster_col>", pair_to_plot=["<case_label>", "<control_label>"], fig_kws={"dpi": 120})
```

> **No-plot alternative:** the pairwise overlap value(s) directly, no scatterplot needed. `df` is a group × clonotype abundance matrix and `dst` a condensed (1-D) `pdist` array — pair `squareform(dst)` with `df.index` for a named lookup (see `pytcr-repertoire-comparison` for the same pattern in more detail):
> ```python
> from scipy.spatial.distance import squareform
>
> df, dst, lk = ir.tl.repertoire_overlap(mdata, "<cluster_col>", inplace=False)
> df.loc[["<case_label>", "<control_label>"], :].T          # per-clonotype abundance in both groups
> pd.DataFrame(squareform(dst), index=df.index, columns=df.index).loc["<case_label>", "<control_label>"]  # Jaccard distance
> ```

Useful for checking whether two functionally related cell states (e.g. effector vs. tissue-resident memory) draw from overlapping or distinct clonotype pools.

---

## 4. Marker genes in top clonotypes

Compare gene expression between two specific clonotypes directly, again via `ir.get.obs_context` to attach `clone_id` to the GEX `AnnData`. Replace `<clonotype_a>`/`<clonotype_b>` with clonotype IDs of interest (e.g. found via Section 2):

```python
with ir.get.obs_context(mdata["gex"], {"clone_id": mdata.obs["airr:clone_id"]}) as tmp_ad:
    sc.tl.rank_genes_groups(tmp_ad, "clone_id", groups=["<clonotype_a>"], reference="<clonotype_b>", method="wilcoxon")
    sc.pl.rank_genes_groups_violin(tmp_ad, groups="<clonotype_a>", n_genes=15)
```

> **No-plot alternative:** same as Step 1d — per-gene scores/fold-changes/adjusted p-values as a DataFrame.
> ```python
> sc.get.rank_genes_groups_df(tmp_ad, group="<clonotype_a>").head(15)
> ```

---

## Post-analysis

Natural next step: epitope-database query (`ir.pp.ir_dist` + `ir.tl.ir_query`/`ir.tl.ir_query_annotate`) to annotate clonotypes against known antigen-specificity databases.
