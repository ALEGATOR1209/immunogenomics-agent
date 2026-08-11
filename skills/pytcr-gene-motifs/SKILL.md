---
name: pytcr-gene-motifs
description: Analyze CDR3 amino-acid motifs and V(D)J gene usage in a scirpy MuData object — logoplots, V-gene abundance bar charts, VDJ usage Sankey diagrams, and CDR3-length spectratype plots. Use after pytcr-clonotype-clustering, once clonotype/cluster IDs and cell-type annotations exist in mdata.obs.
---

# Motif and Gene Usage Analysis

Run this after `pytcr-clonotype-clustering` (and typically `pytcr-clonotype-analysis`), once cell-type clusters (e.g. `gex:cluster`) are available alongside clonotype IDs. Every `.pl.*` call below has a no-plot, data-only alternative next to it — for agents that can't process images.

## Setup

```python
import pandas as pd
import scirpy as ir
from matplotlib import pyplot as plt
```

---

## 1. Motif analysis (logoplots)

`ir.pl.logoplot_cdr3_motif` generates a sequence logo of CDR3 amino-acid sequences. **Sequences must all be the same length** — subset `mdata` to a single length before plotting (inspect multiple lengths by repeating with a different filter).

Use `ir.get.airr` to pull `junction_aa` for length filtering, and subset by a cell-type column (e.g. `"gex:cluster"`) to focus on a population of interest:

```python
fig, axs = plt.subplots(1, 2, figsize=(12, 2))
for chain, ax in zip(["VJ_1", "VDJ_1"], axs, strict=False):
    ir.pl.logoplot_cdr3_motif(
        mdata[
            (mdata.obs["<cluster_col>"] == "<cell_type>")
            & (ir.get.airr(mdata, "junction_aa", "VDJ_1").str.len() == 14)
            & (ir.get.airr(mdata, "junction_aa", "VJ_1").str.len() == 14)
        ],
        chains=chain,
        to_type="information",
        ax=ax,
    )
```

Replace `14` with the CDR3 length you want to inspect, and `<cluster_col>`/`<cell_type>` with the relevant grouping (e.g. `"gex:cluster"` / `"CD8_Teff"`). `to_type="information"` scales letter height by information content (bits).

> **No-plot alternative:** per-position amino-acid frequency table and consensus sequence for the same length-filtered subset.
> ```python
> subset = mdata[
>     (mdata.obs["<cluster_col>"] == "<cell_type>")
>     & (ir.get.airr(mdata, "junction_aa", "VDJ_1").str.len() == 14)
>     & (ir.get.airr(mdata, "junction_aa", "VJ_1").str.len() == 14)
> ]
> seqs = ir.get.airr(subset, "junction_aa", "VDJ_1")  # or "VJ_1" for the other chain
> position_freq = pd.DataFrame([list(s) for s in seqs]).apply(lambda col: col.value_counts(normalize=True))
> consensus = position_freq.idxmax()  # most frequent amino acid per position
> ```

---

## 2. Gene usage

### 2a. V-gene abundance by cell type

`ir.tl.group_abundance` (via `ir.pl.group_abundance`) works on any `obs` column, so it can also summarize VDJ gene usage. Bring `v_call` into `obs` with `ir.get.airr_context`, then plot by `<chain>_v_call` (e.g. `VJ_1_v_call`, `VDJ_1_v_call`). `max_cols` limits the plot to the N most abundant V genes:

```python
with ir.get.airr_context(mdata, "v_call"):
    ir.pl.group_abundance(
        mdata,
        groupby="VJ_1_v_call",
        target_col="<cluster_col>",
        normalize=True,
        max_cols=10,
    )
```

> **No-plot alternative:** the same counts/fractions as a DataFrame — `pl.group_abundance`'s `normalize` is `tl.group_abundance`'s `fraction`.
> ```python
> with ir.get.airr_context(mdata, "v_call"):
>     abundance = ir.tl.group_abundance(
>         mdata,
>         groupby="VJ_1_v_call",
>         target_col="<cluster_col>",
>         fraction=True,
>     )
> abundance.sum(axis=1).sort_values(ascending=False).head(10)  # most abundant V genes overall
> ```

### 2b. Pre-select specific V genes

Filter `mdata` to specific V genes before plotting to zoom in on genes of interest — here flipping `groupby`/`target_col` to show cell-type composition per gene:

```python
with ir.get.airr_context(mdata, "v_call"):
    ir.pl.group_abundance(
        mdata[mdata.obs["VDJ_1_v_call"].isin(["<gene1>", "<gene2>", "..."]), :],
        groupby="<cluster_col>",
        target_col="VDJ_1_v_call",
        normalize=True,
    )
```

> **No-plot alternative:** same cell-type-composition-per-gene table, pre-filtered to the genes of interest — also answers "which sample has the highest usage of V gene X".
> ```python
> with ir.get.airr_context(mdata, "v_call"):
>     usage = ir.tl.group_abundance(
>         mdata[mdata.obs["VDJ_1_v_call"].isin(["<gene1>", "<gene2>", "..."]), :],
>         groupby="<cluster_col>",
>         target_col="VDJ_1_v_call",
>         fraction=True,
>     )
>     usage_by_sample = ir.tl.group_abundance(mdata, groupby="<sample_col>", target_col="VJ_1_v_call")
> usage  # cell-type composition per gene
> usage_by_sample["<gene>"].idxmax()  # sample with the highest usage of one gene
> ```

### 2c. VDJ usage Sankey plot

`ir.pl.vdj_usage` visualizes exact V(D)J gene combinations as a Sankey diagram:

```python
_ = ir.pl.vdj_usage(
    mdata,
    full_combination=False,
    max_segments=None,
    max_ribbons=30,
    fig_kws={"figsize": (8, 5)},
)
```

`max_ribbons` limits the number of flows shown (busiest combinations first); `max_segments` limits the number of gene segments per chain category.

> **No-plot alternative:** `ir.pl.vdj_usage` has no `.tl.` counterpart — build the same V-D-J combination frequencies by hand, plus any single-gene aggregate (e.g. the most abundant D gene overall).
> ```python
> with ir.get.airr_context(mdata, ["v_call", "d_call", "j_call"], ["VJ_1", "VDJ_1"]):
>     combo_counts = (
>         mdata.obs.groupby(["VDJ_1_v_call", "VDJ_1_d_call", "VDJ_1_j_call"])
>         .size()
>         .sort_values(ascending=False)
>     )
>     most_abundant_d_gene = mdata.obs["VDJ_1_d_call"].value_counts().idxmax()
> combo_counts.head(10)  # busiest V-D-J combinations, same as the Sankey's widest ribbons
> ```

### 2d. VDJ composition of specific clonotypes

Subset by `airr:clone_id` to inspect the exact gene composition of one or more clonotypes:

```python
ir.pl.vdj_usage(
    mdata[mdata.obs["airr:clone_id"].isin(["<id1>", "<id2>", "..."]), :],
    max_ribbons=None,
    max_segments=100,
)
```

> **No-plot alternative:** exact gene composition per clonotype as a table, instead of tracing ribbons for one clonotype's subset.
> ```python
> with ir.get.airr_context(mdata, ["v_call", "d_call", "j_call"], ["VJ_1", "VDJ_1"]):
>     clonotype_genes = (
>         mdata.obs[mdata.obs["airr:clone_id"].isin(["<id1>", "<id2>", "..."])]
>         .groupby(["airr:clone_id", "VDJ_1_v_call", "VDJ_1_d_call", "VDJ_1_j_call", "VJ_1_v_call", "VJ_1_j_call"])
>         .size()
>     )
> clonotype_genes
> ```

---

## 3. Spectratype plots

`ir.pl.spectratype` shows the length distribution of CDR3 regions, optionally split/colored by a category.

### 3a. Bar chart

```python
ir.pl.spectratype(mdata, color="<cluster_col>", viztype="bar", fig_kws={"dpi": 120})
```

> **No-plot alternative:** the CDR3-length distribution table directly — `pl.spectratype`'s `color` is `tl.spectratype`'s `target_col`.
> ```python
> spectra = ir.tl.spectratype(mdata, target_col="<cluster_col>")
> spectra.idxmax()  # length with the highest count, per group
> ```

### 3b. Ridge / curve plot

`curve_layout="shifted"` staggers the curves vertically for readability; `kde_kws={"kde_norm": False}` keeps curve heights proportional to group size instead of normalizing each to a unit area:

```python
ir.pl.spectratype(
    mdata,
    color="<cluster_col>",
    viztype="curve",
    curve_layout="shifted",
    fig_kws={"dpi": 120},
    kde_kws={"kde_norm": False},
)
```

> **No-plot alternative:** same underlying table as 3a — the curve is purely a smoothed rendering of it, so reuse `spectra`.
> ```python
> spectra.idxmax()  # same lookup as 3a, no shape-reading needed
> ```

### 3c. Spectratype by gene usage

Combine with V-gene pre-selection (as in 2b) to compare CDR3-length distributions across specific V genes. `chain` selects which chain slot to read the length from; `normalize` accounts for uneven sample sizes:

```python
with ir.get.airr_context(mdata, "v_call"):
    ir.pl.spectratype(
        mdata[mdata.obs["VDJ_1_v_call"].isin(["<gene1>", "<gene2>", "..."]), :],
        chain="VDJ_1",
        color="VDJ_1_v_call",
        normalize="<sample_col>",
        fig_kws={"dpi": 120},
    )
```

> **No-plot alternative:** same length-by-gene table — `pl.spectratype`'s `normalize` is `tl.spectratype`'s `fraction`, `color` is `target_col`.
> ```python
> with ir.get.airr_context(mdata, "v_call"):
>     spectra_by_gene = ir.tl.spectratype(
>         mdata[mdata.obs["VDJ_1_v_call"].isin(["<gene1>", "<gene2>", "..."]), :],
>         chain="VDJ_1",
>         target_col="VDJ_1_v_call",
>         fraction="<sample_col>",
>     )
> spectra_by_gene.idxmax()  # most common CDR3 length per V gene
> ```

---

## Post-analysis

Natural next steps: repertoire comparison (`ir.tl.repertoire_overlap` → `ir.pl.repertoire_overlap` across samples), GEX integration (clonotype modularity/imbalance across clusters, marker genes in top clonotypes), or epitope database query (`ir.pp.ir_dist` + `ir.tl.ir_query` + `ir.tl.ir_query_annotate`).
