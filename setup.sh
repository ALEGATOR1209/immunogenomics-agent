#!/bin/bash
# One-shot bootstrap for a fresh clone: host-side model server checks + the
# agent container + the bits that are gitignored and therefore absent after
# `git clone`. Safe to re-run - every step is a no-op if already done.
#
# Usage:
#   ./setup.sh                                   # check the host model server, build the container, link skills
#   ./setup.sh --models unsloth/Qwen3-Coder-30B-A3B-Instruct-GGUF:Q4_K_XL
#   ./setup.sh --skip-models                     # container + skills symlink only
#   ./setup.sh --skip-container                  # host side only (no Docker needed)
#   ./setup.sh --with-host-pi                    # also npm-install pi on the host (normally unnecessary)
#
# Models are served by llama.cpp's router on the host, not by Ollama. Which
# models exist and what flags each loads with is declared in
# ~/.config/llama.cpp/presets.ini (or any GGUF under ~/models) - see
# docker-agent/README.md.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AGENT_DOCKERFILE="$SCRIPT_DIR/docker-agent/Dockerfile"
LLAMA_PORT="${LLAMA_PORT:-8080}"
API="http://127.0.0.1:$LLAMA_PORT"

log() { echo ">> $*"; }
warn() { echo ">> WARNING: $*" >&2; }
die() { echo "ERROR: $*" >&2; exit 1; }

# --- argument parsing ---
MODELS=()
SKIP_MODELS=0
SKIP_CONTAINER=0
HOST_PI=0

while (( $# )); do
  case "$1" in
    --models)
      shift
      while (( $# )) && [[ "$1" != --* ]]; do MODELS+=("$1"); shift; done
      ;;
    --skip-models)    SKIP_MODELS=1; shift ;;
    --skip-container) SKIP_CONTAINER=1; shift ;;
    --with-host-pi)   HOST_PI=1; shift ;;
    -h|--help)
      sed -n '2,16p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
      exit 0
      ;;
    *) die "Unknown argument: $1 (try --help)" ;;
  esac
done

command -v python3 >/dev/null 2>&1 || die "python3 isn't on PATH - needed to talk to the model router and to run test/test.py."

router_up() { curl -s -m 3 "$API/models" >/dev/null 2>&1; }

# =====================================================================
# 1. Host model server (llama.cpp)
# =====================================================================
if (( SKIP_MODELS )); then
  log "Skipping model-server checks (--skip-models)."
else
  if ! command -v llama >/dev/null 2>&1; then
    warn "'llama' isn't on PATH. Build llama.cpp and link its binaries, e.g.:"
    echo "     cmake -S <llama.cpp> -B build -G Ninja -DCMAKE_BUILD_TYPE=Release \\"
    echo "           -DGGML_CUDA=ON -DCMAKE_CUDA_ARCHITECTURES=<your-arch> -DLLAMA_CURL=ON"
    echo "     cmake --build build -j\"\$(nproc)\""
    echo "     ln -s <llama.cpp>/build/bin/llama* ~/.local/bin/"
    echo
    echo "   Build against CUDA 12.x, not 13.x: the CUDA 13 prebuilts fail"
    echo "   cublasCreate_v2 on any prompt long enough to take the cuBLAS path."
    echo "   See docker-agent/README.md."
  else
    log "llama binary: $(command -v llama) ($(llama --version 2>&1 | head -1))"
  fi

  if router_up; then
    log "Model router answering on $API:"
    curl -s -m 5 "$API/models" | python3 -c '
import json, sys
try:
    data = json.load(sys.stdin)["data"]
except Exception:
    print("     (unreadable response)"); sys.exit(0)
if not data:
    print("     (no models discovered)")
for m in data:
    print("     [%8s] %s" % (m["status"]["value"], m["id"]))
' || true
  else
    warn "No model router answering on $API. Start one with:"
    echo "     ./docker-agent/llama-server.sh --load <model-id>"
  fi

  # Downloading is done by the router itself (POST /models with a HF repo
  # id), so it has to be running for this.
  for model in "${MODELS[@]+"${MODELS[@]}"}"; do
    router_up || die "--models needs a running router. Start it: ./docker-agent/llama-server.sh"
    log "Asking the router to fetch '$model' (large download; skipped if already cached)..."
    curl -s -m 3600 -X POST "$API/models" \
      -H 'Content-Type: application/json' \
      -d "{\"model\":\"$model\"}" >/dev/null \
      || warn "Fetch request for '$model' failed - check the id (owner/repo[:quant])."
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
# 4. Optional: pi on the host
# =====================================================================
# The container already ships pi - a host install is only needed for running
# it natively outside the sandbox. Pinned to the same version the container
# uses so benchmark output isn't confounded by version drift.
if (( HOST_PI )); then
  pinned="$(grep -o '@earendil-works/pi-coding-agent@[0-9.]*' "$AGENT_DOCKERFILE" | head -1)"
  if command -v npm >/dev/null 2>&1 && npm --version >/dev/null 2>&1; then
    log "Installing $pinned on the host..."
    npm install -g "$pinned" || warn "Host pi install failed - not fatal, the container has its own."
    # The llama.cpp provider is a separate package; without it pi reports
    # "No models available" no matter how LLAMA_BASE_URL is set.
    log "Installing the llama.cpp provider package..."
    pi install git:github.com/huggingface/pi-llama || warn "pi-llama install failed - pi won't see the llama.cpp router until it succeeds."
  else
    warn "npm isn't usable on this host - skipping the host pi install. The container has its own copy, so this only matters if you wanted to run pi natively."
  fi
fi

# =====================================================================
# 5. Eval task data (not git-tracked - fetched automatically where task.json
#    declares a source, otherwise has to be supplied by hand)
# =====================================================================
missing_data_auto=()
missing_data_manual=()
for task_dir in "$SCRIPT_DIR"/test/*/; do
  [[ -f "$task_dir/task.json" ]] || continue
  [[ -d "$task_dir/data" ]] && continue
  if python3 -c 'import json,sys; sys.exit(0 if json.load(open(sys.argv[1])).get("data") else 1)' "$task_dir/task.json" 2>/dev/null; then
    missing_data_auto+=("$(basename "$task_dir")")
  else
    missing_data_manual+=("$(basename "$task_dir")")
  fi
done
if (( ${#missing_data_auto[@]} )); then
  echo
  warn "These eval tasks have no data/ directory but declare a source in task.json - fetch it with test/fetch_data.py <task>, or it'll be fetched automatically on the first test.py run:"
  printf '     %s\n' "${missing_data_auto[@]+"${missing_data_auto[@]}"}" >&2
fi
if (( ${#missing_data_manual[@]} )); then
  echo
  warn "These eval tasks have no data/ directory (it's gitignored - supply it separately before running them):"
  printf '     %s\n' "${missing_data_manual[@]+"${missing_data_manual[@]}"}" >&2
fi

echo
log "Setup complete."
if (( ! SKIP_CONTAINER )); then
  log "Interactive agent:  ./docker-agent/chat.sh"
  log "Eval harness:       cd test && ./test.py 01-data-loading --skills"
fi
