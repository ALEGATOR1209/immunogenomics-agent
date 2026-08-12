# CLAUDE.md

This file provides guidance when working with code in this repository.

## What this repository is

This is a **skills-and-infrastructure repo** for AIRR-seq analysis, plus a small harness for benchmarking AI coding agents (pi, running local models served by llama.cpp) against these skills. There is no application code to build — the deliverables are Claude-compatible skill files, a Docker isolation setup, and a Python-driven eval harness. Three independent parts:

1. **`skills/`** — Claude Code / pi skills for TCR-seq analysis (symlinked into `.claude/skills/`, which is gitignored — `skills/` is the single source of truth). Both harnesses read the Agent Skills format, so the same directory serves both.
2. **`docker-agent/`** — a sandboxed container for running an LLM agent (see below).
3. **`test/`** — a harness that runs pi inside a container against a fixed task + dataset and grades the output.

Tying them together at the root: `setup.sh` (one-shot bootstrap for a fresh clone) and `README.md` (the human-facing entry point — keep it in sync when the setup flow or harness CLI changes). `docs/` holds the longer-form write-ups that don't belong in either: `task-json.md` (task authoring reference), `candidate-papers.md` (datasets/papers screened as benchmark task sources), `context-kv-offload-ablation.md` and `local-coding-models-report.md` (the measurements behind the KV-cache and model-choice notes below). **`AGENTS.md` is a symlink to this file**, so pi and Claude Code read the same guidance — edit `CLAUDE.md`, never copy content between the two.

## Architecture: two independent skill families

The skills split along **single-cell vs. bulk TCR-seq data**, and the two families do not interoperate — they use different underlying tools and never share a data object.

**Single-cell (`pytcr-*`), via scirpy/MuData.** Pipeline order matters and each skill's frontmatter states its prerequisite:
```
pytcr-data-loading → pytcr-preprocess → pytcr-clonotype-clustering
    → pytcr-clonotype-analysis / pytcr-gene-motifs / pytcr-repertoire-comparison / pytcr-gex-integration
```
Operates on a scirpy `MuData` object (`mdata`) with `gex` (transcriptomics) and `airr` (receptor) modalities. Two skills sit off to the side of that chain: **`pytcr-sc-rnaseq-preprocessing`** is the `gex`-side counterpart of `pytcr-preprocess` (which covers only `airr`) — scanpy QC, normalization, HVG selection, run after `pytcr-data-loading` and typically alongside `pytcr-preprocess`; **`pytcr-epitope-databases`** annotates antigen specificity by CDR3 identity and needs only `pytcr-preprocess`, not clonotype clustering.

**Bulk (`pytcr-bulk-*`), via plain pandas.** There is no installable package backing this family — the "tool" is pandas logic ported and refactored from the pyTCR paper's (Peng et al., Mangul Lab) analysis notebooks, run directly in the user's own notebook:
```
pytcr-bulk-data-loading → pytcr-bulk-repertoire-metrics / pytcr-bulk-gene-motifs / pytcr-bulk-repertoire-overlap
```
Operates on a plain `df` with standardized columns (`sample`, `freq`, `#count`, `cdr3aa`, `cdr3nt`, `v`, `d`, `j`).

When adding or editing a skill: match the existing style (a `## Setup` section, numbered pipeline steps, prerequisite stated in the frontmatter `description`, runnable code blocks with `<placeholder>` conventions for user-specific values) rather than inventing a new format.

## Architecture: the agent container (`docker-agent/`)

**`docker-agent/`** runs only the **pi** client in a hardened container (`cap_drop: [ALL]`, `no-new-privileges`, no `docker.sock`); the model stays on the host under **llama.cpp's router** (`llama serve`, keeps GPU acceleration) and is reached via `host.docker.internal:8080`. This is what `test/` builds on top of (its images `FROM pytcr-agent:latest`). `docker-agent/llama-server.sh` is the shorthand that starts the router. Models are declared in `~/.config/llama.cpp/presets.ini` **on the host**, not in this repo — the container discovers them from the router at runtime.

It replaced an earlier opencode + Ollama-in-container setup (removed in 3617c80), which had a blocking upstream bug: Ollama's OpenAI-compatible endpoint silently drops tool calls under streaming ([ollama/ollama#12557](https://github.com/ollama/ollama/issues/12557)), ending runs mid-task with `finish_reason: "stop"` and no error, reproduced across several models. llama.cpp's server doesn't have it.

**Known gotchas already root-caused during development** (see each README for detail — don't re-derive these):
- **Do not use llama.cpp's CUDA 13 prebuilt binaries.** On this hardware (RTX 4070 SUPER, WSL2, driver 591.86) `cublasCreate_v2` fails with `CUBLAS_STATUS_ALLOC_FAILED` on any prompt long enough to take the cuBLAS path (a few hundred tokens), while short prompts succeed and make it look healthy. Independent of free VRAM (fails at 3.6/6.3/7.6 GB free), offload (`-ngl 0` still fails), batch size, mmap, and concurrency. Building the same source against **CUDA 12.6** fixes it. Corollary for any future test: `"hi"` passes on a broken build — always verify with a several-hundred-token prompt.
- **The `llama-cpp` provider is not built into pi.** It comes from the package `git:github.com/huggingface/pi-llama` (installed in `docker-agent/Dockerfile`). Without it, pi reports "No models available" regardless of `LLAMA_BASE_URL` or `auth.json`. Note the id is `llama-cpp` (hyphen); pi also ships a *different* built-in `llama.cpp` (dot) provider. The package reads `process.env.LLAMA_BASE_URL` directly and needs no credential.
- **pi's built-in `llama.cpp` provider stores a base URL in `~/.pi/agent/auth.json` that overrides `LLAMA_BASE_URL`** — only affects host installs, not the container (empty volume, no stored credential).
- **A router bound to `127.0.0.1` is invisible to the container** over `host.docker.internal`. `docker-agent/llama-server.sh` binds `0.0.0.0` by default for exactly this reason; `docker-agent/setup.sh` verifies reachability from inside the container.
- **Only loaded models are servable** — the router returns `400 "model is not loaded"` otherwise, and `--no-models-autoload` is deliberately always passed so a stray request can't pull a multi-GB model into VRAM.
- **KV cache scales linearly with `ctx-size`** and competes with `n-cpu-moe` for the same VRAM. The 30B-A3B's KV is 49152 elements/token (48 layers × 4 KV heads × 128), so at its native 262144 context: 25.8 GB at f16, 13.7 GB at q8_0, 7.3 GB at q4_0. Native context therefore needs **q4_0 K/V plus `n-cpu-moe = 48`** (every expert on CPU) — measured 469 t/s prefill, 16.4 t/s generation at 99k tokens, 1872 MiB spare. `q8_0` at 262k simply doesn't fit and fills the card (227 MiB free, unusable).
- **Keep the KV cache on the GPU.** `--no-kv-offload` fits native context by putting KV in system RAM, but generation collapses to **1.46 t/s** — every token streams the whole cache over PCIe. Context length is nearly free; KV *fidelity* is what you trade.
- **A router-level `-c`/`-ngl` silently overrides each model's preset.** With `-c 32768` on the router, a preset asking for `ctx-size = 262144` spawned its child with `--ctx-size 32768` and no warning. `docker-agent/llama-server.sh` therefore passes neither unless `--ctx`/`--ngl` is given explicitly.
- A **read-only root filesystem broke the old opencode TUI** (`Effect.tryPromise` / "Unexpected error") — reproduced and isolated to `read_only: true` specifically. **Never re-tested against pi**; `docker-agent/docker-compose.yml` still doesn't set it.
- **pi has no permission prompts to bypass** (no built-in sandbox — see its `docs/security.md`), so there's no `--dangerously-skip-permissions` equivalent. Non-interactive modes don't show a trust prompt either; `--approve` trusts project-local resources for one run.
- **pi auto-discovers skills from `~/.pi/agent/skills/`** — the container's home directory. `test/test.py --skills` bind-mounts `skills/` (read-only) to `/root/.pi/agent/skills` — sourced from `skills/` directly, *not* from the gitignored `.claude/skills` symlink, so the harness works on a fresh clone that never ran `setup.sh`.
- Docker's `internal: true` network mode blocks `host.docker.internal` too, not just the wider internet — evaluated and rejected as an egress-restriction mechanism for `docker-agent/` (see its README's "Known limitation").

## Architecture: the eval harness (`test/`)

`test/test.py <task-dir-name> [--skills] [--timeout MINUTES] [--n COUNT] [--provider {llama-cpp,anthropic}] [--model MODEL]` — run from inside `test/` — is the whole harness. It is deliberately a single Python script, not a package; keep changes in that style. `test/run_all.py` is a thin driver on top of it (see below).

Per invocation: builds `pytcr-agent:latest` (once, cached), generates/reuses `<task-dir>/Dockerfile` (extends `pytcr-agent:latest` with a Miniforge/mamba env from `test/environment.yml` — mamba specifically, because plain conda is too slow resolving the bioconda/conda-forge scanpy+scirpy stack), renders `test/SYSTEM.md`'s `<TASK>`/`<OUTPUT_FORMAT>` placeholders from the task's `task.json` (`render_prompt.py` — `<OUTPUT_FORMAT>` is `ground_truth` with every value masked to its zero-equivalent, so the agent sees the required JSON shape but never the answers), runs `pi -p --mode json --approve --no-session --provider <provider> --model <id>` inside a fresh container (`--rm`, brand new every run — no state carries over; memory-capped via `MEMORY_GB`, default 8), extracts `task.ipynb`/`output.json`, then grades against `task.json`'s `grader.config` via `grade.py`.

**`--provider`** selects which pi provider runs the agent: `llama-cpp` (default) for the host's local llama.cpp router — `LLAMA_BASE_URL` is passed into the container so pi finds it — or `anthropic` for the hosted Claude API, using pi's *built-in* `anthropic` provider (already present in `pi-coding-agent`'s own dependencies — unlike `llama-cpp`, it needs no separate package install in `docker-agent/Dockerfile`). `anthropic` requires `ANTHROPIC_API_KEY` set on the host; `test.py` passes it into the container as an env var and never bakes it into the image, and dies before touching Docker if it's unset. The container isn't network-isolated (see `docker-agent/`'s isolation notes above), so it reaches `api.anthropic.com` over normal egress with no other config. `--model` under `anthropic` is a literal Claude model id (e.g. `claude-opus-5`) with no router to resolve or validate against — required outright, same "no hardcoded default" reasoning as the `llama-cpp` case below. `eval_result.json`'s `model_server` field records `anthropic` for these runs, so they stay distinguishable from `llama.cpp` runs when the recorded results are compared. `run_all.py` itself does not forward `--provider` — it always sweeps against whatever `test.py` resolves by default (`llama-cpp` plus `MODEL`/the router's loaded model), so an Anthropic comparison run is currently a manual `test.py` invocation per task, not part of the automated matrix.

Everything from a run lands in **`test/<task-dir>/runs/<timestamp>/`** (per-task, not a shared top-level `runs/`): `prompt.txt` (the exact rendered prompt), `run.jsonl` + `run.txt` (the agent's raw event stream and a readable rendering of it), `outputs/` (the extracted `task.ipynb`/`output.json`), and `eval_result.json`.

`--timeout` (default 20 minutes) stops the container if the agent hasn't finished in time; `--n` (default 1) repeats the run that many times, each as its own directory — `runs/<timestamp>/` for a single run, `runs/<timestamp>_<i>/` once `--n > 1`. Both a timeout and a Ctrl-C stop the in-flight container and still extract/grade whatever `task.ipynb`/`output.json` exists at that point — `eval_result.json` gets `timed_out`/`interrupted` boolean fields marking which (if either) happened; a Ctrl-C also skips any remaining `--n` iterations and exits with status 130.

**`test/run_all.py`** runs the full matrix — every task directory containing a `task.json`, 5 iterations with `--skills` and 5 without, 60-minute timeout each (constants at the top of the file). It suppresses `test.py`'s stdout because `test.py` interleaves the model's raw output with its own progress and has no flag to separate them; progress is reported instead from each run's `eval_result.json` as it lands, and the model's full output is still on disk in `run.txt`/`run.jsonl`. It checkpoints the last fully executed `(task, skill-mode, iteration)` to `test/.run_all_state.json` (gitignored) after every run that produced an `eval_result.json` — a run that died without grading isn't checkpointed, so it's retried. **`--resume`** picks the sweep up at the run after that checkpoint; it falls back to starting from the beginning (with a logged reason) if the state file is missing or names a run no longer in the plan (e.g. a task directory was added or removed).

**`test/SYSTEM.md`** is the shared prompt scaffold wrapped around every task, and its instructions are tuned against failure modes actually observed in runs — build `task.ipynb` and `output.json` *incrementally* (partial credit survives a mid-task death), fix failing cells in place rather than rewriting the pipeline from scratch (which burns the context budget), don't dump large tool outputs, execute the notebook end-to-end before finishing, and load any relevant skill via the Skill tool before writing code (a description alone doesn't convey the APIs). Treat edits to it as changing the experiment, not just the wording — it applies to every task and every past run was graded under the previous version.

There are currently seven tasks, all derived from scirpy tutorial analyses: `01-data-loading`, `02-clonotype-analysis`, `03-clonotype-networks`, `04-gene-usage`, `05-repertoire-similarity`, `06-clonotype-clustering`, `07-epitope-databases`.

Task directory shape (`test/<NN-name>/`): `task.json` (id, task prompt, `grader.config.{ground_truth,tolerances}`, `metadata`, `data`), `solution.ipynb` (the hand-written reference analysis the `ground_truth` values came from — tracked in git, read by no script, kept so a grader value can be traced back to the code that produced it), `data/` (**not git-tracked** — `.gitignore` excludes `data`; either fetched via `task.json`'s `data` field or supplied separately, see `fetch_data.py` below), an optional `starter.ipynb`, and a generated `Dockerfile`. `grade.py`'s tolerance check supports `{"type": "absolute", "value": N}` per numeric field; fields without a tolerance entry are compared as exact string match, case-insensitive. Full `task.json` field reference and how-to: `docs/task-json.md`.

**`test/fetch_data.py <task-dir>`** populates `data/` from the source(s) declared in `task.json`'s `data` field — a single `{"type": "GEO", "uri": "GSM4339771"}` or a list of those for tasks needing several samples. Each entry's entire GEO `suppl/` directory (anonymous FTP, no per-task file filtering) lands in `data/<accession>/` by default; an optional `"path"` overrides that destination (relative to `data/`), so several accessions covering the same physical sample (e.g. a GEX GSM and a TCR-seq GSM for one patient) can share a folder — `01-data-loading` groups `GSM4385992` and `GSM4339771` into `data/C143/` this way. Without `"path"`, no friendly sample alias is stored, so task prompts are responsible for telling the agent which accession is which biological sample. Only `"type": "GEO"` is implemented; other types die loudly rather than silently no-op. Idempotent — re-running skips files already on disk unless `--force`. `test.py` calls this automatically when `data/` is missing and `task.json` declares a source; run it directly to pre-fetch without starting a task run. Tasks whose `task.json` has no `data` field are unaffected — `data/` still has to be supplied by hand for those.

**`starter.ipynb`** (optional): if present, `test.py` copies it into the run's workspace as `task.ipynb` before the container starts, so the agent begins from a partially-built notebook instead of empty — for tasks deliberately scoped to one pipeline stage, assuming an earlier stage already happened (the task prompt then says something like "there's a jupyter notebook with ... already set up. Build upon."). Must live at the task directory root, not inside `data/` — that mount is read-only, so a notebook placed there can't be edited in place and the agent would have to discover and copy it out itself first. **No task currently ships one** — every task starts the agent from an empty workspace — but `test.py` still supports it, and earlier task revisions used it.

**There is no default model.** Under `--provider llama-cpp` (the default), model ids are whatever the router reports (e.g. `unsloth/Qwen3-Coder-30B-A3B-Instruct-GGUF:Q4_K_XL`), and the router only serves *loaded* models, so any hardcoded id would be wrong most of the time. Resolution order: `--model`, then `MODEL=...`, then — if exactly one model is loaded — that one; otherwise `test.py` dies listing what's available. Under `--provider anthropic` there is no router to fall back to at all — resolution is `--model`, then `MODEL=...`, then `test.py` dies naming a Claude model id to pass. `eval_result.json` records the model, harness (`pi`), and model server (`llama.cpp` or `anthropic`) each run actually used.

**`~/.config/llama.cpp/presets.ini` on the host is the single source of truth for models** — which exist and what flags each loads with (`ctx-size`, `n-cpu-moe`, `cache-type-k/v`, `parallel`). Nothing in this repo declares models anymore; the container discovers them from the router. Adding a model means adding a preset section there, or dropping a GGUF into `~/models`.

**Runs recorded before the pi migration have `"harness": "opencode"`** and are not comparable to later ones — harness, model server, and model all changed at once. The historical opencode-era findings (qwen3.6/glm-4.7-flash/devstral-small-2 all dying mid-task with `finish_reason: "stop"`) were traced to the Ollama streaming bug above, not to the models, so they say little about behaviour under llama.cpp.

Gitignored, and therefore absent on a fresh clone: `.claude` (hence the `setup.sh` symlink step that recreates `.claude/skills -> skills/`), `.agents` (the same symlink plus local settings for a host pi install — *not* created by `setup.sh`), `data` (every task's dataset — fetched via `fetch_data.py` where `task.json` declares a source, otherwise supplied separately), `test/*/runs`, `test/.run_all_state.json`, `test/logs`, `test/notebooks`, `test/results`, `.vscode`, and `.env`. These are local run history/scratch/inputs, not source. Notebooks are *not* blanket-ignored — each task's `solution.ipynb` is tracked.

## Common commands

```bash
# Fresh-clone bootstrap (host model-server checks + agent container + gitignored bits)
./setup.sh                                 # checks the llama.cpp router, builds the agent container, links .claude/skills -> skills/
./setup.sh --models unsloth/Qwen3-Coder-30B-A3B-Instruct-GGUF:Q4_K_XL   # have the router fetch a model from HF
./setup.sh --skip-models                   # container + skills symlink only
./setup.sh --skip-container                # host side only, no Docker needed
./setup.sh --with-host-pi                  # also npm-install pi + the pi-llama provider on the host

# Host model server (llama.cpp router)
./docker-agent/llama-server.sh --list                # what the router knows, with load state
./docker-agent/llama-server.sh --load <model-id>     # start it and load one model
./docker-agent/llama-server.sh --port 8081           # non-default port
./docker-agent/llama-server.sh --bind 127.0.0.1      # local only - the container can NOT reach this
./docker-agent/llama-server.sh --ctx 65536           # overrides EVERY preset's ctx-size; normally leave unset

# Isolated pi client, native host llama.cpp
./docker-agent/setup.sh
./docker-agent/chat.sh [model-id]          # defaults to whichever model is loaded

# Eval harness (run from inside test/)
cd test
./fetch_data.py 01-data-loading            # pre-fetch data/ from task.json's "data" field (or let test.py do it)
./test.py 01-data-loading                  # no skills mounted
./test.py 01-data-loading --skills         # mounts skills/ read-only at the container's ~/.pi/agent/skills
./test.py 01-data-loading --timeout 30 --n 3   # 30-minute timeout, 3 repeated runs
MODEL='ggml-org/Qwen3.6-35B-A3B-GGUF:Q4_K_M' ./test.py 01-data-loading
./test.py 01-data-loading --model 'ggml-org/Qwen3.6-35B-A3B-GGUF:Q4_K_M'   # flag takes precedence over MODEL
ANTHROPIC_API_KEY=sk-ant-... ./test.py 01-data-loading --provider anthropic --model claude-opus-5   # compare against Claude
MEMORY_GB=16 ./test.py 01-data-loading            # raise the container memory cap (default 8)
./run_all.py                                      # every task, 5x with skills + 5x without, 60m cap each
./run_all.py --resume                             # continue after the last run recorded in test/.run_all_state.json
python3 grade.py <task.json> <output.json> [duration_seconds] [skills]   # re-grade a saved answer
```

No lint/test suite, package manager, or build step exists for this repo — the "tests" are the eval tasks under `test/`, run via `test.py` above, not a conventional test runner.
