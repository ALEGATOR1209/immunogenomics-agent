import celltypist
import muon as mu

# Expects counts normalized to sum 10 000 on 'gex' modality
def annotate_cells(mdata: mu.MuData) -> mu.MuData:
  gex = mdata['gex']

  celltypist.annotate(
    gex,
    model='Healthy_Human_Liver.pkl',
    majority_voting=True,
  ).to_adata()

  gex.obs['cell_type'] = gex.obs['predicted_labels']

  mdata.update()
  return mdata
