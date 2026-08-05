# Immunogenomics papers featuring AIRR-seq (TCR-seq, BCR-seq) with datasets published on GEO, chosen as candidates for training an AI agent to reproduce paper analyses/conclusions in scanpy/scirpy.

Recency target widened from "2025+ only" to "2023-2026" after an initial 2025-only pass yielded too few candidates that pass hard verification (open GEO GSE series, paired scRNA-seq + TCR and/or BCR VDJ contig files, not just gene-expression matrices). One pre-2025 item (Wu et al. 2020) is kept deliberately as an "easy mode" scaffolding item since it is scirpy's own built-in tutorial dataset — it is not subject to the recency target. Every item below was checked against its paper's own Data Availability statement, not just a secondary GEO search hit; several superficially promising candidates were rejected during research for depositing to non-GEO repositories (DDBJ/NBDC, Synapse, BioProject-only, GSA-Human) or for GEO series that turned out to be gene-expression-only despite the paper discussing TCR/BCR analysis. See fields.yaml's "verification\_confidence" field per item for residual caveats.

## Table of Contents

1. [Peripheral T cell expansion predicts tumour infiltration and clinical response](#wu2020) — Difficulty: low · Context: cancer immunotherapy · Chains: TCR-seq only, paired alpha + beta chain (10x 5' VDJ) · Year: 2020 · Scale: pilot (\<20 patients) · GEO: GSE139555
2. [A single-cell atlas reveals immune heterogeneity in anti-PD-1-treated non-small cell lung cancer](#nsclc_antipd1_atlas_2025) — Difficulty: medium · Context: cancer immunotherapy · Chains: TCR-seq only, paired alpha + beta chain (10x 5' VDJ) · Year: 2025 · Scale: atlas-scale (100+) · GEO: GSE243013
3. [Single-cell transcriptional landscape of liver transplant rejection reveals tissue persistence of clonally expanded, treatment-resistant T cells](#liver_transplant_rejection_2025) — Difficulty: low · Context: solid-organ transplant & irAE · Chains: Both TCR-seq and BCR-seq, paired alpha+beta (TCR) and hea... · Year: 2025 · Scale: pilot (\<20 patients) · GEO: GSE256141
4. [Single-cell transcriptome atlas of peripheral immune features to Omicron breakthrough infection under booster vaccination strategies](#omicron_breakthrough_2025) — Difficulty: low-to-medium · Context: infectious disease & vaccination · Chains: Both TCR-seq and BCR-seq, paired alpha+beta (TCR) and hea... · Year: 2025 · Scale: pilot (\<20 patients) · GEO: GSE248556
5. [Activated polyreactive B cells are clonally expanded in autoantibody positive and patients with recent-onset type 1 diabetes](#t1d_polyreactive_bcells_2025) — Difficulty: high · Context: autoimmune & rheumatic disease · Chains: BCR-seq only, paired heavy + light chain (10x 5' VDJ B-ce... · Year: 2025 · Scale: pilot (\<20 patients) · GEO: GSE270142
6. [Tracking clonal dynamics of CD8 T cells and immune dysregulation in progression of systemic lupus erythematosus with nephritis](#sle_nephritis_clonal_dynamics_2025) — Difficulty: medium · Context: autoimmune & rheumatic disease · Chains: Both TCR and BCR (10x 5' V(D)J), alpha/beta TCR and paire... · Year: 2025 · Scale: pilot (\<20 patients) · GEO: GSE254176
7. [Linking Skin and Joint Inflammation in Psoriatic Arthritis through Shared CD8+ T Cell Clones (preprint title: 'Clonal sharing of CD8+ T-cells links skin and joint inflammation in psoriatic arthritis')](#psa_shared_cd8_clones_2025) — Difficulty: medium-high · Context: autoimmune & rheumatic disease · Chains: TCR only (alpha/beta), 10x 5' V(D)J with feature barcoding · Year: 2025 · Scale: pilot (\<20 patients) · GEO: GSE250242, GSE250243
8. [High-throughput single-cell profiling of B cell responses following inactivated influenza vaccination in young and older adults](#influenza_bcell_aging_2023) — Difficulty: Medium · Context: infectious disease & vaccination · Chains: BCR-seq only (no TCR) · Year: 2023 · Scale: pilot (\<20 patients) · GEO: GSE175524, GSE175522, GSE175523
9. [Tracking in situ checkpoint inhibitor-bound target T cells in patients with checkpoint-induced colitis](#cpi_colitis_2024) — Difficulty: High · Context: cancer immunotherapy / immune-related adverse event (irAE... · Chains: TCR is confirmed and central to the paper · Year: 2024 · Scale: cohort (20-100 patients) · GEO: GSE189185, GSE189040, GSE189754, GSE189184, GSE190564
10. [The Plasma Cell Infiltrate Populating the Muscle Tissue of Patients with Inclusion Body Myositis Features Distinct B Cell Receptor Repertoire Properties](#ibm_muscle_bcr_2023) — Difficulty: High · Context: autoimmune & rheumatic disease (idiopathic inflammatory m... · Chains: BCR-seq only, heavy chain (IGH) only in the newly generat... · Year: 2023 · Scale: pilot (\<20 patients) · GEO: GSE227124

---

<a name="wu2020"></a>
## Peripheral T cell expansion predicts tumour infiltration and clinical response

### Basic Info

- **Title**: Peripheral T cell expansion predicts tumour infiltration and clinical response
- **Authors**: Thomas D. Wu, Shravan Madireddi, Patricia E. de Almeida, ... Richard Bourgon, Jane L. Grogan (corresponding, Genentech Inc.)
- **Journal**: Nature
- **Year**: 2020
- **Pmid Doi**: PMID: 32103181; DOI: 10.1038/s41586-020-2056-8 (Nature 579, 274-278)
- **Geo Accession**: GSE139555 (single flat series, 32 GSMs, GSM4143655-GSM4143686)

### Assay Type

- **Chain Coverage**: TCR-seq only, paired alpha + beta chain (10x 5' VDJ); no BCR component
- **Single Cell Technology**: 10x Genomics Chromium 5' single-cell RNA-seq paired with TCR V(D)J libraries, processed with Cell Ranger
- **Paired Gex**: Yes - each of the 32 samples (tumor/normal-adjacent/blood across lung, esophageal, colorectal and renal cancer, 14 patients) has a matched GEX (barcodes/genes/matrix) and TCR (filtered\_contig\_annotations) file pair from the same Cell Ranger run, sharing cell barcodes

### Reproducibility with scirpy

- **Data Format**: Directly scirpy-compatible, confirmed by inspecting individual GSM supplementary files (not just the series-level summary, which is misleading - see pitfalls). Every one of the 32 GSMs (e.g. GSM4143655\_SAM24345862-lt1.\*) carries four files: barcodes.tsv.gz, genes.tsv.gz, matrix.mtx.gz (standard Cell Ranger count output, loadable with sc.read\_10x\_mtx) AND filtered\_contig\_annotations.csv.gz (standard Cell Ranger vdj output with the full 10x contig schema: barcode, is\_cell, contig\_id, chain, v\_gene/d\_gene/j\_gene/c\_gene, cdr3/cdr3\_nt, reads, umis, raw\_clonotype\_id) - directly loadable with scirpy.io.read\_10x\_vdj. Verified by downloading and inspecting GSM4143655's filtered\_contig\_annotations.csv.gz directly (real TCR contig rows, not a placeholder or stripped table). Separately, scirpy also ships a fully pre-processed, pre-integrated version of this same dataset as a one-line pooch-downloaded MuData via scirpy.datasets.wu2020(), bypassing GEO/file-loading entirely.
- **Vdj Gex Pairing Completeness**: Full 1:1 pairing for all 32 deposited samples - every sample that has a GEX matrix also has a matched filtered\_contig\_annotations.csv sharing the same cell barcodes. Note: only T-cell-relevant sorted populations were VDJ-sequenced (this is the whole point of the dataset), so there is no 'unpaired GEX-only' arm to worry about within the deposited 32 samples themselves; the paper's separate CD45+ non-T-cell populations (cd45\_nont\_integrated.rds referenced at series level) are a distinct, non-VDJ dataset not part of these 32 GSMs.
- **Geo Series Structure**: Flat single GSE (no SuperSeries/subseries), 32 GSMs = tumor (T) / normal-adjacent (N) / blood (B) samples across 14 patients and 4 cancer types (lung, esophageal, colorectal, renal), so an agent needs only one accession and can iterate its GSM list directly.
- **Existing Tutorials**: Extensive - this is scirpy's own official, actively maintained tutorial dataset ('Analysis of 3k T cells from cancer' and a 140k-cell full version at scirpy.scverse.org/en/latest/tutorials/tutorial\_3k\_tcr.html), plus a dedicated analysis notebook in the scirpy paper's companion repo (icbi-lab.github.io/scirpy-paper/wu2020.html) covering QC, clustering, clonal expansion, and V gene usage on this exact dataset.
- **Reconstruction Difficulty**: low - both a fully scirpy-native path (scirpy.datasets.wu2020(), zero file handling) and a genuine from-raw-GEO-files path (sc.read\_10x\_mtx + scirpy.io.read\_10x\_vdj per GSM, join by patient/tissue) are available and give the same underlying data. This is the easiest item in the set precisely because someone (Genentech + scirpy maintainers) already did the awkward reformatting work; an agent mainly needs to handle 32 small per-sample downloads and merge on patient/region metadata parsed from GSM titles (e.g. 'LT1' = Lung Tumor patient 1).

### Biological System

- **Disease Context Category**: cancer immunotherapy
- **Disease Tissue**: Multiple solid tumors (lung adenocarcinoma, esophageal, colorectal, renal cell carcinoma) - matched tumor, normal-adjacent tissue, and peripheral blood
- **Species**: human
- **Cohort Scale Tier**: pilot (\<20 patients)

### Key Analyses & Findings

- **Clonal Expansion**: Yes, and it is the paper's central finding: clonotype expansion (cells sharing an identical TCR) was quantified per tissue compartment (tumor, normal-adjacent tissue, blood) and per cell state, showing expansion of effector-like T cell clonotypes is not confined to the tumor but detectable in normal-adjacent tissue and blood - directly reproducible from the deposited contig files by counting cells per raw\_clonotype\_id per sample.
- **Clonotype Phenotype Mapping**: Yes - expanded clonotypes were mapped onto transcriptionally defined T cell states/clusters (effector-like vs. exhausted vs. naive/memory) to characterize which phenotypes carry the expansion signal and to derive a 'T cell expansion' gene signature associated with clinical response to anti-PD-L1 therapy.
- **Isotype Shm**: Not applicable - TCR-only dataset, no BCR/isotype/SHM component.
- **Disease Specific Conclusion**: Headline conclusion: T cell clonotypes that are expanded in the tumor are also detectable and expanded in matched normal-adjacent tissue and peripheral blood, and patients whose tumors carry a gene-expression signature of this clonotypic expansion respond better to anti-PD-L1 (checkpoint blockade) therapy - i.e., peripheral/normal-tissue T cell expansion is a proxy for productive anti-tumor immunity and a candidate biomarker for immunotherapy response. This conclusion (clonotype sharing and expansion magnitude across tumor/NAT/blood compartments, and its correlation with T cell phenotype) is directly reproducible from the deposited per-sample GEX + TCR contig files; only the treatment-response correlation itself additionally requires the clinical outcome labels from the paper's supplementary tables.

### Lab Suitability

- **Pitfalls**: (1) The GEO series-level summary page (and superficial GEO2R inspection) can look like GEX-only data because the top of the series page foregrounds the large series-level RDS/metadata.txt files - the per-sample filtered\_contig\_annotations.csv.gz files only show up when a specific GSM page is opened, so an agent (or an automated tool) skimming only the series page could wrongly conclude no VDJ data exists; (2) truly raw (unaligned) fastq reads are NOT on GEO at all - they are split across two EGA controlled-access studies (EGAS00001003993 scRNA-seq, EGAS00001003994 scTCR-seq) requiring a Data Access Committee request, so any exercise must work from the already-Cell-Ranger-processed GEO files, not raw reads; (3) sample naming (LT1/LN1/LB6/ET1/EN1/CT1/CN1/RT1/RN1/RB1, etc.) encodes cancer type + tissue region + patient number and must be parsed correctly to reconstruct the tumor/normal/blood/patient design; (4) linking clonotype-expansion findings to clinical response additionally needs outcome metadata from the paper's supplementary tables, which is not in GEO.
- **Compute Needs**: Modest - 32 small samples (a few thousand to ~tens of thousands of cells each), fully laptop-feasible in scanpy/scirpy; this is explicitly scirpy's own training-scale dataset (a 3k-cell downsampled version is shipped for exactly this reason, with a 140k-cell full version also available).
- **Repo Pipeline Fit**: Excellent fit for this repo's pytcr-data-loading -\> pytcr-preprocess -\> pytcr-clonotype-clustering -\> downstream scirpy chain, either via the turnkey scirpy.datasets.wu2020() loader (for a zero-friction first exercise) or via genuine per-GSM sc.read\_10x\_mtx + scirpy.io.read\_10x\_vdj loading (for a slightly more realistic 'load real GEO files' version of the same exercise) - this is exactly why it is retained as the baseline/first-lab scaffolding item.
- **Recommended Scope**: Full dataset (32 samples / 14 patients) - already small and pilot-scale, no reduction needed. If an even lighter version is wanted for a single class session, a natural subset is the 6 lung-cancer patients only (LT1-6/LN1-6/LB6, 13 of the 32 samples), which alone reproduces the tumor-vs-normal-vs-blood clonotype-sharing/expansion finding without needing the other three cancer types.

### Licensing & Data Access

- **Repository Tier**: GEO (open) for processed per-sample GEX + TCR contig files and series-level integrated objects; EGA (controlled-access, application required) for raw fastq reads only
- **Access Class**: Fully open for everything a scirpy exercise needs (processed matrix + contig files); raw reads require an EGA Data Access Committee application, but that is not needed to reproduce the paper's repertoire analyses
- **Verification Confidence**: confirmed (GEO series page and multiple individual GSM pages checked directly; filtered\_contig\_annotations.csv.gz for GSM4143655 downloaded and its contents inspected to confirm standard Cell Ranger VDJ schema)
- **Publication Vintage**: Peer-reviewed and published (Nature, 2020); full-text is paywalled on nature.com without institutional access, but the GEO data and abstract are freely accessible

### Flagged as Uncertain

- vdj\_gene\_usage (paper's emphasis on V/J gene usage bias not confirmed from full text; abstract/secondary sources describe clonotype expansion/sharing as the core repertoire metric, not gene usage)
- diversity\_metrics (no confirmed named diversity index such as Shannon/Simpson found in secondary sources; core metric is per-clonotype expansion size and cross-tissue sharing)
- cohort\_size (exact per-cancer-type patient breakdown and total post-QC cell count taken from scirpy documentation and secondary sources, not independently recomputed from the raw files)

---

<a name="nsclc_antipd1_atlas_2025"></a>
## A single-cell atlas reveals immune heterogeneity in anti-PD-1-treated non-small cell lung cancer

### Basic Info

- **Title**: A single-cell atlas reveals immune heterogeneity in anti-PD-1-treated non-small cell lung cancer
- **Authors**: Liu Z, Yang Z, Wu J, ... Chen C, Gao S, Zhang Z (corresponding, BIOPIC, Peking University / Chongqing Medical University)
- **Journal**: Cell
- **Year**: 2025
- **Pmid Doi**: PMID: 40147443; DOI: 10.1016/j.cell.2025.03.018 (Cell 188(11):3081-3096.e19)
- **Geo Accession**: GSE243013 (single flat series, 243 GSMs, GSM7777207-GSM7777449 with gaps, coded P1-P595)

### Assay Type

- **Chain Coverage**: TCR-seq only, paired alpha + beta chain (10x 5' VDJ); no BCR/VDJ-B component (B cells were profiled transcriptionally only, no BCR sequencing)
- **Single Cell Technology**: 10x Genomics 5' single-cell RNA-seq with paired TCR V(D)J libraries, standard Cell Ranger vdj processing
- **Paired Gex**: Partially confirmed - each sample code (P1...P595) has its own per-sample TCR contig archive (GSM\<id\>\_P\<n\>\_TCR.tar.gz), and GEX is deposited as one large combined series-level matrix (GSE243013\_NSCLC\_immune\_scRNA\_counts.mtx.gz, 6.6 GB) plus a combined metadata.csv.gz - so pairing is real but must be reconstructed by joining the TCR tar's contigs' cell barcodes back to the combined GEX matrix using sample/patient IDs in the metadata table, not by simply reading matched per-GSM GEX+TCR file pairs the way GSE139555 or GSE256141 allow [uncertain: whether every one of the 234 patients' samples in the combined GEX matrix has a corresponding TCR tar, or only a subset - 249 TCR archives were counted for a stated cohort of 234 patients, so coverage looks close to complete but not verified 1:1]

### Reproducibility with scirpy

- **Data Format**: Directly scirpy-compatible for the TCR side, confirmed by downloading and extracting a per-sample TCR archive (GSM7777207\_P1\_TCR.tar.gz): it unpacks to P1\_TCR/{all\_contig\_annotations.csv.gz, filtered\_contig\_annotations.csv.gz, consensus\_annotations.csv.gz} - the exact standard Cell Ranger vdj output triplet, with the full 10x schema (barcode, chain, v\_gene/d\_gene/j\_gene, cdr3/cdr3\_nt, raw\_clonotype\_id, etc.), directly loadable with scirpy.io.read\_10x\_vdj per sample. The GEX side is NOT per-sample Cell Ranger count output - it is one pre-merged, already-integrated series-level sparse matrix (counts.mtx.gz + barcodes.csv.gz + genes.csv.gz + a metadata.csv.gz carrying cluster/cell-type/sample annotations), so an agent must subset this combined matrix by sample/patient rather than load discrete per-sample count matrices.
- **Geo Series Structure**: Flat single GSE (no SuperSeries/subseries) but with an unusual internal split (243 GSMs for TCR archives + separate series-level supplementary files for combined GEX/metadata/UMAP/NMF results that are not attached to any individual GSM), so an agent needs only one accession but must understand that GEX and TCR live at different granularities within it, and must download/parse a 500MB+ RAW.tar plus a \>6GB combined GEX matrix rather than small per-sample files.
- **Existing Tutorials**: None found - this is a 2025 paper with no known scirpy/Python tutorial; the authors' own code (if released) is presumably R/Python custom analysis scripts specific to the paper, not a general-purpose walkthrough.
- **Reconstruction Difficulty**: medium - the TCR side is genuinely easy (standard contig files, scirpy.io.read\_10x\_vdj works directly), but the combined/pre-merged GEX matrix (6.6 GB, no per-sample split) is a real engineering hurdle: it requires memory-careful subsetting by sample before any per-patient analysis, and correctly mapping ~249 TCR archives' sample codes onto the metadata table's patient/response (MPR/non-MPR) labels, which are not exposed in the GSM characteristics fields at all (GSM pages show only 'tissue: lung' / 'disease state: NSCLC', no patient ID or MPR status) - clinical-outcome linkage for the paper's central conclusion (TIME subtypes vs. MPR) requires pulling patient metadata from the paper's supplementary tables, not GEO alone.

### Biological System

- **Disease Context Category**: cancer immunotherapy
- **Disease Tissue**: Non-small cell lung cancer (NSCLC), surgically resected tumor tissue post-neoadjuvant chemo-immunotherapy (anti-PD-1 + chemotherapy)
- **Species**: human
- **Cohort Scale Tier**: atlas-scale (100+)

### Key Analyses & Findings

- **Clonal Expansion**: Yes, and it is a core analysis: CD8+ T cell clonal expansion was quantified per sample/patient (expanded clonotype defined by a minimum shared-cell threshold per TCR clonotype), and expansion patterns were compared between major pathological response (MPR) and non-MPR patients as part of characterizing the five tumor immune microenvironment (TIME) subtypes. Reproducible from the deposited contig files by counting cells per raw\_clonotype\_id per sample.
- **Clonotype Phenotype Mapping**: Yes - expanded T cell clonotypes were mapped onto transcriptionally defined T cell states (e.g. progenitor-exhausted vs. terminally-exhausted CD8+ T cells expressing ENTPD1, used as a proxy for tumor-antigen specificity) to link clonal expansion patterns to functional/exhaustion phenotypes and to the five TIME subtypes (TIME-NK, TIME-BE, TIME-Teff, TIME-Treg, TIME-Mye).
- **Isotype Shm**: Not applicable - TCR-only dataset (no BCR sequencing was performed; B cells are analyzed transcriptionally only, e.g. 'TIME-BE' memory B cell / tertiary lymphoid structure subtype).
- **Disease Specific Conclusion**: Headline conclusion: post-neoadjuvant anti-PD-1 NSCLC tumors segregate into five distinct tumor immune microenvironment (TIME) subtypes with different response/recurrence profiles - MPR (major pathological response) patients are enriched for FGFBP2+ NK/NK-like cells, memory B cells, or effector T cells, while non-MPR patients show elevated CCR8+ Tregs; additionally, abundance of progenitor-exhausted CD8+ T cells predicts reduced recurrence risk even among patients with incomplete pathological response. The clonal-expansion and clonotype-phenotype-mapping components of this conclusion are reproducible from the deposited GEX + TCR data; the MPR/non-MPR and recurrence outcome labels needed to test the TIME-subtype-vs-response link are not present in GEO's GSM metadata and must be sourced from the paper's supplementary clinical tables.

### Lab Suitability

- **Pitfalls**: (1) GEO GSM-level characteristics are minimal (only 'tissue: lung' and 'disease state: NSCLC' - no patient ID, treatment response, or timepoint), so linking any TCR/expression finding to the paper's clinical conclusions (MPR vs non-MPR, recurrence) requires the paper's own supplementary tables, not GEO metadata; (2) the combined 6.6 GB GEX matrix (not split per sample) means naive full-matrix loading is memory-heavy - subsetting strategy must be planned before loading; (3) TCR data is delivered as 249 small per-sample tar.gz archives inside one large RAW.tar (516 MB), requiring batch-extraction and per-sample looping rather than a single clean load; (4) full text of the paper is not freely accessible (Cell/ScienceDirect paywalled, no PMC deposit found at time of research), so several methodological details (software versions, exact expansion thresholds, diversity metrics if any) could not be independently verified beyond the abstract and press coverage.
- **Compute Needs**: Moderate-to-high given atlas scale (234 patients, multi-hundred-thousand cells, 6.6 GB combined GEX matrix) - not laptop-trivial like the pilot-scale items in this set; a full-cohort exercise needs a machine with sufficient RAM to hold/subset the combined matrix, though the TCR side alone (per-sample contig files, a few hundred KB-7 MB each) is lightweight.
- **Repo Pipeline Fit**: Good fit for pytcr-data-loading -\> pytcr-preprocess -\> pytcr-clonotype-clustering once the GEX-subsetting-by-sample step is handled (this is a slightly more advanced 'real-world messy data' exercise than GSE139555/GSE256141, since it forces agents to reconstruct per-sample AnnData objects from a combined matrix before scirpy can operate on typical MuData GEX+airr modality pairs).
- **Recommended Scope**: Reduced scope recommended: subset to a handful of patients (e.g. 5-10) spanning both MPR and non-MPR outcomes, selected via the paper's supplementary clinical table, rather than attempting the full 234-patient/249-sample cohort - this preserves the reproducible core (clonal expansion quantification + clonotype-phenotype/exhaustion mapping, and qualitatively contrasting MPR vs non-MPR expansion patterns) while cutting both the multi-GB combined-matrix subsetting burden and the 249-archive batch-extraction overhead down to a laptop-feasible size. Full TIME-subtype reproduction (all five subtypes, cohort-level MPR association testing) genuinely needs the full cohort and should be scoped out of a training task.

### Licensing & Data Access

- **Access Class**: Fully open for all GEO-deposited processed files (GEX matrix, metadata, TCR contig archives) - no application or embargo found for the GEO deposit itself
- **Verification Confidence**: confirmed for GEO file structure and TCR contig format (series and GSM pages checked directly, one TCR archive downloaded and extracted to confirm genuine filtered\_contig\_annotations.csv.gz/all\_contig\_annotations.csv.gz content); needs-verification for several paper-level methodological details (V gene usage, diversity metrics, exact expansion threshold, NGDC raw-data accession) since full text was not accessible
- **Publication Vintage**: Peer-reviewed and published (Cell, May 2025); full text is paywalled (ScienceDirect/Cell.com returned 403 without subscription access; no PMC deposit found), though the abstract, press release, and GEO data are open

### Flagged as Uncertain

- vdj\_gex\_pairing\_completeness (whether all 249 TCR archives map 1:1 onto distinct patients/samples in the combined GEX metadata, given P-codes running up to P595 for 234 patients, not independently verified)
- cohort\_size (exact total single-cell count across the atlas not independently confirmed)
- vdj\_gene\_usage (not confirmed present or absent as an analysis; full text inaccessible)
- diversity\_metrics (not confirmed present or absent as an analysis; full text inaccessible)
- repository\_tier (NGDC/GSA raw-data accession mentioned by GEO's own submission note but not independently located or confirmed)

---

<a name="liver_transplant_rejection_2025"></a>
## Single-cell transcriptional landscape of liver transplant rejection reveals tissue persistence of clonally expanded, treatment-resistant T cells

### Basic Info

- **Title**: Single-cell transcriptional landscape of liver transplant rejection reveals tissue persistence of clonally expanded, treatment-resistant T cells
- **Authors**: Peters AL, DePasquale EAK, Begum G, Roskin KM, Kotliar M, Barski A, Salomonis N, Shi T, Ranganathan S, Woodle ES, Hildeman DA (corresponding, Cincinnati Children's Hospital Medical Center) - full 11-author list as extracted from the PMC record
- **Journal**: American Journal of Transplantation
- **Year**: 2025
- **Pmid Doi**: PMID: 40812614; DOI: 10.1016/j.ajt.2025.08.004
- **Geo Accession**: GSE256141 (single flat series, 90 GSMs, GSM8086297-GSM8086386)

### Assay Type

- **Chain Coverage**: Both TCR-seq and BCR-seq, paired alpha+beta (TCR) and heavy+light (BCR) chains, both via 10x 5' VDJ
- **Single Cell Technology**: 10x Genomics Chromium 5' single-cell RNA-seq with paired TCR V(D)J and BCR V(D)J libraries per biopsy, Cell Ranger v6.0.0 (counts + vdj functions)
- **Paired Gex**: Yes - each of the 30 cryopreserved liver biopsies has matched GEX, TCR, and BCR libraries (3 GSMs per biopsy = 90 total), confirmed directly from GEO supplementary filenames (e.g. GSM8086297\_Patient\_1\_Pre\_TXP\_GEX\_\*, GSM8086298\_...\_TCR\_\*, GSM8086299\_...\_BCR\_\*)

### Reproducibility with scirpy

- **Data Format**: Directly scirpy-compatible for both TCR and BCR, confirmed from the GEO series file listing: each biopsy has a \*\_TCR\_filtered\_contig\_annotations.csv.gz + \*\_TCR\_clonotypes.csv.gz pair and a \*\_BCR\_filtered\_contig\_annotations.csv.gz + \*\_BCR\_clonotypes.csv.gz pair (standard Cell Ranger vdj output, loadable with scirpy.io.read\_10x\_vdj), alongside standard GEX barcodes/matrix files per biopsy (loadable with sc.read\_10x\_mtx). This is the cleanest, most directly usable file structure of the four items researched in this pass.
- **Vdj Gex Pairing Completeness**: Full 1:1 pairing across all 30 biopsies for all three modalities (GEX, TCR, BCR) - 90 GSMs = 30 biopsies x 3 modalities, no partial/asymmetric coverage found; biopsies span pre-transplant (Pre-TXP), no-rejection, late acute cellular rejection (Late ACR), and post-treatment resolved timepoints, all with the same 3-modality structure.
- **Geo Series Structure**: Flat single GSE (no SuperSeries/subseries), 90 GSMs with a clear, parseable naming convention (Liver\_[Status]\_[Patient-Biopsy]\_[GEX/TCR/BCR]) - an agent needs only one accession and can programmatically group files by patient/biopsy/modality from the GSM titles alone.
- **Existing Tutorials**: None found - this is a newly published (August 2025) paper with no known scirpy/Python tutorial; the authors' own reproducibility code (if released) is not confirmed to use scirpy.
- **Reconstruction Difficulty**: low - clean per-biopsy file triplets (GEX/TCR/BCR), standard Cell Ranger schema throughout, and informative GSM titles that directly encode patient, timepoint, and rejection status make this straightforward to load and analyze in scirpy without needing to reverse-engineer sample identity or reformat any files.

### Biological System

- **Disease Context Category**: solid-organ transplant & irAE
- **Disease Tissue**: Pediatric liver transplant T cell-mediated rejection (TCMR); liver biopsy tissue (pre-transplant, no-rejection, late acute rejection, and post-treatment/resolved timepoints)
- **Species**: human
- **Cohort Size**: 14 pediatric patients; 30 cryopreserved liver biopsies (serial biopsies per patient across rejection/treatment timepoints); 10,566 total cells analyzed post-QC
- **Cohort Scale Tier**: pilot (\<20 patients)

### Key Analyses & Findings

- **Clonal Expansion**: Yes, and it is the paper's central finding: CD8+ T cell clonotypes with \>=2 (paper-defined 'expanded', CD8EXP) cells within a sample were identified, showing highly restricted TCR clonal expansion in rejecting biopsies. Directly reproducible from the deposited filtered\_contig\_annotations.csv per biopsy by counting cells per raw\_clonotype\_id.
- **Clonotype Phenotype Mapping**: Yes - expanded CD8+ clonotypes (CD8EXP) were mapped onto transcriptional programs via supervised gene-expression analysis, characterizing them as effector/'NK-like' T cells; clonotype identity and phenotype were also tracked longitudinally across serial biopsies from the same patient (pre-rejection through post-treatment) to show the same expanded clones and phenotype persist despite corticosteroid/ATG therapy.
- **Vdj Gene Usage**: Not analyzed as a headline finding - confirmed from full-text methods review: TCR/BCR characterization centered on clonotype identity, CDR3 regions, and clonal expansion/persistence/sharing rather than V/J gene segment usage bias; no specific V or J genes are reported as enriched.
- **Diversity Metrics**: Not computed - confirmed from full-text methods review: no Shannon, Simpson, or clonality-index diversity metric was reported; the paper's repertoire quantification is based on clonotype expansion counts, shared-clonotype visualization (immunarch connected barplots), and cross-sample/cross-patient clonotype-sharing heatmaps (pheatmap) rather than a formal diversity index.
- **Isotype Shm**: Partially applicable for BCR: somatic hypermutation was scored per B cell via Cell Ranger vdj immunophenotyping output, but the paper explicitly reports a negative finding - 'B cells were neither clonally expanded nor somatically hypermutated during TCMR' - i.e. SHM was measured but found to be absent/unremarkable, which is itself a reproducible (negative) result. Isotype class-switching was not analyzed.
- **Disease Specific Conclusion**: Headline conclusion: intragraft CD8+ T cell clonotypes that expand during T cell-mediated rejection (CD8EXP, effector/NK-like phenotype) persist in the liver graft across serial biopsies and survive corticosteroid + ATG (anti-thymocyte globulin) treatment even after histologic rejection resolves - i.e., standard anti-rejection therapy does not eliminate the pathogenic expanded T cell clones, which may drive long-term graft fibrosis and failure of operational tolerance. This conclusion (clonal expansion quantification, phenotype mapping, and cross-biopsy clonotype persistence) is directly and fully reproducible from the deposited per-biopsy GEX+TCR+BCR contig files.

### Lab Suitability

- **Pitfalls**: (1) Small pilot cohort (14 patients, 10,566 total cells) means per-biopsy cell counts can be quite low, so clonal expansion/diversity results may be statistically noisy at the single-biopsy level - agents should be shown the paper's own definition of 'expanded' (\>=2 cells sharing a clonotype in a sample) rather than inventing their own threshold; (2) longitudinal/serial-biopsy structure (same patient sampled at multiple rejection/treatment timepoints) requires correctly parsing the GSM title's [Status]/[Patient-Biopsy] fields to reconstruct patient trajectories, not just treating all 30 biopsies as independent samples; (3) BCR analysis in this dataset is a genuine negative result (no clonal expansion or SHM) - useful for agent-training purposes as a 'not every modality finds a signal' example, but could be mistaken for a data-loading bug if agents expect all modalities to show something.
- **Compute Needs**: Low - modest cohort (30 biopsies, ~10.5k cells total across everything), fully laptop-feasible for both GEX and VDJ analysis in scanpy/scirpy.
- **Repo Pipeline Fit**: Excellent fit for pytcr-data-loading -\> pytcr-preprocess -\> pytcr-clonotype-clustering -\> pytcr-clonotype-analysis / pytcr-repertoire-comparison, and additionally exercises the BCR side (isotype\_shm-adjacent fields, even though the paper's own finding here is negative) that TCR-only items in this set (wu2020, nsclc\_antipd1\_atlas\_2025) cannot cover. One of the strongest overall candidates in this batch given clean file structure and full modality coverage.
- **Recommended Scope**: Full dataset (14 patients / 30 biopsies) - already pilot-scale and laptop-feasible, so no reduction is needed; if a lighter version is wanted for a single class session, restrict to the serial-biopsy patients only (those with \>=2 timepoints spanning rejection and post-treatment, a subset of the 14) to preserve the paper's clonotype-persistence-across-treatment finding while dropping single-timepoint biopsies that cannot show persistence.

### Licensing & Data Access

- **Repository Tier**: GEO (open)
- **Access Class**: Fully open, no application or embargo
- **Verification Confidence**: confirmed (GEO series and multiple GSM-level supplementary file listings checked directly; full text reviewed via PMC open-access deposit, including Methods section detail on Cell Ranger version, immunarch/pheatmap usage, and diversity/SHM/V-gene-usage findings)
- **Publication Vintage**: Peer-reviewed and published (American Journal of Transplantation, August 2025); openly available on PMC (NIHMSID: NIHMS2114933) under the PMC Copyright Notice - no paywall encountered

---

<a name="omicron_breakthrough_2025"></a>
## Single-cell transcriptome atlas of peripheral immune features to Omicron breakthrough infection under booster vaccination strategies

### Basic Info

- **Title**: Single-cell transcriptome atlas of peripheral immune features to Omicron breakthrough infection under booster vaccination strategies
- **Authors**: Yuwei Zhang, Shanshan Han, Qingshuai Sun, Tao Liu, Zixuan Wen, Mingxiao Yao, Shu Zhang, Qing Duan, Xiaomei Zhang, Bo Pang, Zengqiang Kou, Xiaolin Jiang (corresponding)
- **Journal**: Frontiers in Immunology
- **Year**: 2025
- **Pmid Doi**: PMID: 39835127; DOI: 10.3389/fimmu.2024.1460442
- **Geo Accession**: GSE248556 (single flat series, 45 GSMs = 15 donors x 3 modalities, GSM7916... range)

### Assay Type

- **Chain Coverage**: Both TCR-seq and BCR-seq, paired alpha+beta (TCR) and heavy+light (BCR) chains, both via 10x 5' VDJ
- **Single Cell Technology**: 10x Genomics Chromium Next GEM Chip K, 5' Gene Expression with paired V(D)J (TCR + BCR) library construction, Cell Ranger v7.0.0
- **Paired Gex**: Yes - each of the 15 PBMC samples has matched GEX, TCR, and BCR libraries (3 GSMs per donor = 45 total), confirmed from GEO supplementary filenames (e.g. GSM7916732\_A\_LC11\_TCR.csv.gz, GSM7916747\_A\_LC11\_BCR.csv.gz plus a matched GEX matrix per donor code)

### Reproducibility with scirpy

- **Data Format**: Directly scirpy-compatible for both TCR and BCR, confirmed by downloading and inspecting GSM7916732\_A\_LC11\_TCR.csv.gz directly: despite the plain '\_TCR.csv.gz' filename (no 'contig' in the name, which could cause a filename-pattern search to miss it), the file content is a genuine, complete Cell Ranger filtered\_contig\_annotations.csv with the full standard schema (barcode, is\_cell, contig\_id, chain, v\_gene/d\_gene/j\_gene/c\_gene, cdr3/cdr3\_nt, reads, umis, raw\_clonotype\_id) - directly loadable with scirpy.io.read\_10x\_vdj once renamed/pointed to correctly. GEX is standard per-sample barcodes/features/matrix.
- **Vdj Gex Pairing Completeness**: Full 1:1 pairing across all 15 donor samples for all three modalities (GEX, TCR, BCR) - 45 GSMs = 15 donors x 3 modalities, confirmed consistent with the paper's stated cohort (9 Omicron-infected + 6 vaccinated-only donors, 15 total).
- **Geo Series Structure**: Flat single GSE (no SuperSeries/subseries), 45 GSMs with group-coded sample names (A\_LC11/12/35 = vaccinees; B\_BI.., C\_YT.., D\_BIC.., E\_BI.. = Omicron-infected subgroups by variant/booster history) - an agent needs only one accession but must learn the paper's group-letter coding (A-E) to correctly assign donors to infected vs. vaccinated-only arms and booster subgroups, since this is not spelled out plainly in GSM titles alone.
- **Existing Tutorials**: None found - this is a 2025 paper with no known scirpy/Python tutorial.
- **Reconstruction Difficulty**: low-to-medium - file content is fully scirpy-compatible (verified genuine contig-level data), but the non-standard filename ('\_TCR.csv.gz' rather than the conventional 'filtered\_contig\_annotations.csv.gz' name scirpy examples usually show) means an agent following a tutorial literally may need to pass an explicit filename argument to scirpy.io.read\_10x\_vdj rather than relying on default auto-discovery; the A-E group-letter donor coding also requires cross-referencing the paper's cohort table to correctly assign vaccinated-only vs. infected/booster-subgroup labels.

### Biological System

- **Disease Context Category**: infectious disease & vaccination
- **Disease Tissue**: SARS-CoV-2 Omicron (BA.5.2 and BF.7 sublineages) breakthrough infection under booster vaccination; peripheral blood mononuclear cells (PBMCs)
- **Species**: human
- **Cohort Size**: 15 donors total: 9 Omicron breakthrough-infected patients (sampled within 7 days of symptom onset, subgrouped by variant/booster dose) + 6 vaccinated-only controls (sampled \>1 month post-last-vaccination, no infection); 153,395 cells sequenced, 123,531 high-quality cells post-QC
- **Cohort Scale Tier**: pilot (\<20 patients)

### Key Analyses & Findings

- **Clonal Expansion**: Yes - large TCR clonal expansions were identified and shown to be concentrated in effector CD8+ T cells following breakthrough infection; directly reproducible from the deposited per-donor TCR contig files by counting cells per raw\_clonotype\_id.
- **Clonotype Phenotype Mapping**: Yes - TCR/BCR clonotypes were projected onto transcriptionally defined cell states via UMAP (using scRepertoire v1.10.1 for barcode-based clonotype-to-cluster projection), linking clonal expansion to antiviral/effector differentiation states and pseudo-time trajectories in T and B lymphocytes.
- **Vdj Gene Usage**: Yes, confirmed from full-text methods/results review with specific gene-level findings: TCR alpha chain showed high usage of TRAV1-2, TRAV3-1, TRAV29/DV5, TRAV21, TRAJ33, TRAJ20, TRAJ49 (with TRAV1-2/TRAJ33 pairing notably increased across all groups); TCR beta chain showed top usage of TRBV20-1, TRBJ2-1, TRBJ2-7. BCR showed skewing toward IGHV3-23, IGHV3-33, IGHJ4, IGKV1-39, IGKV3-20, IGLJ2, with IGHV3-23/IGHJ4 and IGKV1-39/IGKJ2 as the most frequent pairings.
- **Diversity Metrics**: Not computed - confirmed from full-text methods review: no Shannon/Simpson/clonality-index diversity metric was reported; repertoire characterization used clonal expansion counts and V/J gene usage/pairing frequencies rather than a formal diversity index.
- **Isotype Shm**: Not analyzed - confirmed from full-text review: neither isotype class-switching nor somatic hypermutation was examined for the BCR data; BCR analysis was limited to clonal expansion and V/J gene usage/pairing.
- **Disease Specific Conclusion**: Headline conclusion: Omicron breakthrough infection under booster vaccination triggers a rapid, coordinated type-I interferon response (widespread ISG expression) across immune cell types, with T and B lymphocytes showing antiviral/proinflammatory differentiation trajectories; large TCR clonal expansions concentrate in effector CD8+ T cells and BCR clonal expansions/usage skew toward specific IGHV3 family genes - indicating booster vaccination primes an effective, rapidly mobilized adaptive immune response upon Omicron breakthrough. This conclusion (clonal expansion, clonotype-phenotype mapping, and V/J gene usage bias for both TCR and BCR) is directly and fully reproducible from the deposited per-donor GEX+TCR+BCR files.

### Lab Suitability

- **Pitfalls**: (1) Per-sample TCR/BCR files are named '\<code\>\_TCR.csv.gz' / '\<code\>\_BCR.csv.gz' rather than the conventional Cell Ranger 'filtered\_contig\_annotations.csv.gz' naming, which can cause scirpy's default file-discovery helpers or naive automated pipelines to miss them even though the content is fully standard - must pass explicit filenames; (2) donor group coding (A/B/C/D/E prefixes on sample names) encodes vaccination/infection/variant/booster-dose subgroup membership that is not self-explanatory from GSM titles and must be cross-referenced against the paper's cohort table (Table 1-equivalent) to correctly split infected vs. vaccinated-only arms; (3) small, heterogeneous pilot cohort (9 infected across 2 variant subgroups + a 4th-dose subgroup, vs 6 vaccinated-only) means some subgroup comparisons rest on very few donors (as few as 2-3 per subgroup) - appropriate for qualitative reproduction of the top-line finding, not for robust statistical inference.
- **Compute Needs**: Low-to-modest - 15 donors, ~123k cells post-QC total, laptop-feasible for scanpy/scirpy analysis of both GEX and paired TCR/BCR.
- **Repo Pipeline Fit**: Very good fit for pytcr-data-loading -\> pytcr-preprocess -\> pytcr-clonotype-clustering -\> pytcr-gene-motifs (V/J gene usage is a genuine, well-documented finding here) and pytcr-clonotype-analysis; also exercises the BCR/isotype side of the pipeline (though isotype/SHM specifically were not analyzed by the original paper, so that would be an extension beyond reproducing the paper rather than reproduction itself) alongside pytcr-gex-integration for the interferon-response/pseudo-time trajectory component.
- **Recommended Scope**: Full dataset (15 donors) - already pilot-scale and laptop-feasible, so no reduction needed for compute reasons. If scoping down for time rather than compute, the core reproducible findings (TCR clonal expansion in effector CD8 T cells + TRAV1-2/TRAJ33 and BCR IGHV3-23/IGHJ4 gene usage skew) can be shown from a smaller balanced subset (e.g. 3 infected + 3 vaccinated donors) without materially weakening the qualitative conclusion, since the original cohort itself already has as few as 2-3 donors per infected subgroup.

### Licensing & Data Access

- **Repository Tier**: GEO (open)
- **Access Class**: Fully open, no application or embargo
- **Verification Confidence**: confirmed (GEO series and GSM-level supplementary file listings checked directly; one TCR file downloaded and its contents inspected to confirm genuine Cell Ranger contig-level schema despite non-standard filename; full text reviewed via open-access PMC deposit including Methods detail on Cell Ranger/scRepertoire versions and V/J gene usage findings)
- **Publication Vintage**: Peer-reviewed and published (Frontiers in Immunology, January 2025); open access under a Creative Commons Attribution License (CC BY), full text freely available on PMC (PMC11743671)

---

<a name="t1d_polyreactive_bcells_2025"></a>
## Activated polyreactive B cells are clonally expanded in autoantibody positive and patients with recent-onset type 1 diabetes

### Basic Info

- **Title**: Activated polyreactive B cells are clonally expanded in autoantibody positive and patients with recent-onset type 1 diabetes
- **Authors**: Catherine A. Nicholas, Fatima A. Tensun, Spencer A. Evans, Kevin P. Toole, Jessica E. Prendergast, Hali Broncucia, Jay R. Hesselberth, Peter A. Gottlieb, Kristen L. Wells, and Mia J. Smith (corresponding, Barbara Davis Center, University of Colorado Anschutz)
- **Journal**: Cell Reports
- **Year**: 2025
- **Pmid Doi**: PMID: 40117290; DOI: 10.1016/j.celrep.2025.115425 (Cell Reports 44(4), article 115425)
- **Geo Accession**: GSE270142 (single flat series, 48 samples, GSM8335431-GSM8335478)

### Assay Type

- **Chain Coverage**: BCR-seq only, paired heavy + light chain (10x 5' VDJ B-cell receptor); no TCR component
- **Single Cell Technology**: 10x Genomics Chromium Next GEM Single Cell 5' Kit v2 - paired GEX, BCR V(D)J, and Feature Barcode (ADT) libraries per sample
- **Paired Gex**: Yes - each of the 16 donors has matched GEX, ADT, and BCR libraries generated from the same sorted, barcoded islet-antigen-reactive/tetramer-negative B cell pool and merged at the cell-barcode level

### Reproducibility with scirpy

- **Data Format**: NOT directly scirpy-compatible. GEO supplementary files are only 10x GEX matrices (barcodes/features/matrix.mtx per sample, GSE270142\_10X-19.\*) plus already-processed R objects (raw/normalized RNA counts .rda, raw ADT .rda, SCAR-denoised ADT .rda, UMAP coordinates .csv, and a metadata.csv.gz that carries final clone/isotype/SHM calls as columns). No filtered\_contig\_annotations.csv, all\_contig\_annotations.csv, clonotypes.csv, or any other 10x VDJ contig-level file is deposited for any sample - confirmed by checking individual GSM pages (e.g. GSM8335431/2/3), which list only barcodes/features/matrix.mtx.gz and state VDJ output is not separately supplied. Raw BCR reads exist only as unaligned fastq in SRA, and the paper's own clone-calling used Cell Ranger 7.1.0 + Immcantation/Change-O (R), not a Python/scirpy path.
- **Vdj Gex Pairing Completeness**: GEX/ADT/BCR are paired 1:1 per donor for all 16 donors (5 ND, 6 AAB, 5 T1D) in the underlying experiment, but from GEO's perspective only the GEX matrices are readily usable - BCR pairing can only be recovered by trusting the pre-computed 'final\_clone'/isotype columns in metadata.csv.gz (a processed table, not raw contigs) or by re-running Cell Ranger vdj on SRA fastqs and re-joining by barcode.
- **Geo Series Structure**: Flat single GSE (no SuperSeries/subseries) with 48 GSMs = 16 donors x 3 modalities (GEX, ADT, BCR), so an agent needs only one accession, but must correctly parse the GSM title suffixes (\_GEX/\_ADT/\_BCR) to know which files belong to which modality.
- **Reconstruction Difficulty**: high - the GEX/ADT side (matrix.mtx + processed .rda/.csv) is easy to load, but any genuine BCR repertoire analysis (clonal expansion, V/J usage, isotype, SHM) either requires trusting a black-box pre-computed clone column pulled from an R object, or re-deriving contigs from scratch by installing Cell Ranger and Immcantation and running them on SRA fastq - well beyond a standard scirpy.io.read\_10x\_vdj workflow.

### Biological System

- **Disease Context Category**: autoimmune & rheumatic disease
- **Disease Tissue**: Type 1 diabetes / islet autoimmunity; peripheral blood-derived, tetramer-sorted islet-antigen-reactive (INS, GAD, IA-2) B cells
- **Species**: human
- **Cohort Size**: 16 donors total: 5 non-diabetic first-degree relatives (ND), 6 autoantibody-positive prediabetic (AAB), 5 recent-onset T1D; roughly 2,000-11,000 cells per donor post-QC across GEX/ADT/BCR
- **Cohort Scale Tier**: pilot (\<20 patients)

### Key Analyses & Findings

- **Clonal Expansion**: Yes, and it is the paper's central repertoire finding: private (single-donor) vs. public (shared across \>=2 donors) clones were called, and clonally expanded islet-reactive B cells were found almost exclusively in AAB and T1D donors, essentially absent in ND. Reproducible in principle from the deposited clone-assignment columns, but not from raw contigs (see reproducibility\_scirpy).
- **Clonotype Phenotype Mapping**: Yes - expanded/polyreactive clones were mapped onto transcriptionally defined B cell subsets/clusters (from the paired GEX/ADT data) to show altered B-cell-signaling and inflammatory gene programs in disease-associated clones.
- **Vdj Gene Usage**: Yes - heavy and light chain V gene usage was tested with odds-ratio/enrichment tests, identifying disease-enriched IGHV/IGKV or IGLV pairings (e.g. IGHV4-4, IGHV1-3) associated with higher islet-antigen reactivity in AAB/T1D.
- **Diversity Metrics**: Yes - Shannon diversity was calculated per B cell subset and donor group as part of characterizing repertoire restriction/expansion across ND vs. AAB vs. T1D.
- **Isotype Shm**: Yes, both apply and are analyzed: BCR isotype distribution (predominantly IgM in this antigen-sorted population, with isotype-switched fractions compared across groups) and somatic hypermutation frequency in heavy and light chains were both quantified and compared by disease group.
- **Disease Specific Conclusion**: Headline conclusion: islet-antigen-reactive B cells in autoantibody-positive and recent-onset T1D individuals are more clonally expanded, more polyreactive, and phenotypically activated/pro-inflammatory compared to non-diabetic relatives, with specific enriched V-gene pairings linked to islet-antigen reactivity - i.e. repertoire clonality/polyreactivity tracks disease progression toward T1D. This conclusion is reproducible in shape from the deposited processed data, but a rigorous from-scratch verification (own clone calling, own SHM/isotype calls) is not feasible without raw contig-level VDJ data.

### Lab Suitability

- **Pitfalls**: (1) No raw/filtered contig annotation files anywhere in GEO - the biggest blocker for a scirpy-first course, since scirpy.io.read\_10x\_vdj has nothing to read; (2) BCR clone/isotype/SHM calls exist only inside R .rda objects and a metadata.csv, so a Python the agent must reverse-engineer schema and semantics from an R-object dump rather than a standard file format; (3) polyreactivity findings additionally rely on independent recombinant monoclonal antibody validation experiments (wet-lab) that cannot be reproduced computationally at all; (4) ADT data required SCAR ambient-correction, an R-specific step, adding another layer to match exactly; (5) small pilot cohort (16 donors) with antigen-sorted rather than bulk B cells - unusual sampling scheme agents must understand before any diversity/clonality numbers make sense.
- **Compute Needs**: Modest for the GEX/ADT matrices alone (16 samples, a few thousand cells each, laptop-feasible in scanpy). Substantial if attempting genuine VDJ reproduction from SRA fastq: Cell Ranger vdj per sample (multi-core, tens of GB RAM, reference download) plus Immcantation/Change-O clone-calling - effectively a full secondary-analysis pipeline reimplementation, not a training-scale task.
- **Repo Pipeline Fit**: Poor fit for this repo's pytcr-data-loading -\> pytcr-preprocess -\> pytcr-clonotype-clustering scirpy chain as-is, because the entry point the pipeline assumes (10x VDJ contig files ingestible by scirpy) does not exist in this GEO deposit. Could only be used as a 'processed-data' teaching case (load metadata.csv/rda-derived clone calls directly into an AnnData and analyze downstream) rather than as a genuine data-loading exercise, or as a cautionary example of a dataset that looks scirpy-ready from its abstract but isn't from its actual GEO files.
- **Recommended Scope**: Full dataset (16 donors) - scoping down does not help here, since the blocker is structural (no raw VDJ contig files deposited for any donor, disease or comparator) rather than about sample count or accession count. If used at all, restrict to reproducing the pre-computed clone/isotype/SHM columns from metadata.csv.gz for a smaller donor subset (e.g. 2 ND + 2 AAB + 2 T1D) as a lighter version of the same table-loading-and-analysis exercise, and frame it explicitly as processed-data analysis rather than a scirpy VDJ-loading exercise.

### Licensing & Data Access

- **Repository Tier**: GEO (open)
- **Access Class**: Fully open for the deposited matrix/processed files; raw fastq (needed for true VDJ reconstruction) is in SRA, also open access, no controlled-access gate
- **Verification Confidence**: confirmed (GEO series and multiple individual GSM pages directly checked for supplementary file contents)
- **Publication Vintage**: Peer-reviewed and published (Cell Reports 2025); an earlier related preprint/companion paper by the same group covering a subset of this work appeared as 'Islet-antigen reactive B cells display a unique phenotype and BCR repertoire...' (2024, PMC11230262) - a different, earlier publication, not to be conflated with this one

### Flagged as Uncertain

- existing\_tutorials (absence of a scirpy tutorial confirmed by search, but cannot rule out an unindexed one)

---

<a name="sle_nephritis_clonal_dynamics_2025"></a>
## Tracking clonal dynamics of CD8 T cells and immune dysregulation in progression of systemic lupus erythematosus with nephritis

### Basic Info

- **Title**: Tracking clonal dynamics of CD8 T cells and immune dysregulation in progression of systemic lupus erythematosus with nephritis
- **Authors**: Seung-Jun Paek, Hye-Soon Lee, Ye Ji Lee, So-Young Bang, Dongju Kim, Bo-Kyeong Kang, Dae Jin Park, Young Bin Joo, Mimi Kim, Hyunsung Kim, Sung Yul Park, Woong-Yang Park, Tatsuki Abe, Takahiro Itamiya, Yasuo Nagafuchi, Kazuyoshi Ishigaki, Keishi Fujio, Kyu-Tae Kim, and Sang-Cheol Bae (corresponding)
- **Journal**: Experimental & Molecular Medicine
- **Year**: 2025
- **Pmid Doi**: PMID: 40744996; DOI: 10.1038/s12276-025-01504-2 (Exp Mol Med 57(8):1700-1710)
- **Geo Accession**: GSE254176 (single flat series, 'Dynamic changes of immune cells in systemic lupus erythematosus with nephritis using longitudinal peripheral blood single-cell RNA-seq'; healthy-donor comparator drawn from the external Asian Immune Diversity Atlas, not deposited under this accession)

### Assay Type

- **Chain Coverage**: Both TCR and BCR (10x 5' V(D)J), alpha/beta TCR and paired heavy/light BCR; the paper's own repertoire analysis and headline conclusion use only the TCR side (CD8 T cell clonality) - BCR contigs are deposited but not analyzed in the published figures
- **Single Cell Technology**: 10x Genomics Chromium 5' with Single Cell Human TCR and BCR Amplification Kits (nested-PCR V(D)J enrichment), paired with 5' gene expression
- **Paired Gex**: Yes for the SLE patient cohort - each longitudinal PBMC timepoint has matched GEX + TCR + BCR libraries (one GSM per modality per timepoint). The 32 healthy-donor comparator samples are NOT part of this pairing; they come from the separate AIDA resource and are not deposited in this GSE.

### Reproducibility with scirpy

- **Data Format**: Directly scirpy-compatible for the SLE-patient arm. Confirmed by inspecting individual GSM pages: TCR samples deposit a real 10x Cell Ranger output, e.g. GSM8035500 ('Patient 4, timepoint 5, scTCR-seq') supplies '...\_filtered\_contig\_annotations.csv.gz', and BCR samples similarly, e.g. GSM8035520 ('Patient 4, timepoint 6, scBCR-seq') supplies '...\_BCR\_filtered\_contig\_annotations.csv.gz'. GEX samples deposit standard barcodes/features/matrix.mtx.gz triplets (e.g. GSM8035468). This is exactly the file scirpy.io.read\_10x\_vdj expects, no reverse-engineering needed.
- **Vdj Gex Pairing Completeness**: Complete and symmetric within the SLE patient arm: 6 patients x 19 longitudinal timepoints, each timepoint has GEX + TCR + BCR (57 total GSMs, near-1:1 across modalities, with at most one or two missing per the series sample count). However, pairing is fundamentally ASYMMETRIC at the cohort level: the 32 healthy control donors referenced in the paper's summary as the reference/baseline population are not sequenced or deposited in this GEO record at all - they are pulled from the external Asian Immune Diversity Atlas (AIDA), a separate resource with its own access terms and processing pipeline. An agent reproducing group-level comparisons (SLE vs. healthy) cannot do so from GSE254176 alone.
- **Geo Series Structure**: Flat single GSE (not a SuperSeries) with 57 GSMs covering all three modalities for the SLE patient longitudinal cohort - one accession is sufficient for the patient-only repertoire analysis, but the paper's full patient-vs-healthy comparison requires separately locating and accessing AIDA data, which is a materially different retrieval task.
- **Existing Tutorials**: No scirpy-specific tutorial found. Paper's data/code availability states custom analysis code is 'available from the corresponding authors upon request' - no public GitHub repo identified.
- **Reconstruction Difficulty**: medium - loading and running a standard scirpy clonal-expansion/diversity pipeline on the SLE longitudinal cohort alone is straightforward given properly formatted contig files, but reproducing the paper's actual comparative conclusion (flare vs. remission vs. healthy) requires obtaining and harmonizing the external AIDA healthy-control dataset, which adds real friction and a second access process.

### Biological System

- **Disease Context Category**: autoimmune & rheumatic disease
- **Disease Tissue**: Systemic lupus erythematosus with lupus nephritis; peripheral blood mononuclear cells
- **Species**: human
- **Cohort Size**: 6 SLE patients sampled longitudinally (19 timepoints total, before/after 6 flare episodes) in the GEO-deposited cohort; paper additionally cites 32 healthy donors (external AIDA, not in this GEO record) plus separate external validation cohorts (62 SLE + 79 controls bulk RNA/TCR; 162 SLE + 99 controls scRNA-seq) not deposited here either
- **Cohort Scale Tier**: pilot (\<20 patients) for the GEO-deposited scRNA/TCR/BCR cohort itself

### Key Analyses & Findings

- **Clonal Expansion**: Yes, and it is the paper's central analysis: TCR clonotypes with \>=2-fold increase in size during flare, or newly appearing at flare vs. absent at baseline, were classified as 'expanded' and tracked per patient across the longitudinal timepoints. Directly reproducible from the deposited filtered\_contig\_annotations.csv files with a standard scirpy clonal-expansion workflow.
- **Clonotype Phenotype Mapping**: Yes - expanded CD8 T cell clonotypes were tracked across transcriptionally defined subsets (naive to effector-memory transitions) and correlated with cytotoxicity and interferon-signature gene expression, i.e. clonotype identity was mapped onto GEX-derived cell states within the same patients/timepoints.
- **Vdj Gene Usage**: Not reported as a distinct analysis in the paper - no V/D/J gene usage bias/enrichment figures were described; this is not a headline component of the study.
- **Diversity Metrics**: Yes - Shannon entropy was used to quantify TCR diversity per timepoint, showing reduced diversity (repertoire restriction) during flares; Morisita-Horn similarity was also used to measure repertoire overlap between groups/timepoints. Both are standard scirpy-supported metrics.
- **Isotype Shm**: Not applicable as a headline analysis - although BCR V(D)J was also sequenced and deposited, the published paper's repertoire analysis and conclusions focus exclusively on the TCR/CD8 T cell compartment; no isotype-switching or SHM analysis of the BCR data is presented in the paper (this would be an unpublished extension an agent could attempt independently since BCR contigs are present in GEO).
- **Disease Specific Conclusion**: Headline conclusion: clonal expansion of effector CD8 T cells, coupled with reduced overall TCR diversity, is a key driver of SLE flare/disease exacerbation, with expanding clonotypes acquiring heightened cytotoxicity and amplified interferon signaling - linking clonal T cell dynamics mechanistically to lupus nephritis flares. This conclusion (expansion + diversity contraction at flare, phenotype shift of expanded clones) is directly reproducible from the deposited patient-only longitudinal TCR+GEX data; only the healthy-baseline comparison arm requires external data.

### Lab Suitability

- **Pitfalls**: (1) Longitudinal, within-patient design (19 timepoints across only 6 patients) means an agent must handle a repeated-measures structure rather than a simple case/control comparison - clonotype tracking requires careful patient-ID and timepoint bookkeeping across separate contig files; (2) the paper's headline patient-vs-healthy comparison cannot be reproduced from this GEO record alone, since the 32-donor healthy baseline is external (AIDA), potentially access-gated and processed with different QC; (3) BCR data is present but essentially orphaned from the published analysis - an agent attempting to reproduce 'the paper' should not expect BCR figures to exist to check against; (4) small absolute patient count (n=6) limits statistical robustness of any reproduced group-level test, consistent with the original paper's own framing of external validation cohorts as necessary.
- **Compute Needs**: Low to moderate - 57 samples total but each is a standard 10x PBMC-scale library (tens of thousands of cells combined); scanpy/scirpy analysis is feasible on a laptop or modest single-node compute; no need to run Cell Ranger since contig-level files are already deposited.
- **Repo Pipeline Fit**: Good fit for this repo's pytcr-data-loading -\> pytcr-preprocess -\> pytcr-clonotype-clustering -\> pytcr-clonotype-analysis chain: scirpy.io.read\_10x\_vdj works directly on the deposited filtered\_contig\_annotations.csv files, GEX is standard matrix format for pytcr-sc-rnaseq-preprocessing, and the paper's own key metrics (clonal expansion, Shannon diversity, Morisita-Horn overlap, clonotype-phenotype tracking) map cleanly onto pytcr-clonotype-analysis / pytcr-repertoire-comparison skills. The longitudinal/flare structure is a nice added teaching wrinkle beyond a flat case-control design.
- **Recommended Scope**: Full dataset (single accession, already scirpy-ready) needs no reduction for accession/retrieval complexity - this is the cleanest item in the batch on that axis. If compute/time-constrained, scope to 2-3 of the 6 patients spanning one full flare episode (a subset of the 19 timepoints) to keep the within-patient clonal-tracking-across-flare exercise intact while cutting runtime; note this still cannot reproduce the paper's SLE-vs-healthy comparison since the healthy arm (AIDA) isn't on this accession regardless of scope.

### Licensing & Data Access

- **Repository Tier**: GEO (open) for the deposited SLE-patient cohort; the healthy-control comparator (AIDA - Asian Immune Diversity Atlas) is a separate external resource whose access terms were not verified in this pass
- **Access Class**: Fully open for GSE254176 itself; AIDA comparator access class unverified
- **Verification Confidence**: confirmed for GSE254176 structure and file formats (GEO series and multiple individual GSM pages directly checked); needs-verification for AIDA accessibility
- **Publication Vintage**: Peer-reviewed and published (Experimental & Molecular Medicine, 2025)

### Flagged as Uncertain

- AIDA (Asian Immune Diversity Atlas) access class/terms for the healthy-control comparator - not independently verified in this research pass
- exact 57-sample modality breakdown (GEX/TCR/BCR counts may not be perfectly even at 19/19/19; one or two samples appear to be missing one modality based on GSM count arithmetic)

---

<a name="psa_shared_cd8_clones_2025"></a>
## Linking Skin and Joint Inflammation in Psoriatic Arthritis through Shared CD8+ T Cell Clones (preprint title: 'Clonal sharing of CD8+ T-cells links skin and joint inflammation in psoriatic arthritis')

### Basic Info

- **Title**: Linking Skin and Joint Inflammation in Psoriatic Arthritis through Shared CD8+ T Cell Clones (preprint title: 'Clonal sharing of CD8+ T-cells links skin and joint inflammation in psoriatic arthritis')
- **Authors**: L. Durham, F. Humby, N. Ng, R. Laddach, E. Gray, S. Ryan, K. Steel, R. Ross, G. Povoleri, R. Nuamah, K. Fung, A. M. Kallayil, P. Dhami, B. Kirkham, and L. Taams (corresponding, King's College London)
- **Journal**: Arthritis & Rheumatology
- **Year**: 2025 (online 17 Jun 2025) / 2026 (print issue)
- **Pmid Doi**: PMID: 40528683; DOI: 10.1002/art.43286
- **Geo Accession**: GSE250242 (patients PSA1-PSA4, 21 samples) and GSE250243 (patients PSA5-PSA6, 6 samples) - two co-deposited GEO series covering different patient subsets of the same study, not formally linked as a SuperSeries in GEO's metadata

### Assay Type

- **Chain Coverage**: TCR only (alpha/beta), 10x 5' V(D)J with feature barcoding; no BCR component
- **Single Cell Technology**: 10x Genomics Chromium Single Cell 5' v1.1 with feature barcoding (CSP/hashtag antibodies) and VDJ sequencing; separate spatial transcriptomics arm using the NanoString CosMx platform (1,000-plex panel) on an additional patient
- **Paired Gex**: Yes at the patient-channel level, but with an important caveat: each patient's blood/synovial-fluid/synovial-tissue/skin samples were pooled into a single 10x channel per patient using TotalSeq-C hashtag oligos (the CSP library) for tissue-of-origin demultiplexing, rather than each tissue being run as its own separate GEX+VDJ pair. GEX, CSP (hashtag), and VDJ are three separate GSM entries per patient that must be jointly demultiplexed to recover per-tissue, per-cell TCR-GEX pairing.

### Reproducibility with scirpy

- **Data Format**: Directly scirpy-compatible for the VDJ side. Confirmed via GSM inspection: GSM7976172 ('PSA3a VDJ') supplies both 'PsA-3a-clonotypes.csv.gz' and 'PsA-3a-filtered\_contig\_annotations.csv.gz' - a real Cell Ranger vdj output readable by scirpy.io.read\_10x\_vdj. GEX/CSP samples are standard 10x matrix triplets or hashtag count matrices; the CSP (hashtag) sample, e.g. GSM7976168 ('PSA2 CSP'), notes 'supplementary data files not provided' on some entries with raw data only in SRA, so hashtag demultiplexing tables may need to be regenerated from SRA fastq in some cases.
- **Vdj Gex Pairing Completeness**: Present but requires an extra demultiplexing step: because blood/SF/ST/skin were hashtagged and pooled per patient into one GEM well, an agent must first assign each cell (and by extension each clonotype-bearing barcode) to its tissue of origin using the CSP/hashtag data before any tissue-specific (skin vs. joint) repertoire comparison - the paper's central 'shared clone' analysis - can be reproduced. This is materially more involved than a simple 1:1 GEX-VDJ pairing per sample.
- **Geo Series Structure**: Two separate flat GSEs (GSE250242 for patients 1-4, GSE250243 for patients 5-6) that together comprise the full scRNA/TCR cohort; GEO does not mark them as SuperSeries/subseries of one another, so an agent must know from the paper's methods (not GEO metadata alone) that both accessions belong to the same study and need to be fetched and merged. The separate spatial transcriptomics (CosMx) data for a 7th patient is referenced in the paper but its own accession was not independently verified in this pass.
- **Existing Tutorials**: No scirpy tutorial identified. Paper's data availability points to GEO plus a supplementary methods document (docx); no GitHub repository for analysis code was found.
- **Reconstruction Difficulty**: medium-high - the VDJ files themselves are scirpy-ready, but correctly reconstructing the paper's actual comparison (skin vs. synovial fluid vs. synovial tissue vs. blood clone sharing) requires (a) pulling from two separate GEO accessions, (b) performing hashtag-based tissue demultiplexing that is not native to a standard scirpy pipeline, and (c) small per-tissue sample counts (5-6 patients, not all tissues available for every patient) that constrain what an agent can statistically reproduce.

### Biological System

- **Disease Context Category**: autoimmune & rheumatic disease
- **Disease Tissue**: Psoriatic arthritis; paired skin (psoriatic plaque), synovial tissue, synovial fluid, and peripheral blood from the same patients
- **Species**: human
- **Cohort Size**: 6 patients for scRNA-seq/TCR (PSA1-PSA6: 6 skin, 5 synovial tissue, 5 synovial fluid samples, plus matched blood for all 6); 7 patients total for the spatial transcriptomics arm (4 overlapping with the scRNA-seq cohort plus 1 additional)
- **Cohort Scale Tier**: pilot (\<20 patients)

### Key Analyses & Findings

- **Clonal Expansion**: Yes - TCR clonotype identification and frequency quantification per tissue compartment was performed and underlies the clone-sharing analysis; directly reproducible from the deposited filtered\_contig\_annotations.csv files once tissue-of-origin demultiplexing is done.
- **Clonotype Phenotype Mapping**: Yes and central to the paper: shared skin-joint CD8+ clones were mapped back onto transcriptional clusters, showing a consistent cytotoxic, tissue-resident-memory (Trm), type-17 phenotype for clones found in both compartments - this clonotype-to-transcriptional-state linkage is the paper's core mechanistic claim.
- **Vdj Gene Usage**: Not reported as a distinct analysis - no V/D/J gene usage bias/enrichment results were described in the paper; not a component of the study's conclusions.
- **Diversity Metrics**: Yes, but non-standard: the paper uses an inverse Pielou's evenness score to characterize clonal vs. polyclonal populations per tissue, rather than the more commonly reported Shannon/Simpson indices - scirpy supports Shannon/Simpson/Gini-Simpson natively but Pielou's evenness would need to be computed manually (straightforward given clone size distributions).
- **Isotype Shm**: Not applicable - TCR-only study, no BCR/isotype/SHM component.
- **Disease Specific Conclusion**: Headline conclusion: 155 CD8+ T cell clones (1,071 cells) were shared between skin and joint, comprising a median of 13% of the skin and 8% of the joint CD8+ TCR repertoire, and these shared clones display a consistent cytotoxic, type-17, tissue-resident phenotype in both compartments - supporting a model where specific CD8+ T cell clones migrate between skin and joint to propagate inflammation across both sites in PsA. This clone-sharing-with-consistent-phenotype conclusion is reproducible from the deposited VDJ+GEX data given correct hashtag-based tissue assignment, though exact overlap percentages will be sensitive to the clonotype-calling and tissue-demultiplexing choices an agent makes.

### Lab Suitability

- **Pitfalls**: (1) Two separate GEO accessions (GSE250242, GSE250243) must both be located and combined - not obvious from either accession page alone that they're companion series; (2) hashtag/CSP-based tissue-of-origin demultiplexing is a non-trivial extra preprocessing step before any skin-vs-joint comparison is possible, and is not part of a standard scirpy walkthrough; (3) very small, uneven per-tissue sample sizes (5-6 patients, not every tissue present for every patient) limit what statistical claims an agent can actually validate; (4) some CSP/hashtag GSM entries have no processed supplementary files ('not provided'), pushing agents back to raw SRA fastq and Cell Ranger for that piece; (5) the paper's spatial transcriptomics (CosMx) arm is a substantial separate analysis (AtoMx, CatsCradle) that is out of scope for a scirpy-based repertoire course and should be treated as context only, not a reproduction target.
- **Compute Needs**: Low - small cohort (6-7 patients, 27 total scRNA/VDJ/CSP samples), modest cell counts per 10x channel; standard scanpy/scirpy analysis is laptop-feasible. Only the spatial CosMx arm (not needed for the repertoire-focused conclusions) would require heavier image/spatial-analysis compute.
- **Repo Pipeline Fit**: Moderate fit for this repo's scirpy chain: pytcr-data-loading and pytcr-clonotype-clustering apply directly once contig files are fetched, and pytcr-clonotype-analysis / pytcr-repertoire-comparison map well onto the paper's clone-sharing-across-tissues design (a good real-world example of scirpy's repertoire-overlap functionality across \>2 compartments). The two-accession structure and hashtag demultiplexing step would need to be handled as an added data-loading wrinkle beyond what pytcr-data-loading currently assumes.
- **Recommended Scope**: GSE250242 alone (patients PSA1-4, 21 samples) preserves the core skin-vs-joint clone-sharing analysis and drops the need to discover and merge the second, uncross-referenced accession GSE250243 - loses 2 of 6 patients but the paper's central finding (clonal sharing between compartments with a consistent phenotype) is demonstrable with 4. The per-patient hashtag/CSP tissue-demultiplexing step is unavoidable regardless of scope, since it's inherent to how each patient's samples were pooled into one 10x channel.

### Licensing & Data Access

- **Repository Tier**: GEO (open)
- **Access Class**: Fully open for both GSE250242 and GSE250243 supplementary files; raw fastq (needed to regenerate some CSP/hashtag tables) available via SRA, also open
- **Verification Confidence**: confirmed (both GEO series and multiple individual GSM pages in each directly checked for supplementary file contents)
- **Publication Vintage**: Peer-reviewed and published (Arthritis & Rheumatology, online June 2025 / print 2026); an earlier bioRxiv preprint version exists under the title 'Clonal sharing of CD8+ T-cells links skin and joint inflammation in psoriatic arthritis' (2024.05.09.593313)

### Flagged as Uncertain

- spatial transcriptomics (CosMx) data accession/deposit location - not independently verified, likely outside GSE250242/GSE250243
- whether GSE250242 and GSE250243 are formally cross-referenced as related series in GEO metadata beyond both being cited in the same paper
- exact print issue/volume number for the 2026 Arthritis & Rheumatology issue (online-first DOI confirmed, final print pagination not verified)

---

<a name="influenza_bcell_aging_2023"></a>
## High-throughput single-cell profiling of B cell responses following inactivated influenza vaccination in young and older adults

### Basic Info

- **Title**: High-throughput single-cell profiling of B cell responses following inactivated influenza vaccination in young and older adults
- **Authors**: Meng Wang, Ruoyi Jiang, Subhasis Mohanty, Hailong Meng, Albert C. Shaw, Steven H. Kleinstein (Yale University / Yale School of Medicine; Kleinstein lab, corresponding/senior author)
- **Journal**: Aging (Impact Journals)
- **Year**: 2023
- **Pmid Doi**: PMID: 37367734; DOI: 10.18632/aging.204778
- **Geo Accession**: GSE175524 (SuperSeries) containing two SubSeries: GSE175522 (single-cell gene expression, 10x 5' scRNA-seq) and GSE175523 (single-cell BCR/VDJ-seq). The task item lists [GSE175524, GSE175523]; note the GEX subseries GSE175522 is a third accession under the same SuperSeries that is also needed to get paired transcriptomes.

### Assay Type

- **Chain Coverage**: BCR-seq only (no TCR). Heavy and light chain (paired IGH + IGK/IGL) B cell receptor sequences captured per cell via 10x 5' VDJ chemistry.
- **Single Cell Technology**: 10x Genomics 5' single-cell gene expression + V(D)J (BCR) chemistry, sequenced on Illumina NovaSeq 6000 (GPL24676); processed with Cell Ranger v3.1.0.
- **Paired Gex**: Yes, 1:1 paired at the sample/library level - each of the 12 GEX libraries (GSE175522) has a matching BCR library (GSE175523) from the same donor/timepoint (6 donors x 2 timepoints = 12 pairs), and the paper reports 90,133 B cells with both gene expression and BCR data recovered after joint QC/filtering out of 117,278 total single cells profiled.

### Reproducibility with scirpy

- **Data Format**: Raw, scirpy-compatible contig-level VDJ output IS deposited. Each BCR GSM (e.g. GSM5340846) has two supplementary files: a `*_BCRVDJ.tar.gz` archive explicitly described on GEO as containing 'Cell Ranger output files' (i.e. the standard per-sample VDJ outs directory - filtered/all\_contig\_annotations.csv, clonotypes.csv, consensus files, directly loadable via scirpy.io.read\_10x\_vdj or read\_10x\_mtx-equivalent), plus a second file `*_clone_pass_fil_airr.txt.gz` which is the Immcantation-processed, clone-called repertoire in standard AIRR-tsv format (also natively readable by scirpy.io.read\_airr). This is an unusually reproducibility-friendly combination: agents can either start from raw Cell Ranger contigs and rebuild clonotyping themselves, or start from the AIRR table with clone calls already assigned. GEX data (GSE175522) is provided both as a large pre-merged Seurat object (`GSE175522_B_cells_complete.rds.gz`, ~2.5GB, would need R/Seurat or a Python RDS reader to access) and as a `GSE175522_RAW.tar` (~477MB) that appears to hold per-sample Cell Ranger count outputs (h5/mtx-style), which is the piece scirpy/scanpy users actually want.
- **Vdj Gex Pairing Completeness**: Pairing is complete and symmetric across the whole cohort: all 6 donors x 2 timepoints (12 samples) have both a GEX library and a BCR library deposited with matching donor/timepoint naming (e.g. 120648\_0 pattern), and both arms (young and older adults, pre- and post-vaccination) are covered - there is no asymmetric or control-only pairing. The main friction is structural rather than biological: the paired GEX halves live in a separate SubSeries (GSE175522) from the BCR halves (GSE175523) under the shared SuperSeries GSE175524, so a fetch script must pull from two/three accessions and match samples by donor ID + timepoint substring in the filenames rather than by a shared GSM index.
- **Geo Series Structure**: SuperSeries/subseries structure: GSE175524 (SuperSeries, no data files of its own) -\> GSE175522 (GEX subseries) + GSE175523 (BCR subseries). This is one level more complex than a flat GSE: fetch tooling needs at least two accessions (GSE175522 and GSE175523) to reconstruct paired data, and the task's own geo\_accession list only names GSE175524 and GSE175523 - GSE175522 (the GEX half) would need to be added explicitly for `pytcr-sc-rnaseq-preprocessing`/gex-integration work, otherwise agents only get the BCR side.
- **Reconstruction Difficulty**: Medium. Strengths: cohort is small (6 donors, 12 paired samples) so runtime/memory is modest, both raw Cell Ranger VDJ contigs and pre-clone-called AIRR tables are present so agents aren't blocked on clonotyping infrastructure, and file naming cleanly encodes donor+timepoint. Sources of difficulty: (1) the SuperSeries/subseries split requires fetching from 2-3 GEO accessions instead of one; (2) the most convenient GEX artifact is a 2.5GB Seurat .rds object rather than a Python-native h5/mtx, so agents must either parse the RAW.tar Cell Ranger outputs directly (recommended) or convert the RDS via anndata2ri/sceasy; (3) reproducing the paper's headline findings (age-associated clonal expansion differences, SHM, isotype composition) requires joining VDJ clonotype calls to Seurat/Azimuth-derived B cell subtype annotations (naive/memory/activated/plasmablast), which in scirpy means re-deriving or importing a comparable phenotype annotation since the original used Azimuth, not scanpy-native clustering.

### Biological System

- **Disease Context Category**: infectious disease & vaccination
- **Disease Tissue**: Peripheral blood B cells (PBMC-derived, FACS-sorted CD19+ B cells) from healthy adults receiving inactivated seasonal influenza vaccine.
- **Species**: Homo sapiens
- **Cohort Size**: 6 donors total (3 young adults, ages 20-30; 3 older adults, ages 60-100), each sampled at 2 timepoints (day 0 pre-vaccination and day 7 post-vaccination) = 12 paired GEX+BCR libraries; 117,278 total single cells sequenced, 90,133 B cells retained with both GEX and BCR data after QC (62,197 naive, 19,319 resting memory, 6,336 activated, 1,944 plasmablasts, 337 proliferating plasmablasts).
- **Cohort Scale Tier**: pilot (\<20 patients) - 6 donors, deliberately small and deeply profiled rather than broad.

### Key Analyses & Findings

- **Clonal Expansion**: Yes, central to the paper and fully reproducible from the deposited BCR data: clone sizes were called (Immcantation-style clustering, clone\_pass\_fil files already contain clone IDs) and expanded clones were identified per donor/timepoint via Fisher's exact test comparing pre- vs. post-vaccination clone frequencies; clone-size distributions were compared between young and older adults as the paper's central quantitative comparison.
- **Clonotype Phenotype Mapping**: Yes, and it is a key result: the authors mapped each BCR clonotype/clone back to the GEX-derived cell-state annotation (naive, resting memory, activated, plasmablast, proliferating plasmablast, via Seurat/Azimuth) to show that expanded post-vaccination clones in young adults were dominated by plasmablasts, while in older adults expanded clones showed a more heterogeneous mix with a decreased proportion of plasmablasts - this clonotype-to-phenotype join is reproducible in scirpy/MuData via barcode-matched clonotype annotation onto the gex modality, though it requires re-deriving the cell-type labels since the original pipeline used Azimuth.
- **Vdj Gene Usage**: Yes, performed but secondary: heavy-chain V gene usage was analyzed and normalized against light-chain gene usage to control for compositional bias; V/D/J usage bias by age group/timepoint is reproducible from the AIRR tables but is not the paper's headline analysis.
- **Diversity Metrics**: Present but limited: the paper reports clone-size/frequency distributions and clonal expansion statistics rather than a full battery of diversity indices (e.g. no explicit Shannon/Simpson/Gini-index reporting was found) - so a scirpy diversity-metrics exercise (e.g. sc.tl.alpha\_diversity-equivalents) would extend beyond, not directly reproduce, the original figures.
- **Isotype Shm**: Yes, both are core analyses and well supported by the data: isotype/class composition was quantified per cell type and timepoint (predominantly IgG1, with IgM and IgA present), and somatic hypermutation frequency (IGHV mutation frequency via Immcantation's SHazaM) was calculated per cell type, isotype, and timepoint - notably showing higher baseline SHM and more activated B cells in older adults pre-vaccination, one of the paper's key age-related findings.
- **Disease Specific Conclusion**: Young adults mount a significantly more clonal B cell response after influenza vaccination than older adults, with post-vaccination expanded clones in young adults dominated by plasmablasts, whereas older adults show reduced clonal expansion and a more heterogeneous expanded-clone composition (fewer plasmablasts, more activated/memory B cells) despite similar per-cell gene-expression programs within matched cell types - implying a quantitative deficit (fewer/weaker expanding clones) rather than a qualitative defect in the aged humoral response, consistent with older adults' pre-existing higher baseline SHM and activated B cell abundance. This conclusion is reproducible directly from clonal expansion + clonotype-phenotype mapping on the deposited BCR+GEX data.

### Lab Suitability

- **Pitfalls**: (1) Must fetch and join two/three separate GEO accessions (GSE175522 GEX + GSE175523 BCR under SuperSeries GSE175524) and match samples by donor-ID/timepoint substrings in filenames rather than a single index. (2) The most complete GEX object is a large (~2.5GB) Seurat .rds file rather than a native Python format - the RAW.tar Cell Ranger outputs are the better path for scanpy but need to be located/extracted per sample. (3) Cell-type/phenotype labels used in the original paper come from Azimuth reference mapping in Seurat, which has no scirpy/scanpy equivalent out of the box, so reproducing clonotype-to-phenotype figures requires agents to build their own annotation (marker-gene-based or Leiden clustering + manual labeling) rather than reusing the paper's labels. (4) Small cohort (n=3 per age group) means statistical comparisons in any reproduction will be underpowered/noisy - fine for agent-training purposes but should be flagged as illustrative, not confirmatory. (5) BCR-only (no TCR) dataset, so only relevant to the BCR/isotype/SHM-focused parts of the pytcr pipeline.
- **Compute Needs**: Low to moderate. 90k cells across 12 samples is well within single-workstation scanpy/scirpy capability (a few GB RAM for the AnnData/MuData objects, no GPU required); the main resource cost is disk/download for the ~1GB combined raw tars plus the 2.5GB Seurat RDS if that path is used instead of the raw Cell Ranger tars.
- **Repo Pipeline Fit**: Good fit for the single-cell BCR side of the pipeline (pytcr-data-loading -\> pytcr-preprocess -\> pytcr-clonotype-clustering -\> pytcr-clonotype-analysis / pytcr-gex-integration), since raw Cell Ranger VDJ contig files are deposited and paired GEX exists for pytcr-sc-rnaseq-preprocessing + pytcr-gex-integration exercises. It is a BCR-only dataset, so it would not exercise TCR-specific skill content, and because the original phenotype annotation used Azimuth rather than a scanpy-native workflow, using this dataset for pytcr-gex-integration exercises means agents derive their own cell-state labels rather than reusing published ones - reasonable for teaching but worth noting in the task prompt.
- **Recommended Scope**: No reduction available below the minimum pair GSE175522 (GEX) + GSE175523 (BCR) - both subseries are required even to reconstruct a single paired sample, so the SuperSeries overhead can't be escaped by subsetting. What CAN be scoped down is the donor count: 2 donors (1 young + 1 older) x 2 timepoints = 4 sample pairs instead of the full 6-donor/12-pair cohort, keeping the day-0-vs-day-7 clonal-expansion-by-age comparison intact while cutting download size and compute roughly in half.

### Licensing & Data Access

- **Repository Tier**: GEO (open) - raw sequencing reads are also cross-deposited in SRA (BioProject PRJNA728050), fully public.
- **Access Class**: Fully open, no application or embargo. Data availability statement explicitly states deposition in GEO under GSE175524 with no stated restrictions.
- **Verification Confidence**: confirmed - GEO series structure, sample counts, supplementary file names/types, and paper details were directly verified via GEO accession pages and the PMC full text.
- **Publication Vintage**: Peer-reviewed and published (Aging, Impact Journals, June 2023; not a preprint).

### Flagged as Uncertain

- reproducibility\_scirpy.existing\_tutorials

---

<a name="cpi_colitis_2024"></a>
## Tracking in situ checkpoint inhibitor-bound target T cells in patients with checkpoint-induced colitis

### Basic Info

- **Title**: Tracking in situ checkpoint inhibitor-bound target T cells in patients with checkpoint-induced colitis
- **Authors**: Tarun Gupta, Agne Antanaviciute, Chloe Hyun-Jung Lee, Rosana Ottakandathil Babu, Anna Aulicino, Zoe Christoforidou, Paulina Siejka-Zielinska, Caitlin O'Brien-Ball, Hannah Chen, David Fawkner-Corbett, and Alison Simmons (senior/corresponding author, University of Oxford, Kennedy Institute of Rheumatology / Translational Gastroenterology Unit)
- **Journal**: Cancer Cell
- **Year**: 2024
- **Pmid Doi**: PMID: 38744246; DOI: 10.1016/j.ccell.2024.04.010; PMCID: PMC12979251; Cancer Cell 42(5):797-814.e15, published May 13, 2024
- **Geo Accession**: GSE189185 (SuperSeries, 117 samples total) with four child subseries: GSE189040 (CD3+ sorted scRNA-seq/CITE-seq/TCR, 24 samples), GSE189754 (CD45+ sorted scRNA-seq/CITE-seq, 15 samples), GSE189184 (10x Visium spatial transcriptomics, 16 samples), and GSE190564 (whole-tissue scRNA-seq/CITE-seq/TCR/BCR, 62 samples)

### Assay Type

- **Chain Coverage**: TCR is confirmed and central to the paper: alpha/beta paired TCR V(D)J data from 10x 5' Chromium, reconstructed/analyzed with TRUST4 and grouped by specificity motif with GLIPH2, used for clonal tracking between colon and blood. BCR is present in GEO but NOT used anywhere in the paper's own text: individual GSM titles inside subseries GSE190564 explicitly include '\_BCR' (e.g. 'Pool52\_Stromal\_BCR', 'Pool44\_PBMC\_BCR'), confirming BCR V(D)J libraries (heavy + light chain, presumably from the same 10x 5' immune-profiling kit that also generated the TCR libraries) were generated and deposited for that subseries. However, a full-text search of the Methods, Results, STAR Methods/key-resources table, and Data Availability statement of the paper turns up zero mentions of 'BCR', 'B cell receptor', or 'immunoglobulin sequencing' as an analyzed data type -- B cells in the paper are discussed only via gene-expression clustering (e.g. germinal-center/plasma-cell markers), never via receptor repertoire. So: BCR reads exist in GEO (confirmed by sample naming) but were not analyzed, validated, or reported by the authors -- there is no published methodology or result to check an agent's BCR analysis against. The CD45-sorted subseries GSE189754 also carries generic series-level boilerplate mentioning 'TCR and BCR sequence data', but the individual GSM records checked (GSM5706743, GSM5706745, GSM5706750, GSM5706757) all list 'chemistry: 3' chemistry', which does not support 10x V(D)J capture -- so GSE189754 in practice appears to be GEX/ADT-only despite that summary text, and any genuine TCR/BCR contig data lives specifically in GSE189040 (TCR only, CD3-sorted) and GSE190564 (TCR + BCR, whole tissue).
- **Single Cell Technology**: 10x Genomics Chromium 5' Single Cell Immune Profiling (paired GEX + CITE-seq ADT + TCR/BCR V(D)J) for GSE189040 and GSE190564; 10x Genomics 3' scRNA-seq (GEX + ADT only, no V(D)J) for GSE189754; 10x Genomics Visium spatial transcriptomics for GSE189184.
- **Paired Gex**: Yes within the 5' subseries: each sequencing pool (multiplexed via cell hashing across ~5 patients per pool) generated GEX, ADT, and TCR (and, for GSE190564, BCR) libraries from the same captured cell suspension, sharing cell barcodes so GEX and VDJ can be joined per cell after demultiplexing the hashtags. GSE189754 (CD45+ sorted) is 3'-based and has no paired VDJ data at all despite covering the same patient cohort.

### Reproducibility with scirpy

- **Data Format**: Mixed and uneven across the four subseries. GSE189040 is the cleanest entry point: its FTP directory lists per-pool GEX/ADT archives alongside separately named '\_TCR.zip' files (e.g. GSE189040\_Pool1\_TCR.zip, GSE189040\_Pool7\_TCR.zip), strongly consistent with standard Cell Ranger vdj output (filtered\_contig\_annotations.csv-equivalent) bundled per pool -- directly relevant to scirpy.io.read\_10x\_vdj, though still requires unzipping and demultiplexing by hashtag before per-patient files exist. GSE190564 and GSE189754 instead bundle everything into a single large series-level tar.gz (11.1 GB and 4.7 GB respectively); individual GSM pages for both show 'supplementary\_file: NONE', so an agent cannot fetch one clean file per sample -- they must download the whole archive and search inside it for the right pool/modality folder, with no per-GSM file index to confirm what's actually inside before doing so. GSE189184 (spatial) ships as one large GSE189184\_RAW.tar (8.7 GB) of Visium outputs, unrelated to VDJ. No fully-processed, ready-to-read filtered\_contig\_annotations.csv per sample was directly confirmed at the individual-GSM level for any subseries -- the closest confirmed match is the GSE189040 pool-level \_TCR.zip files.
- **Vdj Gex Pairing Completeness**: Partial and asymmetric across the SuperSeries. The T cell-focused arm (GSE189040) has TCR paired with GEX/ADT per pool. The whole-tissue arm (GSE190564) has both TCR and BCR paired with GEX/ADT per pool, but only for the subset of samples processed with 5' chemistry. The CD45-sorted arm (GSE189754), despite the paper needing to relate CD45+ compartment gene expression to receptor identity, was run with 3' chemistry and therefore has GEX/ADT with no matched VDJ at all -- a real gap an agent must discover rather than assume away. The spatial arm (GSE189184) has no VDJ pairing by design (Visium is not single-cell resolution). Net effect: an agent wanting VDJ+GEX pairing for T cells should use GSE189040 (T cell-focused, cleanest) or GSE190564 (broader, includes BCR, messier files), not GSE189754.
- **Geo Series Structure**: GSE189185 is the SuperSeries umbrella (117 samples) with four subseries that an agent must actually open individually, since GSE189185 itself carries no primary data of its own -- it only lists and links the four children: GSE189040 (CD3+ T cells, scRNA+CITE+TCR, 24 samples), GSE189754 (CD45+ immune cells, scRNA+CITE, 15 samples, 3' chemistry / no VDJ), GSE189184 (Visium spatial, 16 sections), and GSE190564 (whole dissociated tissue and matched PBMC, scRNA+CITE+TCR+BCR, 62 samples). An agent should start at GSE189185 to see the four-way split and the shared Data Availability language, then pick GSE189040 for a T cell-only TCR exercise (its per-pool \_TCR.zip files are the most scirpy-friendly artifact in the whole SuperSeries) or GSE190564 if they also want the BCR libraries or PBMC-vs-tissue clone tracking, and should be told explicitly to skip GSE189754's VDJ claim (it's 3' chemistry, GEX/ADT only) and to treat GSE189184 as spatial-only. This 5-accession fan-out, with per-subseries chemistry differences not obvious from the series summary text alone, is itself one of the harder parts of using this dataset.
- **Reconstruction Difficulty**: High. Contributing factors: (1) the 5-accession SuperSeries fan-out with per-subseries chemistry differences that aren't flagged clearly at the series-summary level (GSE189754's misleading 'TCR and BCR' description despite being 3'-only); (2) VDJ files are split unevenly -- clean per-pool zips in GSE189040 vs. opaque multi-GB series-level tarballs with no per-sample file index in GSE190564/GSE189754; (3) all VDJ pools are hashtag-multiplexed across ~5 patients each, so an agent must demultiplex by hashtag/CITE-seq antibody before per-patient clonotype tables exist -- scirpy's standard 10x-VDJ loading path assumes one file set per sample, not per multiplexed pool; (4) the paper's own key TCR findings (clone tracking blood\<-\>tissue, CPI-bound cell-state mapping) depend on integrating GEX + ADT (CITE-seq) + TCR + spatial simultaneously, a substantially more complex multi-modal workflow than a single-assay repertoire exercise; (5) BCR data, if an agent wants to explore it, has no paper-side ground truth to validate against at all, since the authors never analyzed it themselves.

### Biological System

- **Disease Context Category**: cancer immunotherapy / immune-related adverse event (irAE) -- checkpoint-inhibitor-induced colitis; closest fit to the schema's combined 'solid-organ transplant & irAE' bucket via the irAE component (no transplant involved)
- **Disease Tissue**: Colon (endoscopic biopsies, inflamed and non-inflamed) and peripheral blood (PBMC), comparing checkpoint-inhibitor-induced colitis (CC\_I) against checkpoint-inhibitor-treated patients without colitis (CC\_NI), active and non-inflamed idiopathic ulcerative colitis (UC\_I / UC\_NI), and healthy controls (HC); CPI patients received either anti-PD-1 monotherapy or anti-PD-1 + anti-CTLA-4 dual therapy.
- **Species**: human
- **Cohort Size**: Approximately 72 donors in total across the SuperSeries' patient groups (CPI colitis, CPI without colitis, ulcerative colitis, healthy controls), including an immunofluorescence/validation cohort of 25 CPI-colitis patients and 8 CPI-treated non-colitis controls cited in the paper text. Single-cell scale: 72,561 CD3+ cells sequenced from colon biopsies plus 36,176 paired PBMC CD3+ cells (GSE189040); 117 GSM samples/pools total across all four subseries (24 + 15 + 16 + 62).
- **Cohort Scale Tier**: cohort (20-100 patients)

### Key Analyses & Findings

- **Clonal Expansion**: Yes, and it is a genuine reproducible core finding: TCR clones were reconstructed with TRUST4 from the 5' VDJ libraries and tracked for expansion and overlap. The paper reports, for example, that ZNF683+ (tissue-resident memory-like) T cells 'were highly clonal, shared TCRs with actively proliferating T cells, but not cells from blood,' contrasted against other populations that 'showed a strong clonal overlap with T cells from blood' -- i.e. clonal-expansion and blood-vs-tissue clone-sharing analysis is central and reproducible from the deposited TCR contig data (best sourced from GSE189040's per-pool \_TCR.zip files).
- **Clonotype Phenotype Mapping**: Yes -- a core method of the paper. TCR clonotypes were mapped onto CITE-seq/GEX-defined T cell states (peripheral helper Tph, follicular helper Tfh, regulatory Treg, Th17, tissue-resident memory CD8 IFN-gamma+ cells) to show which cell states carry checkpoint-inhibitor-bound, expanded, or tissue/blood-shared clones, and GLIPH2 was additionally used to group clonotypes by predicted shared antigen specificity motifs across patients. Reproducible in principle by joining the TCR clonotype tables to the paired GEX/ADT cell annotations via shared barcodes within each hashtag-demultiplexed pool.
- **Isotype Shm**: BCR-relevant fields do not apply in a way the paper supports. As detailed in chain\_coverage, BCR V(D)J libraries appear to have been generated and deposited for subseries GSE190564 (GSM titles explicitly contain '\_BCR'), but the paper contains no isotype-switching or somatic-hypermutation analysis of any kind -- B cells are discussed only transcriptionally (e.g. inferred 'B cell help', germinal-center gene signatures), never via immunoglobulin repertoire. This resolves the item's note directly: TCR is confirmed and paper-validated; BCR data plausibly exists in GEO (per sample naming) but is entirely unconfirmed/unused in the paper's own text, so isotype/SHM analysis on this dataset would be unsupervised exploration with no ground truth from the source publication.
- **Disease Specific Conclusion**: Headline conclusion, stated in the paper: checkpoint-inhibitor colitis is driven less by direct cytotoxic damage alone and more by loss of regulatory tone -- 'perturbed regulatory cues from targeted Tregs, Tfhs, Tphs, and Th17s may play a bigger role in colitis initiation than previously thought.' Mechanistically, CPI-bound cells were predominantly CD4+ (peripheral helper, follicular helper, and regulatory T cells) that localize to distinct spatial microdomains with characteristic intercellular signaling, while IFN-gamma+ CD8+ T cells (arising from both tissue-resident and peripheral/clonally-shared populations) co-localize with damaged epithelium in microdomains that lack effective regulatory signaling. The TCR clonal-tracking data supports this by showing which of these T cell states are locally expanded versus recruited/shared from blood, i.e. the repertoire analysis alone can reproduce the blood-vs-tissue clonal dynamics part of this conclusion, though the full mechanistic claim also rests on spatial transcriptomics and CITE-seq drug-occupancy staining beyond TCR-seq.

### Lab Suitability

- **Pitfalls**: (1) Five GEO accessions with an easy-to-miss chemistry mismatch: GSE189754's series summary claims 'TCR and BCR sequence data' but its individual GSM records are all 3' chemistry (no V(D)J), which will silently waste an agent's time if they start there for repertoire work. (2) VDJ files are hashtag-multiplexed pools of ~5 patients each, requiring a demultiplexing step (matching hashtag/CITE-seq antibody barcodes to patient IDs from the characteristics fields) before per-patient clonotype tables exist -- not a plug-and-play scirpy.io.read\_10x\_vdj call. (3) GSE190564 and GSE189754 bundle all samples into single multi-GB series-level tar.gz archives with no per-GSM file index, so an agent cannot verify file contents before a large download. (4) No V/J gene usage or diversity-index results are reported in the paper to validate an agent's own computation against -- those exercises would be exploratory rather than confirmatory. (5) BCR data (GSE190564) has zero analytical precedent in the source paper -- a BCR exercise on this dataset would need entirely instructor-authored expected outputs. (6) The paper's headline conclusions depend on integrating spatial transcriptomics and CITE-seq drug-occupancy staining alongside TCR-seq, so a TCR-only reproduction can validate only part of the story (clone sharing/expansion), not the full spatial-microdomain argument.
- **Compute Needs**: Meaningful, above a minimal single-GSE teaching task. Raw processed archives alone total tens of GB across the SuperSeries (GSE189040's zips ~4GB combined, GSE189754 4.7GB, GSE190564 11.1GB, GSE189184 8.7GB), and the CD3 arm alone covers ~109,000 T cells (colon + PBMC combined) -- large enough that standard scirpy/AnnData in-memory workflows are feasible on a workstation but noticeably heavier than smaller single-GSE teaching datasets in this repo; the container's default 8GB memory cap in this repo's harness would likely need raising (MEMORY\_GB) if a task tries to load a full pool's GEX+TCR data.
- **Repo Pipeline Fit**: Reasonable but not turnkey fit for this repo's pytcr-data-loading -\> pytcr-preprocess -\> pytcr-clonotype-clustering chain if scoped to GSE189040 (CD3, TCR-only, per-pool \_TCR.zip files resembling standard Cell Ranger vdj output) -- a task could plausibly use pytcr-data-loading to ingest one demultiplexed pool. However, the hashtag-demultiplexing step needed before per-patient data exists is not something the current skill chain covers, so a task built on this dataset would need either a starter notebook that already performs demultiplexing (per this repo's pattern for narrowly-scoped tasks, e.g. 04/06/07) or an added preprocessing step not currently documented in any skill. GSE189754/GSE190564's bundled-tarball format would require extra unzip/exploration logic beyond what pytcr-data-loading currently assumes for a single clean supplementary file.
- **Recommended Scope**: GSE189040 alone (CD3+ sorted, TCR-only, 24 samples, per-pool \_TCR.zip files) preserves the paper's core TCR clonal-expansion and blood-vs-tissue clone-sharing findings while dropping GSE189754 (the misleading 3'-only no-VDJ subseries), GSE189184 (spatial, out of scope for a repertoire exercise regardless), and GSE190564 (BCR, which the paper itself never analyzed). This is the single biggest scope reduction of any item in the batch - cuts the accession count from 5 to 1 and the download footprint from tens of GB to roughly 4GB, while losing only the CITE-seq-drug-occupancy and spatial-microdomain parts of the paper's full mechanistic argument, not the repertoire-analysis core.

### Licensing & Data Access

- **Repository Tier**: GEO (open) for all five accessions (GSE189185 SuperSeries + 4 subseries); raw sequencing reads for the constituent GSMs are additionally in SRA (e.g. SRP350018 for GSE190564)
- **Access Class**: Fully open -- no dbGaP, EGA, or other controlled-access gate was found for any of the five accessions or their linked SRA/BioProject records; both processed supplementary files and raw fastq are directly downloadable without an application or embargo.
- **Verification Confidence**: confirmed (SuperSeries and all four subseries GEO pages fetched directly; multiple individual GSM records checked for chemistry, titles, and supplementary-file status; PMC full text checked directly for Data Availability, Methods, and BCR/TCR mentions)
- **Publication Vintage**: Peer-reviewed and published (Cancer Cell, May 13, 2024); GEO series made public April 12, 2024, shortly before the print publication date, consistent with a standard embargo-to-publication release.

### Flagged as Uncertain

- existing\_tutorials
- vdj\_gene\_usage
- diversity\_metrics

---

<a name="ibm_muscle_bcr_2023"></a>
## The Plasma Cell Infiltrate Populating the Muscle Tissue of Patients with Inclusion Body Myositis Features Distinct B Cell Receptor Repertoire Properties

### Basic Info

- **Title**: The Plasma Cell Infiltrate Populating the Muscle Tissue of Patients with Inclusion Body Myositis Features Distinct B Cell Receptor Repertoire Properties
- **Authors**: Ruoyi Jiang, Bhaskar Roy, Qian Wu, Subhasis Mohanty, Richard J. Nowak, Albert C. Shaw, Steven H. Kleinstein, Kevin C. O'Connor (senior/corresponding: Kevin C. O'Connor; Kleinstein and O'Connor labs, Yale University)
- **Journal**: ImmunoHorizons
- **Year**: 2023
- **Pmid Doi**: PMID: 37171806; DOI: 10.4049/immunohorizons.2200078 (ImmunoHorizons, Vol 7, Issue 5, pp. 310-322, published May 12 2023)
- **Geo Accession**: GSE227124 (single flat GSE, no subseries; it also bundles re-analyzed/re-processed data from 14 externally-hosted SRX accessions in a series-level supplementary tarball rather than as new GSMs)

### Assay Type

- **Chain Coverage**: BCR-seq only, heavy chain (IGH) only in the newly generated muscle-tissue data (V\_CALL/D\_CALL/J\_CALL and CREGION/isotype columns are all IGH; no light chain / IGK/IGL data). The bundled comparator repertoires are likewise IGH-only (e.g. Donor-155\_IGHA/IGHG/IGHM.tab, musk1/2/3.tab).
- **Single Cell Technology**: None deposited as single-cell for the disease-relevant arm. The newly generated IBM/DM/PM muscle-tissue samples (10 GSMs) are bulk BCR-seq (NEBNext Immune Sequencing Kit) on RNA extracted from frozen muscle sections. Three of the bundled comparator files (musk1.tab, musk2.tab, musk3.tab, from a prior myasthenia gravis study) carry 10x-style cell barcodes in their SEQUENCE\_ID field (e.g. 'CACAGTAGTCGTCTTC-1\_contig\_2'), indicating they originated from 10x Genomics 5' single-cell V(D)J sequencing, but as deposited in this GSE they are already flattened into Change-O/AIRR tab-delimited repertoire tables with a single pre-baked cell-type label per file, not raw 10x contig CSVs.
- **Paired Gex**: Not paired anywhere in this GEO series. I downloaded and inspected both GSE227124\_RAW.tar (the 10 new GSM .tab.gz files) and GSE227124\_airr-seq\_previously\_submitted\_samples.tar.gz (37MB, the bundled comparator data) directly from the GEO FTP. Every file in both archives is a Change-O/AIRR-format tab-delimited repertoire table (columns like V\_CALL, J\_CALL, JUNCTION, CDR3\_IMGT, CLONE, DUPCOUNT, CREGION). None contain a gene-expression/cell-by-gene matrix, and none contain raw 10x filtered\_contig\_annotations-style output. Even the single-cell-derived comparator files (musk1/2/3.tab) carry only a single fixed SUBSET value per file ('Plasma cell') rather than a queryable transcriptome. This directly overrides the framing in the task note: it is not the case that a healthy-donor arm has paired 10x scRNA+BCR data usable with scirpy for GEX pairing — no arm of GSE227124 includes any GEX data at all.

### Reproducibility with scirpy

- **Data Format**: Every sample in GSE227124, in both the 10 new GSMs and the bundled 'previously submitted' comparator tarball, is a legacy Change-O/pRESTO/Immcantation-pipeline tab-delimited table (uppercase columns: SEQUENCE\_ID, V\_CALL, D\_CALL, J\_CALL, JUNCTION, CDR3\_IMGT, CLONE, DUPCOUNT/CONSCOUNT, CREGION, MU\_FREQ in some files), already IgBLAST-annotated and clone-clustered. This is NOT scirpy.io.read\_10x\_vdj-compatible (no filtered\_contig\_annotations.csv, no per-cell barcode x gene matrix) even for the nominally single-cell-derived comparator files (musk1/2/3.tab), which have been flattened to one row per BCR sequence with a single pre-assigned SUBSET label and no transcriptome. Practically, this is bulk-style AIRR data end-to-end: an agent would load it with pandas, rename columns to the repo's bulk convention (v\_call-\>v, j\_call-\>j, junction\_aa/CDR3\_IMGT-\>cdr3aa, dupcount-\>count, cregion-\>isotype), and use the pytcr-bulk-\* family, not scirpy/MuData.
- **Geo Series Structure**: Flat single GSE (10 GSMs, no subseries), but with a non-standard wrinkle: 14 additional SRX-derived comparator samples (healthy-donor bulk memory-B repertoires, MuSK-MG single-cell-derived ASC repertoires, one vaccination ASC sample) are folded into a single series-level tarball (GSE227124\_airr-seq\_previously\_submitted\_samples.tar.gz, containing loose .tab/.tsv files plus a sample\_accessions.csv cross-reference to their original BioSample/SRA/GenBank IDs) rather than being registered as individual GSMs. An agent using only test/fetch\_data.py-style per-GSM fetching would retrieve the 10 new muscle-tissue GSMs cleanly but would need to separately fetch and unpack this series-level tarball (and cross-reference sample\_accessions.csv) to reconstruct the comparator arm described in the paper -- a materially different, more manual retrieval path than a standard GSE.
- **Existing Tutorials**: None found. No scirpy-, scanpy-, or Immcantation-published tutorial notebook reproducing GSE227124 specifically was located via PMC/web search; the data format (legacy Change-O tables) suggests any faithful reproduction would use the Immcantation suite (pRESTO/Change-O/SHazaM/Alakazam) rather than scirpy.
- **Reconstruction Difficulty**: High. Beyond the asymmetric/effectively-absent VDJ-GEX pairing described above, the deposited format is legacy Change-O/pRESTO output (uppercase, IMGT-gapped columns) rather than either scirpy-ready 10x files or this repo's expected bulk columns (sample, freq, #count, cdr3aa, cdr3nt, v, d, j), so an agent must first write a non-trivial column-mapping/renaming layer before any pytcr-bulk-\* skill applies. The dataset also straddles this repo's two explicitly separate skill families in a way that doesn't cleanly resolve: it looks like it should invite the single-cell pytcr-\* / scirpy pipeline (given the 10x-cell-barcode fingerprints in the comparator files and the paper's framing around ASC single-cell repertoires), but in practice every file must be treated with pytcr-bulk-\* pandas tooling since no GEX matrix exists in the series at all. A well-scoped exercise would need to explicitly restrict agents to bulk-only analyses (clonal expansion, V/D/J usage, diversity, isotype/SHM) and explain why clonotype-phenotype mapping is out of scope, rather than let agents discover the missing GEX data mid-task.

### Biological System

- **Disease Context Category**: autoimmune & rheumatic disease (idiopathic inflammatory myopathies)
- **Disease Tissue**: Inclusion body myositis (IBM), dermatomyositis (DM), and polymyositis (PM); muscle biopsy tissue (frozen sections, e.g. left biceps) is the primary disease-arm source, contrasted with peripheral blood B cell subsets (CD27+ memory B cells, antibody-secreting cells) from healthy donors, myasthenia-gravis patients, and a vaccinated subject as comparators.
- **Species**: Homo sapiens
- **Cohort Size**: New disease-arm data: 4 IBM patients (ages 57-77, 2M/2F), 3 DM patients (ages 34-64, all female), 3 PM patients (ages 64-77, all female) -- 10 muscle-biopsy samples total. Comparator data (bundled, not new): 6 healthy-donor bulk peripheral-blood CD27+ memory B cell repertoires, plus single-cell-derived ASC repertoires from 3 MuSK myasthenia-gravis patients and 1 subject 7 days post-influenza-vaccination, all reanalyzed from prior studies.
- **Cohort Scale Tier**: pilot (\<20 patients) -- 10 newly profiled myositis patients plus roughly a dozen comparator individuals reanalyzed from other studies; total repertoire sizes per sample are modest (hundreds to ~1,400 sequences and several hundred clones per muscle sample, per the GSM7092027\_IBM1 file inspected directly).

### Key Analyses & Findings

- **Clonal Expansion**: Yes, and it is the paper's central quantitative result: clone-size/clonality metrics show IBM (and DM) muscle infiltrates have significantly lower Simpson's diversity (i.e., greater clonal expansion) than healthy-donor circulating CD27+ memory B cells (p=0.039 IBM, p=0.019 DM), with IBM clone sizes reported to equal or exceed the highly clonal vaccine-associated ASC repertoire. This is directly reproducible from the deposited CLONE/DUPCOUNT columns using standard clonal-expansion/clonality code (bulk-style, e.g. pytcr-bulk-repertoire-metrics).
- **Clonotype Phenotype Mapping**: Not reproducible for any arm of this dataset as deposited in GEO, which is a stronger statement than the task note's framing. The disease-relevant IBM/DM/PM muscle arm has no single-cell or transcriptomic component at all. The nominally single-cell-derived comparator repertoires (from a prior myasthenia-gravis study and one vaccination sample, not from healthy donors) are provided in GSE227124 only as already-flattened AIRR/Change-O tables carrying a single pre-assigned cell-type label (verified: SUBSET='Plasma cell' for all rows in musk1.tab) and no gene-expression matrix whatsoever -- there is nothing for scirpy to pair VDJ against. A training task built on this dataset can demonstrate clonal expansion, V/D/J usage, diversity, and isotype/SHM analysis convincingly, but cannot demonstrate scirpy-style clonotype-to-cell-state mapping on either the disease tissue or the comparator arm; the comparator arm is not a viable substitute for a paired-GEX demo despite superficially originating from single-cell sequencing.
- **Vdj Gene Usage**: Yes, reproducible and a reported finding: DM shows increased VH1-18 usage versus healthy donors (p=0.019) and decreased VH3-23; IBM uses significantly less VH1-18 than DM (p=0.025); JH gene usage differences were minimal across groups. V\_CALL/J\_CALL columns are present in every deposited file, making V/D/J usage bar-plot/enrichment analysis straightforward with pandas.
- **Diversity Metrics**: Yes: the paper uses generalized Hill-number diversity indices with bootstrap resampling (2000 replicates), plus Simpson's diversity, to show significantly reduced repertoire diversity in myositis muscle infiltrates (IBM, DM) relative to healthy-donor circulating memory B cells. Fully reproducible from the CLONE/DUPCOUNT columns with the repo's bulk diversity tooling.
- **Isotype Shm**: Yes, both apply and are core to this paper's findings (this is the dataset's strongest fit to the repo's teaching goals). Isotype: the CREGION column encodes IGHG/IGHA/IGHM; IgG dominates myositis muscle infiltrates (60-68% average across IIM subtypes) versus ~22% in healthy-donor blood, with only a minor IgM population in IBM. SHM: BASELINe-based selection-pressure analysis (via SHazaM) shows IBM IgG-switched sequences have reduced positive selection pressure in CDRs/FWRs relative to circulating ASCs (p\<=0.001), while the small IBM IgM-expressing population shows an unusually elevated somatic mutation frequency (p=0.012) and distinct CDR3 physicochemical properties (elevated aliphatic index/hydrophobicity). Mutation-frequency fields (MU\_FREQ-family columns) and germline-comparison columns (GERMLINE\_IMGT) needed for SHM calculations are present in the deposited tables, though full BASELINe-style selection analysis would require the Immcantation/SHazaM R toolchain rather than pure Python/scirpy.
- **Disease Specific Conclusion**: The IBM muscle B cell infiltrate is composed almost entirely of terminally differentiated, class-switched (IgG/IgA-dominant) plasma cells forming highly expanded, low-diversity clones comparable in size to a vaccine-driven ASC response, but under reduced somatic-hypermutation selection pressure and with a distinct CDR3 physicochemical/gene-usage signature relative to DM, PM, and circulating antigen-experienced B cell subsets -- interpreted by the authors as evidence the infiltrate is shaped by local selection against a disease-specific (rather than generic autoimmune or germinal-center-driven) antigen set. This headline conclusion is fully reproducible from repertoire-level analysis alone (clonality, isotype, V-gene usage, SHM), i.e. from the bulk BCR data, without any need for the missing single-cell/GEX component.

### Lab Suitability

- **Pitfalls**: (1) Data format is legacy Change-O/pRESTO (uppercase IMGT-gapped columns), not this repo's bulk convention or scirpy-ready 10x files -- requires a column-mapping step before any existing skill applies. (2) The comparator/healthy-donor data is not delivered as individual GSMs but as a single series-level tarball (GSE227124\_airr-seq\_previously\_submitted\_samples.tar.gz) cross-referenced via a sample\_accessions.csv, which test/fetch\_data.py's per-GSM GEO fetch pattern does not handle automatically -- a task built on this dataset would need a custom fetch/unpack step or to scope the exercise to the 10 new muscle-tissue GSMs only. (3) Chain coverage is IGH-only (no light chain), limiting some scirpy-style dual-chain analyses even where otherwise applicable. (4) As detailed above, no GEX/transcriptome data exists anywhere in the series, so any exercise framed around 'paired single-cell BCR+GEX' will fail -- this must be scoped as a pure bulk-repertoire exercise. (5) Per-sample repertoire sizes are modest (low hundreds to ~1,400 sequences, ~200-700 clones per muscle sample), which is good for training run compute but may limit statistical power for some diversity comparisons an agent tries to replicate exactly.
- **Compute Needs**: Very low. Total supplementary data is small (GSE227124\_RAW.tar ~4.1MB compressed for the 10 new GSMs; the comparator tarball is ~37-39MB compressed). All analysis is pandas-scale tabular work; no GPU, no large in-memory AnnData/MuData objects, and no alignment/mapping step is needed since IgBLAST annotation is already done upstream. Runs comfortably on a laptop or the existing container's default memory cap.
- **Repo Pipeline Fit**: Fits the pytcr-bulk-\* family (pytcr-bulk-data-loading -\> pytcr-bulk-repertoire-metrics / pytcr-bulk-gene-motifs / pytcr-bulk-repertoire-overlap) well for clonal expansion, V/D/J usage, diversity, and isotype work, once columns are remapped from Change-O naming to the repo's (sample, freq, #count, cdr3aa, cdr3nt, v, d, j) convention. It does NOT fit the pytcr-\* scirpy/MuData single-cell chain (pytcr-data-loading -\> pytcr-preprocess -\> pytcr-clonotype-clustering -\> ...) at all, despite superficial single-cell provenance for part of the comparator data, because no GEX modality is deposited for any sample. This makes it a poor fit for any exercise intended to teach the pytcr-\* / scirpy MuData pairing workflow, and a reasonable-but-nonstandard fit for the pytcr-bulk-\* pandas workflow (nonstandard chiefly due to the Change-O column format and the series-level comparator tarball).
- **Recommended Scope**: Full new-data arm (10 muscle-tissue GSMs, ~4MB total) is already the minimal useful unit - no further sample-count reduction is meaningful at this scale. Recommend explicitly excluding the bundled 'previously submitted samples' comparator tarball from task scope by default (it requires a non-standard fetch/unpack path via sample\_accessions.csv rather than a clean per-GSM fetch), unless the healthy-donor/MG-comparator baseline comparison is specifically the teaching goal - the 10 new GSMs alone already support the full clonality/V-gene/isotype/SHM analysis and headline conclusion as a self-contained bulk exercise.

### Licensing & Data Access

- **Repository Tier**: GEO (open) -- verified by direct anonymous FTP download of GSE227124\_RAW.tar and GSE227124\_airr-seq\_previously\_submitted\_samples.tar.gz from ftp.ncbi.nlm.nih.gov with no authentication.
- **Access Class**: Fully open, no application or embargo; series has been public since Apr 25 2023.
- **Verification Confidence**: confirmed -- GEO series structure, all 10 GSM titles/sample characteristics/supplementary file names, the series-level supplementary tarball contents, and the paper's PMID/DOI/journal/cohort details were all directly verified from the GEO SOFT record, downloaded/inspected supplementary files, and the publisher's (Oxford Academic/ImmunoHorizons) article page.
- **Publication Vintage**: Peer-reviewed and published (ImmunoHorizons, May 2023), not a preprint.

### Flagged as Uncertain

- vdj\_gex\_pairing\_completeness

---
