#!/bin/bash
# Builds and starts the isolated pi container, which talks to the host's
# llama.cpp router over host.docker.internal rather than running any model
# itself. Safe to re-run.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_FILE="$SCRIPT_DIR/docker-compose.yml"
CONTAINER_NAME="pytcr-agent"
PORT="${LLAMA_PORT:-8080}"
API="http://127.0.0.1:$PORT"

log() { echo ">> $*"; }
die() { echo "ERROR: $*" >&2; exit 1; }

# --- 1. Docker CLI + daemon ---
command -v docker >/dev/null 2>&1 || die "Docker isn't installed. Get it from https://www.docker.com/products/docker-desktop/ and re-run this script."

if ! docker info >/dev/null 2>&1; then
  log "Docker daemon isn't running."
  if [[ "$(uname -s)" == "Darwin" ]]; then
    log "Attempting to start Docker Desktop..."
    open -a Docker 2>/dev/null || die "Couldn't launch Docker Desktop automatically. Start it manually and re-run this script."
  else
    die "Start the Docker daemon and re-run this script."
  fi
  for _ in $(seq 1 60); do
    docker info >/dev/null 2>&1 && break
    sleep 2
  done
  docker info >/dev/null 2>&1 || die "Docker still isn't responding after 2 minutes."
fi
log "Docker is running."

# --- 2. The host needs to actually be serving a model for this to be useful ---
if ! curl -s -m 3 "$API/models" >/dev/null 2>&1; then
  log "WARNING: no llama.cpp router answering on host port $PORT. Start it with:"
  echo "    ./docker-agent/llama-server.sh"
  log "Continuing anyway - the container builds fine, it just won't have anything to talk to yet."
else
  loaded="$(curl -s -m 5 "$API/models" | python3 -c '
import json, sys
try:
    print(sum(1 for m in json.load(sys.stdin)["data"] if m["status"]["value"] == "loaded"))
except Exception:
    print(0)
' 2>/dev/null || echo 0)"
  if [[ "$loaded" == "0" ]]; then
    log "Router is up on $PORT but has no model loaded (pi can only select loaded models)."
    echo "    Load one:  ./docker-agent/llama-server.sh --load <model-id>"
    echo "    See ids:   ./docker-agent/llama-server.sh --list"
  else
    log "Router is up on $PORT with $loaded model(s) loaded."
  fi

  # A router bound to 127.0.0.1 answers here but is invisible to the
  # container - the single most common failure mode of this setup.
  if ! ss -ltn 2>/dev/null | grep -qE "(0\.0\.0\.0|\*):$PORT " ; then
    log "WARNING: the router looks bound to loopback only, so the container won't reach it"
    log "         via host.docker.internal. Restart it with ./docker-agent/llama-server.sh"
    log "         (which binds 0.0.0.0 by default)."
  fi
fi

# --- 3. Build and start ---
log "Building and starting the container..."
docker compose -f "$COMPOSE_FILE" up -d --build

for _ in $(seq 1 15); do
  docker exec "$CONTAINER_NAME" true >/dev/null 2>&1 && break
  sleep 1
done
docker exec "$CONTAINER_NAME" true >/dev/null 2>&1 || die "Container didn't come up - check 'docker logs $CONTAINER_NAME'."

# --- 4. Prove the container can actually see the host's router ---
if docker exec "$CONTAINER_NAME" curl -s -m 5 http://host.docker.internal:"$PORT"/models >/dev/null 2>&1; then
  log "Container can reach the host's router. Good."
else
  log "WARNING: the container cannot reach http://host.docker.internal:$PORT from inside."
  log "         Check the router's bind address (must be 0.0.0.0) and any host firewall."
fi

echo
log "Done. The isolated agent container is running."
log "Chat with it:  ./docker-agent/chat.sh"
