import re

import anndata as ad
import numpy as np
import pandas as pd
import scipy.sparse as sp

_PSA_1_3 = {
  'AHH01': 'blood',
  'AHH02': 'blood',
  'AHH03': 'synovial fluid',
  'AHH04': 'synovial fluid',
  'AHH06': 'synovial tissue',
  'AHH05': 'skin',
}

HASHTAG_TISSUE = {
  'PSA1': _PSA_1_3,
  'PSA2': _PSA_1_3,
  'PSA3a': _PSA_1_3,
  'PSA3b': _PSA_1_3,
  'PSA4': {
    'AHH01': 'blood',
    'AHH02': 'blood',
    'AHH03': 'synovial fluid',
    'AHH04': 'synovial tissue',
    'AHH05': 'synovial tissue',
    'AHH06': 'skin',
  },
  'PSA5': {
    'AHH01': 'blood',
    'AHH02': 'blood',
    'AHH03': 'synovial fluid',
    'AHH04': 'synovial fluid',
    'AHH05': 'synovial tissue',
    'AHH06': 'synovial tissue',
  },
}

HASHTAG_RE = re.compile(r'AHH0[1-6]')

# Expects raw counts that still include the hashtag features, i.e. read with
# sc.read_10x_mtx(..., gex_only=False) and not yet normalized / log-transformed.
# Adds obs['hashtag'] (winning hashtag, 'doublet' or 'negative') and obs['tissue']
# ('doublet' / 'negative' for cells that can't be demultiplexed).
# A cell is assigned to its top hashtag only if it has >= min_ratio times the counts of the runner-up.
def annotate_tissue(adata: ad.AnnData, sample_key: str = 'sample', min_ratio: float = 3.0) -> ad.AnnData:
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
  unknown = set(samples) - HASHTAG_TISSUE.keys()
  if unknown:
    raise ValueError(f'No hashtag mapping for samples: {sorted(unknown)}')

  tissue = [
    HASHTAG_TISSUE[s].get(h, 'unexpected hashtag') if h.startswith('AHH') else h
    for s, h in zip(samples, hashtag.tolist())
  ]

  adata.obs['hashtag'] = pd.Categorical(hashtag)
  adata.obs['tissue'] = pd.Categorical(tissue)
  return adata
