#!/bin/bash
# Prepares pi's state directory on the writable volume and reports whether
# the host's llama.cpp router is actually reachable, so an unreachable model
# server surfaces here rather than as a confusing failure mid-session.
# Non-fatal by design: the container still starts and is still useful when
# the server isn't up yet.
set -euo pipefail

STAGE="${PI_STAGE_HOME:-/opt/pi-home}"
PKG_PATH=/root/.pi/agent/git/github.com/huggingface/pi-llama

mkdir -p /root/.pi/agent

# The named volume mounted at /root is empty on first boot, hiding whatever
# the image installed there. Copy the staged pi-llama package (and its
# settings entry) across once. Existing settings are never overwritten, so
# anything configured from inside a session survives restarts; wipe the
# volume (docker compose down -v) to pick up an updated package from a
# rebuilt image.
if [[ ! -e "$PKG_PATH" && -d "$STAGE/.pi/agent" ]]; then
  echo ">> first boot: installing the pi-llama provider package into the state volume"
  cp -a "$STAGE/.pi/agent/git" /root/.pi/agent/ 2>/dev/null || true
  [[ -f /root/.pi/agent/settings.json ]] \
    || cp "$STAGE/.pi/agent/settings.json" /root/.pi/agent/settings.json
fi

if [[ -n "${LLAMA_BASE_URL:-}" ]]; then
  if curl -s -m 3 "${LLAMA_BASE_URL%/}/models" >/dev/null 2>&1; then
    echo ">> model server reachable at $LLAMA_BASE_URL"
  else
    echo ">> WARNING: nothing answering at $LLAMA_BASE_URL"
    echo ">> Start it on the host with:  ./docker-agent/llama-server.sh"
    echo ">> (it must bind 0.0.0.0, not 127.0.0.1, or the container can't reach it)"
  fi
else
  echo ">> WARNING: LLAMA_BASE_URL is unset - pi's llama.cpp provider has no server to talk to."
fi

exec "$@"
