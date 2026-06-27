---
name: pytcr-data-loading
description: Load single-cell immune receptor (AIRR/TCR/BCR) data into scirpy. Use when importing CellRanger, TraCeR, BraCeR, BD Rhapsody, or AIRR-rearrangement data, building AnnData/MuData objects from custom CDR3 tables, or combining multiple samples for scirpy analysis.
---

# Loading immune receptor data into scirpy

Import single-cell `AIRR` data (TCR/BCR) into an `AnnData` object and, when gene expression is available, merge it into a `MuData` container. This is the required first step before any scirpy analysis (clonotype definition, chain QC, clonal expansion, etc.). If not sure of the origin of data, ask user.

## Setup

```python
import anndata
import muon as mu
import pandas as pd
import scanpy as sc
import scirpy as ir
```

## The scirpy data model (assumptions for all analyses)

- BCR and TCR chains are supported. Chain loci must be valid: `TRA`, `TRG`, `IGK`, `IGL` (VJ-junction chains) or `TRB`, `TRD`, `IGH` (VDJ-junction chains).
- Each cell may have up to two VJ and two VDJ chains (dual IR). Excess chains (lowest read/UMI count) are dropped and the cell is flagged as a multichain-cell.
- Non-productive chains are ignored. CellRanger, TraCeR, and the AIRR format flag these automatically; for custom formats you must pass the `productive` flag or filter beforehand.

## Data loading

Use one of these functions to load data in the defined formats. Use standard pandas or other appropriate approaches to load data in other formats.

| Function | Description |
|----------|-------------|
| read_10x_vdj(path[, filtered, include_fields]) |  Read AIRR data from 10x Genomics cell-ranger output. |
| read_tracer(path, **kwargs) | Read data from TraCeR |
| read_bracer(path, **kwargs) | Read data from BraCeR |
| read_airr(path[, use_umi_count_col, ...]) | Read data from AIRR rearrangement format |
| read_bd_rhapsody(path, **kwargs) | Read IR data from the BD Rhapsody Analysis Pipeline|
| from_dandelion(dandelion[, transfer, to_mudata]) | Import data from Dandelion |

### Loading paired scRNA and TCR sequencing data

Here's an example of loading paired single cell and TCR sequencing data:

```python
# Load the TCR data
adata_tcr = ir.io.read_10x_vdj("example_data/liao-2019-covid19/GSM4385993_C144_filtered_contig_annotations.csv.gz")

# Load the associated transcriptomics data
adata = sc.read_10x_h5("example_data/liao-2019-covid19/GSM4339772_C144_filtered_feature_bc_matrix.h5")
adata.var_names_make_unique()
```

### Loading TraCeR data

Here's an example of loading TraCeR data - a method commonly used to extract TCR sequences from data generated with Smart-seq2 or other full-length single-cell sequencing protocols. First, we load the transcriptomics data from the counts.tsv file:

```python
expr_chung = pd.read_csv("example_data/chung-park-2017/counts.tsv", sep="\t")
# anndata needs genes in columns and samples in rows
expr_chung = expr_chung.set_index("Geneid").T
adata = sc.AnnData(expr_chung)
adata_tcr = ir.io.read_tracer("example_data/chung-park-2017/tracer/")
```

### Loading AIRR-compliant data

Here's an example of loading AIRR-compliant rearrangement table without transcriptomic data. The rearrangement tables are often organized into separate tables per chain.

```python
adata = ir.io.read_airr(
    [
        "example_data/immunesim_airr/immunesim_tra.tsv",
        "example_data/immunesim_airr/immunesim_trb.tsv",
    ]
)
```

### Converting from other formats

Here's an example how to import unknown data. Often, immune receptor (IR) data are just provided as a simple table listing the CDR3 sequences for each cell. Such a table typically contains information about

* CDR3 sequences (amino acid and/or nucleotide)
* The Chain locus, e.g. TRA, TRB, or IGH.
* expression of the receptor chain (e.g. count, UMI, transcripts per million (TPM))
* the V(D)J genes for each chain
* information if the chain is productive.

```python
tcr_table = pd.read_csv(
    "example_data/chung-park-2017/tcr_table.tsv",
    sep="\t",
    index_col=0,
    na_values=["None"],
    true_values=["True"],
)
```

Example of the data in `tcr_table`:

|| cell_id | cdr3_alpha | cdr3_nt_alpha |	count_alpha |	v_alpha |	j_alpha |	cdr3_beta |	cdr3_nt_beta |	count_beta |	v_beta	| d_beta |	j_beta |	productive_alpha |	productive_beta |
|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|
|0 | SRR2973278 |	AVSDIHASGGSYIPT |	GCTGTTTCGGATATTCATGCATCAGGAGGAAGCTACATACCTACA | 9.29463 | TRAV21 | TRAJ6 | ASSWWQNTEAF | GCCAGCAGCTGGTGGCAGAACACTGAAGCTTTC | 37.5984 | TRBV5-1 | NaN | TRBJ1-1 | True | True

Each AirrCell can have an arbitrary number of chains. A chain is simply represented as a Python dictionary following the AIRR Rearrangement Schema.

```python
tcr_cells = []
for _, row in tcr_table.iterrows():
    cell = ir.io.AirrCell(cell_id=row["cell_id"])
    # some fields are mandatory according to the Rearrangement standard, but can be set to NULL
    # the `empty_chain_dict()` function provides a dictionary with all mandatory fields, but set to NULL.
    alpha_chain = ir.io.AirrCell.empty_chain_dict()
    beta_chain = ir.io.AirrCell.empty_chain_dict()
    alpha_chain.update(
        {
            "locus": "TRA",
            "junction_aa": row["cdr3_alpha"],
            "junction": row["cdr3_nt_alpha"],
            "consensus_count": row["count_alpha"],
            "v_call": row["v_alpha"],
            "j_call": row["j_alpha"],
            "productive": row["productive_alpha"],
        }
    )
    beta_chain.update(
        {
            "locus": "TRB",
            "junction_aa": row["cdr3_beta"],
            "junction": row["cdr3_nt_beta"],
            "consensus_count": row["count_beta"],
            "v_call": row["v_beta"],
            "d_call": row["d_beta"],
            "j_call": row["j_beta"],
            "productive": row["productive_beta"],
        }
    )
    cell.add_chain(alpha_chain)
    cell.add_chain(beta_chain)
    tcr_cells.append(cell)
```

Now it can be converted to `AnnData`:

```python
adata_tcr = ir.io.from_airr_cells(tcr_cells)
```

## Data integration

If transcriptomics data available, they can be integrated with AIRR data into a single MuData object. By convention, gene expression data should be stored in the gex modality, immune receptor data in the airr modality.

```python
mdata = mu.MuData({"gex": adata, "airr": adata_tcr})
```

## Combining multiple samples

If the sequencing data are split into multiple samples, load each sample and then concat them:

```python
# Merge anndata objects
adata_gex = anndata.concat(adatas_gex, index_unique="_")
adata_tcr = anndata.concat(adatas_tcr, index_unique="_")
mdata = mu.MuData({"gex": adata_gex, "airr": adata_tcr})

# Set global metadata on `mdata.obs`
mdata.obs["sample"] = mdata.obs_names.to_series().str.split("_", expand=True)[1]
mdata.obs["group"] = mdata.obs["sample"].map(lambda x: samples[x]["group"])
```

`mdata` should look like this:

```
MuData object with n_obs × n_vars = 10715 × 33539
  obs:	'sample', 'group'
  2 modalities
    gex:	10706 x 33539
    airr:	581 x 0
      obsm:	'airr'
```

## Post-importing

When you've finished, propose the user to run pytcr-preprocessing skill.
