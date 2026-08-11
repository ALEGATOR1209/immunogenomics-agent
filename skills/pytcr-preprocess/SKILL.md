---
name: pytcr-preprocess
description: Preprocess and quality-control AIRR (TCR/BCR) data in a scirpy MuData object. Use after loading data with pytcr-data-loading. Covers chain indexing, chain QC, multichain/orphan filtering, and MuData synchronization.
---

# AIRR Data Preprocessing and Quality Control

Run this after loading AIRR data (see `pytcr-data-loading` skill). These steps must be completed before any clonotype analysis. Every `.pl.*` call below has a no-plot, data-only alternative next to it — for agents that can't process images.

> If `mdata` also has a `gex` (transcriptomics) modality, this skill only covers the `airr` side. QC, normalization, and feature selection of the scRNA-seq data **must** be performed separately. Use the `pytcr-sc-rnaseq-preprocessing` skill for that (can run before/after/in parallel).

## Setup

```python
import muon as mu
import numpy as np
import pandas as pd
import scirpy as ir
```

## 1. Index chains

Build chain indices so scirpy can apply its receptor model: separates chains into VJ/VDJ categories, enforces the two-pair-per-cell limit, and flags excess-chain cells as multichain.

```python
ir.pp.index_chains(mdata)
```

Result is stored in `mdata["airr"].obsm["chain_indices"]`.

## 2. Chain QC

Compute per-cell receptor composition summaries:

```python
ir.tl.chain_qc(mdata)
```

This adds three columns to `mdata.obs`:

| Column | Values |
|--------|--------|
| `airr:receptor_type` | `TCR`, `BCR`, `ambiguous` |
| `airr:receptor_subtype` | `TRA+TRB`, `TRG+TRD`, `IGH+IGK`, `IGH+IGL`, … |
| `airr:chain_pairing` | see table below |

**Chain pairing values:**

| Value | Meaning |
|-------|---------|
| `single pair` | One complete VJ + VDJ pair — the expected case |
| `orphan VJ` | Only a VJ chain (e.g. TRA only, no TRB) |
| `orphan VDJ` | Only a VDJ chain (e.g. TRB only, no TRA) |
| `extra VJ` | Full pair + an additional VJ chain |
| `extra VDJ` | Full pair + an additional VDJ chain |
| `two full chains` | Two complete pairs (dual IR cell) |
| `multichain` | More than two pairs — almost certainly a doublet |
| `no IR` | Zero valid chains — e.g. a cell present via the `gex` modality (or otherwise in the merged object) with no productive VJ or VDJ chain at all. A question about "cells with no IR" is answered directly by this value (`chain_pairing == "no IR"`) — no need to compute it indirectly via a GEX-vs-AIRR barcode set difference. |

> **Pitfall: `chain_pairing` vs. `receptor_subtype` are not interchangeable.** `receptor_subtype` (`TRA+TRB`, etc.) only records which chain *types* are present on a cell — it says nothing about how many of each. A cell with an extra VJ or VDJ chain (`chain_pairing == "extra VJ"` / `"extra VDJ"`) or even two full pairs (`"two full chains"`) still shows `receptor_subtype == "TRA+TRB"`, identical to a clean single-pair cell. When a question is about pair *cardinality* — "cells with a single TCR chain pair", "cells with more than one pair of TCRs" — always answer it from `chain_pairing`, never from `receptor_subtype`. Reach for `receptor_subtype` only when the question is genuinely about chain *composition* (e.g. distinguishing TRA+TRB from TRG+TRD cells).

### Visualize the distribution

Replace `<group_col>` with a relevant column in `mdata.obs`, for example `"gex:sample"` or `"gex:source"`. If no GEX modality is present, use a column from `mdata["airr"].obs` or omit `target_col`.

```python
_ = ir.pl.group_abundance(mdata, groupby="airr:receptor_subtype", target_col="<group_col>")
_ = ir.pl.group_abundance(mdata, groupby="airr:chain_pairing", target_col="<group_col>")
```

> **No-plot alternative:** the same counts/fractions as a DataFrame instead of a bar chart — `ir.tl.group_abundance` is the plotting function's own backend and always returns them directly.
> ```python
> ir.tl.group_abundance(mdata, groupby="airr:receptor_subtype", target_col="<group_col>", fraction=True)
> ir.tl.group_abundance(mdata, groupby="airr:chain_pairing", target_col="<group_col>", fraction=True)
> ```

## 3. Filter multichain cells

Multichain cells have more than two receptor pairs and are almost certainly doublets (two cells co-captured in one droplet). **Always remove them.**

Optionally inspect them on a UMAP first (requires GEX UMAP to be available, see `pytcr-sc-rnaseq-preprocessing` skill):

```python
mu.pl.embedding(mdata, basis="gex:umap", color="airr:chain_pairing", groups="multichain")
```

> **No-plot alternative:** the same composition/distribution without an embedding.
> ```python
> mdata.obs["airr:chain_pairing"].value_counts()
> pd.crosstab(mdata.obs["<cluster_or_sample_col>"], mdata.obs["airr:chain_pairing"])
> ```

Then filter:

```python
mu.pp.filter_obs(mdata, "airr:chain_pairing", lambda x: x != "multichain")
```

## 4. Orphan-chain cells — ask the user

Before filtering orphan-chain cells, ask the user how to handle them:

**Option A — Remove them (most common).** Required for most paired-chain analyses (clonotype definition, `ir.tl.define_clonotypes` with `receptor_arms="all"`); cleans the dataset but loses cells that genuinely express only one chain.
```python
mu.pp.filter_obs(mdata, "airr:chain_pairing", lambda x: ~np.isin(x, ["orphan VJ", "orphan VDJ"]))
```

**Option B — Keep them, unfiltered.** Best for γ/δ TCR studies (δ chains often missing), single-chain-focused analyses, or low-depth data where orphans are common; retains all cells, though they're invisible to paired-chain analyses regardless (`receptor_arms="all"` excludes them anyway).

**Option C — Keep and label.** No filtering; use the `airr:chain_pairing` column later to subset paired vs. unpaired cells for exploratory comparison.

Apply the chosen option before continuing.

## 5. Synchronize MuData

After any filtering step, call `.update()` to propagate obs changes across all modalities:

```python
mdata.update()
```

## 6. Verify

Re-plot chain pairing to confirm the outcome matches expectations:

```python
_ = ir.pl.group_abundance(mdata, groupby="airr:chain_pairing", target_col="<group_col>")
```

> **No-plot alternative:** confirm the post-filter counts numerically.
> ```python
> ir.tl.group_abundance(mdata, groupby="airr:chain_pairing", target_col="<group_col>", fraction=True)
> ```

Also check cell counts:

```python
print(mdata)
```

## Post-preprocessing

AIRR preprocessing is complete. The natural next step is clonotype analysis:

- **Define clonotypes** (exact nt-sequence identity): `ir.pp.ir_dist` → `ir.tl.define_clonotypes`
- **Define clonotype clusters** (aa-sequence similarity): `ir.pp.ir_dist(metric="tcrdist")` → `ir.tl.define_clonotype_clusters`
- **Clonal expansion**: `ir.tl.clonal_expansion`
