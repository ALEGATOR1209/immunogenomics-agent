#!/usr/bin/env bash
# Runs one task directory's evaluation inside an isolated container.
#
# Usage (from inside test/):
#   ./test <task-dir-name> [--skills]
#   MODEL=host/qwen3.5 ./test 01-data-loading --skills
#
# --skills: bind-mounts the project's skills/ (read-only) into the
#           container at /root/.claude/skills, which is opencode's
#           "external skills (auto-loaded)" location - no opencode.json
#           config needed, the agent's Skill tool just sees them. Sourced
#           from skills/, not .claude/skills/ - the latter is gitignored
#           (just a local symlink to skills/) and won't exist on a fresh
#           clone or CI.
#
# Default model is qwen3.6-128k, not qwen3.6: Ollama loads qwen3.6 with only
# a 32768-token context by default (see docker-agent/README.md's "Context
# window note"), which multi-step data-exploration tasks can exhaust with
# no error - the model just stops producing useful output. qwen3.6-128k is
# the same weights loaded with a 131072-token context instead.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"   # .../pyTCR/test
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

MODEL="${MODEL:-host/qwen3.6-128k}"
MEMORY_GB="${MEMORY_GB:-8}"

log() { echo ">> $*"; }
die() { echo "ERROR: $*" >&2; exit 1; }

TASK_NAME=""
USE_SKILLS=0
for arg in "$@"; do
  case "$arg" in
    --skills) USE_SKILLS=1 ;;
    -*) die "Unknown flag: $arg" ;;
    *)
      [[ -z "$TASK_NAME" ]] || die "Usage: $0 <task-dir-name> [--skills]  (run from inside test/, e.g. ./test 01-data-loading --skills)"
      TASK_NAME="$arg"
      ;;
  esac
done
[[ -n "$TASK_NAME" ]] || die "Usage: $0 <task-dir-name> [--skills]  (run from inside test/, e.g. ./test 01-data-loading --skills)"
TASK_DIR="$SCRIPT_DIR/$TASK_NAME"

if (( USE_SKILLS )); then
  [[ -d "$REPO_ROOT/skills" ]] || die "--skills was passed but $REPO_ROOT/skills doesn't exist"
fi

[[ -d "$TASK_DIR" ]] || die "No such task directory: $TASK_DIR"
[[ -f "$TASK_DIR/task.json" ]] || die "Missing task.json in $TASK_DIR"
[[ -d "$TASK_DIR/data" ]] || die "Missing data/ in $TASK_DIR"
python3 -c "import json; json.load(open('$TASK_DIR/task.json'))" \
  || die "task.json in $TASK_DIR is not valid JSON"

command -v docker >/dev/null 2>&1 || die "Docker isn't installed."
docker info >/dev/null 2>&1 || die "Docker daemon isn't running (open Docker Desktop and retry)."

# --- 1. Base agent image (docker-agent/) ---
if ! docker image inspect pytcr-agent:latest >/dev/null 2>&1; then
  log "Building base agent image from docker-agent/..."
  docker build -t pytcr-agent:latest "$REPO_ROOT/docker-agent"
fi

# --- 2. Generate this task's Dockerfile if missing ---
if [[ -f "$TASK_DIR/Dockerfile" ]]; then
  log "Using existing $TASK_DIR/Dockerfile"
else
  log "Generating $TASK_DIR/Dockerfile"
  cat > "$TASK_DIR/Dockerfile" <<'DOCKERFILE'
ARG BASE_IMAGE=pytcr-agent:latest
FROM ${BASE_IMAGE}

# Miniforge (conda + mamba, conda-forge-first): mamba resolves the
# bioconda/conda-forge scanpy+scirpy stack far faster and more reliably
# than the classic conda solver.
RUN apt-get update \
    && apt-get install -y --no-install-recommends wget bzip2 ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && wget -qO /tmp/miniforge.sh "https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-$(uname -m).sh" \
    && bash /tmp/miniforge.sh -b -p /opt/conda \
    && rm /tmp/miniforge.sh

# environment.yml lives at test/environment.yml, one level up from this
# task directory - the build context is test/ (see `docker build -f`
# below), so it's visible here as a context-root file.
COPY environment.yml /tmp/environment.yml
RUN /opt/conda/bin/mamba env create -f /tmp/environment.yml \
    && /opt/conda/bin/conda clean -afy

# Make the task's conda env (name: pytcr, from environment.yml) the
# default on PATH for every process in the container, including the
# bash/python calls opencode's agent makes - no `conda activate` needed.
ENV PATH=/opt/conda/envs/pytcr/bin:$PATH
DOCKERFILE
fi

# --- 3. Build the task image (context = test/, so environment.yml is
#         visible; .dockerignore keeps data/ and runs/ out of the
#         build context regardless of which task this is) ---
TASK_IMAGE="pytcr-test-${TASK_NAME}"
log "Building task image: $TASK_IMAGE"
docker build -f "$TASK_DIR/Dockerfile" -t "$TASK_IMAGE" "$SCRIPT_DIR"

# --- 4. Render the prompt (<TASK> and <OUTPUT_FORMAT> filled from task.json) ---
RUN_ID="$(date +%Y%m%d_%H%M%S)"
RUN_DIR="$TASK_DIR/runs/$RUN_ID"
mkdir -p "$RUN_DIR/workspace"

PROMPT="$(python3 "$SCRIPT_DIR/render_prompt.py" "$TASK_DIR/task.json" "$SCRIPT_DIR/SYSTEM.md")"
printf '%s' "$PROMPT" > "$RUN_DIR/prompt.txt"

# --- 5. Run the task, isolated, non-interactively ---
CONTAINER_NAME="pytcr-test-${TASK_NAME}-${RUN_ID}"
log "Starting container: $CONTAINER_NAME (model: $MODEL)"
log "Workspace: $RUN_DIR/workspace"

LOG_FILE="$RUN_DIR/run.jsonl"
PRETTY_FILE="$RUN_DIR/run.txt"

{
  echo "=== Task: $TASK_NAME ==="
  echo "=== Model: $MODEL ==="
  echo "=== Skills: $([[ $USE_SKILLS -eq 1 ]] && echo "enabled ($REPO_ROOT/skills)" || echo "disabled") ==="
  echo "=== Prompt: ==="
  echo "$PROMPT"
  echo
} | tee "$PRETTY_FILE"

SKILLS_MOUNT_ARGS=()
if (( USE_SKILLS )); then
  SKILLS_MOUNT_ARGS=(-v "$REPO_ROOT/skills:/root/.claude/skills:ro")
fi

START_TIME=$(date +%s)
set +e
docker run --rm \
  --name "$CONTAINER_NAME" \
  --add-host=host.docker.internal:host-gateway \
  --cap-drop=ALL --security-opt no-new-privileges:true \
  --memory="${MEMORY_GB}g" \
  -v "$RUN_DIR/workspace:/root/task" \
  -v "$TASK_DIR/data:/root/task/data:ro" \
  "${SKILLS_MOUNT_ARGS[@]+"${SKILLS_MOUNT_ARGS[@]}"}" \
  -w /root/task \
  "$TASK_IMAGE" \
  opencode run --model "$MODEL" --format json --thinking --dangerously-skip-permissions "$PROMPT" \
  | tee "$LOG_FILE" \
  | jq -r --unbuffered '
      if .type == "reasoning" then
        "🧠 THINKING: \(.part.text)"
      elif .type == "tool_use" then
        "🔧 TOOL: \(.part.tool)\n   IN:  \(.part.state.input | tostring | .[0:200])\n   OUT: \(.part.state.output | .[0:300])"
      elif .type == "text" then
        "💬 OUTPUT:\n\(.part.text)"
      elif .type == "step_finish" then
        "📊 STEP TOKENS: input=\(.part.tokens.input) output=\(.part.tokens.output) reasoning=\(.part.tokens.reasoning) total=\(.part.tokens.total)"
      else empty
      end
    ' \
  | tee -a "$PRETTY_FILE"
RUN_STATUS=${PIPESTATUS[0]}
set -e
END_TIME=$(date +%s)
DURATION_S=$((END_TIME - START_TIME))

{
  echo
  echo "=== Container exit status: $RUN_STATUS ==="
  echo "=== Duration: ${DURATION_S}s ==="
} | tee -a "$PRETTY_FILE"

# --- 6. Extract the two deliverables into outputs/, then clear the
#         workspace mount - it's scratch space for the run, not a
#         place to keep things; the run's actual artifacts live in
#         outputs/ (and the full logs, always) from here on. ---
mkdir -p "$RUN_DIR/outputs"
for f in task.ipynb output.json; do
  if [[ -f "$RUN_DIR/workspace/$f" ]]; then
    cp "$RUN_DIR/workspace/$f" "$RUN_DIR/outputs/$f"
  else
    echo "WARNING: $f was not produced" | tee -a "$PRETTY_FILE"
  fi
done
find "$RUN_DIR/workspace" -mindepth 1 -delete

# --- 7. Grade the answer against task.json's ground truth/tolerances ---
EVAL_FILE="$RUN_DIR/eval_result.json"
python3 "$SCRIPT_DIR/grade.py" "$TASK_DIR/task.json" "$RUN_DIR/outputs/output.json" "$DURATION_S" "$USE_SKILLS" > "$EVAL_FILE"

{
  echo "=== Evaluation ==="
  cat "$EVAL_FILE"
} | tee -a "$PRETTY_FILE"

log "Done."
log "Logs:    $LOG_FILE / $PRETTY_FILE"
log "Outputs: $RUN_DIR/outputs"
log "Eval:    $EVAL_FILE"

exit "$RUN_STATUS"
