# Jetson Thor LLM Bench ⚡

**A minimal, reproducible, public-ready benchmark harness for local LLM/VLM inference on NVIDIA Jetson AGX Thor.** Designed around an existing vLLM OpenAI-compatible server; no dependencies beyond Python's standard library.

> **Status:** v0.1.0 · Prototype. The source is unit-tested offline; live benchmark results must be collected on your own Jetson. Not affiliated with NVIDIA, Qwen, or vLLM.

## Why this repository?

Large, quantized MoE models now run on single 128 GB unified-memory devices, but "it boots" is different from measuring **first-token latency, visible-answer latency, sustained decoding, reasoning overhead and context reliability**. This repository records those dimensions without committing private prompts, device identifiers, or model files.

### Suites

| Suite | Measures | What it does *not* claim |
|---|---|---|
| `quick` | Streaming TTFT, TTFC, generation throughput, latency | A standardized coding score |
| `reasoning` | Off / low / medium on the same prompt | Identical output quality across modes |
| `context` | Needle-in-haystack correctness at increasing approximate lengths | Full native context validation |
| `vision` | Local image request / response completeness | Visual accuracy or camera FPS |

## Prerequisites

- Python **3.10+** (`python3` is enough; no pip install required).
- An **already running** vLLM OpenAI-compatible service, e.g. Qwen3.8 Flash Next on Thor, bound to `127.0.0.1:8000`.
- Adequate free memory. Benchmark code is lightweight; **the model is not**.
- Run on Shockwave's terminal for localhost access. With SSH from another machine, use SSH tunneling rather than publicly exposing the API.

## Quick start on Shockwave

```bash
cd ~/Documents/jetson-thor-llm-bench
python3 -m unittest discover -s tests -v   # offline tests
python3 -m thorbench doctor                 # vLLM health, model, context, platform info
python3 -m thorbench bench --suite quick --runs 3
cat results/*-quick/summary.md
```

This does **not** restart the currently working container and does **not** download weights.

### Reasoning-mode comparison

```bash
python3 -m thorbench bench --suite reasoning --runs 2
```

All modes use the same coding prompt. Note that `enable_thinking=false` depends on support from the chosen Qwen model and chat template; any rejected request will be shown as a failure, not silently retried with a different setting.

### Context reliability (start small)

```bash
python3 -m thorbench bench --suite context --runs 1 --warmup 0
# More demanding (opt in after watching memory in jtop):
python3 -m thorbench bench --suite context --context-sizes 16384,32768 --runs 1 --warmup 0
# MUCH later: deliberately opt in to large tests:
# python3 -m thorbench bench --suite context --context-sizes 65536 --allow-large-context --runs 1 --warmup 0
```

Targets are approximate; see `prompt_tokens` for the server's actual count. The context suite stops after the first failure. **Do not start with a 212K input** just because `/v1/models` reports a 212,992-token maximum.

### Vision request

```bash
python3 -m thorbench bench --suite vision --image ~/Pictures/test.jpg --runs 1 --warmup 0
```

Use your own test image. It is sent in memory as a data URI and is **not persisted** in the benchmark results. The test checks API response success, not whether the description is accurate.

## Outputs

Each run creates a timestamped folder below `results/` with:

- `metadata.json` — model name, advertised context, non-identifying Jetson software information.
- `samples.jsonl` — request timing, token counts, pass/fail, and any errors. **No prompt or generated answer content.**
- `summary.md` — scenario-level median latency, TTFT, TTFC, throughput and pass counts.

**Everything under `results/` is ignored by Git.** To publish an anonymized benchmark, inspect it and explicitly copy only the fields you want to share to a tracked document.

## Running against other models

```bash
THOR_BENCH_BASE_URL=http://127.0.0.1:8000 \
THOR_BENCH_MODEL=Qwen3.8-Flash-Next \
python3 -m thorbench bench --suite quick
```

Optional `THOR_BENCH_API_KEY` is read from the environment, never stored in reports. Avoid entering it directly into tracked files.

## Reproducing the initial Thor container (optional)

`scripts/serve_qwen.sh` records the baseline launch flags: `GPU_MEMORY_UTILIZATION=0.90`, `MAX_MODEL_LEN=212992`, `--max-num-seqs 1`, and **MTP disabled**. Do **not** run it while your working vLLM container is already active. It is a convenience recipe, not part of benchmark execution.

The baseline includes a known missing MTP safetensors file and a KV-cache limitation at 262K: see [Shockwave baseline](docs/SHOCKWAVE_BASELINE.md). Model weights and base images are not included or relicensed.

## Make a public repository

```bash
cd ~/Documents/jetson-thor-llm-bench
python3 -m unittest discover -s tests -v
git init -b main
git add .
git diff --cached --stat
git commit -m "Initial public-ready Jetson Thor LLM benchmark harness"
```

Review `git status` and `git diff --cached` before publishing. **Do not publish an older private repository's full Git history** without reviewing it for credentials or machine details. Create a clean-history GitHub repository when ready.

## Documentation

- [Methodology and caveats](docs/METHODOLOGY.md)
- [Observed Shockwave baseline](docs/SHOCKWAVE_BASELINE.md)
- [Security and disclosure](SECURITY.md)
- [Contribution guidelines](CONTRIBUTING.md)

### References and credit

- [NVIDIA Jetson AI Lab — Qwen3.8 Flash Next](https://www.jetson-ai-lab.com/models/qwen3-8-flash-next/)
- [vLLM online serving documentation](https://docs.vllm.ai/en/stable/serving/online_serving/openai_compatible_server/)
- [vLLM reasoning streaming responses](https://docs.vllm.ai/en/stable/features/reasoning_outputs/)
- [Independent Thor deployment / benchmarks](https://github.com/Leibniz-HBI/Qwen3.8-Flash-Next-Jetson-Thor-vLLM) (context only; not copied code)

## License

MIT for benchmark source only. Model and runtime licenses belong to their owners.
