# Open-Weight Coding Models for Your PC

_Generated 2026-08-02 · tuned to detected hardware_

## Your hardware

- **GPU:** RTX 4070 SUPER — **12 GB VRAM**, CUDA 13.1 (driver 591.86)
- **System RAM:** 48 GB
- **CPU:** Ryzen 7 7800X3D (8c/16t)

## Bottom line

The 12 GB VRAM caps *dense* GPU-resident models at ~14B, but your 48 GB of RAM
unlocks the better play in 2026: **Mixture-of-Experts (MoE) models with expert
layers offloaded to system RAM.** These have ~30B total parameters but only ~3B
active per token, so they run at usable speeds while beating 14B dense models on
coding.

**Top pick: `Qwen3-Coder-30B-A3B`** — best coding model that runs well here,
purpose-built for agentic/tool-use coding.

## Recommended models, ranked

| Model | Type | Quant | VRAM | +RAM offload | Speed | Best for |
|---|---|---|---|---|---|---|
| **Qwen3-Coder-30B-A3B** ⭐ | MoE (3B active) | Q4_K_M | ~9–11 GB attn/KV | ~18 GB experts | ~20–30 tok/s | Best overall coder — agentic, tool use, repo-scale |
| **GPT-OSS-20B** | MoE, native MXFP4 | MXFP4 | ~12–13 GB | small | ~30–40 tok/s | Fast reasoning/coding, most VRAM-efficient MoE |
| **Qwen2.5-Coder-14B / Qwen3-14B** | Dense | Q4_K_M | ~9–10 GB | none | ~25–40 tok/s | Fully GPU-resident, lowest latency, offline autocomplete |
| **Gemma 3 12B** | Dense | Q4_K_M | ~8 GB | none | ~30–45 tok/s | General + multimodal, strong reasoning, fits with room to spare |
| **Qwen2.5-Coder-7B** | Dense | Q5/Q6 | ~6–7 GB | none | 50+ tok/s | Fast local autocomplete/FIM in-editor |

### Scientific coding

For Python/NumPy/SciPy/pandas, numerical methods, and plotting, the Qwen-Coder
line is the strongest open-weight choice — it leads open models on Python-heavy
benchmarks and handles library idioms well. Use **Qwen3-Coder-30B-A3B** for hard
problems, **Qwen2.5-Coder-14B** for fast iteration.

## How to run it (easiest → most control)

1. **LM Studio** or **Ollama** — one-line pull, handles MoE offload
   automatically. `ollama run qwen3-coder:30b` splits experts to RAM for you.
   Best starting point.
2. **llama.cpp** directly — most control. Key MoE flag offloads expert tensors to
   CPU while keeping attention/KV on GPU (`-ot` / `--n-cpu-moe`) — exactly what
   your 48 GB RAM is for. To stretch context, quantize the KV cache (`q8_0` keys,
   `q4_0` values).

**Quant rule of thumb:** pick the highest quant that fits — **Q4_K_M** is the
sweet spot (near-lossless, halves memory). Prefer **Unsloth dynamic GGUF** quants;
they preserve quality better than naive Q4.

## Caveat — fast-moving landscape

2026 guides also hype bigger models: **Qwen3-Coder-Next** (targets 48 GB VRAM /
64 GB Mac) and **Qwen 3.6 27B** (best on 24 GB GPUs). Those are a tier above your
VRAM for comfortable use, though Qwen3-Coder-Next can be squeezed on via heavy
offload if you want to experiment. For a smooth daily driver, stick with the
table above.

## Sources

- [PromptQuorum — Local LLMs by VRAM Tier (12/24/48GB)](https://www.promptquorum.com/local-llms)
- [Unsloth — Qwen3-Coder: How to Run Locally](https://unsloth.ai/docs/models/tutorials/qwen3-coder-how-to-run-locally)
- [Arsturn — Qwen3-Coder 30B Hardware Requirements](https://www.arsturn.com/blog/running-qwen3-coder-30b-at-full-context-memory-requirements-performance-tips)
- [LLM-Stats — GPT-OSS-20B vs Qwen3-30B-A3B](https://llm-stats.com/models/compare/gpt-oss-20b-vs-qwen3-30b-a3b)
- [KDnuggets — Top 7 Coding Models to Run Locally in 2026](https://www.kdnuggets.com/top-7-coding-models-you-can-run-locally-in-2026)
