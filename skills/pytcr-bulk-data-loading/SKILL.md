---
name: pytcr-bulk-data-loading
description: Load and standardize bulk TCR-Seq / BCR-Seq repertoire data (e.g. Adaptive ImmunoSEQ, MiXCR exports) into the pyTCR standard table format, combine multiple per-sample files into one repertoire table, and compute the derived columns (frequency, clonotype count) that every bulk pyTCR analysis depends on. Use before any pytcr-bulk-* analysis skill. This is the bulk-repertoire counterpart to pytcr-data-loading, which is for single-cell AIRR data.
---

# Bulk TCR-Seq Data Loading

This is a pandas/numpy/scipy/seaborn-based approach for post-processing bulk TCR-Seq repertoire tables (e.g. output from MiXCR or Adaptive ImmunoSEQ) — as opposed to the `pytcr-data-loading`/`pytcr-preprocess`/... family, which is for single-cell AIRR data via scirpy. There is no installable package here: the "tool" is the pandas logic itself, run directly in a notebook. Use this skill first; its output (`df`) is the input every `pytcr-bulk-*` analysis skill expects.

## Setup

```python
import pandas as pd
import glob
import os
```

---

## 1. The pyTCR standard table format

Every bulk analysis in this family operates on a table with these columns:

| Column | Description |
|--------|-------------|
| `sample` | Sample name |
| `freq` | Clonotype frequency (share of reads) within the sample |
| `#count` | Number of reads (template count) for the clonotype |
| `cdr3aa` | CDR3 amino-acid sequence |
| `cdr3nt` | CDR3 nucleotide sequence |
| `v` | V gene |
| `d` | D gene |
| `j` | J gene |
| *(optional)* | Any other columns you want to analyze/group by later (e.g. `hospitalized`, `patient`, `tissue`) |

Some pre-processing tools (MiXCR, ImmunoSEQ, VDJtools, ...) already filter out non-coding CDR3 sequences — confirm that's true of your input, since this format assumes it.

---

## 2. Convert a single sample file to the standard format

If your source file uses different column names, map them to the standard ones. Replace `<file_path>` and the `<...>` column names with your data's actual columns — this example matches Adaptive ImmunoSEQ's export naming:

```python
file_path = "<file_path>"
target_filename = os.path.basename(file_path)

df_raw = pd.read_table(file_path, low_memory=False, engine="c")

# Map your source columns to the standard pyTCR columns, in this order:
# sample, freq, #count, cdr3aa, cdr3nt, v, d, j
required_columns = ["<sample_col>", "<freq_col>", "<count_col>", "<cdr3aa_col>", "<cdr3nt_col>", "<v_col>", "<d_col>", "<j_col>"]
optional_columns = ["<metadata_col>", "..."]  # e.g. ["hospitalized"]

df_std = df_raw.filter(required_columns + optional_columns)
df_std.columns = ["sample", "freq", "#count", "cdr3aa", "cdr3nt", "v", "d", "j"] + optional_columns

df_std.to_csv(f"{target_filename}.csv", na_rep=".", index=False)
```

Repeat for each sample file, or wrap the above in a loop over `glob.glob("<source_dir>/*")`.

---

## 3. Combine per-sample files into one repertoire table

Once every sample file has been converted to the standard format (Step 2) and saved as `.csv` into one directory, combine them into a single table. If a file has no `sample` column, this also stamps one on from the filename:

```python
globbed_files = glob.glob("<converted_dir>/*.csv")

data = []
for csv_path in globbed_files:
    df_sample = pd.read_csv(csv_path)
    if "sample" not in df_sample.columns:
        df_sample["sample"] = os.path.basename(csv_path).split(".")[0]
    data.append(df_sample)

df_combined = pd.concat(data, ignore_index=True)
df_combined.to_csv("combined_data.tsv", sep="\t", na_rep=".", index=False)
```

Combining upfront means every downstream analysis (basic/clonality/diversity, gene usage/motif, overlap) works across all samples from one table instead of juggling per-sample files — and pyTCR's overlap analysis (`pytcr-bulk-repertoire-overlap`) specifically requires all samples to be in one table.

---

## 4. Load the combined table and compute derived columns

This is the loading step every other `pytcr-bulk-*` skill assumes has already run. It computes per-sample read totals, clonotype frequency, and clonotype counts — used throughout basic/clonality/diversity/gene-usage/motif/overlap analysis.

Replace `<file_path>` with your combined table, and `<group_cols>` with any metadata columns you'll want to group/compare by later (e.g. `["hospitalized"]`; use `[]` if there's none):

```python
group_cols = ["<group_cols>"]  # e.g. ["hospitalized"]

df = pd.read_table("<file_path>", low_memory=False, engine="c")

# Total reads per sample (used to compute frequency)
df_reads = (
    df.groupby(["sample"] + group_cols)
    .agg({"#count": "sum"})
    .reset_index()
    .rename(columns={"#count": "count"})
)

df = pd.merge(df, df_reads, how="outer", on=["sample"] + group_cols).fillna(0)
df["freq"] = df["#count"] / (df["count"] * 1.0)
df.fillna(0, inplace=True)

# Clonotype count per sample
df_diversity = df.groupby(["sample"] + group_cols, sort=False).size().reset_index(name="clonotype_count")
df = pd.merge(df, df_diversity, on=["sample"] + group_cols)
```

`df` now has, in addition to the standard columns: `count` (total reads in the sample), `freq` (recomputed clonotype frequency), and `clonotype_count` (number of unique clonotypes in the sample). This is the table to pass into `pytcr-bulk-repertoire-metrics`, `pytcr-bulk-gene-motifs`, and `pytcr-bulk-repertoire-overlap`.

> If your source data's `freq` column was already computed by an upstream tool, it's recomputed here rather than trusted directly — this keeps `freq` consistent with whatever subset of clonotypes ends up in `df` after any earlier filtering.

---

## Post-loading

With `df` prepared, proceed to:

- **Basic / clonality / diversity metrics**: `pytcr-bulk-repertoire-metrics`
- **Gene usage and motif analysis**: `pytcr-bulk-gene-motifs`
- **Cross-sample overlap analysis**: `pytcr-bulk-repertoire-overlap` (requires ≥2 samples in `df`)
