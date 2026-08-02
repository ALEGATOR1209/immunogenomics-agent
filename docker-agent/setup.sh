#!/bin/bash
# Builds and starts the isolated opencode container, which talks to the
# host's native `ollama serve` over host.docker.internal rather than
# running any model itself. Safe to re-run.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_FILE="$SCRIPT_DIR/docker-compose.yml"
CONTAINER_NAME="pytcr-agent"
# The model chat.sh (and test/test.py) default to. It's a derived model -
# see the context window note in README.md - so it won't exist just from an
# `ollama pull`; ../setup.sh creates it.
DEFAULT_MODEL="qwen3.6-128k"

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
if ! curl -s -m 3 http://localhost:11434/api/tags >/dev/null 2>&1; then
  log "WARNING: nothing answering on host port 11434. Start it with:"
  echo "    ollama serve"
  echo "  (or, if it's already running, check it's actually bound to 11434 - see 'ollama list' / your opencode.json)."
  log "Continuing anyway - the container will build fine, it just won't have anything to talk to yet."
elif ! curl -s -m 3 http://localhost:11434/api/tags | grep -q "\"$DEFAULT_MODEL" ; then
  log "WARNING: the host is serving, but '$DEFAULT_MODEL' (what chat.sh and test/test.py default to) isn't among its models."
  echo "    Create it with:  ../setup.sh --models $DEFAULT_MODEL"
  echo "  (or pass an existing model explicitly: ./docker-agent/chat.sh host/<model>)."
fi

# --- 3. Build and start ---
log "Building and starting the container..."
docker compose -f "$COMPOSE_FILE" up -d --build

for _ in $(seq 1 15); do
  docker exec "$CONTAINER_NAME" true >/dev/null 2>&1 && break
  sleep 1
done
docker exec "$CONTAINER_NAME" true >/dev/null 2>&1 || die "Container didn't come up - check 'docker logs $CONTAINER_NAME'."

echo
log "Done. The isolated agent container is running."
log "Chat with it:  ./docker-agent/chat.sh"
