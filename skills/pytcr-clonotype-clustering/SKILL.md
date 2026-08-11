---
name: pytcr-clonotype-clustering
description: Define clonotypes and clonotype clusters from AIRR data using scirpy. Use after pytcr-preprocess. Covers nucleotide-identity clonotype definition, amino-acid similarity clonotype clustering (tcrdist), network layout/visualization, and optional V-gene-constrained clustering.
---

# Clonotype Definition and Clustering

Run this after `pytcr-preprocess`. Defines clonotypes (exact CDR3 nucleotide identity) and clonotype clusters (CDR3 amino-acid similarity).

## Setup

```python
import scirpy as ir
```

---

## Step 1 — Ask the user for two parameters

**`receptor_arms`** — which chains must match for two cells to be grouped:
- `"all"` (default if no answer given) — both VJ (e.g. TRA/IGK/IGL) and VDJ (e.g. TRB/IGH) chains must match. Standard paired-chain analysis; precise, but excludes cells with a missing/orphan chain.
- `"any"` — a match on either arm is enough. Use for frequent chain dropout, epitope-DB queries, or exploratory analysis; more sensitive, but can merge biologically distinct clonotypes.

**`dual_ir`** — how to treat cells with two receptor pairs (~30% of T cells):
- `"primary_only"` (recommended for clonotype definition) — only the primary (highest-UMI) pair is used.
- `"any"` (recommended for clonotype clusters) — a match on either the primary or secondary pair counts; more inclusive, can merge clonotypes sharing only a secondary chain.

Use the chosen `<receptor_arms>`/`<dual_ir>` values in every step below.

---

## Step 2 — Define clonotypes (nucleotide identity)

```python
ir.pp.ir_dist(mdata)  # default: nucleotide sequences, identity metric
ir.tl.define_clonotypes(mdata, receptor_arms="<receptor_arms>", dual_ir="<dual_ir>")
```

Adds `mdata.obs["airr:clone_id"]` (label) and `["airr:clone_id_size"]` (cell count).

```python
ir.tl.clonotype_network(mdata, min_cells=2)  # raise min_cells to reduce noise in large datasets
_ = ir.pl.clonotype_network(mdata, color="<color_col>", base_size=20, label_fontsize=9, panel_size=(7, 7))
```

`<color_col>` is any `mdata.obs` column (e.g. `"gex:sample"`, `"gex:patient"`). Node = unique receptor configuration, node size = cell count; categorical colors render as pie charts.

---

## Step 3 — Define clonotype clusters (amino-acid similarity)

Reveals convergent recognition: different clones with similar CDR3s that likely target the same antigen.

```python
ir.pp.ir_dist(mdata, metric="tcrdist", sequence="aa", cutoff=15)
```

`cutoff` is the max CDR3 distance (BLOSUM62-based) to count as similar — lower = tighter clusters. (`base_matrix="tcrblosum"` is an alternative alpha/beta-specific substitution matrix.)

```python
ir.tl.define_clonotype_clusters(
    mdata, sequence="aa", metric="tcrdist",
    receptor_arms="<receptor_arms>", dual_ir="<dual_ir>",
)
```

Adds `mdata.obs["airr:cc_aa_tcrdist"]` (label) and `["airr:cc_aa_tcrdist_size"]` (cell count).

```python
ir.tl.clonotype_network(mdata, min_cells=3, sequence="aa", metric="tcrdist")
_ = ir.pl.clonotype_network(mdata, color="<color_col>", base_size=20, label_fontsize=9, panel_size=(7, 7))
```

Now each connected subgraph (not each dot) is a clonotype cluster. Color by patient/sample to spot **public** clusters (shared across patients — interesting, suggests convergent recognition) vs. **private** ones (single patient).

> **Getting cluster/network sizes:** `ir.tl.clonotype_network` only computes plot layout — it has no queryable size/membership output. Use the `_size` columns instead:
> ```python
> mdata.obs["airr:cc_aa_tcrdist_size"].max()   # size of largest cluster, in cells
> ```
> Same applies to Step 2's network via `airr:clone_id_size`.

### Inspect the cells in one cluster

Since scirpy v0.13, AIRR columns aren't in `mdata.obs` by default — use `ir.get.airr_context` to attach them temporarily. Replace `"159"` with the cluster label:

```python
with ir.get.airr_context(mdata, "junction_aa", ["VJ_1", "VDJ_1", "VJ_2", "VDJ_2"]):
    cdr3_ct = (
        mdata.obs.loc[lambda x: x["airr:cc_aa_tcrdist"] == "159"]
        .astype(str)  # works around a pandas dropna=False bug on some versions
        .groupby(
            ["VJ_1_junction_aa", "VDJ_1_junction_aa", "VJ_2_junction_aa", "VDJ_2_junction_aa", "airr:receptor_subtype"],
            observed=True, dropna=False,
        )
        .size()
        .reset_index(name="n_cells")
    )
cdr3_ct
```

Each row = one distinct receptor configuration in the cluster (one dot in the network), with its cell count.

---

## Step 4 (Optional) — Constrain clusters by V-gene

By default, clusters can mix V genes (different CDR1/CDR2). Set `same_v_gene=True` to also require matching VJ and VDJ V genes — use when shared CDR1/CDR2 matters, or you want stronger evidence of a shared binding interface.

```python
ir.tl.define_clonotype_clusters(
    mdata, sequence="aa", metric="tcrdist",
    receptor_arms="<receptor_arms>", dual_ir="<dual_ir>",
    same_v_gene=True, key_added="cc_aa_tcrdist_same_v",
)
```

Result: `mdata.obs["airr:cc_aa_tcrdist_same_v"]`. Find clusters that split when V-gene identity is enforced (e.g. `280` → `280`, `788`):

```python
ct_different_v = mdata.obs.groupby("airr:cc_aa_tcrdist").apply(
    lambda x: x["airr:cc_aa_tcrdist_same_v"].nunique() > 1
)
ct_different_v[ct_different_v].index.tolist()
```

---

## Post-clustering

- **Clonal expansion**: `ir.tl.clonal_expansion` → `ir.pl.clonal_expansion`
- **Diversity**: `ir.pl.alpha_diversity`
- **Repertoire overlap across samples**: `ir.tl.repertoire_overlap` → `ir.pl.repertoire_overlap`
- **Convergent evolution**: `ir.tl.clonotype_convergence`
- **Epitope database query**: `ir.pp.ir_dist` + `ir.tl.ir_query` + `ir.tl.ir_query_annotate`
