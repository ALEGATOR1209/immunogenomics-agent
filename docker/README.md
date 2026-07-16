# Isolated Ollama container (qwen3.6)

Runs a model in a locked-down Docker container so it can't touch anything on
your machine beyond what's explicitly given to it. Right now that's just chat —
no file access, no tool access. That's on purpose: this is meant to be the
base isolation layer that file/tool access gets added onto later, deliberately
and narrowly, rather than something that starts wide open. Works on macOS,
Linux, and WSL2 — see [Performance](#performance) for how they differ.

## Quick start

```bash
./docker/setup.sh
```

This one script:
1. Checks Docker is installed, starts Docker Desktop if it isn't running
2. Works out how much memory the model needs (from its manifest on disk) and
   waits for you to bump Docker's memory allocation if it's currently too low
3. Detects an NVIDIA GPU (Linux/WSL2 only) and enables passthrough if found
4. Builds and starts the container
5. Makes sure the model is actually loaded (pulls it if it isn't already
   present — see [Reproducibility](#reproducibility) below)

Then chat with it:

```bash
./docker/chat.sh              # defaults to qwen3.6
./docker/chat.sh qwen3.5      # or any other model
```

To use a different model with `setup.sh`: `MODEL=qwen3.5 ./docker/setup.sh`.

## What "isolated" means here

Verified, not just asserted — everything below was tested against the running
container:

| Property | How | Verified |
|---|---|---|
| Can't read your files | No host bind mounts except model weights (read-only) | ✅ only mount is `~/.ollama/models:ro` |
| Can't write to its own image / persist malware | `read_only: true` root filesystem | ✅ `touch /root/should-fail` → "Read-only file system" |
| Can't modify the model weights | Models mounted `:ro` | ✅ `touch` inside `models/` fails the same way |
| Can't gain privileges | `cap_drop: [ALL]` + `no-new-privileges:true` | ✅ `docker inspect` confirms both |
| Can't control the Docker daemon / other containers | No `docker.sock` mount, not `--privileged` | ✅ not present in compose file |
| Can't see host processes | Default PID namespace (not `pid: host`) | — Docker default, not overridden |

Two dirs *are* writable inside the container, both container-local (not backed
by anything on the host): a named volume at `/root/.ollama` (Ollama's own
config/keys/logs — thrown away with `docker compose down -v`) and a `tmpfs`
at `/tmp`.

### What isn't isolated (yet)

**Network egress is not blocked.** I tried the obvious fix — Docker's
`internal: true` network mode — and it also breaks host→container access on
the published port, which we need for chat. So right now the container *can*
reach the internet. This isn't a live risk today: the container only runs
`ollama serve`, there's no tool-calling or code-execution wired up, so there's
nothing inside it that would actually make an outbound call. But it's a gap
worth closing for real once file/tool access gets added — options at that
point include a network-namespace proxy with an allowlist, or restructuring
so the model process itself never gets a route out. Flagging this now so it
doesn't get assumed-solved later.

### Reproducibility

`qwen3.6` is a real, public Ollama model (Alibaba's Qwen team, released after
this assistant's knowledge cutoff — hence the earlier confusion; see
[ollama.com/library/qwen3.6](https://ollama.com/library/qwen3.6)). 27B/35B
variants, 17–24GB depending on quantization. `setup.sh` reuses whatever copy
is already in `~/.ollama/models` via a read-only bind mount when one exists
(fast path — this machine already has it, no download needed); on a machine
that doesn't, it falls back to `ollama pull "$MODEL"` inside the container,
which works unmodified since it's a public model. Either way, `./docker/setup.sh`
alone is enough on a fresh machine — it'll just take a few minutes to
download 17-24GB the first time.

## Talking to the model

**Interactive REPL** (via `docker exec`, no ports needed):

```bash
./docker/chat.sh
```

**Ollama-native API** from the host — container is on port **11436**, not
11434 (that's your native `ollama serve`) or 11435 (reserved for
"crocodesktop" per your opencode config):

```bash
curl http://localhost:11436/api/generate -d '{
  "model": "qwen3.6",
  "prompt": "Say hi in one sentence.",
  "stream": false
}' | jq .response
```

**OpenAI-compatible API**, for tools like `opencode`'s
`@ai-sdk/openai-compatible` provider — add to
`~/.config/opencode/opencode.json`:

```jsonc
"docker": {
  "npm": "@ai-sdk/openai-compatible",
  "name": "Dockerized LLMs",
  "options": { "baseURL": "http://127.0.0.1:11436/v1" },
  "models": { "qwen3.6": { "name": "qwen3.6-35b" } }
}
```

## Performance

On **macOS**, this always runs CPU-only — measured ~90s cold (model load) and
~20s warm per short response. This is structural, not a config issue: Docker
Desktop on Mac runs containers inside a Linux VM with no Metal/GPU passthrough
into it, and there's no flag that changes that. If you need Mac-native speed,
run `ollama serve` directly (outside Docker) instead — you lose the isolation
guarantees above in exchange for GPU acceleration.

On **Linux (bare metal) or WSL2 with an NVIDIA GPU**, this is fixable:
`setup.sh` auto-detects `nvidia-smi` and layers in `docker-compose.gpu.yml`,
which requests GPU passthrough via the standard
[NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html)
pattern (`deploy.resources.reservations.devices`, the modern non-Swarm way to
request GPU access from `docker compose up`). Requires the NVIDIA driver +
`nvidia-container-toolkit` installed on the host (and, for WSL2 specifically,
the [CUDA-on-WSL](https://docs.nvidia.com/cuda/wsl-user-guide/index.html) driver
stack). `setup.sh` verifies it worked with `docker exec pytcr-ollama
nvidia-smi` after starting and warns (without failing) if GPU was detected
but passthrough didn't actually take.

**Caveat: the GPU path is unverified.** Everything else in this setup — the
hardening, the memory detection, the CPU inference path — was built and
tested against a real running container on this machine. The GPU path is
based on Docker/NVIDIA's documented pattern but this machine only has a Mac
to test on, so it hasn't been run against real GPU hardware. If it doesn't
work, `docker exec pytcr-ollama nvidia-smi` failing is the first thing to
check, followed by confirming `nvidia-container-toolkit` is actually
configured as Docker's default/available runtime (`docker info | grep -i
runtime`).

**Linux/WSL2 without a GPU** is still CPU-only, same as macOS, but without
the VM overhead — Docker on Linux runs containers directly on the host
kernel rather than inside a virtualized Linux VM, so it should be somewhat
faster than the Mac numbers above even without GPU acceleration, though
that's not something measured here either.

## Teardown

```bash
docker compose -f docker/docker-compose.yml down     # stop, keep state volume
docker compose -f docker/docker-compose.yml down -v  # stop, also wipe state volume
```

The bind-mounted models directory is read-only and untouched either way —
nothing to clean up on the host side.
