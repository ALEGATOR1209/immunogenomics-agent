# CLAUDE.md

This file provides guidance when working with code in this repository.

## What this repository is

This is a **skills-and-infrastructure repo** for AIRR-seq analysis, plus a small harness for benchmarking AI coding agents (opencode, running local Ollama models) against these skills. There is no application code to build — the deliverables are Claude/opencode-compatible skill files, Docker isolation setups, and a Python-driven eval harness. Three independent parts:

1. **`skills/`** — Claude Code / opencode skills for TCR-seq analysis (symlinked into `.claude/skills/`, which is gitignored — `skills/` is the single source of truth).
2. **`docker/` and `docker-agent/`** — two different sandboxed containers for running an LLM agent, built for different tradeoffs (see below).
3. **`test/`** — a harness that runs opencode inside a container against a fixed task + dataset and grades the output.

## Architecture: two independent skill families

The skills split along **single-cell vs. bulk TCR-seq data**, and the two families do not interoperate — they use different underlying tools and never share a data object.

**Single-cell (`pytcr-*`), via scirpy/MuData.** Pipeline order matters and each skill's frontmatter states its prerequisite:
```
pytcr-data-loading → pytcr-preprocess → pytcr-clonotype-clustering
    → pytcr-clonotype-analysis / pytcr-gene-motifs / pytcr-repertoire-comparison / pytcr-gex-integration
```
Operates on a scirpy `MuData` object (`mdata`) with `gex` (transcriptomics) and `airr` (receptor) modalities.

**Bulk (`pytcr-bulk-*`), via plain pandas.** There is no installable package backing this family — the "tool" is pandas logic ported and refactored from the pyTCR paper's (Peng et al., Mangul Lab) analysis notebooks, run directly in the user's own notebook:
```
pytcr-bulk-data-loading → pytcr-bulk-repertoire-metrics / pytcr-bulk-gene-motifs / pytcr-bulk-repertoire-overlap
```
Operates on a plain `df` with standardized columns (`sample`, `freq`, `#count`, `cdr3aa`, `cdr3nt`, `v`, `d`, `j`).

When adding or editing a skill: match the existing style (a `## Setup` section, numbered pipeline steps, prerequisite stated in the frontmatter `description`, runnable code blocks with `<placeholder>` conventions for user-specific values) rather than inventing a new format.

## Architecture: the two Docker setups

Both live at the repo root, both run opencode in a hardened container (`cap_drop: [ALL]`, `no-new-privileges`, no `docker.sock`), but they isolate **different things** and are not interchangeable:

- **`docker/`** — runs Ollama itself inside the container. Fully self-contained, but CPU-only on macOS (Docker Desktop has no Metal passthrough) — see its README's Performance section for the measured cost and the GPU passthrough path for Linux/WSL2+NVIDIA.
- **`docker-agent/`** — runs only the opencode *client* in the container; the model stays on the host's native `ollama serve` (keeps GPU acceleration) and is reached via `host.docker.internal`. This is what `test/` builds on top of (its images `FROM pytcr-agent:latest`). Model/provider config lives in `docker-agent/opencode.json`.

**Known gotchas already root-caused during development** (see each README for detail — don't re-derive these):
- Ollama loads a model with only a **32768-token context by default**, regardless of what the model architecture supports — invisible until a multi-step agent task exhausts it and the model silently stops producing output (no error). Fix used here: a derived model (`ollama create <name> -f Modelfile` with `PARAMETER num_ctx N`), not a global Ollama config change.
- A **read-only root filesystem breaks opencode's TUI** (`Effect.tryPromise` / "Unexpected error") — reproduced and isolated to `read_only: true` specifically, independent of `cap_drop`/`no-new-privileges`/volume state. `docker-agent/docker-compose.yml` intentionally does not set it; see its README for the tradeoff.
- Headless/non-interactive opencode runs need `--dangerously-skip-permissions` (not `--auto` — that flag doesn't exist despite what `--help` might suggest from a different opencode version) or they hang waiting for a permission prompt that never comes.
- opencode auto-loads Claude Code-format skills from `~/.claude/skills/<name>/SKILL.md` — the container's **home directory**, not the project-relative `.claude/skills` Claude Code itself uses. `test/test.py --skills` mounts the project's `.claude/skills` there.
- Docker's `internal: true` network mode blocks `host.docker.internal` too, not just the wider internet — evaluated and rejected as an egress-restriction mechanism for `docker-agent/` (see its README's "Known limitation").

## Architecture: the eval harness (`test/`)

`test/test.py <task-dir-name> [--skills] [--timeout MINUTES] [--n COUNT]` — run from inside `test/` — is the whole harness. It is deliberately a single Python script, not a package; keep changes in that style.

Per invocation: builds `pytcr-agent:latest` (once, cached), generates/reuses `<task-dir>/Dockerfile` (extends `pytcr-agent:latest` with a Miniforge/mamba env from `test/environment.yml` — mamba specifically, because plain conda is too slow resolving the bioconda/conda-forge scanpy+scirpy stack), renders `test/SYSTEM.md`'s `<TASK>`/`<OUTPUT_FORMAT>` placeholders from the task's `task.json` (`render_prompt.py` — `<OUTPUT_FORMAT>` is `ground_truth` with every value masked to its zero-equivalent, so the agent sees the required JSON shape but never the answers), runs opencode non-interactively inside a fresh container (`--rm`, brand new every run — no state carries over), extracts `task.ipynb`/`output.json` into `runs/<timestamp>/outputs/`, then grades against `task.json`'s `grader.config` via `grade.py` into `runs/<timestamp>/eval_result.json`.

`--timeout` (default 20 minutes) stops the container if the agent hasn't finished in time; `--n` (default 1) repeats the run that many times, each as its own `runs/<timestamp>_<i>/` directory. Both a timeout and a Ctrl-C stop the in-flight container and still extract/grade whatever `task.ipynb`/`output.json` exists at that point — `eval_result.json` gets `timed_out`/`interrupted` boolean fields marking which (if either) happened; a Ctrl-C also skips any remaining `--n` iterations and exits with status 130.

Task directory shape (`test/<NN-name>/`): `task.json` (id, task prompt, `grader.config.{ground_truth,tolerances}`, `metadata`), `data/` (**not git-tracked** — supply separately, `.gitignore` excludes `data`), and a generated `Dockerfile`. `grade.py`'s tolerance check supports `{"type": "absolute", "value": N}` per numeric field; fields without a tolerance entry are compared as exact string match, case-insensitive.

Default model is `host/glm-4.7-flash-128k` (not `host/glm-4.7-flash` — see the context-window gotcha above; switched from `host/qwen3.6-128k` after repeated runs surfaced a qwen3.6-specific chat-template bug where the reasoning channel leaks raw `<|mask_start|>`/`<|mask_end|>` tokens and the turn terminates early, mid-task, with no error); override per-run with `MODEL=... ./test.py ...`. `runs/`, `test/logs`, `test/notebooks`, `test/results`, and all `*.ipynb` are gitignored — they're local run history/scratch, not source.

## Common commands

```bash
# Isolated Ollama-in-container setup
./docker/setup.sh                          # build + start + memory check
./docker/chat.sh [model]                   # interactive REPL

# Isolated opencode client, native host Ollama
./docker-agent/setup.sh
./docker-agent/chat.sh [host/model]

# Eval harness (run from inside test/)
cd test
./test.py 01-data-loading                  # no skills mounted
./test.py 01-data-loading --skills         # mounts .claude/skills into the container
./test.py 01-data-loading --timeout 30 --n 3   # 30-minute timeout, 3 repeated runs
MODEL=host/qwen3.5 ./test.py 01-data-loading
python3 grade.py <task.json> <output.json> [duration_seconds] [skills]   # re-grade a saved answer
```

No lint/test suite, package manager, or build step exists for this repo — the "tests" are the eval tasks under `test/`, run via `test.py` above, not a conventional test runner.
