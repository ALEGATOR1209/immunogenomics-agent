#!/bin/bash
# Interactive opencode session inside the isolated container, talking to
# the host's native ollama serve.
set -euo pipefail

MODEL="${1:-host/qwen3.6}"

docker exec -it pytcr-agent opencode --model "$MODEL"
