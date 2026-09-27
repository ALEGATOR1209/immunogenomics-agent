from pathlib import Path

import anndata as ad
import muon as mu
import numpy as np
import scanpy as sc
import scirpy as ir

from .tissue import annotate_tissue

def read_vdj(path: Path) -> ad.AnnData:
  adata = ir.io.read_10x_vdj(path)
  ir.pp.index_chains(adata)
  ir.tl.chain_qc(adata)
  return adata

# Reads one sample directory (e.g. data/PSA1). The sample name is the directory name,
# stored in obs['sample'] of both modalities. GEX cells get obs['tissue'] from the hashtags;
# hashtag doublets / negatives are dropped along with the antibody features.
def read_sample(path: Path) -> tuple[ad.AnnData, ad.AnnData]:
  mtx = next(path.glob("*-matrix.mtx.gz"))
  prefix = mtx.name[: -len("matrix.mtx.gz")]

  adata_gex = sc.read_10x_mtx(path, var_names="gene_symbols", prefix=prefix, gex_only=False)
  adata_gex.var_names_make_unique()
  adata_gex.obs["sample"] = path.name
  annotate_tissue(adata_gex)
  mu.pp.filter_obs(adata_gex, "tissue", lambda x: ~np.isin(x, ["doublet", "negative"]))
  mu.pp.filter_var(adata_gex, "feature_types", lambda x: x == "Gene Expression")

  sc.pp.filter_cells(adata_gex, min_genes=200)
  sc.pp.filter_genes(adata_gex, min_cells=3)
  adata_gex.var["mt"] = adata_gex.var_names.str.startswith("MT-")
  sc.pp.calculate_qc_metrics(adata_gex, qc_vars=["mt"], inplace=True, log1p=True)
  mu.pp.filter_obs(adata_gex, 'pct_counts_mt', lambda x: x < 10)

  adata_airr = read_vdj(next(path.glob("*-filtered_contig_annotations.csv.gz")))
  adata_airr.obs["sample"] = path.name
  mu.pp.filter_obs(adata_airr, "receptor_subtype", lambda x: ~np.isin(x, ["multichain", "ambiguous", "no IR"]))
  mu.pp.filter_obs(adata_airr, "chain_pairing", lambda x: x == "single pair")

  return adata_gex, adata_airr
