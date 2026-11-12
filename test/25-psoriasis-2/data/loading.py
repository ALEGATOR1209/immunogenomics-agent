from pathlib import Path

import anndata as ad
import muon as mu
import numpy as np
import scanpy as sc

def read_sample(
  path: Path,
) -> ad.AnnData:
  mtx = next(path.glob("*-matrix.mtx.gz"))
  prefix = mtx.name[: -len("matrix.mtx.gz")]

  adata = sc.read_10x_mtx(path, var_names="gene_symbols", prefix=prefix, gex_only=False)
  adata.var_names_make_unique()
  adata.obs["sample"] = path.name
  mu.pp.filter_obs(adata, "tissue", lambda x: ~np.isin(x, ["doublet", "negative"]))

  adata_gex = adata[:, adata.var["feature_types"] == "Gene Expression"].copy()

  sc.pp.filter_cells(adata_gex, min_genes=200)
  sc.pp.filter_genes(adata_gex, min_cells=3)
  adata_gex.var["mt"] = adata_gex.var_names.str.startswith("MT-")
  sc.pp.calculate_qc_metrics(adata_gex, qc_vars=["mt"], inplace=True, log1p=True)
  mu.pp.filter_obs(adata_gex, 'pct_counts_mt', lambda x: x < 10)

  return adata_gex
