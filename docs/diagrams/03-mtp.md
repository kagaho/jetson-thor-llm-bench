# 03 — MTP speculative decoding

```mermaid
flowchart TD
    A[Ready to generate next tokens] --> B{MTP enabled with compatible draft weights?}
    B -- No --> C[Target model generates token by token]
    B -- Yes --> D[Draft model proposes up to N tokens]
    D --> E[Target verifies candidates]
    E --> F[Accept valid prefix, discard mismatches]
    C --> G[Output tokens]
    F --> G
    G --> H[Measure decode tok/s, accuracy, draft acceptance]
```

| State | Config | Result / gate |
|---|---|---|
| Baseline | **No `--speculative-config`** | Stable inference (~23–25 tok/s observed intervals) |
| Initial attempted on | `--speculative-config '{"method":"mtp","num_speculative_tokens":3,"model":"/opt/qwen38-mtp-model"}'` | **FAILED** missing `model-00001-of-00034.safetensors` |
| Community custom stack | Embedded/compatible MTP=3 on pinned RadixArk checkpoint | Reported higher throughput; **not plug-and-play** on our image |

Do not add that failed draft path back to `serve.sh`. Track [issue #3](https://github.com/kagaho/jetson-thor-llm-bench/issues/3); only enable after checkpoint integrity, parser/grammar, tool-call quality, deterministic A/B and long-run testing.
