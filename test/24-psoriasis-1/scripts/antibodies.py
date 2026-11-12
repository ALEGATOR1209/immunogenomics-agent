import re

import anndata as ad
import numpy as np
import pandas as pd
import scipy.sparse as sp

ADT_RE = re.compile(r"ADT[_-](.+?)_TotalSeqC")
ADT_ALIASES = {"PD1": "PD-1"}  # PSA5 spells it differently


def _clean_adt_name(name: str) -> str:
  m = ADT_RE.search(name)
  marker = m.group(1) if m else name
  return ADT_ALIASES.get(marker, marker)


# Threshold that best separates two groups of values (maximum between-class variance).
def _otsu_threshold(x: np.ndarray, n: int = 256) -> float:
  candidates = np.linspace(x.min(), x.max(), n)[1:-1]

  def score(t):
    lo, hi = x[x < t], x[x >= t]
    if len(lo) == 0 or len(hi) == 0:
      return -1.0
    return len(lo) * len(hi) * (lo.mean() - hi.mean()) ** 2

  return float(max(candidates, key=score))


# Expects a matrix read with sc.read_10x_mtx(..., gex_only=False). Returns the antibody
# (ADT) features as a new AnnData with plain marker names (CD8a, CD103, ...); hashtags and
# genes are left out.
def extract_adt(adata: ad.AnnData) -> ad.AnnData:
  is_adt = (adata.var["feature_types"] == "Antibody Capture") & adata.var_names.str.contains("ADT")
  adata_adt = adata[:, is_adt].copy()
  adata_adt.var_names = [_clean_adt_name(v) for v in adata_adt.var_names]
  return adata_adt


# Log-transforms the antibody counts, calls each
# marker positive or negative with a threshold set separately for each sample, and
# assigns cell types from `rules` (data/adt_cell_types.csv).
#
# `rules` has columns annotation, label, then one column per marker holding '+' (at or
# above the marker's threshold), '-' (below) or blank (ignored). Each annotation becomes
# an obs column; its rows are checked top to bottom and the first matching row's label
# wins. Cells that match no row get 'unassigned'.
def annotate_adt(adata_adt: ad.AnnData, rules: pd.DataFrame) -> ad.AnnData:
  adata_adt.layers["counts"] = adata_adt.X.copy()
  X = adata_adt.X.toarray() if sp.issparse(adata_adt.X) else np.asarray(adata_adt.X)
  adata_adt.X = np.log1p(X)

  thresholds = {}
  for marker in adata_adt.var_names:
    values = np.asarray(adata_adt.obs_vector(marker), dtype=float)
    thresholds[marker] = _otsu_threshold(values)
    adata_adt.obs[f"{marker}_pos"] = values >= thresholds[marker]

  adata_adt.uns["adt_thresholds"] = thresholds

  markers = [c for c in rules.columns if c not in ("annotation", "label")]
  unknown = set(markers) - set(adata_adt.var_names)
  if unknown:
    raise ValueError(f"Markers in the cell type rules but not in the data: {sorted(unknown)}")

  for annotation, group in rules.groupby("annotation", sort=False):
    labels = np.full(adata_adt.n_obs, "unassigned", dtype=object)
    for _, rule in group.iloc[::-1].iterrows():
      match = np.ones(adata_adt.n_obs, dtype=bool)
      for marker in markers:
        state = str(rule[marker]).strip() if pd.notna(rule[marker]) else ""
        if state == "+":
          match &= adata_adt.obs[f"{marker}_pos"].to_numpy()
        elif state == "-":
          match &= ~adata_adt.obs[f"{marker}_pos"].to_numpy()
      labels[match] = rule["label"]
    adata_adt.obs[annotation] = pd.Categorical(labels)
  return adata_adt
