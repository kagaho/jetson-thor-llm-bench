# Serving feature workflows — Mermaid source

These diagrams render directly on GitHub. They describe **design and benchmark hypotheses**, not claims that every engine feature is currently enabled on Shockwave. Prefer reading [the optimization matrix](../OPTIMIZATION_MATRIX.md) for exact on/off/default states.

| Diagram | Why it matters | Baseline state |
|---|---|---|
| [01 Request and agent lifecycle](01-request-and-agent-lifecycle.md) | Inference != validated agent outcome | API inference passes, agent evaluation pending |
| [02 Prefix cache toggle](02-prefix-cache.md) | Repeated long prompts vs cache misses | Not explicitly set; measure it |
| [03 MTP toggle](03-mtp.md) | Draft/verify speedup vs missing draft shard | Off |
| [04 Memory and context](04-memory-and-context.md) | Shared RAM, KV budget and context gate | 0.90; 212,992 tokens advertised |
| [05 Optimization rollout](05-optimization-rollout.md) | Controlled A/B with quality and stability gates | Planned |
| [06 Tool calling and reasoning](06-tool-calling-and-reasoning.md) | API output vs agent correctness | Qwen3 parser + qwen3_xml |
| [07 Hybrid weights and throughput](07-hybrid-weights-and-throughput.md) | Quantization/engine and concurrency differences | Baseline NVFP4, one slot |
| [08 Prefix-cache evidence](08-prefix-cache-evidence.md) | Separate measured latency from actual KV hit counters | Historical hits unverified; new probes available |
| [09 Agent shared-context sequence](09-agent-prefix-sequence.md) | Stable repository context, changing tasks | Synthetic responsiveness, not full agent correctness |

Each page also includes a state table, exact known flags, impact, safeguards, and measurement plan.
