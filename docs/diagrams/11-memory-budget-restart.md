# Shockwave: observed A→B→B2 experiment

This diagram now represents the **observed sequence**, not an unexecuted plan. Cache values and memory numbers are from operator-provided logs; long-term stability is unverified.

```mermaid
flowchart TD
    A[Working baseline A: auto KV 5.26 GiB, context 212992, GPU fraction 0.90] --> B[Record 30/30 tool routing and prefix tests]
    B --> C[Manual B: KV 4 GiB, context 131072, GPU fraction 0.90]
    C --> D{Startup check passed?}
    D -->|No: free 109.94 GiB below 110.52 GiB| E[Stop failed candidate and retain logs]
    E --> F[B2: KV 4 GiB, context 131072, GPU fraction 0.88]
    F --> G{Startup and health passed?}
    G -->|Yes| H[30/30 tool routing; 5 prefix + 5 agent pairs; 8K/32K retrieval passes]
    H --> I[MemAvailable 2.9 GiB post tests; 1.1 GiB previous snapshot]
    I --> J{Sustained stability and matched workloads proven?}
    J -->|Not yet| K[Retain B2 as experimental; preserve baseline rollback]
    J -->|After future tests| L[Consider a recommended low-memory profile]
    G -->|No| M[Rollback using recorded baseline A recipe]
```

**Interpretation:** a manual KV-cache size skipped cache profiling **after** startup, but the observed pinned vLLM build still evaluated the utilization-based initial free-memory gate. Changes to context, KV cache, and startup threshold mean B2 is not a single-variable A/B test.

See [runbook](../MEMORY_AB_EXPERIMENT.md) and [measurements](../benchmarks/2026-11-08-shockwave-b2-vs-a.md).
