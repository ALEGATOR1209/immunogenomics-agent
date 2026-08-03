#!/bin/bash
# Shorthand for launching llama.cpp's router server on the host - the model
# server that docker-agent's pi container talks to over host.docker.internal.
#
# Router mode (no -m/--hf-repo) is deliberate: it discovers every GGUF under
# --models-dir plus every section of --models-preset, and loads/unloads them
# on demand. That's what pi's `/llama` command drives, and it's why per-model
# flags live in presets.ini rather than on this command line.
#
# Usage:
#   ./llama-server.sh                          # start the router, load nothing
#   ./llama-server.sh --load <model-id>        # start it and load one model
#   ./llama-server.sh --list                   # what the running router has
#   ./llama-server.sh --port 8081
#   ./llama-server.sh --bind 127.0.0.1         # local only (container can't reach it)
#   ./llama-server.sh --ctx 65536              # override EVERY model's preset ctx-size
#
# Context size and GPU layers come from each model's section in
# --models-preset. --ctx/--ngl shadow them for every model at once, so leave
# them unset unless that's what you want.
#
# Env equivalents: LLAMA_PORT, LLAMA_BIND, LLAMA_CTX, LLAMA_NGL,
# LLAMA_MODELS_DIR, LLAMA_PRESETS. Flags win over env.
set -euo pipefail

PORT="${LLAMA_PORT:-8080}"
# 0.0.0.0 by default because llama-server's own default (127.0.0.1) is not
# reachable from a container over host.docker.internal - that binding is the
# single most common reason the agent container can't see the model. See the
# LAN-exposure note printed at startup.
BIND="${LLAMA_BIND:-0.0.0.0}"
# Deliberately EMPTY by default. A router-level -c / -ngl overrides the
# per-model ctx-size / n-gpu-layers in presets.ini - verified: with `-c 32768`
# on the router, a preset asking for ctx-size 262144 spawned its child with
# --ctx-size 32768 anyway, silently. Presets own per-model flags; these only
# exist for a deliberate one-off override of every model at once.
CTX="${LLAMA_CTX:-}"
NGL="${LLAMA_NGL:-}"
MODELS_DIR="${LLAMA_MODELS_DIR:-$HOME/models}"
PRESETS="${LLAMA_PRESETS:-$HOME/.config/llama.cpp/presets.ini}"
LOAD=""
LIST_ONLY=0

log() { echo ">> $*"; }
die() { echo "ERROR: $*" >&2; exit 1; }

while [[ $# -gt 0 ]]; do
  case "$1" in
    --load)       LOAD="${2:-}"; [[ -n "$LOAD" ]] || die "--load needs a model id (see --list)"; shift 2 ;;
    --list)       LIST_ONLY=1; shift ;;
    --port)       PORT="${2:?--port needs a value}"; shift 2 ;;
    --bind)       BIND="${2:?--bind needs a value}"; shift 2 ;;
    --ctx)        CTX="${2:?--ctx needs a value}"; shift 2 ;;
    --ngl)        NGL="${2:?--ngl needs a value}"; shift 2 ;;
    --models-dir) MODELS_DIR="${2:?--models-dir needs a value}"; shift 2 ;;
    --preset)     PRESETS="${2:?--preset needs a value}"; shift 2 ;;
    -h|--help)    sed -n '2,20p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *)            die "Unknown argument: $1 (see --help)" ;;
  esac
done

API="http://127.0.0.1:$PORT"

models_json() { curl -s -m 5 "$API/models" 2>/dev/null; }

print_models() {
  models_json | python3 -c '
import json, sys
try:
    data = json.load(sys.stdin)["data"]
except Exception:
    print("  (router not answering)"); sys.exit(0)
if not data:
    print("  (no models discovered - check --models-dir and --preset)")
for m in data:
    print("  [%8s] %s" % (m["status"]["value"], m["id"]))
' 2>/dev/null || echo "  (router not answering)"
}

if [[ $LIST_ONLY -eq 1 ]]; then
  models_json >/dev/null || die "No router answering on $API - start one first."
  log "Models known to the router on $API:"
  print_models
  exit 0
fi

command -v llama >/dev/null 2>&1 \
  || die "'llama' not found on PATH. Build it (see ../README.md) and symlink build/bin/* into ~/.local/bin."

if models_json >/dev/null 2>&1; then
  log "A server is already answering on $API - not starting a second one."
  print_models
  [[ -n "$LOAD" ]] || exit 0
else
  [[ -d "$MODELS_DIR" ]] || { log "Creating models dir: $MODELS_DIR"; mkdir -p "$MODELS_DIR"; }

  PRESET_ARGS=()
  if [[ -f "$PRESETS" ]]; then
    PRESET_ARGS=(--models-preset "$PRESETS")
    log "Presets:    $PRESETS"
  else
    log "Presets:    (none at $PRESETS - per-model flags will fall back to the defaults below)"
  fi

  OVERRIDE_ARGS=()
  [[ -n "$CTX" ]] && OVERRIDE_ARGS+=(-c "$CTX")
  [[ -n "$NGL" ]] && OVERRIDE_ARGS+=(-ngl "$NGL")

  log "Models dir: $MODELS_DIR"
  log "Listening:  http://$BIND:$PORT"
  if (( ${#OVERRIDE_ARGS[@]} )); then
    log "Override:   ${OVERRIDE_ARGS[*]}  (applies to EVERY model, shadowing its preset)"
  else
    log "Context:    per-model, from each preset's ctx-size"
  fi
  if [[ "$BIND" == "0.0.0.0" ]]; then
    log "NOTE: bound to all interfaces so the agent container can reach this via"
    log "      host.docker.internal. That also exposes it to your LAN - pass"
    log "      --bind 127.0.0.1 if you're not using the container."
  fi

  # --no-models-autoload: loading stays explicit (via pi's /llama, --load
  # here, or POST /models/load). Without it a stray request can pull a
  # multi-GB model into VRAM as a side effect.
  llama serve \
    --models-dir "$MODELS_DIR" \
    --no-models-autoload \
    --jinja \
    --host "$BIND" \
    --port "$PORT" \
    "${OVERRIDE_ARGS[@]+"${OVERRIDE_ARGS[@]}"}" \
    "${PRESET_ARGS[@]+"${PRESET_ARGS[@]}"}" &
  SERVER_PID=$!

  # Hand Ctrl-C to the server rather than orphaning it.
  trap 'kill "$SERVER_PID" 2>/dev/null || true' INT TERM

  for _ in $(seq 1 60); do
    models_json >/dev/null 2>&1 && break
    kill -0 "$SERVER_PID" 2>/dev/null || die "Server exited during startup."
    sleep 1
  done
  models_json >/dev/null 2>&1 || die "Server didn't start answering on $API within 60s."
  log "Router up (pid $SERVER_PID)."
fi

if [[ -n "$LOAD" ]]; then
  log "Loading '$LOAD' (a cold multi-GB load takes minutes - this waits for it)..."
  curl -s -m 15 -X POST "$API/models/load" \
    -H 'Content-Type: application/json' \
    -d "{\"model\":\"$LOAD\"}" >/dev/null \
    || die "Load request failed. Is '$LOAD' a known model id? Try: $0 --list"

  for _ in $(seq 1 300); do
    status="$(models_json | python3 -c '
import json, sys
want = sys.argv[1]
try:
    for m in json.load(sys.stdin)["data"]:
        if m["id"] == want:
            print(m["status"]["value"]); break
    else:
        print("unknown")
except Exception:
    print("unknown")
' "$LOAD" 2>/dev/null)"
    [[ "$status" == "loaded" ]] && break
    [[ "$status" == "unknown" ]] && die "'$LOAD' isn't a model this router knows. Try: $0 --list"
    sleep 2
  done
  [[ "${status:-}" == "loaded" ]] || die "'$LOAD' didn't finish loading in 10 minutes."
  log "Loaded. Current state:"
  print_models
fi

# When this script started the server, stay in the foreground so Ctrl-C
# stops it; when it attached to an existing one, just exit.
if [[ -n "${SERVER_PID:-}" ]]; then
  log "Ctrl-C to stop. Chat with it:  ./docker-agent/chat.sh"
  wait "$SERVER_PID"
fi
