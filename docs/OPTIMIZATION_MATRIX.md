# Thor inference optimization matrix — evaluated sources vs untested knobs

This matrix retains the historical v0.2.0 baseline feature state and proposed experiments. For A/B2 profile selection, complete commands and the latest dated live observation, use the [serving-profile reference](SERVING_PROFILES.md). The tracked [baseline Docker invocation](../models/qwen3.8-flash-next/serve.sh) and [machine-readable declared launch profile](../models/qwen3.8-flash-next/launch-profile.json) describe the original A recipe. Use `thorbench bench --container qwen38-flash-next` to capture a **sanitized observation** of the actual running container's CLI flags. Observed flags are not necessarily effective vLLM defaults.

## What the forum results actually compare

- [Marco Pastorio, forum post #1](https://forums.developer.nvidia.com/t/qwen3-8-flash-next-at-46-7-tok-s-on-jetson-agx-thor/383269): reported **34.8 to 46.7 output tok/s (token-weighted C1)** over a Code/JSON/LongCode/etc. `sgbench` mix on Thor. He changed *checkpoint weights* (selected dense BF16 matrices → blockwise FP8), used MTP=3 and a **custom built vLLM/kernel/mmap path**. Base RadixArk routed experts remained NVFP4; KV and recurrent state BF16. Not achieved by flags alone.
- [Marco's pinned fast recipe](https://github.com/pastoriomarco/NemoClaw-Thor/blob/main/serving/docs/QWEN38-FLASH-NEXT-FAST-THOR.md): uses RadixArk checkpoint at a pinned revision, a locally built `sm110-fast-v3` image, FP8-hybrid conversion, fused GDN, improved PLE access and draft-vocabulary changes. Exact options and measured results are author-controlled and may evolve. His 94/100 Tool-Eval claim tests **mock tool workflows**, not an end-to-end coding agent automatically maintaining a repo.
- [Ryan Johns, forum post #6](https://forums.developer.nvidia.com/t/qwen3-8-flash-next-at-46-7-tok-s-on-jetson-agx-thor/383269/6) and [technical report](https://github.com/Divhanthelion/Smithy-Windows/blob/main/reports/2026-09-24-unattended-runs-on-the-thor.md): *real agent integration* used prefix caching, explicit KV sizing, compiler/test gates and power monitoring. A repeated 16K-token prompt reported TTFT **9.05 s cold → ~1 s warm** with cached prompt tokens near 90%; they measured **28–46 decode tok/s** in selected workloads. An agent's success required external tooling and supervision, not just a model or `HTTP 200`.
- **Our Shockwave baseline:** 22.8 effective tokens/s on **one 253-token request** (`11.09232 s`), with peak rolling decode ~24 tok/s on a separate longer request. **Do not divide these by 46.7**: workload, image, weights, prefill, MTP, power, context and metric are different.

## Toggle matrix

| Feature | Shockwave v0.2.0 baseline | Alternate mode / how | Expected benefit | Risk, proof required | Priority |
|---|---|---|---|---|---|
| Prefix caching | Flag **unspecified**; effective default unknown | After checking `vllm serve --help`, use `--enable-prefix-caching` when appropriate | Reuse stable agent system/repository prefixes, faster repeat TTFT | Cache eviction, shared-token isolation, memory cost; measure cold/repeat `prefix` suite | **P0** |
| Reasoning effort | Per-request `low` in coding test; parser `qwen3` | `enable_thinking=false`, `reasoning_effort=low/medium/xhigh` | Reduce hidden token overhead on easy tasks | Quality regression on hard tasks; run same prompts / score outputs | **P0** |
| Memory budget | `--gpu-memory-utilization 0.90` | Evaluate `--kv-cache-memory-bytes` on a stopped *separate* run | More predictable KV reserve under page-cache pressure | Memory overcommit/OOM; not a blanket fix; see issue #2 | P1 |
| KV precision | `--kv-cache-dtype` **unspecified** (not proof of BF16) | Set `bfloat16` or test FP8 only if supported | KV memory saving / longer context when FP8 | Tool quality degradation reported by Marco; match accuracy | P2 |
| Context cap | `--max-model-len 212992` (advertised, not stress-tested) | 262144 only when KV fits | Longer repo / document context | Long prefill latency and memory; needle quality and concurrency | P1 |
| MTP speculative decode | **Off** (missing `/opt/qwen38-mtp-model/…` shard) | Custom compatible MTP checkpoint + `--speculative-config` | Lower decode latency, especially structured output | Different build, missing files, acceptance/correctness; issue #3 | P1 |
| Scheduler concurrency | `--max-num-seqs 1` | 2–3 **only after** memory/latency characterization | Aggregate throughput for parallel agent workers | Lower per-stream speed, KV pressure and isolation | P1 |
| Chunked prefill | Flag **unspecified** | `--enable-chunked-prefill`, optional `--max-num-batched-tokens` when supported | Smoother TTFT under mixed long inputs | Model/version compatibility; benchmark mixed workloads | P2 |
| Dense FP8 hybrid | Original `local-inference-lab` checkpoint | Pinned RadixArk + author's FP8 delta and custom image | Less loaded dense weight memory and faster output | **Different checkpoint/runtime**; audit licenses, hashes, conversion, quality | P2 |
| PLE mmap / fused GDN | NVIDIA Jetson AI Lab image | Custom build as described by Marco | Reduce memory I/O & kernel cost | Build complexity, correctness/thermal validation | P2 |
| Tool parser | `qwen3_xml` and auto tool choice | Test `qwen3_coder` if model/build supports it | Structured tool-call compatibility | Schema adherence, malformed tools, grammar bugs | P1 |
| Power / clocks | Not recorded | Capture `sudo nvpmodel -q`, clocks and oc3/thermal counters | Stable long runs and comparable measurements | MAXN may throttle or trigger over-current in some setups | **P0** |
| Vision | Not yet validated | Vision API smoke + scored image QA | On-device multimodal input | Latency, memory, image decoding accuracy | P2 |

**Feature state terminology:** `off` means we explicitly disabled it or omitted its enabling mechanism where no alternative is known (MTP here). `not specified` means **unknown effective state**—the engine may enable it by default. `measured` is reserved for verified results.

## Controlled experiment order (one change at a time)

1. **No restart**: `python3 -m thorbench doctor --container qwen38-flash-next`; benchmark `quick`, `reasoning`, and `prefix` with observed metadata. These capture *current* state, not an A/B change.
2. Record model/image digests, `nvpmodel`, frequencies, context and token usage; repeat each scenario after warmup. Record the distinct **cold/repeat prefix** pair in one run. Prefix results depend on actual caching and engine defaults.
3. **Separate maintenance window:** stop vLLM, adjust *one* launch flag with a new profile/commit, rerun same prompts. Don't run both 100GB-scale models simultaneously.
4. Only then compare FP8 hybrid/MTP stacks. Treat as different model-plus-runtime deployments, including model quality and tool-call correctness as gates.
5. **Agent-readiness** requires integration tests: code execution in a sandbox, tool-schema correctness, multiple turns, retries, cancellation, safe persistence, and long-run stability. A single `tok/s` number cannot establish this.

## References

- [Qwen3.8 forum benchmark](https://forums.developer.nvidia.com/t/qwen3-8-flash-next-at-46-7-tok-s-on-jetson-agx-thor/383269)
- [NemoClaw-Thor fast recipe](https://github.com/pastoriomarco/NemoClaw-Thor/blob/main/serving/docs/QWEN38-FLASH-NEXT-FAST-THOR.md)
- [Smithy agent field report](https://github.com/Divhanthelion/Smithy-Windows/blob/main/reports/2026-09-24-unattended-runs-on-the-thor.md)
- [vLLM v0.28.0 engine configuration](https://docs.vllm.ai/en/v0.28.0/configuration/engine_args/)
