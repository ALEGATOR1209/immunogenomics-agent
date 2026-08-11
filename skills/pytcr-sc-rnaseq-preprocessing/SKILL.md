---
name: pytcr-sc-rnaseq-preprocessing
description: Quality-control, normalize, and select features for the gene expression data (scRNA-seq). Mito/ribo/hemoglobin QC metrics, cell/gene filtering, doublet detection, count normalization (median + log1p), and highly-variable-gene selection. Use after pytcr-data-loading whenever mdata has a gex modality, independently of (and typically before or alongside) pytcr-preprocess. Should be run before pytcr-gex-integration.
---

# scRNA-seq (GEX) Quality Control and Preprocessing

Run this on the `gex` modality of a scirpy `MuData` object or on a gene expression `AnnData` object once it has been loaded (see `pytcr-data-loading`). GEX QC/normalization should be complete before any GEX embedding, clustering, or `pytcr-gex-integration` step. Every `.pl.*` call below has a no-plot, data-only alternative next to it — for agents that can't process images.

## Setup

```python
import scanpy as sc
```

`scanpy`'s `sc.pp`/`sc.tl`/`sc.pl` functions operate on plain `AnnData`, not `MuData`, so work directly on `mdata["gex"]`:

```python
gex = mdata["gex"]
```

## 1. Quality control metrics

Flag mitochondrial, ribosomal, and hemoglobin genes by name prefix, then compute per-cell QC metrics:

```python
# mitochondrial genes
gex.var["mt"] = gex.var_names.str.startswith("MT-")  # "MT-" for human, "Mt-" for mouse
# ribosomal genes
gex.var["ribo"] = gex.var_names.str.startswith(("RPS", "RPL"))
# hemoglobin genes
gex.var["hb"] = gex.var_names.str.contains("^HB[^(P)]")

sc.pp.calculate_qc_metrics(gex, qc_vars=["mt", "ribo", "hb"], inplace=True, log1p=True)
```

This adds `n_genes_by_counts`, `total_counts`, `pct_counts_mt`, `pct_counts_ribo`, `pct_counts_hb` (and `log1p_*` variants) to `gex.obs`.

### Inspect

```python
sc.pl.violin(gex, ["n_genes_by_counts", "total_counts", "pct_counts_mt"], jitter=0.4, multi_panel=True)
sc.pl.scatter(gex, "total_counts", "n_genes_by_counts", color="pct_counts_mt")
```

> **No-plot alternative:** the same distributions as summary statistics, for picking filtering thresholds.
> ```python
> gex.obs[["n_genes_by_counts", "total_counts", "pct_counts_mt"]].describe()
> gex.obs[["n_genes_by_counts", "total_counts", "pct_counts_mt"]].quantile([0.01, 0.05, 0.5, 0.95, 0.99])
> gex.obs.groupby("<sample_col>")[["n_genes_by_counts", "total_counts", "pct_counts_mt"]].describe()
> ```

Use these to decide filtering thresholds. If the dataset has multiple batches/samples, inspect QC metrics per-sample — thresholds can vary substantially between batches.

## 2. Filter cells and genes

A permissive filter is recommended at this stage; prefer revisiting stricter thresholds later during clustering rather than over-filtering up front:

```python
sc.pp.filter_cells(gex, min_genes=100)
sc.pp.filter_genes(gex, min_cells=3)
```

Tighter manual/automatic thresholds on `pct_counts_mt` or `total_counts` (based on the plots above) can be applied here instead if the data warrants it — ask the user before removing a large fraction of cells.

## 3. Doublet detection

Run Scrublet to flag likely doublets. Replace `<sample_col>` with the batch/sample column in `gex.obs`:

```python
sc.pp.scrublet(gex, batch_key="<sample_col>")
```

Adds `doublet_score` and `predicted_doublet` to `gex.obs`. Ask the user whether to filter doublets now or defer to after clustering (predicted doublets are easier to sanity-check once clusters exist).

To filter immediately:

```python
gex = gex[~gex.obs["predicted_doublet"].to_numpy()].copy()
```

## 4. Normalization

Preserve raw counts, then apply median count-depth scaling with log1p transformation:

```python
gex.layers["counts"] = gex.X.copy()

sc.pp.normalize_total(gex)
sc.pp.log1p(gex)
```

## 5. Feature selection (highly variable genes)

Reduce dimensionality to the most informative genes. Replace `<sample_col>` with the batch/sample column if correcting for batch effects:

```python
sc.pp.highly_variable_genes(gex, n_top_genes=2000, batch_key="<sample_col>")
sc.pl.highly_variable_genes(gex)
```

> **No-plot alternative:** the same mean-expression-vs-dispersion info as columns instead of a scatter plot.
> ```python
> gex.var["highly_variable"].sum()   # number of HVGs selected
> gex.var[["means", "dispersions", "dispersions_norm", "highly_variable"]]
> ```

## 6. Sync back to MuData

If any cell filtering was applied (step 2 or 3), write the modality back and resync `mdata.obs`:

```python
mdata.mod["gex"] = gex
mdata.update()
```

## 7. (Optional) Dimensionality Reduction

For user-facing output, cell-type annotation, or downstream clustering, visualize the cellular composition via PCA -> neighbor graph -> UMAP:

```python
sc.tl.pca(adata)
sc.pl.pca_variance_ratio(adata, n_pcs=50, log=True)  # variance contributed by each PC
```

> **No-plot alternative:** the same per-PC variance curve as numbers, for picking how many PCs to keep.
> ```python
> adata.uns["pca"]["variance_ratio"]              # per-PC variance ratio
> adata.uns["pca"]["variance_ratio"].cumsum()      # cumulative variance explained
> ```

```python
sc.pp.neighbors(adata)
sc.tl.umap(adata)
sc.pl.umap(adata, color="sample")
```

> **No-plot alternative:** cell counts per sample instead of a colored scatter.
> ```python
> adata.obs["sample"].value_counts()
> ```

Leiden clustering on the neighbor graph helps with cell annotation and with comparing cells across patients/conditions:

```python
sc.tl.leiden(adata, flavor="igraph")
sc.pl.umap(adata, color=["leiden"])
```

> **No-plot alternative:** the same "how do clusters/samples relate" info as a table instead of a colored scatter.
> ```python
> adata.obs.groupby("leiden")["sample"].value_counts(normalize=True)
> ```

## Post-preprocessing

The `gex` modality is now QC'd, normalized, and has HVGs flagged.

Once `mdata["gex"]` has a computed embedding/clustering, `pytcr-gex-integration` can combine it with clonotype identity (after `pytcr-preprocess` → `pytcr-clonotype-clustering` → `pytcr-clonotype-analysis` on the `airr` side).
