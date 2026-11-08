# Shockwave memory A/B evaluation — baseline A and experimental B2

**Status as of November 8, 2026:** Candidate **B2 started successfully** with explicit 4 GiB KV cache, 131,072 maximum context and 0.88 startup utilization threshold. It passed 30/30 synthetic tool-routing cases, 5/5 prefix pairs, 5/5 synthetic agent pairs and two single-shot context retrieval probes. **Keep B2 running** for further stability testing; this is not a universal recommendation to replace high-context A.

For operational selection, both full Docker commands, shared features and the later dated live inspection, use the [serving-profile reference](SERVING_PROFILES.md). The historical A/B measurements below remain unchanged.

## Configurations and observed results

| Metric | Baseline A | Tuned B2 |
|---|---:|---:|
| Image digest | `512bf772…e7526` | Same |
| vLLM version | `0.28.1rc1.dev580+g385dce36b` | Same |
| GPU utilization threshold | `0.90` | `0.88` |
| KV memory | 5.26 GiB automatic | 4.00 GiB explicit (`4294967296` bytes) |
| KV token capacity | 214,535 | 159,862 |
| Maximum context | 212,992 | 131,072 |
| Reported concurrency for max context | 1.01× | 1.22× |
| `free -h` MemAvailable snapshot | 1.1 GiB | 3.4 GiB after start; 2.9 GiB after tests |
| Tool routing (first decision) | 30/30 | 30/30 |
| Median tool-routing latency | 2.9165 s | 3.1947 s |
| Prefix repeat TTFT (median) | ~0.51 s | ~0.52 s |
| Synthetic agent follow-up TTFT | ~0.63 s | ~0.65 s |

These are **different capacity configurations** (GPU threshold, KV budget and context limit changed), not a clean single-variable A/B. Differences in memory snapshots may reflect different OS/runtime states and should not all be attributed to KV-cache allocation.

## What the failed B attempt taught us

The **first** 4 GiB candidate with `--gpu-memory-utilization 0.90` failed its *initial* startup gate: free **109.94 GiB** was below required **110.52 GiB**. This is **not** an inference OOM. The observed vLLM build still evaluates this gate despite a manually specified KV cache. When B2 used utilization `0.88`, the gate passed; its logs explicitly say **`reserved 4.0 GiB memory for KV Cache as specified ... skipped memory profiling`**.

The B2 logs then reported **159,862** token KV capacity at max context 131,072 and successful API startup. Model loading consumed approximately **97.84 GiB** (vLLM logger figure). Its actual long-run stability and ability to fully utilize the 131K context remain unproven.

## First-decision tool routing: don't confuse more tokens with slower decoding

`no_tool_needed` returned a median **94 completion tokens / 4.30 s** on A versus **140 tokens / 6.44 s** on B2. `run_cache_tests` increased **58 → 73 tokens** and **2.82 → 3.59 s**. These increases in generation length are consistent with most of the extra wall time, but end-to-end response latency is **not** a pure decode-rate measurement. Other cases showed smaller differences; don't attribute them to the KV profile without matched outputs and power/clocks.

B2's context probes processed **7,992 prompt tokens / 91 completion tokens** in **9.8524 s**, and **31,652 prompt tokens / 90 completion tokens** in **25.603 s**. Both returned the required retrieval code. Their output lengths are matched, so higher *input* processing cost is a more plausible driver of the latency increase. Each context size had only one non-streaming request.

See the dedicated [B2 A/B results](benchmarks/2026-11-08-shockwave-b2-vs-a.md) and [output-length confounder case study](benchmarks/2026-11-08-shockwave-b2-output-length-context.md).

## Reproduce the two profiles (manual, sequential only)

The original working profile is [`models/qwen3.8-flash-next/serve.sh`](../models/qwen3.8-flash-next/serve.sh) (0.90, auto KV, 212,992 context). The experimental pinned image/low-memory profile is [`serve-lowmem.sh`](../models/qwen3.8-flash-next/serve-lowmem.sh) (0.88, 4 GiB KV, 131,072 context). **Neither script is executed by the benchmark suite.** Each uses the same container name and binds the same model caches; **never launch both simultaneously**.

Before any further restart, capture current Docker args, `free -h`, `/health`, benchmark reports and logs. Stop the running container explicitly, then run **one** desired profile from the repository root. If the low-memory candidate becomes unstable, stop it and restore the proven baseline profile.

```bash
# DO NOT run these while the serving container is already alive.
# Only after a deliberate shutdown:
bash models/qwen3.8-flash-next/serve-lowmem.sh
# Or rollback to the original higher-context profile:
bash models/qwen3.8-flash-next/serve.sh
```

For the observed image, `--kv-cache-memory-bytes` overrides KV sizing derived from `gpu_memory_utilization`, **but it did not eliminate the initial utilization-based free-memory check**. Do not keep reducing the threshold to bypass repeated failures, do not run page-cache drops during benchmark measurement, and do not change MTP/concurrency simultaneously.

## Acceptance gates before recommending B2 long term

1. Keep 30/30 synthetic tool-routing accuracy across controlled repeated runs; document input and output tokens.
2. Validate prefix hit **counter deltas** on an isolated endpoint and check sustained response latency; server-wide counters are not proof of request attribution without isolation.
3. Verify all required long-context workloads with actual `prompt_tokens`, *not* just configured max context.
4. Record power profile, clocks, available memory, GPU and model runtime allocations before/after the same workloads.
5. Check for crashes/OOM across repeated idle/active cycles; do not confuse one successful startup with long-run stability.

References: [vLLM KV-cache memory configuration](https://docs.vllm.ai/en/stable/configuration/engine_args/), [vLLM metrics](https://docs.vllm.ai/en/stable/usage/metrics/), and [historical startup-memory issue #2](https://github.com/kagaho/jetson-thor-llm-bench/issues/2).
