from pathlib import Path

import anndata as ad
import muon as mu
import numpy as np
import pandas as pd
import scanpy as sc
import scirpy as ir

from .antibodies import annotate_adt, extract_adt
from .tissue import annotate_tissue


def read_vdj(path: Path) -> ad.AnnData:
  adata = ir.io.read_10x_vdj(path)
  ir.pp.index_chains(adata)
  ir.tl.chain_qc(adata)
  return adata


# Reads one sample directory (e.g. data/PSA1). The sample name is the directory name,
# stored in obs['sample'] of all modalities. Cells get obs['tissue'] from the hashtags,
# using `hashtags` (data/hashtags.csv: sample, hashtag, tissue); hashtag doublets /
# negatives are dropped. Antibody (ADT) features are returned as a separate AnnData with
# the same cells as the GEX data after QC. Cell types from `adt_rules`
# (data/adt_cell_types.csv, see antibodies.annotate_adt) are added to both.
def read_sample(
  path: Path,
  hashtags: pd.DataFrame,
  adt_rules: pd.DataFrame,
) -> tuple[ad.AnnData, ad.AnnData, ad.AnnData]:
  mtx = next(path.glob("*-matrix.mtx.gz"))
  prefix = mtx.name[: -len("matrix.mtx.gz")]

  adata = sc.read_10x_mtx(path, var_names="gene_symbols", prefix=prefix, gex_only=False)
  adata.var_names_make_unique()
  adata.obs["sample"] = path.name
  annotate_tissue(adata, hashtags)
  mu.pp.filter_obs(adata, "tissue", lambda x: ~np.isin(x, ["doublet", "negative"]))

  adata_adt = extract_adt(adata)
  adata_gex = adata[:, adata.var["feature_types"] == "Gene Expression"].copy()

  sc.pp.filter_cells(adata_gex, min_genes=200)
  sc.pp.filter_genes(adata_gex, min_cells=3)
  adata_gex.var["mt"] = adata_gex.var_names.str.startswith("MT-")
  sc.pp.calculate_qc_metrics(adata_gex, qc_vars=["mt"], inplace=True, log1p=True)
  mu.pp.filter_obs(adata_gex, 'pct_counts_mt', lambda x: x < 10)

  adata_adt = adata_adt[adata_gex.obs_names].copy()
  annotate_adt(adata_adt, adt_rules)
  for annotation in adt_rules["annotation"].unique():
    adata_gex.obs[annotation] = adata_adt.obs[annotation]

  adata_airr = read_vdj(next(path.glob("*-filtered_contig_annotations.csv.gz")))
  adata_airr.obs["sample"] = path.name
  mu.pp.filter_obs(adata_airr, "receptor_subtype", lambda x: ~np.isin(x, ["multichain", "ambiguous", "no IR"]))
  mu.pp.filter_obs(adata_airr, "chain_pairing", lambda x: x == "single pair")

  return adata_gex, adata_adt, adata_airr
