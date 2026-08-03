#!/bin/bash
# Interactive pi session inside the isolated container, talking to the
# host's llama.cpp router.
#
#   ./chat.sh                 # use whatever model the router already has loaded
#   ./chat.sh <model-id>      # pick one explicitly (must already be loaded)
#
# Only *loaded* models are selectable - the router serves nothing else. Load
# one with `./llama-server.sh --load <id>`, or from inside pi with /llama.
set -euo pipefail

PORT="${LLAMA_PORT:-8080}"
API="http://127.0.0.1:$PORT"
MODEL="${1:-}"

die() { echo "ERROR: $*" >&2; exit 1; }

docker ps --format '{{.Names}}' 2>/dev/null | grep -qx pytcr-agent \
  || die "Container 'pytcr-agent' isn't running. Start it with: ./docker-agent/setup.sh"

if [[ -z "$MODEL" ]]; then
  MODEL="$(curl -s -m 5 "$API/models" 2>/dev/null | python3 -c '
import json, sys
try:
    loaded = [m["id"] for m in json.load(sys.stdin)["data"] if m["status"]["value"] == "loaded"]
except Exception:
    loaded = []
print(loaded[0] if loaded else "")
' 2>/dev/null)"

  [[ -n "$MODEL" ]] || die "No model is loaded on $API.
  Start the server and load one:  ./docker-agent/llama-server.sh --load <model-id>
  List what's available:          ./docker-agent/llama-server.sh --list"
fi

# Provider id is `llama-cpp` (hyphen) - that's what the pi-llama package
# registers, distinct from pi's own built-in `llama.cpp` extension.
echo ">> model: $MODEL"
exec docker exec -it pytcr-agent pi --provider llama-cpp --model "$MODEL"
