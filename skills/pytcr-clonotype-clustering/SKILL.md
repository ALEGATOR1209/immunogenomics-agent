---
name: pytcr-clonotype-clustering
description: Define clonotypes and clonotype clusters from AIRR data using scirpy. Use after pytcr-preprocess. Covers nucleotide-identity clonotype definition, amino-acid similarity clonotype clustering (tcrdist), network layout/visualization, and optional V-gene-constrained clustering.
---

# Clonotype Definition and Clustering

Run this after `pytcr-preprocess`. This skill defines clonotypes (exact nucleotide identity) and clonotype clusters (amino-acid sequence similarity).

## Setup

```python
import scirpy as ir
```

---

## Step 1 — Ask the user about `receptor_arms`

Before generating any code, ask the user which receptor arms must match for two cells to be considered the same clonotype or cluster. Present the options:

**`receptor_arms="all"` (most stringent)**
Both the VJ chain (e.g. TRA/IGK/IGL) and the VDJ chain (e.g. TRB/IGH) must match.
- **Use when:** Standard TCR/BCR paired-chain analysis. Ensures clonotypes represent cells that share the same complete receptor.
- **Pro:** Biologically precise; fewer false-positive clonotype groupings.
- **Con:** Cells with a missing chain (orphan) are effectively excluded.

**`receptor_arms="any"` (permissive)**
A match on either the VJ or the VDJ arm is sufficient.
- **Use when:** Datasets with frequent chain dropout; querying epitope databases; exploratory analysis.
- **Pro:** Higher sensitivity; captures partial matches.
- **Con:** May group biologically distinct clonotypes that share only one chain.

---

## Step 2 — Ask the user about `dual_ir`

Ask the user how to handle cells with two receptor pairs (dual IR cells). Present the options:

**`dual_ir="primary_only"` (recommended for clonotype definition)**
Only the primary (highest-UMI) chain pair is considered for matching.
- **Use when:** Strict clonotype identity. ~30% of T cells can carry dual TCRs — this setting ignores the secondary pair and treats these cells like single-receptor cells.
- **Pro:** Consistent with traditional clonotype definitions; simpler interpretation.
- **Con:** Ignores secondary receptor information.

**`dual_ir="any"` (recommended for clonotype clusters)**
A match on either the primary or the secondary chain pair counts.
- **Use when:** Clonotype cluster / similarity analysis where you want to capture cells that share any receptor configuration.
- **Pro:** More inclusive; captures biologically related cells with dual receptors.
- **Con:** Can merge clonotypes that share only a secondary chain.

Once the user has decided on both parameters, proceed with the steps below using their chosen values.

---

## Step 3 — Define clonotypes (nucleotide-sequence identity)

Clonotypes are groups of cells with identical CDR3 nucleotide sequences. This is the most stringent level of clonal grouping.

### 3a. Compute nucleotide distance matrices

```python
ir.pp.ir_dist(mdata)
```

Default: nucleotide sequences, identity metric. Stores two sparse distance matrices in `mdata["airr"].uns` — one for VJ sequences, one for VDJ sequences.

### 3b. Define clonotypes

Use the `receptor_arms` and `dual_ir` values chosen above:

```python
ir.tl.define_clonotypes(mdata, receptor_arms="<receptor_arms>", dual_ir="<dual_ir>")
```

Adds to `mdata.obs`:
- `airr:clone_id` — clonotype label
- `airr:clone_id_size` — number of cells in the clonotype

### 3c. Compute network layout

```python
ir.tl.clonotype_network(mdata, min_cells=2)
```

`min_cells` controls the minimum clonotype size shown. Increase it to reduce noise in large datasets.

### 3d. Visualize

Replace `<color_col>` with a column from `mdata.obs` (e.g. `"gex:sample"`, `"gex:cluster"`, `"gex:patient"`):

```python
_ = ir.pl.clonotype_network(mdata, color="<color_col>", base_size=20, label_fontsize=9, panel_size=(7, 7))
```

Each node represents a unique receptor configuration. Node size = number of cells. Categorical variables can be rendered as pie charts.

---

## Step 4 — Define clonotype clusters (amino-acid sequence similarity)

Clonotype clusters group cells by CDR3 amino-acid similarity rather than exact identity. This reveals convergent evolution — different clones that likely recognize the same antigen.

### 4a. Compute amino-acid distance matrices

```python
ir.pp.ir_dist(
    mdata,
    metric="tcrdist",
    sequence="aa",
    cutoff=15,
)
```

`metric="tcrdist"` uses the BLOSUM62 substitution matrix (Dash et al.). `cutoff=15` means cells with CDR3 distance ≤ 15 are considered similar — roughly equivalent to ~1–2 conservative amino-acid substitutions. Adjust `cutoff` based on how strictly you want to define similarity; lower values = tighter clusters.

Alternatively, use `base_matrix="tcrblosum"` for TCRBLOSUM alpha/beta-specific substitution matrices.

### 4b. Define clonotype clusters

Use the `receptor_arms` and `dual_ir` values chosen above:

```python
ir.tl.define_clonotype_clusters(
    mdata,
    sequence="aa",
    metric="tcrdist",
    receptor_arms="<receptor_arms>",
    dual_ir="<dual_ir>",
)
```

Adds to `mdata.obs`:
- `airr:cc_aa_tcrdist` — cluster label
- `airr:cc_aa_tcrdist_size` — number of cells in the cluster

### 4c. Compute network layout

```python
ir.tl.clonotype_network(mdata, min_cells=3, sequence="aa", metric="tcrdist")
```

### 4d. Visualize

```python
_ = ir.pl.clonotype_network(mdata, color="<color_col>", base_size=20, label_fontsize=9, panel_size=(7, 7))
```

Nodes now represent unique receptor configurations; connected subgraphs are clonotype clusters. Nodes within the same subgraph have CDR3 distances ≤ `cutoff`.

---

## Step 5 (Optional) — Constrain clusters by V-gene

By default, cells can be grouped into the same clonotype cluster even if they use different V genes (different CDR1/CDR2 regions). Setting `same_v_gene=True` adds the constraint that both VJ and VDJ V genes must also match.

**When to use:** When you care about shared CDR1/CDR2 in addition to CDR3 similarity, or when you want stricter evidence that cells recognize the same antigen via the same binding interface.

```python
ir.tl.define_clonotype_clusters(
    mdata,
    sequence="aa",
    metric="tcrdist",
    receptor_arms="<receptor_arms>",
    dual_ir="<dual_ir>",
    same_v_gene=True,
    key_added="cc_aa_tcrdist_same_v",
)
```

Result stored in `mdata.obs["airr:cc_aa_tcrdist_same_v"]`. You can compare it against the unconstrained clustering to find clusters that split when V-gene identity is enforced:

```python
ct_different_v = (
    mdata.obs
    .groupby("airr:cc_aa_tcrdist")
    .apply(lambda x: x["airr:cc_aa_tcrdist_same_v"].nunique() > 1)
)
ct_different_v[ct_different_v].index.tolist()
```

---

## Post-clustering

With clonotype IDs defined, the natural next steps are:

- **Clonal expansion**: `ir.tl.clonal_expansion` → `ir.pl.clonal_expansion`
- **Diversity**: `ir.pl.alpha_diversity`
- **Repertoire overlap across samples**: `ir.tl.repertoire_overlap` → `ir.pl.repertoire_overlap`
- **Convergent evolution**: `ir.tl.clonotype_convergence`
- **Epitope database query**: `ir.pp.ir_dist` + `ir.tl.ir_query` + `ir.tl.ir_query_annotate`
