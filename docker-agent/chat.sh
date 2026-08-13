#!/bin/bash
# Interactive pi session inside the isolated container.
#
#   ./chat.sh                                    # llama-cpp, whatever model the router already has loaded
#   ./chat.sh <model-id>                         # llama-cpp, pick one explicitly (must already be loaded)
#   ./chat.sh --provider anthropic <model-id>    # hosted Claude API instead, e.g. claude-opus-5
#   ./chat.sh --provider openai <model-id>       # hosted OpenAI API instead, e.g. gpt-5.5
#
# With no <model-id>, MODEL from the environment or the repo-root .env is used
# (llama-cpp then falls back to the router's single loaded model).
#
# Only *loaded* models are selectable on llama-cpp - the router serves
# nothing else. Load one with `./llama-server.sh --load <id>`, or from
# inside pi with /llama.
#
# --provider anthropic/openai use pi's *built-in* providers (already present
# in pi-coding-agent's own dependencies - no extra package, unlike llama-cpp's
# pi-llama). Each needs its own key, from this shell or from the repo-root
# .env (below): ANTHROPIC_API_KEY or OPENAI_API_KEY. Only the one belonging to
# the provider in use is passed into the already-running container per
# invocation via `docker exec -e`, the same per-run pattern test.py uses -
# never baked into the image or docker-compose.yml, and never persisted in the
# container.
#
# ANTHROPIC_API_KEY, OPENAI_API_KEY, MODEL and LLAMA_PORT are read from the gitignored .env at
# the repo root when they aren't already set in the shell - the same file
# test/test.py and test/run_all.py read via test/env_file.py, kept in step
# here in plain bash rather than shelling out to Python for it.
set -euo pipefail

die() { echo "ERROR: $*" >&2; exit 1; }

ENV_FILE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/.env"

# Deliberately not `source`d: .env is data, not script - sourcing it would run
# whatever it contains and would also clobber variables already exported here.
load_env_file() {
  [[ -f "$ENV_FILE" ]] || return 0
  local line key value loaded=()
  while IFS= read -r line || [[ -n "$line" ]]; do
    line="${line#"${line%%[![:space:]]*}"}"
    [[ -z "$line" || "$line" == '#'* ]] && continue
    [[ "$line" == 'export '* ]] && line="${line#export }"
    [[ "$line" == *=* ]] || continue
    key="${line%%=*}"
    value="${line#*=}"
    key="${key//[[:space:]]/}"
    [[ "$key" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]] || continue
    value="${value#"${value%%[![:space:]]*}"}"
    value="${value%"${value##*[![:space:]]}"}"
    if [[ ${#value} -ge 2 ]] && { [[ "$value" == \"*\" ]] || [[ "$value" == \'*\' ]]; }; then
      value="${value:1:${#value}-2}"
    fi
    # Already set in the shell wins, exactly as in test/env_file.py.
    [[ -n "${!key+x}" ]] && continue
    export "$key=$value"
    loaded+=("$key")
  done < "$ENV_FILE"
  # Names only - never the values.
  [[ ${#loaded[@]} -eq 0 ]] || echo ">> loaded from $ENV_FILE: ${loaded[*]}"
}
load_env_file

PORT="${LLAMA_PORT:-8080}"
API="http://127.0.0.1:$PORT"

docker ps --format '{{.Names}}' 2>/dev/null | grep -qx pytcr-agent \
  || die "Container 'pytcr-agent' isn't running. Start it with: ./docker-agent/setup.sh"

PROVIDER="llama-cpp"
if [[ "${1:-}" == "--provider" ]]; then
  PROVIDER="${2:-}"
  case "$PROVIDER" in
    llama-cpp|anthropic|openai) ;;
    *) die "Unknown --provider '$PROVIDER' (expected llama-cpp, anthropic or openai)" ;;
  esac
  shift 2
fi

# The env var each hosted provider's credential comes from (the same mapping
# test/test.py keeps in HOSTED_PROVIDER_KEYS), plus an example id for the
# "no model given" error - an example, not a default or a whitelist.
case "$PROVIDER" in
  anthropic) KEY_VAR="ANTHROPIC_API_KEY"; EXAMPLE_MODEL="claude-opus-5" ;;
  openai)    KEY_VAR="OPENAI_API_KEY";    EXAMPLE_MODEL="gpt-5.5" ;;
  *)         KEY_VAR="";                  EXAMPLE_MODEL="" ;;
esac
# Model resolution mirrors test.py's: the argument, else MODEL from the
# environment (or .env), else - for llama-cpp only - the router's single
# loaded model.
MODEL="${1:-${MODEL:-}}"

EXEC_ENV=()
if [[ -n "$KEY_VAR" ]]; then
  [[ -n "$MODEL" ]] || die "No model given for --provider $PROVIDER.
  Pass a model id, e.g.  ./chat.sh --provider $PROVIDER $EXAMPLE_MODEL"
  [[ -n "${!KEY_VAR:-}" ]] \
    || die "$KEY_VAR is not set (shell or $ENV_FILE) - required for --provider $PROVIDER."
  EXEC_ENV=(-e "$KEY_VAR=${!KEY_VAR}")
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
