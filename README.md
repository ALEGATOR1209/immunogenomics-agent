# pyTCR skills

Agent skills for **TCR-seq / BCR-seq / AIRR-seq repertoire analysis**, plus the benchmanrk
infrastructure to measure whether they actually help a coding agent do the
analysis.

## Project Architecture

| Directory | What it is |
|---|---|
| [`skills/`](./skills) | Open standard skills compatible with Claude Code and other harnesses. The skills cover single-cell (scirpy) and bulk (pandas) TCR-seq pipelines.<br/><br/> ❗️For now only the single-cell skills are tested and fine-tuned. |
| [`docker-agent/`](./docker-agent) | Sandboxed container for providing an isolated environment for the agent evaluation. The LLM is hosted outside of the container and is accessed via API. The harness is launched inside the container with access to input data and preinstalled Python environment.<br/><br/>Two execution modes: interactive chat, or launching with a defined task. |
| [`test/`](./test) | An eval harness: runs pi against a fixed task + dataset, with and without the skills mounted, and grades the answers |

## The skills

### Single-cell

**Single-cell** skills are based on [scirpy](https://scirpy.scverse.org/) & [scanpy](https://scanpy.readthedocs.io/) ecosystem.

| Skill | Description |
|-------|-------------|
| [`pytcr-data-loading`](skills/pytcr-data-loading/SKILL.md) | Data loading of AIRR or mixed scRNA-seq + AIRR data via scirpy (10x CellRanger, BD Rhapsody, TraCeR, BraCeR, etc). Builds a `MuData` object with `gex` and `airr` modalities.
| [`pytcr-preprocess`](skills/pytcr-preprocess/SKILL.md) | Preprocessing, chain indexing, receptor type & pairing filtering. |
| [`pytcr-sc-rnaseq-preprocessing`](skills/pytcr-sc-rnaseq-preprocessing/SKILL.md) | AIRR analyzis often involves scRNA-seq analysis to some extent, so this skill provides basic scRNA-seq preprocessing workflow. Minimum genes/cells filtering, HVG detection, log-normalization. |
| [`pytcr-clonotype-clustering`](skills/pytcr-clonotype-clustering/SKILL.md) | Clonotype definition (nucleotide-sequence identity, amino-acid similarity), distance matrixes, clonotype clusters & networks calculation. |
| [`pytcr-clonotype-analysis`](skills/pytcr-clonotype-analysis/SKILL.md) | Clonal expansion, abundance analysis, alpha-diversity, convergent evolution analysis. |
| [`pytcr-gene-motifs`](skills/pytcr-gene-motifs/SKILL.md) | Gene/motif analysis. V-gene abundance, VDJ-genes usage. Spectratype plots. |
| [`pytcr-repertoire-comparison`](skills/pytcr-repertoire-comparison/SKILL.md) | Analysis of repertoire overlap, sample similarity. |
| [`pytcr-gex-integration`](skills/pytcr-gex-integration/SKILL.md) | Clonotype modularity analysis, differentially expressed clonotypes, clonotype imbalance, marker genes. |

## User Setup

To use the skills, clone the repository and install them:

```bash
git clone https://github.com/ALEGATOR1209/immunogenomics-agent.git
```

### Standardized Install
```bash
cp -r immunogenomics-agent/skills/* ~/.agents/skills
```

### Claude Code:

```bash
cp -r immunogenomics-agent/skills/* ~/.claude/skills/
```

### Codex

```bash
cp -r immunogenomics-agent/skills/* ~/.codex/skills/
```

### Pi

```bash
cp -r immunogenomics-agent/skills/* ~/.pi/agent/skills
```

## Development Setup

**Dependencies:**
1. Docker (with Compose v2)
2. [llama.cpp](https://github.com/ggml-org/llama.cpp)
3. Python 3 (env can be created from [environment.yml](test/environment.yml))

Then, from the repo root:

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
# have the router fetch a model
./setup.sh --models unsloth/Qwen3-Coder-30B-A3B-Instruct-GGUF:Q4_K_XL

# container + skills symlink only
./setup.sh --skip-models

# host side only, no Docker needed
./setup.sh --skip-container

# also install pi + its llama.cpp provider on the host
./setup.sh --with-host-pi

./setup.sh --help
```

> [!NOTE]
> If you encounter errors related to `cublasCreate_v2`, rebuild llama.cpp against CUDA 12.x instead of 13.x

Start the model server before using the agent:

```bash
# list available models
./docker-agent/llama-server.sh --list

# start the router and load a model
./docker-agent/llama-server.sh --load <model-id>
```

### Fetching test data

Input datasets for the tests are loaded automatically via the [`test.py`](test/test.py) script. It can be loaded manually via [`fetch_data.py`](test/fetch_data.py) script like this:

```bash
cd test
./fetch_data.py 01-data-loading
```

## Running the agent

```bash
# interactive pi session in a Docker container,
# using whichever model the router has loaded
./docker-agent/chat.sh

# pick one explicitly (it must already be loaded)
./docker-agent/chat.sh <model-id>

# a hosted model instead of the local router
# (ANTHROPIC_API_KEY / OPENAI_API_KEY from the repo-root .env, or from the shell)
./docker-agent/chat.sh --provider anthropic claude-opus-5
./docker-agent/chat.sh --provider openai gpt-5.5
```

The model runs natively on the host (keeping GPU acceleration); only the
agent — the part with file and shell access — is sandboxed, with
`cap_drop: [ALL]`, no host bind mounts and no Docker socket. See
[`docker-agent/README.md`](./docker-agent/README.md).

## Running the benchmark

```bash
cd test

# baseline: no skills mounted
./test.py 01-data-loading

# with skills/ mounted into the container
./test.py 01-data-loading --skills

# 30-minute cap, 3 repeats
./test.py 01-data-loading --timeout 30 --n 3

# select specific model (must be pre-loaded)
./test.py 01-data-loading --model 'ggml-org/Qwen3.6-35B-A3B-GGUF:Q4_K_M'

# compare against a hosted model, via pi's built-in anthropic/openai providers
# (the API key comes from the .env at the repo root, or from the shell)
./test.py 01-data-loading --provider anthropic --model claude-opus-5
./test.py 01-data-loading --provider openai --model gpt-5.5

# full benchmark: every task,
# 5 times with skills and 5 without
./run_all.py

# continue an interrupted benchmark from the last completed run
./run_all.py --resume

# full benchmark against a hosted model instead of the local router
./run_all.py --provider anthropic --model claude-opus-5
./run_all.py --provider openai --model gpt-5.5
```

`test.py` and `run_all.py` read their environment variables — `ANTHROPIC_API_KEY`,
`OPENAI_API_KEY`, `MODEL`, `MEMORY_GB`, `LLAMA_BASE_URL`, `HOST_LLAMA_URL` — from a `.env` at the
repo root, so a key never has to be typed on the command line. The file is
gitignored; anything exported in the shell takes precedence over it.

```bash
# .env at the repo root
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
MODEL=claude-opus-5
```

Each run builds a task image (the agent container + a mamba env with
scanpy/scirpy), starts a **fresh** container, gives the agent [a base prompt](test/SYSTEM.md), the task
prompt (from the respective `task.json`) plus the required output shape with all values masked. The results is stored in a
`output.json` that is later graded automatically. Additionally, Jupyter notebook with the completed task is saved. Everything lands
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
