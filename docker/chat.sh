#!/bin/bash
# Interactive REPL with qwen3.6 running inside the pytcr-ollama container.
set -euo pipefail

MODEL="${1:-qwen3.6}"

docker exec -it pytcr-ollama ollama run "$MODEL"
