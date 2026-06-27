---
name: pytcr-preprocess
description: Preprocess and quality-control AIRR (TCR/BCR) data in a scirpy MuData object. Use after loading data with pytcr-data-loading. Covers chain indexing, chain QC, multichain/orphan filtering, and MuData synchronization.
---

# AIRR Data Preprocessing and Quality Control

Run this after loading AIRR data (see `pytcr-data-loading` skill). These steps must be completed before any clonotype analysis.

## Setup

```python
import muon as mu
import numpy as np
import scirpy as ir
```

## 1. Index chains

Build chain indices so scirpy can apply its receptor model to the raw AIRR data. This separates chains into VJ and VDJ categories, enforces the two-pair-per-cell limit, and flags cells with excess chains as multichain.

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

### Visualize the distribution

Replace `<group_col>` with a relevant column in `mdata.obs`, for example `"gex:sample"` or `"gex:source"`. If no GEX modality is present, use a column from `mdata["airr"].obs` or omit `target_col`.

```python
_ = ir.pl.group_abundance(mdata, groupby="airr:receptor_subtype", target_col="<group_col>")
_ = ir.pl.group_abundance(mdata, groupby="airr:chain_pairing", target_col="<group_col>")
```

Use these plots to understand the composition before filtering.

## 3. Filter multichain cells

Multichain cells have more than two receptor pairs and are almost certainly doublets (two cells co-captured in one droplet). **Always remove them.**

Optionally inspect them on a UMAP first (requires GEX UMAP to be available):

```python
mu.pl.embedding(mdata, basis="gex:umap", color="airr:chain_pairing", groups="multichain")
```

Then filter:

```python
mu.pp.filter_obs(mdata, "airr:chain_pairing", lambda x: x != "multichain")
```

## 4. Orphan-chain cells — ask the user

Before filtering orphan-chain cells, ask the user how they would like to handle them. Present the following options and their trade-offs:

**Option A — Remove orphan-chain cells (most common)**

Keep only cells that have at least one complete receptor pair (VJ + VDJ):

```python
mu.pp.filter_obs(mdata, "airr:chain_pairing", lambda x: ~np.isin(x, ["orphan VJ", "orphan VDJ"]))
```

- **When to use:** Most paired-chain analyses (clonotype definition, TCR/BCR repertoire analysis). Required for `ir.tl.define_clonotypes` with `receptor_arms="all"`.
- **Pro:** Clean dataset; avoids incomplete receptors biasing clonotype stats.
- **Con:** Loses real biology — some cells genuinely express only one chain.

**Option B — Keep orphan-chain cells**

Do not filter on `chain_pairing` at all.

- **When to use:** γ/δ TCR studies (δ chains are often missing); analyses that focus on individual chains; datasets where low sequencing depth makes orphan chains common.
- **Pro:** Retains all cells for downstream analysis.
- **Con:** Orphan-chain cells are invisible to paired-chain analyses (e.g. `define_clonotypes` with `receptor_arms="all"` will effectively exclude them anyway).

**Option C — Keep but label**

Keep orphan cells and use them only in single-chain analyses. No filtering needed; the `airr:chain_pairing` column can be used later to subset.

- **When to use:** Exploratory analysis where you want to compare paired vs. unpaired populations.

Once the user has decided, apply their chosen option before continuing.

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

Also check cell counts:

```python
print(mdata)
```

## Post-preprocessing

AIRR preprocessing is complete. The natural next step is clonotype analysis:

- **Define clonotypes** (exact nt-sequence identity): `ir.pp.ir_dist` → `ir.tl.define_clonotypes`
- **Define clonotype clusters** (aa-sequence similarity): `ir.pp.ir_dist(metric="tcrdist")` → `ir.tl.define_clonotype_clusters`
- **Clonal expansion**: `ir.tl.clonal_expansion`
