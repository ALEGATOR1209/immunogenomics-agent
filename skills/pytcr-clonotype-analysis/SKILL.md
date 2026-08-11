---
name: pytcr-clonotype-analysis
description: Analyze defined clonotypes in a scirpy MuData object — clonal expansion, clonotype abundance across categories, and convergent evolution. Use after pytcr-clonotype-clustering, once clonotype and/or clonotype cluster IDs exist in mdata.obs.
---

# Clonotype Analysis

Run this after `pytcr-clonotype-clustering`, once `mdata.obs["airr:clone_id"]` (and optionally `airr:cc_aa_tcrdist`) are defined. Every `.pl.*` call below has a no-plot, data-only alternative next to it — for agents that can't process images.

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

> **No-plot alternative:** the same expansion-category breakdown and clone-size distribution, straight from the two `obs` columns — no embedding needed.
> ```python
> mdata.obs["airr:clonal_expansion"].value_counts()
> mdata.obs["airr:clone_id_size"].describe()
> ```

### 1c. Stacked bar plot by category

Replace `<group_col>` with a categorical column such as `"gex:cluster"` (e.g. cell type):

```python
_ = ir.pl.clonal_expansion(mdata, target_col="clone_id", groupby="<group_col>", breakpoints=(1, 2, 5), normalize=False)
```

> **No-plot alternative:** the same per-group expansion-bucket breakdown as absolute cell counts, as a DataFrame.
> ```python
> ir.tl.summarize_clonal_expansion(mdata, groupby="<group_col>", target_col="clone_id", summarize_by="cell", normalize=False)
> ```

`breakpoints` defines the size bins for the expansion categories (here: 1, 2, up to 5, and above). `normalize=False` shows absolute cell counts.

Omit `normalize` (or set it `True`, the default) to normalize to group size instead, making the fraction of expanded clones comparable across groups of different sizes:

```python
ir.pl.clonal_expansion(mdata, target_col="clone_id", groupby="<group_col>")
```

> **No-plot alternative:** same breakdown, normalized to fractions of each group.
> ```python
> ir.tl.summarize_clonal_expansion(mdata, groupby="<group_col>", target_col="clone_id", summarize_by="cell", normalize=True)
> ```

A cell type with a high fraction of expanded clonotypes (e.g. CD8+ effector T cells) is consistent with antigen-driven proliferation.

### 1d. Cross-check with diversity

Groups with more clonal expansion should show lower repertoire diversity:

```python
_ = ir.pl.alpha_diversity(mdata, metric="normalized_shannon_entropy", groupby="<group_col>")
```

> **No-plot alternative:** the per-group diversity value directly, as a DataFrame.
> ```python
> diversity = ir.tl.alpha_diversity(mdata, groupby="<group_col>", metric="normalized_shannon_entropy", inplace=False)
> diversity.loc["<group>"].item()  # one group's value
> ```

---

## 2. Clonotype abundance

`ir.pl.group_abundance` produces bar charts of any categorical `obs` column, split by a second grouping column. Use it to see how the largest clonotypes distribute across cell types or samples.

### 2a. Abundance across cell-type clusters

```python
_ = ir.pl.group_abundance(mdata, groupby="airr:clone_id", target_col="<group_col>", max_cols=10)
```

> **No-plot alternative:** the same counts as a DataFrame (rows = clonotype, columns = `<group_col>` category), read off the top rows instead of eyeballing bar heights.
> ```python
> abundance = ir.tl.group_abundance(mdata, groupby="airr:clone_id", target_col="<group_col>")
> abundance.sum(axis=1).sort_values(ascending=False).head(10)  # 10 largest clonotypes by cell count
> ```

`max_cols` limits the plot to the N largest clonotypes (by cell count).

### 2b. Normalize by sample size

Raw counts can be biased by differing sample sizes — normalize against the sample-identifying column (e.g. `"gex:sample"`):

```python
_ = ir.pl.group_abundance(
    mdata,
    groupby="airr:clone_id",
    target_col="<group_col>",
    max_cols=10,
    normalize="<sample_col>",
)
```

> **No-plot alternative:** `pl.group_abundance`'s `normalize` is `tl.group_abundance`'s `fraction` — same DataFrame, values normalized within each `<sample_col>` category.
> ```python
> ir.tl.group_abundance(mdata, groupby="airr:clone_id", target_col="<group_col>", fraction="<sample_col>")
> ```

### 2c. Public vs. private clonotypes

Coloring/grouping by tissue or patient reveals whether a clonotype is **private** (specific to one tissue/patient) or **public** (shared across several):

```python
_ = ir.pl.group_abundance(mdata, groupby="airr:clone_id", target_col="<tissue_col>", max_cols=15, figsize=(5, 3))
```

> **No-plot alternative:** count how many distinct tissues each clonotype appears in — >1 means public across tissues.
> ```python
> abundance_tissue = ir.tl.group_abundance(mdata, groupby="airr:clone_id", target_col="<tissue_col>")
> (abundance_tissue > 0).sum(axis=1).sort_values(ascending=False)  # tissues per clonotype
> ```

Cross-*patient* sharing is typically much rarer than cross-tissue sharing — worth checking separately:

```python
_ = ir.pl.group_abundance(mdata, groupby="airr:clone_id", target_col="<patient_col>", max_cols=15, figsize=(5, 3))
```

> **No-plot alternative:** same idea at the patient level — clonotypes with a count >1 here are public across patients.
> ```python
> abundance_patient = ir.tl.group_abundance(mdata, groupby="airr:clone_id", target_col="<patient_col>")
> (abundance_patient > 0).sum(axis=1).sort_values(ascending=False)  # patients per clonotype
> ```

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

> **No-plot alternative:** count convergent vs. non-convergent cells directly — no embedding needed.
> ```python
> mdata.obs["airr:is_convergent"].value_counts()
> ```

---

## Post-analysis

Natural next steps: motif analysis (CDR3 logo plots), gene usage (`ir.tl.group_abundance`/`ir.pl.spectratype`), repertoire comparison (`ir.tl.repertoire_overlap`/`ir.pl.repertoire_overlap`), GEX integration (modularity, cluster imbalance, marker genes), and epitope-database query (`ir.pp.ir_dist` + `ir.tl.ir_query`/`ir.tl.ir_query_annotate`).
