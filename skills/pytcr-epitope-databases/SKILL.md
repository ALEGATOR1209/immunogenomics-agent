---
name: pytcr-epitope-databases
description: Query epitope reference databases (e.g. IggyTop, aggregating IEDB/VDJdb) to annotate cells with antigen specificity by CDR3 sequence identity. Use after pytcr-preprocess (clonotype clustering not required first).
---

# Epitope Database Query

Uses the same `ir_dist`/`ir_query` machinery as clonotype clustering (see `pytcr-clonotype-clustering`), but the "reference" is an external database instead of the dataset itself. Every `.pl.*` call below has a no-plot, data-only alternative next to it — for agents that can't process images.

## Setup

```python
import pandas as pd
import scirpy as ir
```

## 1. Load a reference database

```python
reference = ir.datasets.iggytop()
```

IggyTop is a metadatabase aggregating IEDB, VDJdb, and others, with `antigen_species`/`antigen_name` annotations. Any AnnData in scirpy's format can serve as a reference — build a custom one with `pytcr-data-loading` if the database you need isn't in `scirpy.datasets`.

## 2. Compute distances against the reference

```python
ir.pp.ir_dist(mdata, reference, metric="identity", sequence="aa")
```

Passing `reference` as a positional argument computes cross-dataset distances instead of within-dataset ones — stored separately, so this doesn't collide with any `ir.pp.ir_dist(mdata)` run earlier for clonotype definition.

## 3. Query matches per cell

```python
ir.tl.ir_query(
    mdata,
    reference,
    metric="identity",
    sequence="aa",
    receptor_arms="any",
    dual_ir="any",
)
```

`receptor_arms`/`dual_ir` mean the same as in clonotype clustering. Reference databases are sparse relative to a real repertoire, so `"any"`/`"any"` (lenient — a match on either arm/chain pair counts) is the reasonable default here, unlike clonotype definition where `"all"` is preferred. Tighten to `"all"` for higher-confidence hits.

## 4. Annotate cells

Two ways to read out matches, both need the same `reference`/`metric`/`sequence` args as step 3:

**All matches, one row per (cell, reference entry) pair** — use when a cell can plausibly match several entries and you want to inspect all of them:

```python
ir.tl.ir_query_annotate_df(
    mdata,
    reference,
    metric="identity",
    sequence="aa",
    include_ref_cols=["antigen_species", "antigen_name"],
)
```

**One label per cell** — collapses matches per `strategy`:

```python
ir.tl.ir_query_annotate(
    mdata,
    reference,
    metric="identity",
    sequence="aa",
    include_ref_cols=["antigen_species"],
    strategy="most-frequent",
)
```

`strategy`: `"unique-only"` (default; cells with multiple inconsistent matches get `"ambiguous"`), `"most-frequent"` (assigns the most common match, ties → `"ambiguous"`), or `"json"` (stores all matches + counts as a JSON string). Adds `mdata.obs["airr:<ref_col>"]` for each column in `include_ref_cols`.

## 5. Visualize

```python
mu.pl.embedding(mdata, "gex:umap", color="airr:antigen_species")
```

> **No-plot alternative:** the annotation counts and its localization against a cluster/cell-type column, instead of eyeballing the UMAP.
> ```python
> mdata.obs["airr:antigen_species"].value_counts()
> pd.crosstab(mdata.obs["<cluster_col>"], mdata.obs["airr:antigen_species"])
> ```

Requires GEX UMAP (see `pytcr-sc-rnaseq-preprocessing`).
