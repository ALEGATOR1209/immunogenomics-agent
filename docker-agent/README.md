# docker-agent

A sandboxed container for running [pi](https://github.com/badlogic/pi-mono)
against a locally-served LLM, without giving the agent any access to the host
filesystem, other containers, or the Docker daemon.

The model itself runs natively on the host via llama.cpp's router server, so
it keeps full GPU acceleration. Only the agent process — the part with file
and shell access — runs inside the sandbox. The two talk over the network.

This is one of two isolation setups in this repository; see
[Comparison with `docker/`](#comparison-with-docker) for when to use which.

## Why isolate the agent instead of the model

A language model on its own can only produce text — it can't touch a
filesystem or run a command. The thing that actually needs sandboxing is the
agent harness wrapping it: tool-calling, file access, shell execution.
Isolating the client rather than the model server has two consequences:

- The model keeps whatever hardware acceleration the host provides (CUDA on
  Linux/WSL2 with an NVIDIA GPU) instead of being CPU-bound in a container.
- Sandboxing effort goes where the actual risk is, and stays in place as more
  tools get added to the agent later.

## Prerequisites

- Docker (or a compatible runtime) with Compose v2.
- A working `llama` binary on the host, with `llama-server`/`llama` on PATH.

  **Build it from source — do not use the prebuilt CUDA 13 binaries.** On this
  hardware (RTX 4070 SUPER, WSL2, driver 591.86) the cu13 prebuilt fails
  `cublasCreate_v2` with `CUBLAS_STATUS_ALLOC_FAILED` on *any* prompt long
  enough to take the cuBLAS path — a few hundred tokens — while short prompts
  succeed and make it look healthy. It is independent of free VRAM, offload
  (`-ngl 0` still fails), batch size, mmap, and concurrency. Building the same
  source against **CUDA 12.6** fixes it outright. See the repo-root README for
  the build recipe.

- At least one GGUF model, either under `~/models` or declared in
  `~/.config/llama.cpp/presets.ini`.

## Quick start

```bash
./docker-agent/llama-server.sh --load <model-id>   # host: start the router, load a model
./docker-agent/setup.sh                            # build + start the container
./docker-agent/chat.sh                             # interactive session
```

`setup.sh` verifies from *inside* the container that it can actually reach the
host's router, which is the failure this setup hits most often.

For scripting or automated testing:

```bash
docker exec pytcr-agent pi -p "your prompt" \
  --provider llama-cpp --model <model-id>
```

### Chatting with Claude instead of a local model

`chat.sh` can also drive pi's *built-in* `anthropic` provider — no extra
package needed (unlike `llama-cpp`, which comes from the separate
`pi-llama` install in this directory's `Dockerfile`):

```bash
export ANTHROPIC_API_KEY=sk-ant-...
./docker-agent/chat.sh --provider anthropic claude-opus-5
```

The key is read from your current shell and passed into the already-running
`pytcr-agent` container per invocation (`docker exec -e`) — it's never baked
into the image, `docker-compose.yml`, or persisted in the container, and
there's no need to restart the container or re-run `setup.sh` to use it.
Unlike `llama-cpp`, there's no router to fall back to for model selection —
`--provider anthropic` requires an explicit model id (e.g. `claude-opus-5`,
`claude-sonnet-5`, `claude-haiku-4-5`). The container isn't network-isolated,
so it reaches `api.anthropic.com` over normal egress with no other config.

## `llama-server.sh` — the model server

Starts llama.cpp in **router mode**, which discovers every GGUF under
`--models-dir` plus every section of `--models-preset` and loads/unloads them
on demand. That's what pi's `/llama` command drives, and it's why per-model
flags belong in `presets.ini` rather than on the command line.

```bash
./llama-server.sh                        # start, load nothing
./llama-server.sh --load <model-id>      # start and load one model (waits for it)
./llama-server.sh --list                 # what a running router knows
./llama-server.sh --port 8081
./llama-server.sh --bind 127.0.0.1       # local only - container can NOT reach this
./llama-server.sh --ctx 65536            # override EVERY model's preset ctx-size
```

Env equivalents: `LLAMA_PORT`, `LLAMA_BIND`, `LLAMA_CTX`, `LLAMA_NGL`,
`LLAMA_MODELS_DIR`, `LLAMA_PRESETS`. Flags win. Re-running while a server is
already up attaches to it instead of starting a second one.

**`--ctx`/`--ngl` are deliberately unset by default.** A router-level `-c`
silently overrides the per-model `ctx-size` in `presets.ini`: with `-c 32768`
on the router, a preset asking for `ctx-size = 262144` spawned its child with
`--ctx-size 32768` and no warning. Per-model flags belong in the preset.

**It binds `0.0.0.0` by default.** llama-server's own default is
`127.0.0.1`, which a container cannot reach over `host.docker.internal` — the
single most common reason the agent can't see the model. The tradeoff is LAN
exposure; pass `--bind 127.0.0.1` when you're not using the container.

**`--no-models-autoload` is always passed**, so loading stays explicit. Without
it a stray request can pull a multi-GB model into VRAM as a side effect.

## Configuration

There is no model config in this directory. `~/.config/llama.cpp/presets.ini`
on the host is the single source of truth for which models exist and what
flags each one loads with; the container discovers them from the router at
runtime. A preset looks like:

```ini
[unsloth/Qwen3-Coder-30B-A3B-Instruct-GGUF:Q4_K_XL]
jinja = 1
ctx-size = 262144       # the model's native context
hf-repo = unsloth/Qwen3-Coder-30B-A3B-Instruct-GGUF:Q4_K_XL
n-gpu-layers = 99
n-cpu-moe = 48          # ALL experts to CPU, freeing VRAM for the KV cache
cache-type-k = q4_0
cache-type-v = q4_0
parallel = 1
```

### Sizing the KV cache against `n-cpu-moe`

Both compete for the same 12 GB. This model's KV cost is fixed by its shape
(48 layers × 4 KV heads × 128 dim = 49152 elements/token):

| KV type | per token | at 131072 | at 262144 |
|---|---|---|---|
| f16 | 96 KB | 12.9 GB | 25.8 GB |
| q8_0 | 51 KB | 6.8 GB | 13.7 GB |
| q4_0 | 27 KB | 3.6 GB | 7.3 GB |

So native context is only reachable with `q4_0` K/V, and only if the weights
get out of the way (`n-cpu-moe = 48` puts every expert on the CPU). Measured
at ~99k tokens of actual context on a 12 GB RTX 4070 SUPER:

| ctx | KV | where | `n-cpu-moe` | free VRAM | prefill | generation |
|---|---|---|---|---|---|---|
| 262144 | q8_0 | **RAM** (`-nkvo`) | 32 | 2745 MiB | 363 t/s | **1.46 t/s** |
| 131072 | q4_0 | GPU | 40 | 2541 MiB | 523 t/s | 18.4 t/s |
| 131072 | q8_0 | GPU | 48 | 2491 MiB | 490 t/s | 16.1 t/s |
| **262144** | **q4_0** | **GPU** | **48** | **1872 MiB** | 469 t/s | **16.4 t/s** |

**Keep the KV cache on the GPU.** `--no-kv-offload` also fits native context
by putting the cache in system RAM, but generation collapses to 1.46 t/s:
every generated token streams the entire cache across PCIe (~9 GB per token
at 181k context). Length itself is nearly free — native context runs at the
same speed as half context; what you actually trade is KV *fidelity*.

At shorter contexts, where KV is small, `n-cpu-moe` is purely a speed knob —
at 32k with `q8_0` KV: 36 → 639/35.1 t/s, 32 → 830/40.4, 28 → 898/42.0,
24 → 954/44.1 (but only 204 MiB spare, inside the range the Windows desktop
fluctuates by).

### The provider package is required

The `llama-cpp` provider is **not** built into pi. It comes from
`git:github.com/huggingface/pi-llama`, installed in the Dockerfile. Without
it, `pi --list-models` reports "No models available" regardless of
`LLAMA_BASE_URL` or `auth.json` — verified on a clean pi home, including with
both env vars set and with a hand-seeded credential.

Two details that follow from how that package works:

- The provider id is **`llama-cpp`** (hyphen). pi ships its own separate
  built-in `llama.cpp` (dot) extension; they are different providers with
  different behaviour, and passing the wrong one gives
  `Unknown provider "llama-cpp"` or a silent fallback.
- It reads `process.env.LLAMA_BASE_URL` directly (default
  `http://localhost:8080`) and needs no credential. `docker-compose.yml` sets
  it to `http://host.docker.internal:8080`.

Because /root is a named volume, the package is installed at build time under
a staging HOME (`/opt/pi-home`) and copied across on first boot by
`entrypoint.sh`. Existing settings are never overwritten; run
`docker compose down -v` to pick up an updated package from a rebuilt image.

### Only loaded models are usable

The router serves what's resident. Requesting an unloaded model returns
`400 {"message":"model is not loaded"}`. `chat.sh` defaults to whichever model
is currently loaded and tells you how to load one if none is. Inside a
session, `/llama` loads and unloads.

### If you run pi on the host too

pi's *built-in* `llama.cpp` extension stores a base URL in
`~/.pi/agent/auth.json` when you `/login`, and **that stored value overrides
the `LLAMA_BASE_URL` environment variable** (`credentialServerUrl(credential)
?? env` in its `provider.js`). A host pi pointed at a stale port will silently
keep using it. The container is unaffected — it starts with an empty volume
and no stored credential.

## Isolation model

| Property | Mechanism |
|---|---|
| No host filesystem access | Zero host bind mounts — not even read-only |
| Can't escalate privileges | `cap_drop: [ALL]` + `no-new-privileges:true` |
| Can't reach the Docker daemon or other containers | No `docker.sock` mount |
| Config/cache state | A container-only named volume, discarded with `docker compose down -v` |

**The root filesystem is writable, not read-only.** This dates from the
opencode era, where `read_only: true` reliably crashed opencode's TUI
(`Effect.tryPromise / Unexpected error`), isolated by removing hardening flags
one at a time until only `read_only` remained the differentiator. **That
finding has not been re-tested against pi** — it may well work now. It matters
less than it sounds: an agent that writes files as part of its job needs a
writable filesystem anyway, and scope is enforced by having no host bind
mounts at all, so writes stay inside the container.

**Known limitation — network egress is not restricted.** The container can
reach the open internet, not just the host's model server. Docker's
`internal: true` network mode was evaluated and rejected: it also blocks
`host.docker.internal`, which this setup depends on. Closing this would need
something like a proxy sidecar with an allowlist.

`host.docker.internal` is provided out of the box by Docker Desktop (macOS,
Windows/WSL2). `docker-compose.yml` also maps it explicitly via `extra_hosts:
host-gateway` for plain Linux Docker installs, where it otherwise doesn't
exist.

## Relationship to `test/`

The eval harness under `test/` builds `FROM pytcr-agent:latest` and has been
migrated alongside this directory: it invokes
`pi -p --mode json --provider llama-cpp --model <id>` and parses pi's event
stream. Two consequences worth knowing:

- **Model ids are router ids now** (`unsloth/Qwen3-Coder-30B-A3B-Instruct-GGUF:Q4_K_XL`),
  not `host/<name>`. There's no hardcoded default: `test.py` uses `--model`,
  then `MODEL`, then the router's single loaded model, and fails with the list
  if that's ambiguous.
- **Skills mount at `/root/.pi/agent/skills`** (pi's global auto-discovery
  location) rather than `/root/.claude/skills`.

`docker-agent/opencode.json` is gone; nothing reads it. Runs recorded before
the migration have `"harness": "opencode"` in their `eval_result.json` and are
not comparable to later ones — the harness, the model server, and the prompt
scaffold all changed at once.

## Comparison with `docker/`

| | [`docker/`](../docker/) | `docker-agent/` (this one) |
|---|---|---|
| What's isolated | The model itself | The agent/client |
| Model acceleration | CPU-only on macOS; GPU passthrough on Linux/WSL2 with an NVIDIA GPU | Whatever the host natively supports |
| Host dependencies | None beyond Docker | A running llama.cpp router on the host |
| Best for | Untrusted model files; Linux/WSL2 with GPU passthrough | Keeping native GPU acceleration |
