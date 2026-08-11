---
name: pytcr-data-loading
description: Load single-cell immune receptor (AIRR/TCR/BCR) data into scirpy. Unite with scRNA-seq in a single MuData object. Basic AnnData/MuData manipulations. Use when importing CellRanger, TraCeR, BraCeR, BD Rhapsody, or AIRR-rearrangement data, or combining multiple samples for scirpy analysis.
---

# Loading immune receptor data into scirpy

The goal is an `AnnData` object (AIRR-seq only), or, when GEX data is also available, a single `MuData` with a `gex` (transcriptomics) and an `airr` (receptor) modality — merging multiple samples into one unified object where applicable. This is a **required** first step before any downstream analysis; if unsure of the data's origin or how to import it, ask the user.

## Setup

```python
import anndata
import muon as mu
import pandas as pd
import scanpy as sc
import scirpy as ir
```

## The scirpy data model (assumptions for all analyses)

- Chain loci must be valid: `TRA`, `TRG`, `IGK`, `IGL` (VJ-junction chains) or `TRB`, `TRD`, `IGH` (VDJ-junction chains).
- Each cell may have up to two VJ and two VDJ chains (dual IR). Excess chains (lowest read/UMI count) are dropped and the cell is flagged as a multichain-cell.
- Non-productive chains are ignored. CellRanger, TraCeR, and the AIRR format flag these automatically; for custom formats you must pass the `productive` flag or filter beforehand.

## Data loading

### AIRR data

All of the functions below return an `AnnData` object unless specified otherwise.

#### Determining what data you have

##### 10X Genomics Cell Ranger
Files like `{all,filtered}_contig_annotations.csv` or `all_contig_annotations.json` — compressed and prefixed variants allowed (e.g. `GSM000001_filtered_contig_annotations.csv.gz`) — mean 10X Cell Ranger data.

Use `scirpy.io.read_10x_vdj(path, filtered=True, include_fields=None, **kwargs)`. `path` points to one of the CSV/JSON files above. `filtered=True` keeps only `is_cell` + `high_confidence` contigs (a no-op if `path` is already `filtered_contig_annotations.csv`).

##### TraCeR
A per-cell directory structure — `<directory>/<cell_name>/{aligned_reads, Trinity_output, IgBLAST_output, unfiltered_TCR_seqs, expression_quantification, filtered_TCR_seqs}` — means TraCeR data. Only the `filtered_TCR_seqs/<CELL_ID>.pkl` files are actually needed. **The output of `tracer summarise` does not work**: per scirpy's docs, those summary files omit required fields.

Use `scirpy.io.read_tracer(path, **kwargs)`, where `path` is the TraCeR output folder.

##### BraCeR
A directory structure similar to TraCeR's but with `unfiltered_BCR_seqs`/`filtered_BCR_seqs` means BraCeR data. Unlike TraCeR, here you **do** need the output of `bracer summarise`: look for a `changeodb.tab` file under `<directory>/filtered_BCR_summary` or `<directory>/unfiltered_BCR_summary` (or ask the user to provide it directly, noting it's BraCeR).

Use `scirpy.io.read_bracer(path, **kwargs)`, where `path` is the `changeodb.tab` file.

##### AIRR rearrangement format
A tsv with `cell_id`, `productive`, a `locus` column (valid IMGT locus name), at least one of `consensus_count`/`duplicate_count`/`umi_count`, and at least one of `junction_aa`/`junction` means AIRR rearrangement format.

Use `scirpy.io.read_airr(path, use_umi_count_col=None, infer_locus=True, cell_attributes='is_cell', include_fields=None, **kwargs)`. `path` can be a single tsv, a list of per-chain files (e.g. `["path/to/tcr_alpha.tsv", "path/to/tcr_beta.tsv"]`), or a pandas DataFrame (or list thereof). `infer_locus=True` derives the locus column from gene names when it isn't already present. `cell_attributes` lists fields that are per-cell rather than per-chain (must be identical across all of a cell's records). `use_umi_count_col` and `include_fields` are deprecated no-ops.

##### BD Rhapsody
Files like `*_perCellChain.csv`, `*_perCellChain_unfiltered.csv`, `*_VDJ_Dominant_Contigs.csv`, `*_VDJ_Unfiltered_Contigs.csv` (gzipped or not) mean BD Rhapsody data. `*_perCell.csv` is not supported.

Use `scirpy.io.read_bd_rhapsody(path, **kwargs)`, where `path` is the perCellChain/Contigs file.

##### Dandelion
Given an already-initialized `dandelion.Dandelion` instance, use `scirpy.io.from_dandelion(dandelion, transfer=False, to_mudata=False, **kwargs)`. `transfer=True` runs `dandelion.tl.transfer` to pull all data onto the AnnData; `to_mudata=True` returns a MuData instead of an AnnData.

### RNA data

All of the functions below return an `AnnData` object unless specified otherwise.

#### Determining what data you have

##### 10X Genomics

A `.hdf5` file from 10X Genomics: `scanpy.read_10x_h5(filename, *, genome=None, gex_only=True, backup_url=None)`. `genome=` filters to one genome, required for legacy 10x h5 files with more than one; `gex_only=True` drops non-'Gene Expression' features (Antibody Capture, CRISPR Guide Capture, Custom).

A directory with `*_.barcodes.tsv`, `*_.genes.tsv`, `*_.matrix.mtx` (unzip first if gzipped and you hit import errors) is 10X mtx data: `scanpy.read_10x_mtx(path, *, var_names='gene_symbols', make_unique=True, cache=False, gex_only=True, prefix=None, compressed=True)`. `prefix` is whatever precedes `matrix.mtx`/`genes.tsv`/`barcodes.tsv` (files named `patientA_matrix.mtx` etc. need `prefix="patientA_"`). `compressed=True` expects Cell Ranger v3+ files gzipped — set `False` for STARsolo output (no effect on legacy v2- files).

10X Visium: `scanpy.read_visium()`.

##### Other formats

Standard scanpy readers, one line each:
- `.h5ad` → `scanpy.read_h5ad()`
- `.csv` → `scanpy.read_csv()`
- `.xlsx` → `scanpy.read_excel()` (assumes first column = row names, first row = column names)
- `.h5` (hdf5) → `scanpy.read_hdf()`
- `.loom` → `scanpy.read_loom()`
- `.mtx` → `scanpy.read_mtx()`
- `.txt`/`.tab`/`.data` → `scanpy.read_text()`
- gzipped condensed count matrix from umi_tools → `scanpy.read_umi_tools()`

### Building a MuData

Typical loading workflow looks like this:

```python
adata_tcr = ir.io.read_10x_vdj("example_data/liao-2019-covid19/GSM4385993_C144_filtered_contig_annotations.csv.gz")

adata = sc.read_10x_h5("example_data/liao-2019-covid19/GSM4339772_C144_filtered_feature_bc_matrix.h5")
adata.var_names_make_unique()

mdata = mu.MuData({"gex": adata, "airr": adata_tcr})
```

### Combining multiple samples
Load each sample independently, then unite the `AnnData`s using `anndata.concat()`

```python
from glob import glob

# define sample metadata. Usually read from a file.
samples = {
    "C144": {"group": "mild"},
    "C146": {"group": "severe"},
    "C149": {"group": "healthy control"},
}

adatas_tcr = {}
adatas_gex = {}
for sample in samples.keys():
    gex_file = glob(f"example_data/liao-2019-covid19/*{sample}*.h5")[0]
    tcr_file = glob(f"example_data/liao-2019-covid19/*{sample}*.csv.gz")[0]
    adata_gex = sc.read_10x_h5(gex_file)
    adata_tcr = ir.io.read_10x_vdj(tcr_file)
    # concatenation only works with unique gene names
    adata_gex.var_names_make_unique()
    adatas_tcr[sample] = adata_tcr
    adatas_gex[sample] = adata_gex

adata_gex = anndata.concat(adatas_gex, index_unique="_")
adata_tcr = anndata.concat(adatas_tcr, index_unique="_")
mdata = mu.MuData({"gex": adata_gex, "airr": adata_tcr})

# global metadata on `mdata.obs`
mdata.obs["sample"] = mdata.obs_names.to_series().str.split("_", expand=True)[1]
mdata.obs["group"] = mdata.obs["sample"].map(lambda x: samples[x]["group"])
```

## Next step

Run the `pytcr-preprocess` skill next — propose it to the user, or run it directly in autonomous mode.
