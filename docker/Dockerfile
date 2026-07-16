FROM ollama/ollama:latest

# curl/jq for talking to the API from inside the container
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl jq \
    && rm -rf /var/lib/apt/lists/*

# Point Ollama at a models dir we bind-mount from the host, so the
# already-pulled qwen3.6 blobs (~23GB) don't need to be re-downloaded
# or copied into the image.
ENV OLLAMA_MODELS=/root/.ollama/models
ENV OLLAMA_HOST=0.0.0.0:11434
