#!/bin/bash
# One-shot bootstrap for a fresh clone: host-side model provisioning +
# the agent container + the bits that are gitignored and therefore absent
# after `git clone`. Safe to re-run - every step is a no-op if already done.
#
# Usage:
#   ./setup.sh                                   # provision the harness default model (qwen3.6-128k)
#   ./setup.sh --models qwen3.6-128k glm-4.7-flash-128k
#   ./setup.sh --all-models                      # every *-128k model declared in docker-agent/opencode.json
#   ./setup.sh --skip-models                     # container + skills symlink only
#   ./setup.sh --skip-container                  # host side only (no Docker needed)
#   ./setup.sh --with-host-opencode              # also npm-install opencode on the host (normally unnecessary)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OPENCODE_JSON="$SCRIPT_DIR/docker-agent/opencode.json"
AGENT_DOCKERFILE="$SCRIPT_DIR/docker-agent/Dockerfile"
DEFAULT_MODELS=(qwen3.6-128k)

log() { echo ">> $*"; }
warn() { echo ">> WARNING: $*" >&2; }
die() { echo "ERROR: $*" >&2; exit 1; }

# --- argument parsing ---
MODELS=()
ALL_MODELS=0
SKIP_MODELS=0
SKIP_CONTAINER=0
HOST_OPENCODE=0

while (( $# )); do
  case "$1" in
    --models)
      shift
      # everything up to the next flag is a model name
      while (( $# )) && [[ "$1" != --* ]]; do MODELS+=("$1"); shift; done
      ;;
    --all-models)     ALL_MODELS=1; shift ;;
    --skip-models)    SKIP_MODELS=1; shift ;;
    --skip-container) SKIP_CONTAINER=1; shift ;;
    --with-host-opencode) HOST_OPENCODE=1; shift ;;
    -h|--help)
      sed -n '2,12p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
      exit 0
      ;;
    *) die "Unknown argument: $1 (try --help)" ;;
  esac
done

command -v python3 >/dev/null 2>&1 || die "python3 isn't on PATH - needed to read docker-agent/opencode.json and to run test/test.py."
[[ -f "$OPENCODE_JSON" ]] || die "Missing $OPENCODE_JSON - are you running this from a complete clone?"

# opencode.json is the single source of truth for which models exist and
# what context window each one claims, so the Modelfile's num_ctx and
# opencode's declared `limit.context` can't drift apart (they must match,
# or auto-compaction never fires - see docker-agent/README.md).
model_context() {
  python3 -c "
import json, sys
cfg = json.load(open('$OPENCODE_JSON'))
m = cfg['provider']['host']['models'].get(sys.argv[1])
print(m['limit']['context'] if m and 'limit' in m else '')
" "$1"
}

all_derived_models() {
  python3 -c "
import json
cfg = json.load(open('$OPENCODE_JSON'))
print('\n'.join(n for n in cfg['provider']['host']['models'] if n.endswith('-128k')))
"
}

# =====================================================================
# 1. Host models (Ollama)
# =====================================================================
if (( SKIP_MODELS )); then
  log "Skipping model provisioning (--skip-models)."
else
  if (( ALL_MODELS )); then
    mapfile -t MODELS < <(all_derived_models)
  elif (( ${#MODELS[@]} == 0 )); then
    MODELS=("${DEFAULT_MODELS[@]}")
  fi

  command -v ollama >/dev/null 2>&1 || die "Ollama isn't installed. Linux/WSL2: curl -fsSL https://ollama.com/install.sh | sh   macOS: brew install ollama (or https://ollama.com/download). Then re-run this script."

  # The models below are created through the server, not just on disk, so
  # it has to actually be up before we start.
  if ! curl -s -m 3 http://localhost:11434/api/tags >/dev/null 2>&1; then
    log "Nothing answering on localhost:11434 - starting 'ollama serve' in the background..."
    nohup ollama serve >/tmp/ollama-serve.log 2>&1 &
    for _ in $(seq 1 30); do
      curl -s -m 2 http://localhost:11434/api/tags >/dev/null 2>&1 && break
      sleep 1
    done
    curl -s -m 3 http://localhost:11434/api/tags >/dev/null 2>&1 \
      || die "Ollama still isn't answering on 11434 after 30s - see /tmp/ollama-serve.log, start it yourself with 'ollama serve', and re-run."
  fi
  log "Ollama is serving on localhost:11434."

  have_model() {
    ollama list | awk 'NR>1{print $1}' | grep -qxE "$1|$1:latest"
  }

  for model in "${MODELS[@]}"; do
    ctx="$(model_context "$model")"
    [[ -n "$ctx" ]] || die "'$model' has no entry (with a limit.context) in $OPENCODE_JSON. Add one first - opencode can't reference a model that isn't declared there."

    if have_model "$model"; then
      log "$model already present - skipping."
      continue
    fi

    if [[ "$model" == *-128k ]]; then
      base="${model%-128k}"
      # Derived model: same weights as the base, only the loaded context
      # window differs. Ollama caps a loaded model at 32768 tokens
      # regardless of architecture support, and blows past it silently -
      # see docker-agent/README.md's context window note.
      if ! have_model "$base"; then
        log "Pulling base model '$base' (this is the big download)..."
        ollama pull "$base" || die "Couldn't pull '$base'. If it's local-only, make sure it's under ~/.ollama/models and re-run."
      fi
      modelfile="$(mktemp)"
      printf 'FROM %s:latest\nPARAMETER num_ctx %s\n' "$base" "$ctx" >"$modelfile"
      log "Creating '$model' from '$base' with num_ctx=$ctx (no re-download - same blobs)..."
      ollama create "$model" -f "$modelfile" || { rm -f "$modelfile"; die "'ollama create $model' failed."; }
      rm -f "$modelfile"
      ollama show "$model" --parameters 2>/dev/null | grep -q "num_ctx *$ctx" \
        || warn "'$model' was created but doesn't report num_ctx=$ctx - check 'ollama show $model --parameters'."
    else
      log "Pulling '$model'..."
      ollama pull "$model" || die "Couldn't pull '$model'."
    fi
    log "$model ready."
  done
fi

# =====================================================================
# 2. Skills symlink (.claude/skills -> skills/, gitignored)
# =====================================================================
# skills/ is the single source of truth; Claude Code itself reads
# .claude/skills, which is gitignored and so absent on a fresh clone.
# (test/test.py mounts skills/ directly and doesn't need this.)
mkdir -p "$SCRIPT_DIR/.claude"
skills_link="$SCRIPT_DIR/.claude/skills"
if [[ -L "$skills_link" ]]; then
  log ".claude/skills symlink already exists."
elif [[ -e "$skills_link" ]]; then
  warn ".claude/skills exists but isn't a symlink - leaving it alone. Remove it and re-run if you want it pointed at skills/."
else
  ln -s ../skills "$skills_link"
  log "Linked .claude/skills -> skills/."
fi

# =====================================================================
# 3. Agent container image
# =====================================================================
if (( SKIP_CONTAINER )); then
  log "Skipping the agent container (--skip-container)."
else
  command -v docker >/dev/null 2>&1 || die "Docker isn't installed. Get it from https://www.docker.com/products/docker-desktop/ and re-run (or pass --skip-container)."
  docker info >/dev/null 2>&1 || die "Docker daemon isn't running - start it and re-run (or pass --skip-container)."
  log "Building and starting the agent container (docker-agent/setup.sh)..."
  "$SCRIPT_DIR/docker-agent/setup.sh"
fi

# =====================================================================
# 4. Optional: opencode on the host
# =====================================================================
# The container already ships opencode - a host install is only needed for
# running it natively outside the sandbox. Pinned to the same version the
# container uses so benchmark output isn't confounded by version drift.
if (( HOST_OPENCODE )); then
  pinned="$(grep -o 'opencode-ai@[0-9.]*' "$AGENT_DOCKERFILE" | head -1)"
  if command -v npm >/dev/null 2>&1 && npm --version >/dev/null 2>&1; then
    log "Installing $pinned on the host..."
    npm install -g "$pinned" || warn "Host opencode install failed - not fatal, the container has its own."
  else
    warn "npm isn't usable on this host - skipping the host opencode install. The container has its own copy, so this only matters if you wanted to run opencode natively."
  fi
fi

# =====================================================================
# 5. Eval task data (not git-tracked - has to be supplied by hand)
# =====================================================================
missing_data=()
for task_dir in "$SCRIPT_DIR"/test/*/; do
  [[ -f "$task_dir/task.json" ]] || continue
  [[ -d "$task_dir/data" ]] || missing_data+=("$(basename "$task_dir")")
done
if (( ${#missing_data[@]} )); then
  echo
  warn "These eval tasks have no data/ directory (it's gitignored - supply it separately before running them):"
  printf '     %s\n' "${missing_data[@]}" >&2
fi

echo
log "Setup complete."
if (( ! SKIP_CONTAINER )); then
  log "Interactive agent:  ./docker-agent/chat.sh host/${MODELS[0]:-qwen3.6-128k}"
  log "Eval harness:       cd test && ./test.py 01-data-loading --skills"
fi
