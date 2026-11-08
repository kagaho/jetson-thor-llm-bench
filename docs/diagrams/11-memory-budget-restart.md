# Controlled memory restart — explicit KV budgeting

```mermaid
flowchart TD
    A[Existing working Docker container: do not stop yet] --> B[Capture running flags, logs, memory, benchmarks]
    B --> C{Baseline recorded and rollback verified?}
    C -->|No| A
    C -->|Yes| D[Stop original Docker container]
    D --> E[Restart unchanged baseline A: GPU utilization 0.90]
    E --> F{A passes health, context, inference?}
    F -->|No| G[Investigate baseline startup; no tuning]
    F -->|Yes| H[Record exact vLLM version and available KV budget]
    H --> I[Stop A and start candidate B: explicit measured KV cache bytes]
    I --> J{B starts and required context fits?}
    J -->|No| K[Rollback to documented baseline A]
    J -->|Yes| L[Matched quick/prefix/agent/tool-routing tests]
    L --> M{Improved reliability without regressions?}
    M -->|No| K
    M -->|Yes| N[Document validated optional candidate profile]
```

**Important:** `--kv-cache-memory-bytes` does not increase physical RAM; where supported it changes how vLLM derives cache size and overrides `--gpu-memory-utilization` for that calculation. Not every version of the specialized NVIDIA Jetson container necessarily supports the same options as upstream vLLM. This flow deliberately does not provide an arbitrary cache-size value.

See [experiment runbook](../MEMORY_AB_EXPERIMENT.md).
