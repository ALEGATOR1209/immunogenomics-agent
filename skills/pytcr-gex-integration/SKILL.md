---
name: pytcr-gex-integration
description: Integrate gene expression (GEX) data with immune-receptor clonotypes in a scirpy MuData object — clonotype modularity, clonotype imbalance between cell clusters, repertoire overlap between cell types, and marker-gene / differential-expression analysis of top clonotypes. Use after pytcr-clonotype-clustering and pytcr-clonotype-analysis, once clonotype IDs, a GEX embedding, and cell-type cluster annotations exist in mdata.
---

# Integrating Gene Expression Data

Run this after `pytcr-clonotype-clustering` and `pytcr-clonotype-analysis`, once `mdata["gex"]` has a computed embedding/clustering (e.g. `gex:umap`, `gex:cluster`) and `mdata.obs` has clonotype IDs. This skill covers cross-modality analyses that combine transcriptomics with receptor identity: clonotype modularity, clonotype imbalance across cell clusters, repertoire overlap between cell types, and marker-gene analysis of specific clonotypes.

## Setup

```python
import muon as mu
import scanpy as sc
import scirpy as ir
from cycler import cycler
from matplotlib import cm as mpl_cm
from matplotlib import pyplot as plt
```

---

## 1. Clonotype modularity

Clonotype modularity identifies clonotypes (or clonotype clusters) whose cells are transcriptionally *more similar to each other than expected by chance*. The score is the log2 fold change of edges in the cell-cell neighborhood graph within the clonotype, versus a random background model. A high score means the clonotype has a consistent molecular phenotype.

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

### 1d. Differential expression of top clonotypes vs. the rest

`sc.tl.rank_genes_groups` doesn't understand `MuData`, so temporarily attach the clonotype column to the GEX `AnnData` with `ir.get.obs_context`:

```python
with ir.get.obs_context(mdata["gex"], {"cc_aa_tcrdist": mdata.obs["<cc_col>"]}) as tmp_ad:
    sc.tl.rank_genes_groups(tmp_ad, "cc_aa_tcrdist", groups=clonotypes_top_modularity, reference="rest", method="wilcoxon")
    fig, axs = plt.subplots(1, 2, figsize=(8, 4))
    for ct, ax in zip(clonotypes_top_modularity, axs, strict=False):
        sc.pl.rank_genes_groups_violin(tmp_ad, groups=[ct], n_genes=15, ax=ax, show=False, strip=False)
```

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

Visualize the cluster assignment alongside the top differential clonotypes to confirm they are enriched in one cluster over the other:

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

---

## 3. Repertoire overlap of cell types

The same `ir.pl.repertoire_overlap` used for cross-sample comparison (see `pytcr-repertoire-comparison`) can compare cell types/clusters instead — pass the cell-type column as the grouping and the two labels of interest:

```python
_ = ir.pl.repertoire_overlap(mdata, "<cluster_col>", pair_to_plot=["<case_label>", "<control_label>"], fig_kws={"dpi": 120})
```

Useful for checking whether two functionally related cell states (e.g. effector vs. tissue-resident memory) draw from overlapping or distinct clonotype pools.

---

## 4. Marker genes in top clonotypes

Compare gene expression between two specific clonotypes directly, again via `ir.get.obs_context` to attach `clone_id` to the GEX `AnnData`. Replace `<clonotype_a>`/`<clonotype_b>` with clonotype IDs of interest (e.g. found via Section 2):

```python
with ir.get.obs_context(mdata["gex"], {"clone_id": mdata.obs["airr:clone_id"]}) as tmp_ad:
    sc.tl.rank_genes_groups(tmp_ad, "clone_id", groups=["<clonotype_a>"], reference="<clonotype_b>", method="wilcoxon")
    sc.pl.rank_genes_groups_violin(tmp_ad, groups="<clonotype_a>", n_genes=15)
```

---

## Post-analysis

The remaining natural next step is:

- **Epitope database query**: `ir.pp.ir_dist` + `ir.tl.ir_query` + `ir.tl.ir_query_annotate`, to annotate clonotypes against known antigen-specificity databases.
