---
name: pytcr-clonotype-analysis
description: Analyze defined clonotypes in a scirpy MuData object — clonal expansion, clonotype abundance across categories, and convergent evolution. Use after pytcr-clonotype-clustering, once clonotype and/or clonotype cluster IDs exist in mdata.obs.
---

# Clonotype Analysis

Run this after `pytcr-clonotype-clustering`, once `mdata.obs["airr:clone_id"]` (and optionally `airr:cc_aa_tcrdist`) are defined. This skill covers clonal expansion, clonotype abundance across categories, and convergent evolution.

## Setup

```python
import muon as mu
import scirpy as ir
```

---

## 1. Clonal expansion

Clonal expansion identifies clonotypes consisting of more than one cell — a signature of positive selection for a reactive clone.

### 1a. Compute

```python
ir.tl.clonal_expansion(mdata)
```

Adds `mdata.obs["airr:clonal_expansion"]` — an expansion *category* (e.g. singleton, 2 cells, >2 cells), distinct from `airr:clone_id_size`, which is the absolute cell count of a clonotype.

### 1b. Visualize on the embedding

Overlay expansion category and clonotype size directly on a GEX embedding (e.g. UMAP):

```python
mu.pl.embedding(mdata, basis="gex:umap", color=["airr:clonal_expansion", "airr:clone_id_size"])
```

### 1c. Stacked bar plot by category

Replace `<group_col>` with a categorical column such as `"gex:cluster"` (e.g. cell type):

```python
_ = ir.pl.clonal_expansion(mdata, target_col="clone_id", groupby="<group_col>", breakpoints=(1, 2, 5), normalize=False)
```

`breakpoints` defines the size bins for the expansion categories (here: 1, 2, up to 5, and above). `normalize=False` shows absolute cell counts.

Set `normalize=True` (or omit it — it defaults to `True`) to normalize to group size instead, which makes the fraction of expanded clones comparable across groups of different sizes:

```python
ir.pl.clonal_expansion(mdata, target_col="clone_id", groupby="<group_col>")
```

A cell type with a high fraction of expanded clonotypes (e.g. CD8+ effector T cells) is consistent with antigen-driven proliferation.

### 1d. Cross-check with diversity

Groups with more clonal expansion should show lower repertoire diversity:

```python
_ = ir.pl.alpha_diversity(mdata, metric="normalized_shannon_entropy", groupby="<group_col>")
```

---

## 2. Clonotype abundance

`ir.pl.group_abundance` produces bar charts of any categorical `obs` column, split by a second grouping column. Use it to see how the largest clonotypes distribute across cell types or samples.

### 2a. Abundance across cell-type clusters

```python
_ = ir.pl.group_abundance(mdata, groupby="airr:clone_id", target_col="<group_col>", max_cols=10)
```

`max_cols` limits the plot to the N largest clonotypes (by cell count).

### 2b. Normalize by sample size

Raw counts can be biased by differing sample sizes. Normalize to mitigate this:

```python
_ = ir.pl.group_abundance(
    mdata,
    groupby="airr:clone_id",
    target_col="<group_col>",
    max_cols=10,
    normalize="<sample_col>",
)
```

`normalize` should reference the column identifying samples (e.g. `"gex:sample"`).

### 2c. Public vs. private clonotypes

Coloring/grouping by tissue or patient reveals whether a clonotype is **private** (specific to one tissue/patient) or **public** (shared across several):

```python
_ = ir.pl.group_abundance(mdata, groupby="airr:clone_id", target_col="<tissue_col>", max_cols=15, figsize=(5, 3))
```

Clonotypes shared across *patients* (as opposed to just across tissues within one patient) are typically much rarer — worth checking explicitly:

```python
_ = ir.pl.group_abundance(mdata, groupby="airr:clone_id", target_col="<patient_col>", max_cols=15, figsize=(5, 3))
```

---

## 3. Convergent evolution

Convergent evolution identifies receptors that likely recognize the same antigen but arose from genetically distinct clones — detected by comparing a coarse clonotype definition (amino-acid similarity, e.g. `cc_aa_tcrdist`) against a fine one (exact nucleotide identity, e.g. `clone_id`). A clonotype cluster containing more than one distinct `clone_id` is evidence of convergence.

Requires clonotype clusters from `pytcr-clonotype-clustering` (Step 4) in addition to clonotypes (Step 3).

### 3a. Compute

```python
ir.tl.clonotype_convergence(mdata, key_coarse="cc_aa_tcrdist", key_fine="clone_id")
```

Adds `mdata.obs["airr:is_convergent"]`.

### 3b. Visualize

```python
mu.pl.embedding(mdata, "gex:umap", color="airr:is_convergent")
```

---

## Post-analysis

With clonal expansion, abundance, and convergence characterized, natural next steps are:

- **Motif analysis**: logo plots of CDR3 motifs within a clonotype cluster
- **Gene usage**: `ir.tl.group_abundance` / spectratype plots (`ir.pl.spectratype`) for V/J gene usage patterns
- **Repertoire comparison**: `ir.tl.repertoire_overlap` → `ir.pl.repertoire_overlap` across samples
- **Integrating gene expression**: clonotype modularity, clonotype imbalance among cell clusters, marker genes in top clonotypes
- **Epitope database query**: `ir.pp.ir_dist` + `ir.tl.ir_query` + `ir.tl.ir_query_annotate`
