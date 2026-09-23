import celltypist
import muon as mu

# Expects counts normalized to sum 10 000 on 'gex' modality
def annotate_cells(mdata: mu.MuData) -> mu.MuData:
  gex = mdata['gex']

  celltypist.annotate(
    gex,
    model='Immune_All_Low.pkl',
    majority_voting=True,
  ).to_adata()

  mdata.update()
  return mdata
