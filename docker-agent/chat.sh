#!/bin/bash
# Interactive pi session inside the isolated container.
#
#   ./chat.sh                                    # llama-cpp, whatever model the router already has loaded
#   ./chat.sh <model-id>                         # llama-cpp, pick one explicitly (must already be loaded)
#   ./chat.sh --provider anthropic <model-id>    # hosted Claude API instead, e.g. claude-opus-5
#
# Only *loaded* models are selectable on llama-cpp - the router serves
# nothing else. Load one with `./llama-server.sh --load <id>`, or from
# inside pi with /llama.
#
# --provider anthropic uses pi's *built-in* anthropic provider (already
# present in pi-coding-agent's own dependencies - no extra package, unlike
# llama-cpp's pi-llama). It needs ANTHROPIC_API_KEY set in *this* shell: the
# key is passed into the already-running container per invocation via
# `docker exec -e`, the same per-run pattern test.py uses - never baked into
# the image or docker-compose.yml, and never persisted in the container.
set -euo pipefail

PORT="${LLAMA_PORT:-8080}"
API="http://127.0.0.1:$PORT"

die() { echo "ERROR: $*" >&2; exit 1; }

docker ps --format '{{.Names}}' 2>/dev/null | grep -qx pytcr-agent \
  || die "Container 'pytcr-agent' isn't running. Start it with: ./docker-agent/setup.sh"

PROVIDER="llama-cpp"
if [[ "${1:-}" == "--provider" ]]; then
  PROVIDER="${2:-}"
  [[ "$PROVIDER" == "llama-cpp" || "$PROVIDER" == "anthropic" ]] \
    || die "Unknown --provider '$PROVIDER' (expected llama-cpp or anthropic)"
  shift 2
fi
MODEL="${1:-}"

EXEC_ENV=()
if [[ "$PROVIDER" == "anthropic" ]]; then
  [[ -n "$MODEL" ]] || die "No model given for --provider anthropic.
  Pass a Claude model id, e.g.  ./chat.sh --provider anthropic claude-opus-5"
  [[ -n "${ANTHROPIC_API_KEY:-}" ]] \
    || die "ANTHROPIC_API_KEY is not set in this shell - required for --provider anthropic."
  EXEC_ENV=(-e "ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY")
else
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
fi

# Provider id is `llama-cpp` (hyphen) - that's what the pi-llama package
# registers, distinct from pi's own built-in `llama.cpp` extension. The
# `anthropic` provider is pi's own built-in id.
echo ">> provider: $PROVIDER"
echo ">> model: $MODEL"
exec docker exec "${EXEC_ENV[@]}" -it pytcr-agent pi --provider "$PROVIDER" --model "$MODEL"
