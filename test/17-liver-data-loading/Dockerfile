ARG BASE_IMAGE=pytcr-agent:latest
FROM ${BASE_IMAGE}

# Miniforge (conda + mamba, conda-forge-first): mamba resolves the
# bioconda/conda-forge scanpy+scirpy stack far faster and more reliably
# than the classic conda solver. gzip: task data ships as .csv.gz/.mtx.gz -
# guaranteed here rather than left to whatever the base image happens to
# bundle, so the agent never has to install it itself mid-task.
RUN apt-get update \
    && apt-get install -y --no-install-recommends wget bzip2 gzip ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && wget -qO /tmp/miniforge.sh "https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-$(uname -m).sh" \
    && bash /tmp/miniforge.sh -b -p /opt/conda \
    && rm /tmp/miniforge.sh

# environment.yml lives at test/environment.yml, one level up from this
# task directory - the build context is test/ (see `docker build -f`
# below), so it's visible here as a context-root file.
# channel_priority flexible: strict (Miniforge's default) refuses to mix
# bioconda's scirpy>=0.24 with conda-forge's anndata>=0.9 it depends on,
# even though both are installable together - see the solver's own
# "Could not solve for environment specs" error without this.
COPY environment.yml /tmp/environment.yml
RUN /opt/conda/bin/conda config --set channel_priority flexible \
    && /opt/conda/bin/mamba env create -f /tmp/environment.yml \
    && /opt/conda/bin/conda clean -afy

# R, in a separate env (name: r, from environment-r.yml) so its solve can't
# disturb the Python stack above, then the immune-repertoire R packages from
# CRAN/Bioconductor source (install_r_packages.R fails the build if any is
# missing). Kept after the Python layer so changing R packages doesn't
# rebuild the Python env.
# The R env is ~600 MB of downloads, and conda's CDN has dropped connections
# mid-transfer while building it (SSL EOFs, a stalled download timing out),
# failing the whole layer. So: more per-file retries, and up to 3 attempts at
# the env, removing the half-created env between them; packages already
# downloaded stay in the package cache, so a retry only fetches what's missing.
COPY environment-r.yml /tmp/environment-r.yml
RUN /opt/conda/bin/conda config --set remote_max_retries 10 \
    && for attempt in 1 2 3; do \
         /opt/conda/bin/mamba env create -y -f /tmp/environment-r.yml && break; \
         [ "$attempt" = 3 ] && exit 1; \
         echo "R env attempt $attempt failed, retrying"; rm -rf /opt/conda/envs/r; sleep 10; \
       done \
    && /opt/conda/bin/conda clean -afy
# duckdb (needed by immunarch, via duckplyr) has no aarch64 conda build, so
# it's compiled from source - on every architecture, so the images match.
# It's by far the slowest build (a large C++ library), hence its own layer,
# cached independently of install_r_packages.R, and MAKEFLAGS to compile it
# on all cores. `mamba run` activates the env, which is what puts the conda
# compilers and make on PATH (and sets CC/CXX) for the source builds.
RUN MAKEFLAGS="-j$(nproc)" /opt/conda/bin/mamba run -n r Rscript -e \
      'install.packages("duckdb", repos = "https://cloud.r-project.org"); library(duckdb)'
COPY install_r_packages.R /tmp/install_r_packages.R
RUN /opt/conda/bin/mamba run -n r Rscript /tmp/install_r_packages.R

# Register R as a Jupyter kernel in the Python env's Jupyter, so the agent
# can write R notebooks and execute them with nbconvert like Python ones.
RUN PATH=/opt/conda/envs/pytcr/bin:$PATH \
    /opt/conda/envs/r/bin/Rscript -e 'IRkernel::installspec(user = FALSE, prefix = "/opt/conda/envs/pytcr")'

# Make the task's conda envs the default on PATH for every process in the
# container, including the bash/python/R calls pi's agent makes - no
# `conda activate` needed. pytcr comes first, so `python`/`jupyter` resolve
# there; the r env adds `R`/`Rscript`.
ENV PATH=/opt/conda/envs/pytcr/bin:/opt/conda/envs/r/bin:$PATH
