# Shockwave memory/KV-cache experiment — **do not restart yet**

**Goal:** Determine whether explicit KV-cache budgeting improves *startup repeatability* and memory headroom for Qwen3.8 Flash Next NVFP4 on a single Jetson AGX Thor. Keep latency, cache-hit observations, decode speed and usable context as acceptance gates. **This is an experiment plan, not a tested replacement launch command.**

## Baseline we must preserve

| Parameter | Observed working baseline |
|---|---|
| Device | Jetson AGX Thor 128 GB unified memory, JetPack 7.2.1 / R39.2.1 |
| Inference | `ghcr.io/nvidia-ai-iot/vllm:qwen3.8-next-jetson-thor` serving `local-inference-lab/Qwen3.8-Flash-Next-NVFP4` |
| GPU fraction | `--gpu-memory-utilization 0.90` |
| Configured max context | `--max-model-len 212992` (not verified at full length) |
| Concurrency | `--max-num-seqs 1` |
| MTP | Off, due to missing draft checkpoint shards |
| Prefix reuse | Server cache-hit counters observed in five-pair tests; default effective flag not independently confirmed |
| Current launch recipe | [`models/qwen3.8-flash-next/serve.sh`](../models/qwen3.8-flash-next/serve.sh) |

Historical failed setting: `--gpu-memory-utilization 0.93` required **114.21 GiB** but only **112.66 GiB** was free at startup; clearing filesystem cache increased the latter only to **113.24 GiB**, still not enough. Reducing to 0.90 succeeded. See [memory issue #2](https://github.com/kagaho/jetson-thor-llm-bench/issues/2).

## Key technical constraint

In supported versions of vLLM, `--kv-cache-memory-bytes N` **replaces** the automatic KV sizing driven by `--gpu-memory-utilization`; it does **not** add memory, increase model capacity, or establish that 262,144 context tokens will fit. Model weights, CUDA graphs, other allocations and OS processes still share the physical RAM budget. A too-small explicit KV budget can fail the model's context-capacity startup check even if model loading succeeds.

The specialized NVIDIA image may have different vLLM flags or semantics. **Check support inside that exact image before attempting a replacement.** Do not assume the latest upstream documentation describes the pinned Jetson runtime.

References: [vLLM current engine arguments](https://docs.vllm.ai/en/latest/configuration/engine_args/) and [prefix-cache production metrics](https://docs.vllm.ai/en/stable/usage/metrics/).

## Phase A: record the working state without stopping Docker

From a second terminal, while the existing model serves:

```bash
cd ~/Documents/jetson-thor-llm-bench
python3 -m thorbench doctor --container qwen38-flash-next > results/pre-restart-doctor.json
free -h
sudo nvpmodel -q
curl -fsS http://127.0.0.1:8000/health
# Keep any raw Docker logs LOCAL: they may contain paths, prompts or credentials.
docker logs --tail 200 qwen38-flash-next > results/pre-restart-docker.log 2>&1
```

Also capture current `--gpu-memory-utilization`, `--max-model-len`, model revision, container image digest, power mode and available memory. Run the `quick`, `prefix`, `agent` and tool-routing suites (same flags across A/B), then preserve their numeric summaries privately. This prevents comparing a freshly initialized candidate against a warmed baseline as if they were equivalent.

## Phase B: **later, scheduled restart** after baselines and rollback review

1. Confirm the original `docker run` terminal can be interrupted. If Docker was started interactively with `--rm`, **Ctrl+C generally stops and removes the container**; an explicit `docker stop qwen38-flash-next` from a second terminal is usually clearer. Confirm with `docker ps`. The Hugging Face and vLLM caches are bind-mounted in the documented recipe; verify your actual container's volumes before stopping it.
2. Start the **same unchanged baseline** once using `bash models/qwen3.8-flash-next/serve.sh`. Verify `/health`, model registration, free memory, 8192-token inference and prefix hits. If this fails, stop and investigate startup repeatability rather than attempting tunings.
3. Stop that reproduced baseline. For **candidate B**, introduce just `--kv-cache-memory-bytes` with a **measured budget** determined from runtime cache allocation logs, required context capacity, and safety margin. Do not use an arbitrary size or alter MTP, max-model-len, GPU fraction, quantization and concurrency in the same comparison. Test that the customized Jetson image actually recognizes the flag.
4. Compare startup success, memory available, reported KV capacity/context, TTFT, decode throughput and cache reuse across equal prompt workloads. Record failures and OOM logs. **Do not repeatedly call `drop_caches` during timing tests** (it distorts I/O and performance).
5. If candidate B fails or regresses, **rollback** to the known recipe: `bash models/qwen3.8-flash-next/serve.sh` after ensuring no same-named container remains.

Do not directly use a custom startup flag until its support and KV allocation requirements are verified. If context capacity must be reduced, treat that as a **separate experiment** with a different hypothesis; it is not an apples-to-apples memory fix.

## Proposed comparison table (fill only after measurements)

| Metric | A: verified 0.90 baseline | B: explicit KV budget |
|---|---|---|
| Image digest / checkpoint revision | Record | Same as A |
| Startup success | Record | Pending |
| Available RAM before startup | Record | Record |
| Peak/steady RAM | Record | Pending |
| KV cache capacity / context | Record | Pending |
| Prefix-hit counter behavior | Record | Pending |
| Median TTFT/TTFC | Record | Pending |
| Decode tok/s | Record | Pending |
| Tool routing pass rate | Record | Pending |

**Decision gate:** Keep B only if it starts reliably, stays within physical memory, preserves required context and tool behavior, and delivers a measurable benefit. Otherwise revert to A. See [workflow diagram](diagrams/11-memory-budget-restart.md).
