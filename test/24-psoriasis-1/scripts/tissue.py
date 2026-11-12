import re

import anndata as ad
import numpy as np
import pandas as pd
import scipy.sparse as sp

HASHTAG_RE = re.compile(r'AHH0[1-6]')

# Expects raw counts that still include the hashtag features, i.e. read with
# sc.read_10x_mtx(..., gex_only=False) and not yet normalized / log-transformed.
# `hashtags` maps hashtags to tissues per sample: a DataFrame with columns
# sample, hashtag, tissue (data/hashtags.csv).
# Adds obs['hashtag'] (winning hashtag, 'doublet' or 'negative') and obs['tissue']
# ('doublet' / 'negative' for cells that can't be demultiplexed).
# A cell is assigned to its top hashtag only if it has >= min_ratio times the counts of the runner-up.
def annotate_tissue(
  adata: ad.AnnData,
  hashtags: pd.DataFrame,
  sample_key: str = 'sample',
  min_ratio: float = 3.0,
) -> ad.AnnData:
  hashtag_tissue = {
    sample: dict(zip(group['hashtag'], group['tissue']))
    for sample, group in hashtags.groupby('sample')
  }

  hto_vars = [v for v in adata.var_names if HASHTAG_RE.search(v)]
  if not hto_vars:
    raise ValueError('No AHH0[1-6] hashtag features found; read the matrix with gex_only=False')

  counts = adata[:, hto_vars].X
  counts = counts.toarray() if sp.issparse(counts) else np.asarray(counts)
  names = np.array([HASHTAG_RE.search(v).group() for v in hto_vars])

  order = np.argsort(-counts, axis=1)
  top = counts[np.arange(len(counts)), order[:, 0]]
  second = counts[np.arange(len(counts)), order[:, 1]]

  hashtag = np.where(top >= min_ratio * second, names[order[:, 0]], 'doublet')
  hashtag = np.where(top == 0, 'negative', hashtag)

  samples = adata.obs[sample_key].astype(str).to_numpy()
  unknown = set(samples) - hashtag_tissue.keys()
  if unknown:
    raise ValueError(f'No hashtag mapping for samples: {sorted(unknown)}')

  tissue = [
    hashtag_tissue[s].get(h, 'unexpected hashtag') if h.startswith('AHH') else h
    for s, h in zip(samples, hashtag.tolist())
  ]

  adata.obs['hashtag'] = pd.Categorical(hashtag)
  adata.obs['tissue'] = pd.Categorical(tissue)
  return adata
