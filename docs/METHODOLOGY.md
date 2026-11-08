# Benchmark methodology

For an illustrated explanation of every suite, its counting rules and exact outcome gates, start with the [benchmark visual guide](BENCHMARK_VISUAL_GUIDE.md). The [streaming timeline](diagrams/15-streaming-and-reasoning.md), [context workflow](diagrams/16-context-retrieval.md), [vision workflow](diagrams/17-vision-smoke.md) and [report interpretation](diagrams/21-results-and-evidence.md) show how observations become results.

## What we measure

- `elapsed_s`: monotonic wall-clock duration for the whole HTTP request, from sending bytes until the final response.
- `ttft_s`: time to first **generated** SSE delta containing either `reasoning` (or `reasoning_content`) or visible `content`. This includes initial network/prefill wait.
- `ttfc_s`: time to first **visible content** SSE delta, important for reasoning models where hidden thinking may precede the answer.
- `effective_tokens_s`: all completion tokens (including reasoning) divided by end-to-end elapsed time.
- `decode_tokens_s`: `(completion_tokens - 1) / (elapsed_s - ttft_s)`, estimated steady decoding from the first token; includes reasoning tokens and any stream overhead.
- `prompt_tokens`, `completion_tokens`, `reasoning_tokens`: as reported by vLLM's OpenAI-compatible usage object. If streaming usage isn't supported, metrics that require counts are `n/a`, **not** fabricated.
- `finish_reason`: `stop` is treated as a completed response; `length` is incomplete even if text was returned.

## Suites

- `quick`: 3 repeats + 1 warmup by default, same coding request and low reasoning effort.
- `reasoning`: identical prompt with `off`, `low`, and `medium` thinking. Off requests the Qwen chat-template switch; support depends on the deployed model/template.
- `context`: synthetic needle-in-haystack prompts; tests whether the model returns `SW-THOR-7391-ALPHA`. Context target sizes use a **4-character-per-token heuristic**, so the actual length is `usage.prompt_tokens`, **not** the scenario label. Defaults to ~1K, ~4K, ~8K target sizes. Large tests require an explicit opt-in; the script stops after the first failing length.
- `vision`: supplies a user-chosen local image as a base64 data URI. This is only an API smoke test, not a visual accuracy benchmark.

## Constraints

- Requests are **sequential**; no concurrency test is included.
- The model context length displayed by `/v1/models` is a configured upper bound, **not** proof that long contexts work.
- Warmups aren't counted; cold-start latency is out of scope.
- Prompt/token throughput shown by the vLLM server is averaged over reporting windows and isn't identical to per-request generation rate.
- Compare results at fixed power mode, clocks, thermal state, quantization, model revision, vLLM image digest and benchmark suite.
- Concurrent loads or background downloads can confound results.
- Raw prompts/outputs/images and personally identifying hardware details aren't saved.

## Memory safety

Thor has unified RAM. Avoid jumping directly to ~200K context with a ~100 GiB resident model. Start small, review `jtop`/`tegrastats`, then escalate deliberately. Do not run other models in parallel when testing near memory limits.

## Aggregation and failure populations

In `thorbench bench`, every recorded failure stays in the scenario pass/total count, while per-scenario timing medians use successful rows. Paired TTFT ratios require both requests to complete and usable timing values; unsuccessful pairs still contribute their request failures to scenario totals. Warmups are excluded from all recorded counts.

The separate first-decision and multi-turn tool evaluators include available numeric timings from failed cases/episodes in their medians. The seeded evaluator also reports interpolated p90. Consequently, compare timing populations as well as suite and protocol identities. Multi-turn prompt usage includes repeated conversation history, not unique context tokens. See the [report workflow](diagrams/21-results-and-evidence.md).

## Repeated prompts and cache evidence (v0.4.0 protocol)

For first/repeat or synthetic agent-like probes, `--runs` counts **pairs** and `--warmup 0` is required. Each pair uses a fresh random marker, and requests run sequentially. The benchmark may scrape server-wide `vllm:prefix_cache_hits_total` and `vllm:prefix_cache_queries_total` around each request. If the server does not expose the counters, record the status as *unavailable*, not zero. Even with a positive delta, other traffic to the engine prevents per-request attribution. A latency improvement alone is not a confirmed prefix-cache hit.

See [reproducibility protocol](AGENT_BENCHMARK_PROTOCOL.md) and the [November 7 Shockwave observations](benchmarks/2026-11-07-shockwave-prefix.md).
