# Running Qwen3-Coder-30B-A3B at native 262k context on a 12 GB card

_Measured 2026-08-03 · RTX 4070 SUPER (12 GB) · WSL2 · llama.cpp `b10235`_

An ablation over **context size × KV cache type × KV placement × expert
offload**, to find a configuration that runs this model at its full native
context on a 12 GB GPU at usable speed.

Units: **MiB/GiB** throughout, to match `nvidia-smi`.

## Bottom line

Native 262144 context is reachable, and costs almost nothing in speed
relative to half that context. What it actually costs is **KV cache
fidelity** — q4_0 instead of q8_0 — and **all expert layers on the CPU**.

```ini
[unsloth/Qwen3-Coder-30B-A3B-Instruct-GGUF:Q4_K_XL]
jinja = 1
ctx-size = 262144
hf-repo = unsloth/Qwen3-Coder-30B-A3B-Instruct-GGUF:Q4_K_XL
n-gpu-layers = 99
n-cpu-moe = 48          # every expert to CPU
cache-type-k = q4_0
cache-type-v = q4_0
parallel = 1
```

→ 469 t/s prefill, 16.4 t/s generation at 99k tokens of context, 1872 MiB
VRAM spare.

The single most important finding: **keep the KV cache on the GPU.**
`--no-kv-offload` also fits native context, by putting the cache in system
RAM, and looks fine on short prompts — but generation collapses to 1.46 t/s
once the context is actually full.

## Setup

| | |
|---|---|
| GPU | RTX 4070 SUPER, 12282 MiB, driver 591.86 |
| Host RAM | 48 GB, of which WSL2 sees **35 GB** |
| llama.cpp | `b10235-221f0f635`, built from source against **CUDA 12.6**, `sm_89` |
| Model | `unsloth/Qwen3-Coder-30B-A3B-Instruct-GGUF:Q4_K_XL`, 17 GB |
| Architecture | 48 layers, 128 experts (~3B active), 4 KV heads, head dim 128 |
| Native context | 262144 (`qwen3moe.context_length` in the GGUF header) |

**Prerequisite:** these numbers are only obtainable on a CUDA 12 build. The
prebuilt CUDA 13 binaries fail `cublasCreate_v2` with
`CUBLAS_STATUS_ALLOC_FAILED` on any prompt long enough to take the cuBLAS
path, independent of free VRAM, offload, batch size and mmap. Short prompts
succeed and make a broken build look healthy. See
[`../docker-agent/README.md`](../docker-agent/README.md#prerequisites).

### Method

Each configuration: start `llama serve` standalone, wait for
`llama_server: model loaded`, issue one `/v1/chat/completions` request, record
`prompt eval time` / `eval time` from the server log plus `nvidia-smi` free
VRAM and process RSS. Probe prompts are synthetic filler
(`Item {i}: the quick brown fox ... number {i}.`) sized to a target depth:

| probe | context tokens |
|---|---|
| short | 760 |
| deep | 99,000 |
| very deep | 181,800 |

## The KV cache is the binding constraint

KV size is fixed by architecture: 2 (K+V) × 48 layers × 4 KV heads × 128 dim
= **49152 elements per token**. Per-element cost is 2 B at f16, 1.0625 B at
q8_0 (32 values per 34-byte block), 0.5625 B at q4_0 (32 per 18 bytes):

| KV type | per token | at 131072 | at 262144 |
|---|---|---|---|
| f16 | 96 KiB | 12 GiB | **24 GiB** |
| q8_0 | 51 KiB | 6.4 GiB | **12.75 GiB** |
| q4_0 | 27 KiB | 3.4 GiB | **6.75 GiB** |

Against ~11.2 GiB of usable VRAM (the Windows desktop holds 1.0–1.5 GiB
persistently), only q4_0 leaves room for weights at native context. This is
arithmetic, not a measurement — but every row below is consistent with it.

## Ablation 1 — expert offload at 32k context

`ctx-size = 32768`, q8_0 KV on GPU, 760-token probe. Here KV is small
(1.6 GiB), so `n-cpu-moe` is purely a speed knob:

| `n-cpu-moe` | free VRAM | prefill | generation |
|---|---|---|---|
| 36 | 3636 MiB | 639 t/s | 35.1 t/s |
| 32 | 2338 MiB | 830 t/s | 40.4 t/s |
| 28 | 996 MiB | 898 t/s | 42.0 t/s |
| 24 | 204 MiB | 954 t/s | 44.1 t/s |

Monotonic: every expert layer moved back to the GPU buys speed. 24 is not
usable in practice — 204 MiB spare is inside the range the Windows desktop
fluctuates by.

## Ablation 2 — KV placement at native context

`ctx-size = 262144`, `--no-kv-offload` (KV in system RAM), `n-cpu-moe = 32`:

| KV type | free VRAM | process RSS | prefill @760 |
|---|---|---|---|
| q8_0 | 2772 MiB | 24.2 GB | 812 t/s |
| q4_0 | 2893 MiB | 18.2 GB | 812 t/s |

The 6 GB RSS gap matches the predicted q8_0−q4_0 KV difference, confirming
the cache really is in host RAM. **On a short prompt this looks excellent** —
native context, plenty of VRAM spare, 812 t/s.

Then the same configuration at 181,800 tokens of context:

| depth | prefill | generation | wall |
|---|---|---|---|
| 760 | 812 t/s | — | 5 s |
| 181,800 | 363 t/s | **1.46 t/s** | **504 s** |

Prefill degrades gracefully; generation does not. The mechanism is
straightforward: with the cache in RAM, every generated token reads the
entire KV cache across PCIe. At 181,800 tokens × 51 KiB ≈ 8.8 GiB per token,
and ~13–16 GB/s of achievable PCIe bandwidth, that predicts ~0.6 s/token ≈
1.5 t/s — matching the measured 1.46 t/s.

**A short-prompt benchmark cannot detect this.** It is the same trap as the
CUDA 13 cuBLAS bug: healthy at 760 tokens, unusable at depth.

## Ablation 3 — the full matrix at depth

All rows below at **99,000 tokens** of context, KV on the GPU, except the
first (repeated from above at 181,800 for reference):

| ctx | KV | placement | `n-cpu-moe` | free VRAM | prefill | generation |
|---|---|---|---|---|---|---|
| 262144 | q8_0 | RAM | 32 | 2745 MiB | 363 t/s | **1.46 t/s** ¹ |
| 131072 | q4_0 | GPU | 40 | 2541 MiB | 523 t/s | 18.4 t/s |
| 131072 | q4_0 | GPU | 32 | 356 MiB | 614 t/s | 19.1 t/s |
| 131072 | q8_0 | GPU | 48 | 2491 MiB | 490 t/s | 16.1 t/s |
| **262144** | **q4_0** | **GPU** | **48** | **1872 MiB** | 469 t/s | **16.4 t/s** |

¹ measured at 181,800 tokens, not 99,000 — deeper than the other rows, so not
a strictly like-for-like comparison. Depth alone does not explain an 11×
gap, though: the GPU-resident rows lose only ~15% of prefill between 2k and
99k.

Three conclusions:

1. **Context length is nearly free.** 262144 runs at the same speed as
   131072 (16.4 vs 16.1 t/s). Doubling context costs ~3.4 GiB of VRAM, not
   throughput.
2. **KV placement dominates everything.** GPU-resident KV is ~11× faster at
   generation than RAM-resident.
3. **The real trade is fidelity, not length.** At a fixed ~16 t/s you may
   have either 262144 with q4_0 KV, or 131072 with q8_0 KV.

## Confounders found and eliminated

- **A router-level `-c` silently overrides each model's preset.** With
  `-c 32768` passed to `llama serve`, a preset requesting
  `ctx-size = 262144` spawned its child with `--ctx-size 32768` and no
  warning. This invalidated an earlier round of "32k is insufficient"
  conclusions. `docker-agent/llama-server.sh` now passes neither `-c` nor
  `-ngl` unless explicitly asked.
- **Free-VRAM thresholds looked causal and were not.** During the CUDA 13
  investigation, `cublasCreate_v2` failed at 3637, 6323 and 7670 MiB free
  and once *succeeded* at 7670 MiB — the apparent threshold was noise around
  a build defect.
- **The Windows desktop shares this GPU.** Idle baseline moved between 1027
  and 1513 MiB across the session, so any configuration leaving < ~500 MiB
  spare is not reproducible.

## Limitations

- **Single-shot measurements**, no repeats, no error bars.
- **Generation throughput is measured over 8–24 tokens**, so those figures
  are coarse; prefill figures come from thousands of tokens and are firmer.
- **Output quality was not evaluated at all.** Whether q4_0 K-cache degrades
  answers on real repertoire-analysis tasks is untested, and it is the main
  open question for the recommended configuration. If results look worse
  than expected, `ctx-size = 131072` with q8_0 K/V is the same speed with a
  better cache.
- **Synthetic filler prompts.** Highly repetitive text; attention behaviour
  and cache locality on real code/notebook context may differ.
- **One model, one quant, one GPU.**
- The 99,000-token probes fill ~38% of the native window. Behaviour at
  200k+ is extrapolated, not measured.

## Reproducing

```bash
M='unsloth/Qwen3-Coder-30B-A3B-Instruct-GGUF:Q4_K_XL'

# build a deep probe (~99k tokens)
python3 - <<'PY'
import json
body = " ".join(f"Item {i}: the quick brown fox jumps over the lazy dog number {i}." for i in range(4400))
json.dump({"model":"x","messages":[{"role":"user","content":body+"\n\nHow many items are listed?"}],
           "max_tokens":24}, open("probe.json","w"))
PY

llama serve --hf-repo "$M" --jinja -ngl 99 -ncmoe 48 \
  --ctx-size 262144 -ctk q4_0 -ctv q4_0 --parallel 1 \
  --host 127.0.0.1 --port 9400 &

curl -s http://127.0.0.1:9400/v1/chat/completions \
  -H 'Content-Type: application/json' --data-binary @probe.json
# then read `prompt eval time` / `eval time` from the server log
```

End-to-end check through the router (what the agent actually uses): a
99,000-token request returned HTTP 200 with the correct answer in 211 s.

## See also

- [`../docker-agent/README.md`](../docker-agent/README.md) — the CUDA 12 build
  requirement, preset layout, and the container that consumes this server
- [`local-coding-models-report.md`](./local-coding-models-report.md) — why
  this model was chosen for this hardware
