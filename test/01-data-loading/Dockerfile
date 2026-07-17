ARG BASE_IMAGE=pytcr-agent:latest
FROM ${BASE_IMAGE}

# Miniforge (conda + mamba, conda-forge-first): mamba resolves the
# bioconda/conda-forge scanpy+scirpy stack far faster and more reliably
# than the classic conda solver.
RUN apt-get update \
    && apt-get install -y --no-install-recommends wget bzip2 ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && wget -qO /tmp/miniforge.sh "https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-$(uname -m).sh" \
    && bash /tmp/miniforge.sh -b -p /opt/conda \
    && rm /tmp/miniforge.sh

# environment.yml lives at test/environment.yml, one level up from this
# task directory - the build context is test/ (see `docker build -f`
# below), so it's visible here as a context-root file.
COPY environment.yml /tmp/environment.yml
RUN /opt/conda/bin/mamba env create -f /tmp/environment.yml \
    && /opt/conda/bin/conda clean -afy

# Make the task's conda env (name: pytcr, from environment.yml) the
# default on PATH for every process in the container, including the
# bash/python calls opencode's agent makes - no `conda activate` needed.
ENV PATH=/opt/conda/envs/pytcr/bin:$PATH
