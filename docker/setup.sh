#!/bin/bash
# One-shot setup: builds the isolated Ollama container, makes sure Docker
# has enough memory allocated to actually load the model, starts it, and
# makes sure the model is available inside the container. Safe to re-run.
#
# Usage:
#   ./docker/setup.sh              # loads $MODEL (default: qwen3.6)
#   MODEL=qwen3.5 ./docker/setup.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_FILE="$SCRIPT_DIR/docker-compose.yml"
GPU_COMPOSE_FILE="$SCRIPT_DIR/docker-compose.gpu.yml"

MODEL="${MODEL:-qwen3.6}"
CONTAINER_NAME="pytcr-ollama"
MEMORY_OVERHEAD_GB=3   # headroom above raw model size for KV cache / runtime (rough heuristic - verified empirically for a 24GB Q4 model; bump manually if a load still OOMs)

log() { echo ">> $*"; }
die() { echo "ERROR: $*" >&2; exit 1; }

# --- 1. Docker CLI present? ---
command -v docker >/dev/null 2>&1 || die "Docker isn't installed. Get it from https://www.docker.com/products/docker-desktop/ and re-run this script."

# --- 2. Docker daemon running? ---
if ! docker info >/dev/null 2>&1; then
  log "Docker daemon isn't running."
  if [[ "$(uname -s)" == "Darwin" ]]; then
    log "Attempting to start Docker Desktop..."
    open -a Docker 2>/dev/null || die "Couldn't launch Docker Desktop automatically. Start it manually and re-run this script."
  else
    die "Start the Docker daemon and re-run this script."
  fi
  log "Waiting for Docker to come up..."
  for _ in $(seq 1 60); do
    docker info >/dev/null 2>&1 && break
    sleep 2
  done
  docker info >/dev/null 2>&1 || die "Docker still isn't responding after 2 minutes. Start Docker Desktop manually and re-run."
fi
log "Docker is running."

# --- 3. Figure out how much memory the model needs ---
# If the model is already present on the host (~/.ollama/models), sum its
# manifest layer sizes for an exact figure. Otherwise fall back to a
# generic default (it'll be pulled inside the container instead).
manifest_size_gb() {
  local model="$1"
  local namespace="library" name="$model" tag="latest"
  [[ "$model" == *:* ]] && { name="${model%%:*}"; tag="${model##*:}"; }
  [[ "$name" == */* ]] && { namespace="${name%%/*}"; name="${name##*/}"; }
  local manifest="$HOME/.ollama/models/manifests/registry.ollama.ai/$namespace/$name/$tag"
  [[ -f "$manifest" ]] || return 1
  python3 -c "
import json
d = json.load(open('$manifest'))
total = sum(l['size'] for l in d.get('layers', [])) + d.get('config', {}).get('size', 0)
print(round(total / 1e9))
" 2>/dev/null
}

MODEL_SIZE_GB="$(manifest_size_gb "$MODEL" || echo 20)"
REQUIRED_GB=$((MODEL_SIZE_GB + MEMORY_OVERHEAD_GB))
export MEM_LIMIT_GB="$REQUIRED_GB"
log "Model '$MODEL' needs roughly ${MODEL_SIZE_GB}GB + ${MEMORY_OVERHEAD_GB}GB overhead = ${REQUIRED_GB}GB."

# --- 4. Does Docker's VM have enough memory allocated? ---
docker_mem_bytes() {
  docker info --format '{{.MemTotal}}' 2>/dev/null || echo 0
}

CURRENT_MEM_GB=$(( $(docker_mem_bytes) / 1073741824 ))
if (( CURRENT_MEM_GB < REQUIRED_GB )); then
  log "Docker currently has only ${CURRENT_MEM_GB}GB allocated; need at least ${REQUIRED_GB}GB."
  echo
  echo "  Open Docker Desktop -> Settings -> Resources -> Memory,"
  echo "  raise it to at least ${REQUIRED_GB}GB, then click 'Apply & restart'."
  echo
  log "Waiting for you to do that (checking every 5s, Ctrl+C to abort)..."
  while (( CURRENT_MEM_GB < REQUIRED_GB )); do
    sleep 5
    # Docker Desktop restarts the daemon when settings are applied, so
    # `docker info` may briefly fail during that window - that's fine.
    docker info >/dev/null 2>&1 || continue
    CURRENT_MEM_GB=$(( $(docker_mem_bytes) / 1073741824 ))
  done
fi
log "Docker has ${CURRENT_MEM_GB}GB available. Good."

# --- 5. Detect an NVIDIA GPU (Linux / WSL2 only - macOS never has passthrough) ---
COMPOSE_ARGS=(-f "$COMPOSE_FILE")
USE_GPU=0
if [[ "$(uname -s)" != "Darwin" ]] && command -v nvidia-smi >/dev/null 2>&1 && nvidia-smi >/dev/null 2>&1; then
  USE_GPU=1
  COMPOSE_ARGS+=(-f "$GPU_COMPOSE_FILE")
  log "NVIDIA GPU detected - enabling GPU passthrough (see docker-compose.gpu.yml; unverified on real hardware, first checkout on this kind of host - if it doesn't work, 'docker exec $CONTAINER_NAME nvidia-smi' is the first thing to check)."
else
  log "No NVIDIA GPU detected (or running on macOS, which never has passthrough) - running CPU-only."
fi

# --- 6. Build and start the container ---
log "Building and starting the container..."
docker compose "${COMPOSE_ARGS[@]}" up -d --build

log "Waiting for the container to become healthy..."
for _ in $(seq 1 30); do
  h="$(docker inspect --format='{{.State.Health.Status}}' "$CONTAINER_NAME" 2>/dev/null || echo "unknown")"
  [[ "$h" == "healthy" ]] && break
  [[ "$h" == "unhealthy" ]] && { docker logs "$CONTAINER_NAME" --tail 40; die "Container reported unhealthy - see logs above."; }
  sleep 2
done
[[ "$h" == "healthy" ]] || die "Container never became healthy in time."

if (( USE_GPU )); then
  if docker exec "$CONTAINER_NAME" nvidia-smi >/dev/null 2>&1; then
    log "GPU passthrough confirmed working inside the container."
  else
    log "WARNING: GPU was detected on the host but 'nvidia-smi' failed inside the container - it's likely running CPU-only. Check that nvidia-container-toolkit is installed and configured (https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html)."
  fi
fi

# --- 7. Make sure the model is actually loaded inside the container ---
if ! docker exec "$CONTAINER_NAME" ollama list | awk 'NR>1{print $1}' | grep -qxE "${MODEL}:latest|${MODEL}"; then
  log "'$MODEL' isn't present yet - pulling it inside the container..."
  docker exec "$CONTAINER_NAME" ollama pull "$MODEL" \
    || die "Couldn't pull '$MODEL'. If this is a custom/local-only model, make sure it's already present under ~/.ollama/models on the host, then re-run this script."
fi

echo
log "Done. '$MODEL' is running, isolated, in the '$CONTAINER_NAME' container."
log "Chat with it:      ./docker/chat.sh $MODEL"
log "Or via the API:    curl http://localhost:11436/api/generate -d '{\"model\":\"$MODEL\",\"prompt\":\"hi\",\"stream\":false}'"
