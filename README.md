# pyTCR skills

Agent skills for **TCR-seq / AIRR-seq repertoire analysis**, plus the
infrastructure to measure whether they actually help a coding agent do the
analysis.

Three parts, independent of each other:

| Directory | What it is |
|---|---|
| [`skills/`](./skills) | The deliverable — Claude Code / opencode skills covering single-cell (scirpy) and bulk (pandas) TCR-seq pipelines |
| [`docker/`](./docker), [`docker-agent/`](./docker-agent) | Two sandboxed containers for running a local LLM agent, isolating different things ([comparison](./docker-agent/README.md#comparison-with-docker)) |
| [`test/`](./test) | An eval harness: runs opencode against a fixed task + dataset, with and without the skills mounted, and grades the answers |

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
`.claude/skills/` (`skills/` stays the single source of truth). opencode
reads them from `~/.claude/skills/` instead — the eval harness mounts them
there itself.

## Setup

Requirements: **Docker** (with Compose v2), **[Ollama](https://ollama.com)**,
**Python 3**. Then, from the repo root:

```bash
./setup.sh
```

That is idempotent and does everything a fresh clone needs:

1. Starts `ollama serve` if nothing is listening on `:11434`.
2. Pulls `qwen3.6` and derives **`qwen3.6-128k`** from it. Ollama loads every
   model with a 32768-token context by default no matter what the
   architecture supports, and blows past it *silently* mid-task — so the
   `-128k` variant (same weights, `PARAMETER num_ctx 131072`, no
   re-download) is what everything here defaults to. `num_ctx` is read from
   [`docker-agent/opencode.json`](./docker-agent/opencode.json) so it can't
   drift from the context limit opencode is told about.
3. Links `.claude/skills` → `skills/`.
4. Builds and starts the agent container (`pytcr-agent:latest`).

Useful variations:

```bash
./setup.sh --models glm-4.7-flash-128k   # a different model (must be declared in docker-agent/opencode.json)
./setup.sh --all-models                  # every *-128k model declared there
./setup.sh --skip-models                 # container + skills symlink only
./setup.sh --skip-container              # host side only, no Docker needed
./setup.sh --help
```

**Eval data is not in this repo.** Each `test/<NN-name>/` needs a `data/`
directory supplied separately (it's gitignored); `setup.sh` lists the tasks
that are missing one.

## Running the agent

```bash
./docker-agent/chat.sh                          # interactive opencode, default host/qwen3.6-128k
./docker-agent/chat.sh host/glm-4.7-flash-128k  # any model declared in opencode.json
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
./test.py 01-data-loading --model host/glm-4.7-flash-128k
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
ground truth, per-field tolerances), a `data/` directory, and optionally a
`starter.ipynb` to begin from a partially-built notebook.

## Known issue

Ollama's OpenAI-compatible endpoint — the one opencode talks to — silently
drops tool calls under streaming
([ollama/ollama#12557](https://github.com/ollama/ollama/issues/12557)), so a
run can end mid-task with `finish_reason: "stop"` and no error. It's
upstream and model-independent (reproduced on qwen3.6 and glm-4.7-flash).
Routing around it via llama.cpp was attempted and blocked; the full write-up
is in [`docker-agent/README.md`](./docker-agent/README.md#known-issue--ollamas-openai-compat-endpoint-drops-tool-calls-under-streaming).
