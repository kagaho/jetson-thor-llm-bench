# Serving feature workflows — Mermaid source

These diagrams render directly on GitHub. They describe serving designs, benchmark workflows and evidence limits. For the latest dated serving configuration, use the [profile reference](../SERVING_PROFILES.md); the [optimization matrix](../OPTIMIZATION_MATRIX.md) retains historical baseline states and candidate experiments.

| Diagram | Why it matters | Baseline state |
|---|---|---|
| [01 Request and agent lifecycle](01-request-and-agent-lifecycle.md) | Inference != validated agent outcome | API inference passes, agent evaluation pending |
| [02 Prefix cache toggle](02-prefix-cache.md) | Repeated long prompts vs cache misses | Not explicitly set; measure it |
| [03 MTP toggle](03-mtp.md) | Draft/verify speedup vs missing draft shard | Off |
| [04 Memory and context](04-memory-and-context.md) | Shared RAM, KV budget and context gate | 0.90; 212,992 tokens advertised |
| [05 Optimization rollout](05-optimization-rollout.md) | Controlled A/B with quality and stability gates | Planned |
| [06 Tool calling and reasoning](06-tool-calling-and-reasoning.md) | API output vs agent correctness | Qwen3 parser + qwen3_xml |
| [07 Hybrid weights and throughput](07-hybrid-weights-and-throughput.md) | Quantization/engine and concurrency differences | Baseline NVFP4, one slot |
| [08 Prefix-cache evidence](08-prefix-cache-evidence.md) | Separate measured latency from actual KV hit counters | Five-pair tests report server-wide hits; per-request attribution conditional |
| [09 Agent shared-context sequence](09-agent-prefix-sequence.md) | Stable repository context, changing tasks | Synthetic responsiveness, not full agent correctness |
| [10 Tool-routing evaluation](10-agent-tool-evaluation.md) | Real structured tool decision, zero execution | 30/30 tested on A and B2 |
| [11 Memory/KV A/B restart](11-memory-budget-restart.md) | Preserve baseline and rollback before changing cache budget | A→B failure→B2 startup and initial tests recorded |
| [12 Multi-turn simulated agent](12-multi-turn-simulator.md) | Multi-step tool outcomes with bounded recovery and strict host-safety boundary | v0.6.0 observed 25/25 fixed synthetic episodes |
| [13 Seeded evaluation workflow](13-generalization-seeded-fixtures.md) | Oracle boundary, bounded model/tool loop, failure handling and private reports | Package 0.7.0 includes scorer 0.7.3; recorded 25/30 run used scorer 0.7.2 |
| [14 Seeded test families](14-generalization-test-families.md) | Required observations, fixture state and final-answer gates for all six families | Five variants per family in the recorded run; no-tool 0/5 for verbosity |

The [results guide](../AGENT_GENERALIZATION_RESULTS.md) includes outcome and latency graphs with scorer/seed attribution. Individual diagrams explain their relevant state, evidence requirements and measurement limits.
