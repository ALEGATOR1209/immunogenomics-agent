#!/bin/bash
# NOT CURRENTLY WORKING - kept for a future retry, not wired into
# docker-agent/opencode.json (which is back on `ollama serve`). Both models
# we tried failed to load: glm-4.7-flash's architecture (glm4moelite) isn't
# recognized by llama.cpp even on the latest Homebrew stable (10050), and
# qwen3.6's GGUF fails on a metadata-schema mismatch (rope.dimension_sections
# array length). See docker-agent/README.md's "Known issue" section before
# retrying - a fix would need fresh GGUFs built against the current
# llama.cpp version, or building llama.cpp from source/HEAD.
#
# Runs llama.cpp's llama-server natively on the host (Metal-accelerated),
# loading the GGUF weights straight out of Ollama's blob store - no
# re-download needed, Ollama's blobs are plain GGUF files.
#
# The intent: replace `ollama serve` as the thing docker-agent's opencode
# container talks to over host.docker.internal, since Ollama's
# OpenAI-compatible endpoint (/v1/chat/completions) silently drops tool
# calls under streaming (upstream bug, ollama/ollama#12557) and llama.cpp's
# own OpenAI-compatible server doesn't have that bug.
#
# Only one model can run at a time (each is 19-23GB; this machine can't
# hold two in memory at once). Re-run this script with a different model
# to switch - it's safe to just Ctrl-C the old one first.
set -euo pipefail

MODEL="${1:-glm-4.7-flash}"
CONTEXT="${2:-131072}"
PORT="${PORT:-8080}"

log() { echo ">> $*"; }
die() { echo "ERROR: $*" >&2; exit 1; }

command -v llama-server >/dev/null 2>&1 || die "llama-server not found. Install with: brew install llama.cpp"
command -v ollama >/dev/null 2>&1 || die "ollama not found - it's only used here to resolve the blob path, not to serve."

BLOB="$(ollama show "$MODEL" --modelfile 2>/dev/null | awk '/^FROM/ {print $2}')"
[[ -n "$BLOB" && -f "$BLOB" ]] || die "Couldn't resolve a GGUF blob for model '$MODEL' (is it pulled? try: ollama pull $MODEL)"

log "Model:   $MODEL"
log "Blob:    $BLOB"
log "Context: $CONTEXT tokens"
log "Port:    $PORT"
log ""
log "--jinja is required for GLM models (without it, tool calls and thinking"
log "blocks come out malformed) - passed unconditionally since it's harmless"
log "for qwen too. Binding 0.0.0.0 so the docker-agent container can reach"
log "this over host.docker.internal (llama-server's default is 127.0.0.1-only,"
log "which Docker Desktop's host networking can't reach)."
log ""

exec llama-server \
  -m "$BLOB" \
  -c "$CONTEXT" \
  --port "$PORT" \
  --host 0.0.0.0 \
  --jinja \
  --reasoning auto \
  --alias "$MODEL"
