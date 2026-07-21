#!/bin/bash
# Interactive opencode session inside the isolated container, talking to
# the host's native ollama serve.
set -euo pipefail

MODEL="${1:-host/glm-4.7-flash-128k}"

docker exec -it pytcr-agent opencode --model "$MODEL"
