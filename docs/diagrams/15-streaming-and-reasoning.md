# Streaming timing and reasoning-mode tests

## One streamed request

```mermaid
sequenceDiagram
    autonumber
    participant B as Benchmark client
    participant S as Existing vLLM server
    B->>B: Start monotonic request timer
    B->>S: Send public prompt with stream enabled
    Note over S: Queueing and prompt processing occur before first generation
    opt Reasoning appears before visible content
        S-->>B: First nonempty reasoning delta
        B->>B: Record TTFT at first generated delta
    end
    S-->>B: First nonempty visible content delta
    B->>B: Record TTFC and TTFT if still unset
    S-->>B: Remaining deltas, finish reason and available usage
    B->>B: End request timer and evaluate completion
    B->>B: Persist timings and counts without prompt or answer
```

TTFT is elapsed time to the first nonempty generated SSE delta, including reasoning if present. TTFC is elapsed time to the first visible content delta. They coincide when the first generated delta is visible text. Neither measures model startup; the server is already running. Streaming chunks can contain multiple tokens, so these are observed delta timings.

| Metric | Calculation or observation |
|---|---|
| Request latency | Time from sending the request until its response ends |
| Effective throughput | Reported completion tokens divided by request latency |
| Estimated decode throughput | `(completion_tokens - 1) / (elapsed_s - ttft_s)` when the inputs are available and valid |
| Reasoning tokens | Server-reported usage; included in completion accounting when reported that way |

Missing token usage or timing produces `n/a`, not an invented zero. The quick suite checks `finish_reason=stop`; it does not execute the returned coding solution or check its correctness. The default is one excluded warmup plus three recorded quick requests.

## Reasoning-mode workflow

```mermaid
flowchart TD
    P[Same public coding prompt and temperature] --> O[Request off with enable_thinking false]
    P --> L[Request reasoning_effort low]
    P --> M[Request reasoning_effort medium]
    O --> W[For each mode: run excluded warmups]
    L --> W
    M --> W
    W --> R[Run N measured streamed requests for that mode]
    R --> C[Check finish reason and retain failed rows]
    C --> U[Compare TTFT, TTFC, latency and reported token lengths]
    U --> V[Keep quality and effective thinking behavior as separate questions]
```

The CLI runs modes in the order off, low, medium; it is not a randomized experiment. Each mode uses the same output budget, which differs from the quick suite's budget. With `--runs 2 --warmup 1`, there are six recorded requests and three excluded warmups. Server/template support determines whether the requested off switch is honored; the request flag alone does not prove reasoning was disabled.

Longer output or hidden reasoning can explain latency differences. The harness does not grade the coding answers, so this test cannot rank reasoning quality. API or truncation failures remain in the pass denominator. Per-scenario latency medians in the `bench` report use successful rows only.

See the [complete suite guide](../BENCHMARK_VISUAL_GUIDE.md#quick-and-reasoning), [methodology](../METHODOLOGY.md) and [report interpretation](21-results-and-evidence.md).
