# Comparing Shockwave with public Jetson Thor benchmark reports

**This is a reference catalog, not a leaderboard.** References were reviewed November 7, 2026. Their numerical claims are attributed to the respective authors, not independently reproduced by this project.

## Model identity

| Property | Shockwave baseline |
|---|---|
| Served model | `Qwen3.8-Flash-Next` |
| Checkpoint | [`local-inference-lab/Qwen3.8-Flash-Next-NVFP4`](https://huggingface.co/local-inference-lab/Qwen3.8-Flash-Next-NVFP4) |
| Device | NVIDIA Jetson AGX Thor 128 GB unified memory |
| Runtime | `ghcr.io/nvidia-ai-iot/vllm:qwen3.8-next-jetson-thor`, image digest in [baseline](../models/qwen3.8-flash-next/baseline.md) |
| Quantization | NVFP4 / modelopt mixed |
| MTP | Off (missing bundled draft-model shard in first test) |
| Single-stream concurrency | `--max-num-seqs 1` |
| Max configured context | 212,992 tokens; NOT proven at full length |
| JetPack / CUDA | 7.2.1 / 13.2 |

## Public references

| Source | Public claim | Environment and caveat |
|---|---:|---|
| [NVIDIA Jetson AI Lab](https://www.jetson-ai-lab.com/models/qwen3-8-flash-next/) | N/A | Official Thor recipe/model reference, no directly comparable performance metric |
| [Leibniz-HBI Thor vLLM recipe](https://github.com/Leibniz-HBI/Qwen3.8-Flash-Next-Jetson-Thor-vLLM) | ~23–24 decode tok/s | Reported with RadixArk NVFP4, pinned custom vLLM, PLE mmap, Marlin, MTP=1; prompt/clock dependent |
| [NVIDIA forum FP8 hybrid](https://forums.developer.nvidia.com/t/qwen3-8-flash-next-at-46-7-tok-s-on-jetson-agx-thor/383269) | 46.7 output tok/s weighted mean | Author's `sgbench` C1 Code/JSON/LongCode weighted output rate, custom FP8-hybrid weights and MTP=3; includes prefill and TTFT |
| [Smithy agent field report](https://forums.developer.nvidia.com/t/qwen3-8-flash-next-at-46-7-tok-s-on-jetson-agx-thor/383269/6) | Repeated 16K-token prompt: TTFT 9.05 s cold → 1.0 s warm | Different custom stack; prefix caching, approximately 90% cache hits, and external coding/test gates; **not a throughput comparison** |

**Do not divide Shockwave's ~22.8 effective tok/s by 46.7 or declare a performance gap.** The checkpoints, prompts, output lengths, reasoning settings, runtimes, decoding optimizations, power profiles, and measurement formulas are not matched. Published ranges must remain labeled with their methodology.

## Reproducible benchmark protocol

1. Record exact model repository *and revision*, CUDA, JetPack, container *digest*, power mode (`sudo nvpmodel -q`), clocks, inference settings, and quantization. `doctor` does not automatically capture all of these.
2. Use the **same prompt**, input length, temperature, `max_tokens`, thinking mode, concurrency, quantization, MTP policy and cache policy across controlled comparisons.
3. Use warmup requests and record each successful sample, with median and number of repetitions; report failures rather than deleting them.
4. Prefer streamed client-side TTFT, TTFC and TPOT as described in [vLLM's definitions](https://docs.vllm.ai/en/latest/benchmarking/cli/). Decode throughput here is an estimate using server-reported token counts, not vLLM's own standardized native benchmark.
5. When comparing an external result, repeat its protocol on the same model/hardware or state clearly that the values are **illustrative, not directly comparable**.

For a lightweight local view, run `python3 -m thorbench references` and `python3 -m thorbench compare --run results/<folder>`.

## Publishing results

Copy **reviewed, anonymized** numeric summaries into a pull request or a new Markdown document. Do not add `results/` raw files by force, and never upload private prompts or machine identifiers. See [SECURITY.md](../SECURITY.md).

## Standardized quality evaluation (future work)

The v0.2.0 suite tests infrastructure and request timing, **not model accuracy**. The next milestone is implementing pinned, standardized [EvalPlus HumanEval+](https://github.com/evalplus/evalplus), [IFEval](https://github.com/google-research/google-research/tree/master/instruction_following_eval), and [MMLU-Pro](https://github.com/TIGER-AI-Lab/MMLU-Pro). These must be scored using each benchmark's reference protocol and dataset version; see [the tracking issue draft](issues/standardized-quality-evaluations.md).

## Agent-field follow-up and vLLM feature flags (2026-11-07 review)

The [September 30 Smithy post (#6)](https://forums.developer.nvidia.com/t/qwen3-8-flash-next-at-46-7-tok-s-on-jetson-agx-thor/383269/6) is **not a repeat of Marco's 46.7 tok/s `sgbench` result**. It describes an actual coding-agent runner behind a related custom serving build: fixed-KV memory, prefix reuse, tool/test gates and thermal/power stability. See the [feature matrix](OPTIMIZATION_MATRIX.md) for reported flags and citations. We still have no protocol-matched A/B on Shockwave. Do not represent their mock tool-eval scores or overnight successful tasks as production-service reliability certification.
