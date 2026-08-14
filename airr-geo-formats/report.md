# Single-cell TCR/BCR/AIRR-seq datasets on GEO, by loader format, for testing the...

Single-cell TCR/BCR/AIRR-seq datasets on GEO, by loader format, for testing the pytcr-data-loading skill (scirpy readers: read_tracer, read_airr, read_bd_rhapsody). BraCeR and Dandelion were dropped from scope: research found no valid native-format GEO deposits for either (BraCeR's own paper used EGA EGAD00001004199; both Dandelion anchor papers used EGA/ArrayExpress). read_10x_vdj (CellRanger) was excluded from research entirely — already covered by a working real-GEO example in the skill (liao-2019-covid19, GSM4385993 + GSM4339772).

## Table of Contents

1. [GSE158055 — Ren et al. COVID-19 Chinese cell atlas](#gse158055-ren-et-al-covid-19-chinese-cell-atlas) - Status: confirmed_negative_not_airr_flattened... | Loadability: low | GEO: GSE158055 | Year: 2021 | Species: Homo sapiens | Format: AIRR-TSV
2. [Open item: confirmed post-2021 10x 5' VDJ GEO dataset with native airr_rearrangement.tsv](#open-item-confirmed-post-2021-10x-5-vdj-geo-dataset-with-native-airr-rearrangementtsv) - Status: positive_confirmed_high_confidence | Loadability: high | GEO: GSE275092 | Year: 2025 | Species: Homo sapiens | Format: AIRR-TSV
3. [GSE197456 — Type 1 Diabetes TCR, BD Rhapsody VDJ CDR3 Assay (trap example)](#gse197456-type-1-diabetes-tcr-bd-rhapsody-vdj-cdr3-assay-trap-example) - Status: negative_trap | Loadability: low | GEO: GSE197456 | Year: 2022 | Species: Human | Format: BD Rhapsody
4. [GSE291290 — heart transplant PBMC multi-omics](#gse291290-heart-transplant-pbmc-multi-omics) - Status: positive_medium_confidence | Loadability: low | GEO: GSE291290 | Year: 2024 (medRxiv preprint) / 2026 (peer-... | Species: Human | Format: BD Rhapsody
5. [GSE125077 — murine SCC neoantigens (trap example)](#gse125077-murine-scc-neoantigens-trap-example) - Loadability: None/not applicable — there is no VDJ... | GEO: GSE125077 | Year: 2023 | Species: Mus musculus | Format: TraCeR
6. [GSE270928 — Automated HT Smart-seq3 CD4+ T cells (2024)](#gse270928-automated-ht-smart-seq3-cd4-t-cells-2024) - Loadability: Low for read_tracer() directly on the... | GEO: GSE270928 | Year: 2024 | Species: Homo sapiens | Format: TraCeR

## Excluded From Scope

- **BraCeR**: No GSE record found with native BraCeR output after extensive search. The tool's own verification dataset is on EGA (EGAD00001004199), not GEO. One superficially promising GEO hit (GSE225574) contained only a raw UMI count matrix, no BCR reconstruction output.
- **Dandelion**: Both anchor papers confirmed off-GEO: Stephenson et al. 2021 (Nat Med, COMBAT cohort) is on EGA (EGAS00001005493) + Zenodo; Suo et al. 2023 (Nat Biotechnol, the Dandelion tool paper) is on ArrayExpress (E-MTAB-12524). No third-party GSE with native Dandelion output found. Likely a structural null set for GEO.
- **CellRanger (read_10x_vdj)**: Not researched — already has a working, verified real-GEO example built into the skill (liao-2019-covid19: GSM4385993 TCR contigs + GSM4339772 GEX).

---

## GSE158055 — Ren et al. COVID-19 Chinese cell atlas
<a id="gse158055-ren-et-al-covid-19-chinese-cell-atlas"></a>

### Identification

- **Paper Title**: COVID-19 immune features revealed by a large-scale single-cell transcriptome atlas
- **Year**: 2021
- **Journal**: Cell (Volume 184, Issue 7, pp. 1895-1913.e19)
- **Doi**: 10.1016/j.cell.2021.01.053

### Data Location

- **Geo Accession**: GSE158055
- **Repository Confirmed Geo**: True

**Alternate Repository**:

> N/A for the processed data used here — confirmed hosted directly on GEO. Raw sequencing reads for human subjects are separately deposited on the Genome Sequence Archive for Human (GSA-Human, BIG Data Center, China National Center for Bioinformation), accession HRA001149, per the paper's Data Availability statement — standard practice for Chinese human genetic resource data, not a GEO/EGA split of the kind seen in other items in this outline.

**Supplementary File Names**:

> Confirmed directly from the raw GEO series text record (acc.cgi, form=text) for GSE158055: GSE158055_cell_annotation.csv.gz (9.0 Mb), GSE158055_covid19_BCR_TCR.tar.gz (44.4 Mb / 46,555,019 bytes), GSE158055_covid19_barcodes.tsv.gz (5.8 Mb), GSE158055_covid19_counts.mtx.gz (7.6 Gb), GSE158055_covid19_features.tsv.gz (70.5 Kb), GSE158055_sample_metadata.xlsx (48.5 Kb). The BCR/TCR tarball was downloaded directly (byte-identical 46,555,019-byte size matched the GEO listing) and extracted; it contains exactly two files inside a GSE158055_covid19_BCR_TCR/ directory: GSE158055_covid19_tcr_vdjnt_pclone.tsv.gz (18,988,291 bytes, 220,968 data rows) and GSE158055_covid19_bcr_vdjnt_pclone.tsv.gz (27,623,202 bytes, 282,464 data rows) — no per-sample or per-GSM files, and no Cell Ranger-native filenames anywhere in the archive.


### Format Specifics

**Expected Reader Function**:

> None of scirpy's built-in readers apply directly. It is not filtered_contig_annotations.csv/all_contig_annotations.json (read_10x_vdj / CellRanger format), not a native airr_rearrangement.tsv (read_airr), not TraCeR's per-cell pickle directory structure (read_tracer), and not a BD Rhapsody export (read_bd_rhapsody). The data would have to be loaded via a custom pandas parse of the two vdjnt_pclone.tsv.gz files followed by manual AirrCell/AnnData construction (scirpy's generic 'from_dataframe'-style manual-construction path), mapping cellBarcode/TCRA_*/TCRB_* (or BCRH_*/BCRL_K_*) columns onto AIRR fields.

- **Native Vs Flattened Output**: flattened summary table

**File Structure Notes**:

> Directly inspected both extracted TSVs. Each is a one-row-per-cell table (not one row per contig/chain) retaining only the single highest-UMI ('dominated') chain pair per cell, exactly matching the paper's STAR Methods clonotype-calling description. TCR file (GSE158055_covid19_tcr_vdjnt_pclone.tsv.gz) columns: cellBarcode, sampleID, PatientID, TCRA_cgene, TCRA_vgene, TCRA_dgene, TCRA_jgene, TCRA_cdr3aa, TCRA_cdr3nt, TCRB_cgene, TCRB_vgene, TCRB_dgene, TCRB_jgene, TCRB_cdr3aa, TCRB_cdr3nt, then three parallel families of derived clonotype-grouping columns at increasing scope — TCR_clone.* (patient+sample-specific), TCR_pclone.* (patient-level), TCR_sclone.* (sample-level) — each with .id/.seq/.freq/.clonal/.identifier sub-columns. BCR file (GSE158055_covid19_bcr_vdjnt_pclone.tsv.gz) is structurally identical with BCRH_* (heavy chain) and 'BCRL/K_*' (light chain, literal column name contains a slash) in place of TCRA_*/TCRB_*. Row counts (220,968 TCR rows; 282,464 BCR rows, both header-exclusive) match the paper's reported '220,968 T cells with TCR information and 282,464 B cells with BCR information' used for STARTRAC analysis, confirming these are the actual per-cell dominant-chain summary tables described in Methods, not raw per-contig Cell Ranger output. There is no contig_id, no reads/umis count, no is_cell/high_confidence/productive flag, and no multi-row-per-barcode structure of any kind — everything Cell Ranger's native vdj outputs (and AIRR-TSV) carry per-contig is absent.

**Pipeline Version**:

> Confirmed verbatim in the paper's full-text STAR Methods ('TCR and BCR analysis' subsection, retrieved via Europe PMC fullTextXML for PMC7857060): 'TCR/BCR sequences were assembled and quantified following Cell Ranger (v.3.0.2) vdj protocol against GRCh38 reference genome.' Cell Ranger v3.0.2 predates the airr_rearrangement.tsv sidecar output entirely — per 10x Genomics' own release notes, that file was first introduced in Cell Ranger v4.0.0 (July 2020) and only became a default part of the combined GEX+VDJ 'cellranger multi' pipeline at v6.0 (~2021). Independent of that version gap, the deposited files are not even Cell Ranger's native raw vdj outputs (filtered_contig_annotations.csv, consensus_annotations.csv, clonotypes.csv, etc.) — they are the paper authors' own downstream, per-cell, dominant-chain-only summary export, confirmed by direct inspection of the file contents.


### Sample Context

- **Species**: Homo sapiens

**Tissue Disease**:

> Multiple tissue sources (predominantly PBMC, plus sputum/BALF and other sites per the series design) from COVID-19 patients (mild/moderate, severe/critical, and convalescent) and healthy controls — 196 individuals, 284 samples, ~1.46 million cells total in the companion gene-expression matrix.

**Single Cell Platform**:

> 10x Genomics 5' scRNA-seq (paired gene expression + BCR/TCR V(D)J libraries), per the paper's Methods ('Most samples were subjected to scRNA-seq based on the 10x Genomics 5′ sequencing platform to generate both the gene expression and T cell receptor (TCR) or B cell receptor (BCR) data').

**Species And Chain Coverage**:

> Both TCR (alpha/beta, TRA/TRB) and BCR (heavy/light, IGH paired with IGL or IGK) are profiled, each in its own separate flattened TSV within the same tarball — TCR-only cells require at least one TRA and one TRB; BCR-only cells require at least one IGH and one IGL/IGK. Only the single highest-expression chain of each type is retained per cell (dominant-chain model), not all recovered chains.

**Linked Gex Modality**:

> Yes — the same GSE158055 series also deposits GSE158055_covid19_counts.mtx.gz plus matching barcodes.tsv.gz/features.tsv.gz (the full ~1.46M-cell expression matrix) and GSE158055_cell_annotation.csv.gz (cell-type/metadata annotations), so a scirpy MuData with both gex and airr modalities is buildable in principle, but the airr side requires the custom-format reformatting described above, not a direct reader call.


### Loadability

- **Loadability Confidence**: low

**File Completeness Caveat**:

> The data is genuinely present and complete for what it is (confirmed by direct download — full cell counts match the paper), so there is no missing-data caveat. The caveat is purely a format mismatch against this item's 'AIRR-TSV' label: the deposited files are a custom, per-cell, single-dominant-chain summary table produced by the authors' own post-processing script, not Cell Ranger's native per-contig outputs and not an AIRR Rearrangement-schema TSV (no sequence_id, no productive flag, no duplicate_count/reads columns, no separate row per contig). The original outline's hypothesis (that this predates the AIRR TSV sidecar and is therefore likely filtered_contig_annotations.csv/all_contig.fasta-style Cell Ranger output) was directionally right about the version gap but the actual format is one step further removed — a fully custom, non-Cell-Ranger-native, non-AIRR schema.

**Reformatting Needed**:

> A full manual remap: read the two gzipped TSVs with pandas, split TCRA_*/TCRB_* (or BCRH_*/BCRL_K_*) into separate per-chain records, map v/d/j/c gene columns and cdr3aa/cdr3nt onto AIRR field names (v_call, d_call, j_call, c_call, junction, junction_aa), synthesize the required AIRR fields that are simply absent from the source (sequence_id, productive, duplicate_count, locus, rev_comp, etc. — many with no real value to fill in since per-contig read/UMI counts were not retained, only clonotype frequency), and construct AirrCell/AnnData objects manually rather than via any scirpy reader function. This is a materially larger transform than the reformatting needed for the BD Rhapsody or TraCeR flattened-CSV cases documented elsewhere in this outline, because no scirpy reader targets this schema family at all.


### Provenance

**Verification Method**:

> Full-chain direct verification, not inference: (1) fetched the raw GEO series text record (acc.cgi?...&form=text) for GSE158055 to get the authoritative supplementary_file list; (2) downloaded GSE158055_covid19_BCR_TCR.tar.gz directly from the NCBI GEO FTP mirror (ftp.ncbi.nlm.nih.gov/geo/series/GSE158nnn/GSE158055/suppl/), confirmed the downloaded byte size (46,555,019 bytes) matches the GEO-listed 44.4 Mb exactly; (3) extracted the tarball and inspected both TSVs directly with gzip/head/wc — actual header row and actual row counts, not filenames alone; (4) cross-checked those row counts (220,968 TCR / 282,464 BCR) against the paper's own reported cell counts in its full text; (5) retrieved the paper's full-text STAR Methods via Europe PMC's fullTextXML endpoint (PMC7857060) to independently confirm the Cell Ranger v3.0.2 claim and the dominant-chain clonotype-calling logic, which matches the column structure observed in the actual files. This resolves the original 'unconfirmed_needs_download' status with a definitive, file-content-verified negative finding for the AIRR-TSV format claim.


### Uncertain Fields

- authors

## Open item: confirmed post-2021 10x 5' VDJ GEO dataset with native airr_rearrangement.tsv
<a id="open-item-confirmed-post-2021-10x-5-vdj-geo-dataset-with-native-airr-rearrangementtsv"></a>

### Identification

**Paper Title**:

> Plasmodium falciparum infection induces T cell tolerance that is associated with decreased disease severity upon re-infection

- **Authors**: Diana Muñoz Sandoval, Florian A. Bach, Alasdair Ivens, Adam C. Harding, Natasha L. Smith, et al.
- **Year**: 2025
- **Journal**: Journal of Experimental Medicine (JEM), Vol. 222, Issue 7, e20241667
- **Doi**: 10.1084/jem.20241667

### Data Location

**Geo Accession**:

> GSE275092 (12 GSMs organized as 2 sample pools [first infection, third infection] x 3 library types [cell-surface/hashing, 5' gene expression, TCR V(D)J] x 2 A-chip wells per pool, i.e. CS1_2/CS3_4, GEX1_2/GEX3_4, VDJ1_2/VDJ3_4 file groupings)

- **Repository Confirmed Geo**: True

**Alternate Repository**:

> N/A for this single-cell dataset — confirmed hosted directly on GEO. The paper separately deposits companion bulk TCRβ-seq data in the European Nucleotide Archive (ENA), and a related bulk RNA-seq SuperSeries (flow-sorted CD4 T cell subsets) is on GEO as GSE172481 — neither is a repository substitution for GSE275092 itself.

**Supplementary File Names**:

> Confirmed directly from the raw GEO series text record (acc.cgi, form=text) for GSE275092 — all 18 Series_supplementary_file lines fetched verbatim: GSE275092_CS1_2_barcodes.tsv.gz, GSE275092_CS1_2_features.tsv.gz, GSE275092_CS1_2_matrix.mtx.gz, GSE275092_CS3_4_barcodes.tsv.gz, GSE275092_CS3_4_features.tsv.gz, GSE275092_CS3_4_matrix.mtx.gz, GSE275092_GEX1_2_barcodes.tsv.gz, GSE275092_GEX1_2_features.tsv.gz, GSE275092_GEX1_2_matrix.mtx.gz, GSE275092_GEX3_4_barcodes.tsv.gz, GSE275092_GEX3_4_features.tsv.gz, GSE275092_GEX3_4_matrix.mtx.gz, GSE275092_VDJ1_2_airr_rearrangement.tsv.gz (8.7 Mb), GSE275092_VDJ1_2_clonotypes.csv.gz, GSE275092_VDJ1_2_consensus_annotations.csv.gz, GSE275092_VDJ3_4_airr_rearrangement.tsv.gz (10.4 Mb), GSE275092_VDJ3_4_clonotypes.csv.gz, GSE275092_VDJ3_4_consensus_annotations.csv.gz. The two airr_rearrangement.tsv.gz files are literally, exactly named that (with only the GEO accession + pool-id prefix added), satisfying the task's strong positive signal directly.


### Format Specifics

**Expected Reader Function**:

> read_airr (scirpy) — GSE275092_VDJ1_2_airr_rearrangement.tsv.gz and GSE275092_VDJ3_4_airr_rearrangement.tsv.gz are Cell Ranger's own native AIRR-community-schema TSV sidecar output, unmodified apart from gzip compression and the GEO filename prefix.

**Native Vs Flattened Output**:

> native pipeline structure. Each VDJ pool's deposited trio (airr_rearrangement.tsv.gz, clonotypes.csv.gz, consensus_annotations.csv.gz) is a subset of Cell Ranger's standard outs/ directory annotation files — the per-contig BAM/FASTA raw-sequence files were not deposited, but the AIRR TSV itself is untouched native Cell Ranger multi output, not a custom or flattened re-export.

**File Structure Notes**:

> Two sample pools, each with matched GEX (barcodes/features/matrix.mtx.gz triplet — standard Cell Ranger count-matrix format), cell-surface hashing/CITE-seq (CS*, same triplet format), and TCR VDJ (airr_rearrangement.tsv.gz + clonotypes.csv.gz + consensus_annotations.csv.gz) file groups, all keyed by pool (1_2 = first infection pool across 2 A-chip wells, 3_4 = third infection pool). This mirrors the outputs of running `cellranger multi` once per pool with GEX + VDJ-T + Antibody Capture libraries configured together, then depositing the vdj_t/ and per-sample count-matrix outputs from each pool's outs/ directory. No BCR/vdj_b output exists in this series (study is TCR-only by design).

**Pipeline Version**:

> Confirmed verbatim in the paper's full-text Methods ('Single-cell RNAseq analysis' subsection, retrieved via Europe PMC fullTextXML for PMC11987708): 'Cell Ranger multi (v6.0.2) was used to align 5′ gene expression and V(D)J sequencing reads to the GRCh38 reference genome.' This is >= Cell Ranger v6, consistent with airr_rearrangement.tsv being a default `cellranger multi` sidecar output at that version generation (note: 10x's release notes actually place the airr_rearrangement.tsv file's first introduction at Cell Ranger v4.0.0 for plain `cellranger vdj`, with `cellranger multi` — the combined GEX+VDJ pipeline — adopting it as a default part of its per-sample outputs starting around v6.0; both facts are consistent with this dataset's v6.0.2 usage).


### Sample Context

- **Species**: Homo sapiens

**Tissue Disease**:

> Flow-sorted CD4+ T cells from cryopreserved PBMCs; controlled human malaria infection (CHMI) model, Plasmodium falciparum blood-stage infection (VAC063C study, ClinicalTrials.gov NCT03906474), comparing first-ever infection vs. third infection, sampled at baseline (pre-infection) and 6 days post-treatment (peak circulating T cell response).

**Single Cell Platform**:

> 10x Genomics Chromium Controller, super-loaded (~30,000 singlets/pool across 2 wells of an A chip), 5' Gene Expression + TotalSeq-C antibody-oligo cell-surface hashing (Stoeckius et al. 2018 cell-hashing workflow) + TCR V(D)J libraries, sequenced on Illumina NovaSeq 6000.

**Species And Chain Coverage**:

> TCR-only — alpha and beta chains (TRA/TRB), no BCR profiling in this series. Chain-to-cell matching used Cell Ranger's native contig annotations combined with scRepertoire's createHTOContigList() per the paper's Methods.

- **Linked Gex Modality**: True

### Loadability

- **Loadability Confidence**: high

**File Completeness Caveat**:

> Files are deposited per sample-pool (2 pools: first-infection VDJ1_2, third-infection VDJ3_4), not per individual volunteer — the 6 individually barcoded volunteers within each pool are disambiguated downstream via the TotalSeq-C hashing/cell-surface (CS) data and metadata, not via separate per-volunteer airr_rearrangement.tsv files. This is a study-design granularity note, not a data-completeness gap: TCR-only by design (no BCR is expected or missing), and the airr_rearrangement.tsv files themselves are complete, native, single-pipeline-run outputs.

**Reformatting Needed**:

> None expected for the core load — scirpy's read_airr() (or the equivalent ir.io function) should ingest GSE275092_VDJ1_2_airr_rearrangement.tsv.gz / GSE275092_VDJ3_4_airr_rearrangement.tsv.gz directly, since they are genuine, unmodified Cell Ranger multi v6.0.2 AIRR-TSV sidecar output. Building a full scirpy MuData with both gex and airr modalities additionally requires reading the matched GEX*_barcodes/features/matrix.mtx.gz triplets (standard 10x/scanpy count-matrix format, no special handling) and aligning cell barcodes across the airr and gex files for each pool — routine multi-modal assembly, not format remediation.


### Provenance

**Verification Method**:

> GEO's own DataSets (gds) search engine does not index individual supplementary filenames (its 'Supplementary Files' [SFIL] field only carries coarse file-type categories like TSV/CSV/TAR, confirmed by testing SFIL against known category tokens vs. filename fragments), so search-engine-summary approaches for this item were unreliable by construction. Instead used NCBI E-utilities esearch directly against db=gds with term='airr AND rearrangement' (150 total hits across GSE + GSM-level records) via the ALL-fields full-text index, which does surface series whose title/description/data-processing text mentions AIRR terminology, then fetched esummary for each hit to filter down to entryType=GSE records and their titles/dates. Six GSE-level candidates emerged; the raw GEO accession page for each candidate was then fetched directly (acc.cgi, not a search-engine summary) to check the actual supplementary_file listing for a literal airr_rearrangement.tsv(.gz) filename. GSE275092 was selected as the primary answer and further independently cross-verified via the raw GEO text record (acc.cgi?...&form=text, all 18 Series_supplementary_file lines fetched verbatim) and via the associated publication's full-text Methods (Europe PMC fullTextXML for PMC11987708), which states verbatim 'Cell Ranger multi (v6.0.2) was used to align 5' gene expression and V(D)J sequencing reads' and independently cites GSE275092 in its Data Availability statement — a two-source (GEO record + paper methods) confirmation matching this outline's own stated anti-hallucination pattern (the GSE75688/TraCeR false link caught during initial research). Two additional mouse-only candidates from the same search were also directly confirmed (via GEO accession page fetch) to carry literal airr_rearrangement.tsv.gz files but were not selected as the primary answer: GSE245084 ('Antigen-level resolution of commensal-specific B cell responses...', unpublished/no PMID at time of research) and GSE284621 ('Antigen-selected gut IgA is generated from IgG1 germinal center B cells (BCR)', PMID 41253159, BCR not TCR). These stand as secondary corroboration that the open research question has more than one real answer, not just a single fragile hit.


## GSE197456 — Type 1 Diabetes TCR, BD Rhapsody VDJ CDR3 Assay (trap example)
<a id="gse197456-type-1-diabetes-tcr-bd-rhapsody-vdj-cdr3-assay-trap-example"></a>

### Identification

**Paper Title**:

> Characterization of Peripheral Blood TCR in Patients with Type 1 Diabetes Mellitus by BD Rhapsody(TM) VDJ CDR3 Assay

**Authors**:

> Takuro Okamura, Masahide Hamaguchi, Hiroyuki Tominaga, Noriyuki Kitagawa, Yoshitaka Hashimoto, Saori Majima, Takafumi Senmaru, Hiroshi Okada, Emi Ushigome, Naoko Nakanishi, Shigeyuki Shichino, Michiaki Fukui

- **Year**: 2022
- **Journal**: Cells (MDPI), Vol. 11, Issue 10, Art. 1623
- **Doi**: 10.3390/cells11101623

### Data Location

- **Geo Accession**: GSE197456 (GSM5917901, GSM5917902, GSM5917903, GSM5917904)
- **Repository Confirmed Geo**: True
- **Alternate Repository**: N/A — dataset is confirmed deposited on GEO itself

**Supplementary File Names**:

> Series level: GSE197456_BD_Rhapsody_T_Cell_Expression_Panel_Hs.fasta.gz (30 KB, targeted-panel probe reference), GSE197456_RAW.tar (2.7 MB, bundles the 4 GSM MolsPerCell files, verified via filelist.txt), filelist.txt. Per-GSM (individually re-checked for all 4 sub-records): GSM5917901_S1_DBEC_MolsPerCell.csv.gz (~563 KB), GSM5917902_S2_DBEC_MolsPerCell.csv.gz (~1.47 MB), GSM5917903_S3_DBEC_MolsPerCell.csv.gz (~258 KB), GSM5917904_S4_DBEC_MolsPerCell.csv.gz (~571 KB). No filename containing VDJ, CDR3, TCR, contig, or clonotype appears anywhere in the series-level listing, the RAW.tar contents, or any of the 4 individual GSM sub-record pages.


### Format Specifics

**Expected Reader Function**:

> read_bd_rhapsody (scirpy) is the nominal target implied by the assay name in the title, but this is moot: no VDJ output file exists anywhere in the record for it to read.

- **Native Vs Flattened Output**: gene-expression-only (no VDJ deposited)

**File Structure Notes**:

> Only WTA/targeted-panel molecule-count matrices are deposited: *_DBEC_MolsPerCell.csv.gz, one per sample/GSM, a cell x gene molecule-count table produced by the BD Rhapsody Targeted mRNA / T Cell Expression Panel workflow (DBEC = Distribution-Based Error Correction). None of BD Rhapsody's VDJ pipeline outputs (*_VDJ_perCell.csv, *_perCellChain.csv, *_VDJ_Dominant_Contigs.csv, *_VDJ_Unfiltered_Contigs.csv) are present at the series level or in any of the 4 individual GSM sub-records, despite the series title, the deposited FASTA panel-reference filename, and every GSM description explicitly naming the 'VDJ CDR3 Assay' / TCR profiling as part of the study design.


### Sample Context

- **Species**: Human

**Tissue Disease**:

> Peripheral blood mononuclear cells (PBMC); Type 1 Diabetes Mellitus patients (n=4; mixed 1A autoimmune and SPIDDM subtypes, per individual GSM descriptions)

**Single Cell Platform**:

> BD Rhapsody (Express system, T Cell Expression Panel targeted probes; a 'VDJ CDR3 Assay' is named in the title/description but its output was not actually deposited)

**Species And Chain Coverage**:

> Intended paired TCR alpha/beta coverage per the named VDJ CDR3 Assay and study description, but this cannot be confirmed in practice — no chain-level VDJ data of any kind was deposited.

- **Linked Gex Modality**: True

### Loadability

- **Loadability Confidence**: low

**File Completeness Caveat**:

> No VDJ/CDR3 file is deposited anywhere in the series. Re-confirmed directly against the GEO accession page and FTP listing beyond the original series-level check: (1) the series-level suppl/ directory (GSE197456_BD_Rhapsody_T_Cell_Expression_Panel_Hs.fasta.gz, GSE197456_RAW.tar, filelist.txt), (2) filelist.txt's enumeration of RAW.tar's contents (the same 4 MolsPerCell.csv.gz files, no VDJ file), and (3) all 4 individual GSM sub-records (GSM5917901–GSM5917904) checked one by one, each listing only its own *_DBEC_MolsPerCell.csv.gz as supplementary file. This is a title/description-vs-content mismatch — the paper and GEO series title explicitly name the 'BD Rhapsody VDJ CDR3 Assay' and the sample descriptions state 'TCR analysis to characterize peripheral blood TCR profiles,' yet no VDJ output was ever uploaded. GEO gives no submitter note explaining the omission (unlike GSE291290's explicit 'file loss' note).

**Reformatting Needed**:

> Not applicable for VDJ/AIRR loading — there is no VDJ file to reformat or remap. If only the gene-expression side is wanted, the *_DBEC_MolsPerCell.csv.gz per-sample cell x gene count tables could be loaded as a plain pandas table into an AnnData object (transposing to the standard cells-as-obs/genes-as-var orientation), but this produces no `airr` modality and cannot feed read_bd_rhapsody or any other scirpy IR reader.


### Provenance

**Verification Method**:

> Direct re-verification performed for this task, going beyond the original series-level-only check: fetched the GEO series page (acc.cgi?acc=GSE197456), the raw NCBI FTP suppl/ directory listing and its filelist.txt (enumerating RAW.tar's contents), and all four individual GSM sub-record pages (GSM5917901, GSM5917902, GSM5917903, GSM5917904) one by one — each confirmed to list only its own *_DBEC_MolsPerCell.csv.gz. Cross-checked against the associated publication (Okamura et al., 2022, Cells, doi 10.3390/cells11101623) located via web search / PubMed / PMC (PMC9139223), which confirms the study design (BD Rhapsody VDJ CDR3 Assay, n=4 T1DM patients) without independently confirming any additional deposited VDJ file. The negative_trap characterization is confirmed, not just inferred from the series-level listing.


### Uncertain Fields

- pipeline_version

## GSE291290 — heart transplant PBMC multi-omics
<a id="gse291290-heart-transplant-pbmc-multi-omics"></a>

### Identification

**Paper Title**:

> Proinflammatory and cytotoxic CD38+HLA-DR+ effector memory CD8+ T cells are peripherally expanded in human cardiac allograft vasculopathy

**Authors**:

> Yuko Tada, Sujit Silas Armstrong Suthahar, Payel Roy, Vasantika Suryawanshi, Runpei Wu, Erpei Wang, Felix Sebastian Nettersheim, Anusha Bellapu, Katarzyna Dobaczewska, Cheryl Kim, Florin Vaida, Gerald P. Morris, Klaus Ley, Paul J. Kim

- **Year**: 2024 (medRxiv preprint) / 2026 (peer-reviewed journal issue, published online October 2025)

**Journal**:

> American Journal of Transplantation, Vol. 26, Issue 2, pp. 276-290 (peer-reviewed); originally posted as a medRxiv preprint

- **Doi**: 10.1016/j.ajt.2025.10.015 (journal); 10.1101/2024.12.23.24319590 (medRxiv preprint)

### Data Location

**Geo Accession**:

> GSE291290 (GSM8833027, GSM8833028, GSM8833029, GSM8833030, GSM8833031, GSM8833032 — 6 samples/libraries)

- **Repository Confirmed Geo**: True
- **Alternate Repository**: N/A — dataset is confirmed deposited on GEO itself

**Supplementary File Names**:

> GSE291290_Ab_raw.csv.gz, GSE291290_Genes_raw.csv.gz, GSE291290_Metadata.csv.gz, GSE291290_Vdj_combined.csv.gz — all four confirmed present via direct GEO FTP listing. All four are study-wide/combined files; no per-GSM supplementary files are attached to the individual GSM8833027–032 sample records.


### Format Specifics

**Expected Reader Function**:

> read_bd_rhapsody (scirpy) is the nominal target, but per scirpy's current source/docstring (scverse/scirpy, main branch) it only accepts *_perCellChain.csv, *_perCellChain_unfiltered.csv, *_VDJ_Dominant_Contigs.csv, or *_VDJ_Unfiltered_Contigs.csv, and explicitly states that '*_perCell' files are not supported. GSE291290_Vdj_combined.csv.gz's schema, confirmed by directly downloading and parsing the file, is exactly the *_VDJ_perCell.csv dominant-chain-per-cell schema — the one format class read_bd_rhapsody rejects. The actual load path is therefore the pytcr-data-loading skill's generic 'Converting from other formats' manual AirrCell-construction pattern (CDR3 + V/D/J genes + locus + count columns per cell), not a direct read_bd_rhapsody call.

**Native Vs Flattened Output**:

> flattened summary table — a study-wide concatenation of what would otherwise be 6 separate per-sample dominant-chain-per-cell (*_VDJ_perCell.csv-schema) tables into a single file, with Cell_Index prefixed by library id (L1_ through L6_) to disambiguate cells across samples.

**File Structure Notes**:

> Directly downloaded and parsed GSE291290_Vdj_combined.csv.gz (2.85 MB compressed, 119,300 data rows, confirmed via direct `gunzip`/`wc -l`). Header/columns: Cell_Index, Total_VDJ_Read_Count, Total_VDJ_Molecule_Count, then four per-locus column blocks — BCR_Heavy, BCR_Light, TCR_Alpha_Gamma, TCR_Beta_Delta — each with {locus}_V_gene_Dominant (and D/J/C_gene_Dominant where applicable), {locus}_CDR3_Nucleotide_Dominant, {locus}_CDR3_Translation_Dominant, {locus}_Read_Count, {locus}_Molecule_Count, plus BCR_Paired_Chains and TCR_Paired_Chains (boolean) and Cell_Type_Experimental. This is one row per cell holding only the single dominant chain per locus type (not one row per chain/contig) — i.e. BD Rhapsody's standard per-cell VDJ summary schema, concatenated across all 6 libraries. Per-library Cell_Index prefix breakdown (directly counted): L1=22,958, L2=18,205, L3=19,342, L4=16,833, L5=21,281, L6=20,682 cells. GSE291290_Metadata.csv.gz shares the same Cell_Index key and supplies Library, SampleTag, SampleName (e.g. 'CAV1'), SampleType (e.g. 'CAV'), and clinical covariates — this is the join table needed to split the combined file back into its 6 constituent GSM8833027–032 samples. GSE291290_Genes_raw.csv.gz (WTA) and GSE291290_Ab_raw.csv.gz (AbSeq/CITE-seq protein) are the companion study-wide gene-expression/protein matrices, keyed on the same Cell_Index scheme.


### Sample Context

- **Species**: Human

**Tissue Disease**:

> Peripheral blood mononuclear cells (PBMC); heart transplant recipients with vs. without cardiac allograft vasculopathy (CAV) / graft dysfunction — SampleType values include 'CAV', directly confirmed in Metadata.csv.gz alongside clinical covariates (LVEF, HLA mismatch, DSA history, etc.)

**Single Cell Platform**:

> BD Rhapsody (WTA + AbSeq/CITE-seq + VDJ-seq, per the GEO series summary: 'BD Rhapsody CITE-seq and VDJ-seq')

**Species And Chain Coverage**:

> Paired TCR + BCR in the same combined table: BCR (Heavy/Light) and TCR (Alpha/Gamma, Beta/Delta) dominant chains are both captured per cell. BCR_Paired_Chains and TCR_Paired_Chains boolean columns flag, per cell, whether both chains of a receptor were recovered (e.g. row 3 in the sample data has both TRUE for TCR and BCR).

- **Linked Gex Modality**: True

### Loadability

- **Loadability Confidence**: low

**File Completeness Caveat**:

> GEO record states 'missing raw files are due to file loss' (submitter note) — indicating some other intended raw file(s) were never deposited. The four files that are present (Ab_raw, Genes_raw, Metadata, Vdj_combined) are all study-wide/combined rather than the per-GSM breakdown implied by there being 6 separate GSM accessions; no per-sample supplementary files are attached to any of GSM8833027–032 individually.

**Reformatting Needed**:

> (1) read_bd_rhapsody cannot be called directly on this file — confirmed against scirpy's current source/docstring that it does not accept *_perCell-schema files (only *_perCellChain.csv/*_perCellChain_unfiltered.csv/*_VDJ_Dominant_Contigs.csv/*_VDJ_Unfiltered_Contigs.csv are supported), and Vdj_combined.csv.gz's confirmed column layout is exactly the unsupported *_VDJ_perCell.csv schema. (2) Melt/reshape the four per-locus column blocks (BCR_Heavy, BCR_Light, TCR_Alpha_Gamma, TCR_Beta_Delta) into individual chain records (locus, v/d/j/c_call, junction, junction_aa, consensus_count) per cell, following the pytcr-data-loading skill's generic 'Converting from other formats' AirrCell.empty_chain_dict() pattern — this is a mechanical, well-scoped transform once the schema is known. (3) Split by sample using Metadata.csv.gz's Cell_Index -> Library/SampleName join (Cell_Index prefixes L1_ through L6_ map 1:1 to the 6 GSM accessions), or keep one combined AnnData/MuData with a sample obs column, since scirpy natively supports multi-sample objects. (4) Join Genes_raw.csv.gz and Ab_raw.csv.gz on the same Cell_Index to build the paired `gex` modality for a scirpy MuData object.


### Provenance

**Verification Method**:

> Direct verification: fetched the GEO series page and confirmed all 4 supplementary filenames plus the 'missing raw files are due to file loss' submitter note. Downloaded GSE291290_Vdj_combined.csv.gz and GSE291290_Metadata.csv.gz directly from the NCBI FTP suppl/ directory (not inferred from filenames) and parsed them with shell tools (header inspection, total row count, per-library Cell_Index prefix breakdown) to firm up the file-structure and loadability assessment beyond the prior 'likely' characterization. Cross-checked scirpy's read_bd_rhapsody support surface directly against its current docstring/implementation on the scverse/scirpy GitHub main branch (not just high-level documentation pages). Identified and matched the associated publication via the GEO record's linked PubMed IDs (41138970 journal version, 39763556 medRxiv preprint) and independently confirmed the link by matching the 'CAV' SampleType value found in Metadata.csv.gz against the paper's cardiac allograft vasculopathy (CAV) cohort design.


### Uncertain Fields

- pipeline_version

## GSE125077 — murine SCC neoantigens (trap example)
<a id="gse125077-murine-scc-neoantigens-trap-example"></a>

### Identification

**Authors**:

> Joseph S. Dolina, Joey Lee, et al. (incl. Spencer E. Brightman, Sara McArdle, Samantha M. Hall, Rukman R. Thota, Karla S. Zavala, Manasa Lanka, Ashmitaa Logandha Ramamoorthy Premlal, Jason A. Greenbaum, Ezra E. W. Cohen, Bjoern Peters, Stephen P. Schoenberger; La Jolla Institute for Immunology)

- **Year**: 2023
- **Journal**: Journal of Clinical Investigation (J Clin Invest)
- **Doi**: 10.1172/JCI164258

### Data Location

**Geo Accession**:

> GSE125077 (Single-cell SubSeries, 123 GSM samples, GSM3562194–GSM3562316), SubSeries of SuperSeries GSE125078, which also has a Bulk-seq SubSeries GSE125048; BioProject PRJNA515089, SRA SRP179106

- **Repository Confirmed Geo**: True
- **Alternate Repository**: N/A — confirmed hosted on GEO directly

**Supplementary File Names**:

> GSE125077_Single_cell_HTSeq_counts.tsv.gz (535.1 Kb) is the only supplementary file at the GSE125077 series level. Verified via the raw GEO text record (form=text): single 'Series_supplementary_file' line, pointing to this HTSeq gene-count file only. Checked a representative sample record (GSM3562194): 'Sample_supplementary_file_1 = NONE', confirming no per-sample supplementary files either. Also checked the SuperSeries GSE125078 level: only a GSE125078_RAW.tar (200.0 Kb, containing per-sample TSV count files) and the Bulk-seq SubSeries GSE125048 are present; no TCR/TraCeR/VDJ-named file anywhere in the SuperSeries or either SubSeries.


### Format Specifics

**Expected Reader Function**:

> N/A — no TCR/VDJ output of any kind was deposited, so no scirpy reader (read_tracer, read_airr, or otherwise) has anything to load

- **Native Vs Flattened Output**: gene-expression-only (no VDJ deposited)

**File Structure Notes**:

> The single deposited file, GSE125077_Single_cell_HTSeq_counts.tsv.gz, is an HTSeq-count gene x sample expression matrix (per Series_data_processing: STAR v2.4.1c alignment to mm10, HTSeq-count v0.7.1 with '-m union -s no -t exon -i gene_name -r name'). This is single-cell (well/plate-based, 123 samples) RNA-seq expression data only. The Methods (Series_overall_design in the raw GEO record) explicitly describe running TraCeR (v0.6.0) with reference genome GRCm38 on the same FASTQ files to reconstruct TCR alpha/beta chains, and completing them with IMGT leader sequences, but none of that TraCeR output (chain calls, CDR3 sequences, clonality assignments) was ever deposited to GEO — only the upstream gene-count matrix used for expression analysis.

**Pipeline Version**:

> N/A — no AIRR-TSV or any VDJ file was deposited; TraCeR v0.6.0 was the tool used per the Methods text, but its output was not archived.


### Sample Context

- **Species**: Mus musculus

**Tissue Disease**:

> Splenocytes and tumor-draining lymph node lymphocytes; SCCVII spontaneous murine squamous cell carcinoma model (resembles human head & neck squamous cell carcinoma); IFN-γ-captured, FACS-sorted CD4+ and CD8+ T cells responding to neoantigen peptides in vitro

**Single Cell Platform**:

> Plate-based Smart-seq2-adapted single-cell RNA-seq (FACS-sorted into 96-well plates, Nextera XT library prep), sequenced on Illumina HiSeq 2500

**Species And Chain Coverage**:

> Intended TCR alpha/beta pairs per the Methods (TraCeR reconstruction of both chains, clonal calls requiring alpha+beta identified together in >1 cell), but this is moot for loading since no TCR output file was ever deposited to GEO

**Linked Gex Modality**:

> The deposited data IS the gene-expression matrix itself (HTSeq counts) — i.e. GEX exists but AIRR/VDJ data does not, so no gex+airr MuData can be built from this GEO record alone


### Loadability

**Loadability Confidence**:

> None/not applicable — there is no VDJ file of any kind on GEO for this accession, so no reader function (read_tracer or otherwise) can be pointed at it. This is a 'tool used, output not deposited' case, not a format-mismatch case.

**File Completeness Caveat**:

> Methods explicitly state TraCeR (v0.6.0) was used to reconstruct and analyze TCR alpha/beta chains, but only the upstream HTSeq gene-count matrix was deposited to GEO (series level, SuperSeries level, and per-sample level all checked and confirmed empty of TCR files). Title and abstract promise T-cell neoantigen/TCR characterization work, but no TCR-derived file backs it on GEO.

**Reformatting Needed**:

> Not applicable — there is nothing to reformat. TCR output would have to be obtained from the authors directly (e.g. by request) or is simply unavailable; it cannot be reconstructed from the deposited gene-count matrix.


### Provenance

**Verification Method**:

> GEO supplementary-file listing fetched directly from the NCBI GEO series text record (acc.cgi form=text) for GSE125077 itself, for its SuperSeries GSE125078, and for a representative sample (GSM3562194) — all three confirmed independently that no TCR/TraCeR/VDJ file exists anywhere in the record. The TraCeR v0.6.0 usage claim comes directly from the Series_overall_design free text in the same raw GEO record (Methods-equivalent description), not from a search-engine summary. Publication identity (JCI 2023, differing title from the GEO series title) was cross-verified by fetching the full paper abstract and confirming it cites GSE125078 in its Data Availability statement and discusses the same SCCVII/Pik3ca/Ctnnd1/Otud5/Cltc neoantigens named in the GEO series summary.


### Uncertain Fields

- paper_title

## GSE270928 — Automated HT Smart-seq3 CD4+ T cells (2024)
<a id="gse270928-automated-ht-smart-seq3-cd4-t-cells-2024"></a>

### Identification

**Paper Title**:

> Single-cell sequencing of full-length transcripts and T-cell receptors with automated high-throughput Smart-seq3

- **Year**: 2024
- **Journal**: BMC Genomics
- **Doi**: 10.1186/s12864-024-11036-0

### Data Location

**Geo Accession**:

> GSE270928 (6,415 GSM sample accessions, GSM8358885–GSM8365304; SRA BioProject PRJNA1129044). Sibling series GSE270917 holds the paired 10X-platform comparison data, not part of this item.

- **Repository Confirmed Geo**: True
- **Alternate Repository**: N/A — confirmed hosted on GEO directly

**Supplementary File Names**:

> GSE270928_Seurat_Object_HT_SS3.rds.gz (299.0 Mb, R Seurat object — gene expression); GSE270928_TraCeR_filtered_cell_data_HT_SS3.csv.gz (156.9 Kb, 6,311 data rows); GSE270928_TraCeR_filtered_recombinants_HT_SS3.txt.gz (453.7 Kb, 22,165 data rows). Verified directly via the GEO series text record (form=text) and by downloading and decompressing both TraCeR files from the GEO FTP site.


### Format Specifics

**Expected Reader Function**:

> read_tracer (per filenames/branding); realistic path is read_airr after remapping to AIRR-TSV, since the deposited files are TraCeR's flattened summarise-step output rather than the per-cell pickle directory read_tracer() parses

- **Native Vs Flattened Output**: flattened summary table

**File Structure Notes**:

> Confirmed by direct inspection of decompressed file contents. GSE270928_TraCeR_filtered_cell_data_HT_SS3.csv.gz is a CSV with columns cell_name, A_unproductive, A_productive, B_unproductive, B_productive, clonal_group, group_size (one row per cell, 6,311 cells) — this matches TraCeR's own 'summarise' step 'cell_data.csv' output. GSE270928_TraCeR_filtered_recombinants_HT_SS3.txt.gz is a TSV with columns cell_name, locus, recombinant_id, productive, reconstructed_length, CDR3aa, CDR3nt (22,165 rows, one row per reconstructed recombinant; loci observed: A, B) — matches TraCeR's 'recombinants.txt' summarise output. Both are per-run aggregate summary tables, not the native filtered_TCR_seqs/<cell_name>/*.pkl per-cell directory structure that scirpy's read_tracer() expects to walk. recombinant_id embeds V/J gene calls and the junction nucleotide substring (e.g. 'TRAV6_CTAGATAATTCAGG_TRAJ6'), and CDR3aa/CDR3nt/productive are given directly per recombinant, so v_call, j_call, locus (A/B -> TRA/TRB), junction, junction_aa, productive, and cell_id could all be programmatically derived to build an AIRR rearrangement TSV for read_airr(). Full V(D)J contig sequence/alignment fields are NOT present in either flattened file (only the CDR3 nt substring), so a remapped AIRR-TSV would carry only the minimal/junction-level fields, not the full sequence/sequence_alignment fields.


### Sample Context

- **Species**: Homo sapiens

**Tissue Disease**:

> Peripheral blood mononuclear cell (PBMC)-derived, FACS-sorted CD4+ T cells from 2 healthy donors; DMSO vehicle control vs. PMA/Ionomycin stimulation (3 h), no disease state

**Single Cell Platform**:

> HT Smart-seq3 (automated, robotic high-throughput Smart-seq3; full-length plate-based scRNA-seq, not droplet-based)

**Species And Chain Coverage**:

> TCR-only (no BCR); paired alpha/beta (TRA and TRB) chains recovered per cell where reconstructable, with unproductive and productive rearrangements both reported for each chain

**Linked Gex Modality**:

> Yes — matched full-length gene expression from the same cells is deposited in the same GSE as GSE270928_Seurat_Object_HT_SS3.rds.gz (Seurat object), so a scirpy MuData with both gex and airr modalities is in principle buildable, though the GEX side would need converting out of the Seurat/RDS format for a Python/scirpy workflow.


### Loadability

**Loadability Confidence**:

> Low for read_tracer() directly on the deposited files (wrong structure — flattened tables, not the per-cell pickle directory). Medium-to-high for read_airr() after a remapping script, since cell_name, locus, parseable V/J gene calls, productive flag, and CDR3aa/CDR3nt are all present at recombinant-level granularity in GSE270928_TraCeR_filtered_recombinants_HT_SS3.txt.gz.

**File Completeness Caveat**:

> Files are TraCeR's own aggregate 'summarise' output (cell_data.csv + recombinants.txt), not its native per-cell filtered_TCR_seqs/<cell>/*.pkl output that read_tracer() expects; no full reconstructed V(D)J contig sequences are included (only CDR3 nt/aa), so any AIRR-TSV built from these files will lack sequence/sequence_alignment-level fields.

**Reformatting Needed**:

> Parse recombinant_id in the recombinants file to split out v_call and j_call gene segments (delimited by underscores around the junction nt substring); map locus values A/B to TRA/TRB; join productive, CDR3aa (junction_aa), CDR3nt (junction), and cell_name (cell_id) into one row per rearrangement; assemble into a minimal AIRR rearrangement TSV (cell_id, locus, v_call, j_call, junction, junction_aa, productive at minimum) that read_airr() can consume. The cell_data.csv clonal_group/group_size columns could optionally be carried through as auxiliary per-cell clonotype metadata.


### Provenance

**Verification Method**:

> GEO supplementary-file listing fetched directly from the NCBI GEO series text record (acc.cgi form=text) and cross-checked against the rendered GEO web page; both TraCeR supplementary files were additionally downloaded directly from the GEO FTP site and decompressed to inspect actual column headers and row counts (not inferred from the paper text alone). Publication metadata (title/authors/journal/DOI/PMID) and the TraCeR version/module usage were confirmed from the open-access full text on PMC (PMC11583680).


### Uncertain Fields

- authors
- pipeline_version
