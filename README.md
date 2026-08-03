# pyTCR skills

Agent skills for **TCR-seq / AIRR-seq repertoire analysis**, plus the
infrastructure to measure whether they actually help a coding agent do the
analysis.

Three parts, independent of each other:

| Directory | What it is |
|---|---|
| [`skills/`](./skills) | The deliverable — Claude Code / pi skills covering single-cell (scirpy) and bulk (pandas) TCR-seq pipelines |
| [`docker/`](./docker), [`docker-agent/`](./docker-agent) | Two sandboxed containers for running a local LLM agent, isolating different things ([comparison](./docker-agent/README.md#comparison-with-docker)) |
| [`test/`](./test) | An eval harness: runs pi against a fixed task + dataset, with and without the skills mounted, and grades the answers |

## The skills

Two families that don't interoperate — they use different tools and never
share a data object. Each skill's frontmatter states its prerequisite.

**Single-cell**, via [scirpy](https://scirpy.scverse.org/) on a `MuData`
object with `gex` + `airr` modalities:

```
pytcr-data-loading → pytcr-preprocess → pytcr-clonotype-clustering
    → pytcr-clonotype-analysis / pytcr-gene-motifs
    / pytcr-repertoire-comparison / pytcr-gex-integration
```

(`pytcr-preprocess` handles the `airr` modality; `pytcr-sc-rnaseq-preprocessing`
is its `gex`-side counterpart — scanpy QC, normalization and HVG selection.)

**Bulk**, plain pandas on a standardized table (`sample`, `freq`, `#count`,
`cdr3aa`, `cdr3nt`, `v`, `d`, `j`) — ported from the pyTCR paper's analysis
notebooks, no package to install:

```
pytcr-bulk-data-loading → pytcr-bulk-repertoire-metrics
    / pytcr-bulk-gene-motifs / pytcr-bulk-repertoire-overlap
```

To use them in Claude Code, `./setup.sh` links `skills/` into
`.claude/skills/` (`skills/` stays the single source of truth). pi
auto-discovers skills from `~/.pi/agent/skills/` instead — the eval harness
mounts them there itself.

## Setup

Requirements: **Docker** (with Compose v2), a **llama.cpp** build on the host
(see the warning below), **Python 3**. Then, from the repo root:

```bash
./setup.sh
```

That is idempotent and does everything a fresh clone needs:

1. Checks for the `llama` binary and reports what the model router has.
2. Links `.claude/skills` → `skills/`.
3. Builds and starts the agent container (`pytcr-agent:latest`), verifying
   from inside it that the host's router is actually reachable.

Useful variations:

```bash
./setup.sh --models unsloth/Qwen3-Coder-30B-A3B-Instruct-GGUF:Q4_K_XL  # have the router fetch a model
./setup.sh --skip-models                 # container + skills symlink only
./setup.sh --skip-container              # host side only, no Docker needed
./setup.sh --with-host-pi                # also install pi + its llama.cpp provider on the host
./setup.sh --help
```

**Build llama.cpp against CUDA 12.x, not 13.x.** The CUDA 13 prebuilt
binaries fail `cublasCreate_v2` with `CUBLAS_STATUS_ALLOC_FAILED` on any
prompt long enough to take the cuBLAS path — a few hundred tokens — while
short prompts succeed and make the build look healthy. It is independent of
free VRAM, offload, batch size and mmap. Details in
[`docker-agent/README.md`](./docker-agent/README.md#prerequisites).

Start the model server before using the agent:

```bash
./docker-agent/llama-server.sh --list              # what's available
./docker-agent/llama-server.sh --load <model-id>   # start the router and load one
```

**Eval data is not in this repo.** Each `test/<NN-name>/` needs a `data/`
directory (it's gitignored); `setup.sh` lists the tasks that are missing
one. If a task's `task.json` declares a `"data"` field, it's fetched
automatically - either on the first `test.py` run, or ahead of time with
`test/fetch_data.py <task-dir>`. Otherwise it has to be supplied by hand.

## Running the agent

```bash
./docker-agent/chat.sh              # interactive pi, using whichever model the router has loaded
./docker-agent/chat.sh <model-id>   # pick one explicitly (it must already be loaded)
```

The model runs natively on the host (keeping GPU acceleration); only the
agent — the part with file and shell access — is sandboxed, with
`cap_drop: [ALL]`, no host bind mounts and no Docker socket. See
[`docker-agent/README.md`](./docker-agent/README.md). The alternative,
[`docker/`](./docker), isolates the *model* instead and is the right choice
when the model file itself is untrusted.

## Running the evals

From inside `test/`:

```bash
cd test
./test.py 01-data-loading                     # baseline: no skills mounted
./test.py 01-data-loading --skills            # with skills/ mounted into the container
./test.py 01-data-loading --timeout 30 --n 3  # 30-minute cap, 3 repeats
./test.py 01-data-loading --model 'ggml-org/Qwen3.6-35B-A3B-GGUF:Q4_K_M'
./run_all.py                                  # every task, 5x with skills and 5x without
```

Each run builds a task image (the agent container + a mamba env with
scanpy/scirpy), starts a **fresh** container, gives the agent the task
prompt plus the required output shape with all values masked, and grades the
`output.json` it produces against the task's ground truth. Everything lands
in `test/<task>/runs/<timestamp>/`:

| File | Contents |
|---|---|
| `run.txt` / `run.jsonl` | The agent's thinking, tool calls and output |
| `outputs/` | The `task.ipynb` and `output.json` it produced |
| `eval_result.json` | Score, pass/fail, duration, model, and `timed_out` / `interrupted` flags |

Ctrl-C stops the container but still extracts and grades whatever the agent
had written by then. To re-grade a saved answer without re-running:

```bash
python3 grade.py <task.json> <output.json> [duration_seconds] [skills]
```

Adding a task means a new `test/<NN-name>/` with a `task.json` (prompt,
ground truth, per-field tolerances), a `data/` directory (or a `"data"`
field for `fetch_data.py` to populate it from GEO - see `test/fetch_data.py
--help`), and optionally a `starter.ipynb` to begin from a partially-built
notebook. See [`docs/task-json.md`](./docs/task-json.md) for the full
`task.json` field reference and a step-by-step walkthrough.

## History

This setup previously ran **opencode against Ollama**. Ollama's
OpenAI-compatible endpoint silently drops tool calls under streaming
([ollama/ollama#12557](https://github.com/ollama/ollama/issues/12557)), so
runs ended mid-task with `finish_reason: "stop"` and no error —
model-independent, reproduced on qwen3.6, glm-4.7-flash and
devstral-small-2. Moving to llama.cpp's own server routes around it.

Eval runs from before the migration carry `"harness": "opencode"` in their
`eval_result.json` and are **not comparable** to later ones: harness, model
server and model changed together. [`docker/`](./docker) still runs the old
opencode + Ollama-in-container arrangement and was intentionally left alone.
