# docker-agent

A sandboxed container for running [opencode](https://opencode.ai) against a
locally-served LLM, without giving the agent any access to the host
filesystem, other containers, or the Docker daemon.

The model itself runs natively on the host via `ollama serve`, so it keeps
full GPU acceleration. Only the agent process — the part that will eventually
have file and tool access — runs inside the sandbox. The two talk to each
other over the network.

This is one of two isolation setups in this repository; see
[Comparison with `docker/`](#comparison-with-docker) for when to use which.

## Why isolate the agent instead of the model

A language model on its own can only produce text — it can't touch a
filesystem or run a command. The thing that actually needs sandboxing is the
agent harness wrapping it: the part with tool-calling, file access, and shell
execution. Isolating the client rather than the model server has two
consequences:

- The model keeps whatever hardware acceleration the host provides (Metal on
  macOS, CUDA on Linux/WSL2 with an NVIDIA GPU) instead of being CPU-bound
  inside a container.
- Sandboxing effort goes where the actual risk is, and stays in place as more
  tools get added to the agent later.

## Prerequisites

- [Docker](https://www.docker.com/products/docker-desktop/) or a compatible
  container runtime, with Compose v2
- [Ollama](https://ollama.com) installed and serving on the host:

  ```bash
  ollama serve
  ollama pull qwen3.6
  ```

  Then derive the 128k-context variant this setup defaults to (see
  [the context window note](#configuration) for why) — or just run the
  repo-root [`../setup.sh`](../setup.sh), which does the pull, the derive,
  and everything below in one go:

  ```bash
  printf 'FROM qwen3.6:latest\nPARAMETER num_ctx 131072\n' > Modelfile
  ollama create qwen3.6-128k -f Modelfile
  ```

## Quick start

```bash
./docker-agent/setup.sh
```

This builds the image, starts the container, and confirms it can reach the
host's Ollama server. Then:

```bash
./docker-agent/chat.sh                        # interactive session, default: host/qwen3.6-128k
./docker-agent/chat.sh host/glm-4.7-flash-128k # or any other configured model
```

For scripting or automated testing:

```bash
docker exec pytcr-agent opencode run --model host/qwen3.6-128k "your prompt"
```

## Configuration

Models are declared in [`opencode.json`](./opencode.json) under a provider
named `host`, pointing at the host's Ollama server:

```jsonc
{
  "provider": {
    "host": {
      "npm": "@ai-sdk/openai-compatible",
      "options": { "baseURL": "http://host.docker.internal:11434/v1" },
      "models": { "qwen3.6": { "name": "qwen3.6-35b" } }
    }
  }
}
```

Add an entry per model you want available, then rebuild
(`docker compose -f docker-agent/docker-compose.yml up -d --build`). Models
are referenced as `host/<name>`, matching the provider name.

**Context window note:** Ollama defaults a model's loaded context window to
32768 tokens regardless of what the model architecture actually supports —
visible via `ollama ps`'s `CONTEXT` column, and as the `-c` flag on the
underlying `llama-server` process (`ps aux | grep llama-server`). Multi-step
agentic tasks that inspect real data can exhaust 32768 tokens of cumulative
tool-call history before finishing, with no error — the model just silently
stops producing useful output once the context fills. Every `*-128k` entry
in `opencode.json` is a derived model (`ollama create qwen3.6-128k -f
Modelfile` with `FROM qwen3.6:latest` + `PARAMETER num_ctx 131072`) for
exactly this case — same weights, no re-download, only the loaded context
window differs. Memory cost is small (measured ~1GB extra RSS for 4x the
context). Use `host/qwen3.6-128k` (the default here and in `test/`) rather
than `host/qwen3.6` for anything involving nontrivial tool use.

Even at 128k, a long multi-step task can still fill the window — opencode
has automatic compaction (`compaction.auto`, on by default) meant to
summarize and free up space before that happens, but it only triggers if
opencode knows the model's context size. For custom `openai-compatible`
models this isn't inferred from anywhere, so each model entry above
declares `"limit": { "context": N, "output": N }` matching its Modelfile's
`num_ctx` — without it, auto-compaction never fires and the run instead
rides straight to the hard wall (observed: token count climbs to exactly
`num_ctx` and the model silently stops producing output, same failure mode
as the default-32768 case above, just at whatever ceiling was configured).

### Known issue — Ollama's OpenAI-compat endpoint drops tool calls under streaming

Repeated eval-harness runs (see `test/03-clonotype-networks`) have hit a
failure independent of model or prompt/skill content: partway through a
task — consistently right after an ordinary tool error the model needed to
recover from, e.g. a Python `SyntaxError` — the turn ends abruptly with
`finish_reason: "stop"`, no tool call, no error, session just over. This
reproduced on **both** qwen3.6 (reasoning channel leaking literal
`<|mask_start|><think>` tokens) and glm-4.7-flash (a malformed
`<tool_call>`-tag leak) — two structurally different models, same failure
shape, different leak signatures. Root cause: this is a documented,
maintainer-acknowledged upstream Ollama bug
([ollama/ollama#12557](https://github.com/ollama/ollama/issues/12557)) —
Ollama's OpenAI-compatible endpoint (`/v1/chat/completions`, exactly what
`opencode.json` is pointed at) silently drops tool calls under streaming.
Ollama's *native* `/api/chat` endpoint doesn't have this bug, but opencode
has no built-in native-Ollama provider.

**We tried switching to llama.cpp's own `llama-server` to route around this
entirely (cutting Ollama's serving path out, reusing its already-downloaded
GGUF blobs directly — `~/.ollama/models/blobs/sha256-...` are plain GGUF
files, confirmed via the `GGUF` magic number) — it didn't work, for reasons
independent of the tool-calling bug itself:**
- `glm-4.7-flash`'s architecture (`glm4moelite`) isn't recognized by
  llama.cpp, even on the latest Homebrew-packaged stable release (`brew
  upgrade llama.cpp` to 10050 didn't help).
- `qwen3.6`'s GGUF fails on a metadata-schema mismatch: `error loading model
  hyperparameters: key qwen35moe.rope.dimension_sections has wrong array
  length; expected 4, got 3` — the architecture is recognized, but this
  specific blob's metadata was written by a different llama.cpp/converter
  version than what's installed now.

Both are real, verified blockers (not something to retry past) — Ollama's
distributed GGUF blobs are structurally valid GGUF files but aren't
guaranteed metadata-schema-compatible with an independently-versioned
llama.cpp build. A retry would need either freshly-converted GGUFs from a
source that targets the current llama.cpp version (e.g. Unsloth's
Hugging Face GGUF repos) or building llama.cpp from source/HEAD past what
Homebrew packages — neither attempted yet. Until then, this setup is back on
`ollama serve`, living with the streaming-tool-call bug (mitigated only by
`test/SYSTEM.md`'s explicit "don't rewrite the whole notebook after one
error" instruction, which reduces how often the agent lands on the exact
recovery-after-error moment that seems to trigger it — not a real fix).
Also worth noting for a future attempt: `--jinja` is mandatory for GLM
models on `llama-server` (without it, tool calls/thinking blocks come out
malformed — a different bug, same symptom class as the one above).

`host.docker.internal` is Docker's standard container→host DNS name and
works out of the box on Docker Desktop (macOS, Windows/WSL2). On Linux you
may need `--add-host=host.docker.internal:host-gateway`, already set for
Docker Desktop but not always for other Linux Docker installs.

## Isolation model

| Property | Mechanism |
|---|---|
| No host filesystem access | Zero host bind mounts — not even read-only |
| Can't escalate privileges | `cap_drop: [ALL]` + `no-new-privileges:true` |
| Can't reach the Docker daemon or other containers | No `docker.sock` mount |
| Config/cache state | A container-only named volume, discarded with `docker compose down -v` |

**The root filesystem is writable, not read-only.** A `read_only: true` root
filesystem reliably crashed opencode's TUI (`Effect.tryPromise / Unexpected
error`) — reproduced with a fresh state volume and every other hardening
flag still in place, isolated by removing flags one at a time until only
`read_only` remained the differentiator; `strace` didn't surface one clearly
causal failing syscall. This turned out not to matter much: the agent is
meant to run commands and write files as part of its normal job, so a
container-local writable filesystem isn't something to lock down, it's a
requirement. What's still enforced is *scope* — there are no host bind
mounts, so writes stay inside the container's own filesystem (image layers
+ the state volume) and never touch the host. A deliberately scoped,
writable workspace mount is the natural next step for giving the agent real
project files to work with.

**Known limitation — network egress is not restricted.** The container can
reach the open internet, not just the host's Ollama server. Docker's
`internal: true` network mode was evaluated as a way to close this, but it
also blocks `host.docker.internal`, which this setup depends on — so it
isn't usable here without further work (e.g. a proxy sidecar with an
allowlist).

## Performance

Isolating the agent rather than the model avoids the CPU-only penalty that
running Ollama itself in a container incurs on macOS (see
[`docker/README.md`](../docker/README.md#performance)). Measured on a 35B
Q4_K_M model with GPU acceleration confirmed active on the host
(`ollama ps` reporting `100% GPU`):

| Call path | Time (warm) |
|---|---|
| Direct Ollama API call | ~3.5s |
| `opencode run` inside this container | ~19s |
| `opencode run` natively on the host, no container | ~44s (single sample) |

The overhead between a bare API call and an opencode session comes from
opencode itself — system prompt and tool schemas sent on every turn, plus
the model's own reasoning trace — not from containerization. The sandbox
adds no measurable cost of its own.

## Comparison with `docker/`

| | [`docker/`](../docker/) | `docker-agent/` (this one) |
|---|---|---|
| What's isolated | The model itself | The agent/client |
| Model acceleration | CPU-only on macOS; GPU passthrough on Linux/WSL2 with an NVIDIA GPU | Whatever the host natively supports |
| Host dependencies | None beyond Docker | A running `ollama serve` on the host |
| Best for | Untrusted model files; Linux/WSL2 with GPU passthrough | macOS, or anywhere the model should keep native acceleration |
