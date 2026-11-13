# Immune-repertoire R packages, installed from source into the "r" conda env
# at image build time (see environment-r.yml for why not from conda).
# install.packages() only warns when a package fails, so the check at the
# end turns any failure into a failed docker build instead of an image that
# silently lacks the package.
options(
  Ncpus = parallel::detectCores(),
  repos = c(CRAN = "https://cloud.r-project.org")
)

cran <- c("immunarch", "alakazam", "shazam", "tigger", "scoper")
bioc <- c("scRepertoire")

# Everything through BiocManager, so CRAN packages with Bioconductor
# dependencies (shazam needs Biostrings, GenomicAlignments) can resolve them.
# update = FALSE: don't replace the conda-installed packages.
BiocManager::install(c(cran, bioc), ask = FALSE, update = FALSE)

missing <- setdiff(c(cran, bioc), rownames(installed.packages()))
if (length(missing) > 0) {
  stop("Failed to install: ", paste(missing, collapse = ", "))
}
for (p in c(cran, bioc, "Seurat", "SingleCellExperiment", "IRkernel")) {
  suppressPackageStartupMessages(library(p, character.only = TRUE))
}
cat("R packages OK:", paste(c(cran, bioc), collapse = ", "), "\n")
