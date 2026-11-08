# Benchmark and serving workflows — Mermaid source

These diagrams render directly on GitHub. They describe serving designs, benchmark workflows and evidence limits. For the latest dated serving configuration, use the [profile reference](../SERVING_PROFILES.md); the [optimization matrix](../OPTIMIZATION_MATRIX.md) retains historical baseline states and candidate experiments.

**Start with the [complete benchmark visual guide](../BENCHMARK_VISUAL_GUIDE.md)** for a map of every suite, its question, exact PASS gate and counting unit. Diagrams 01–07 retain original serving-design assumptions; the test-specific pages below explain the implemented workflows and current evidence limits.

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
| [15 Streaming and reasoning](15-streaming-and-reasoning.md) | TTFT versus TTFC, excluded warmups and off/low/medium comparisons | Timing and completion checks; coding answers are not executed |
| [16 Context retrieval](16-context-retrieval.md) | Approximate input construction, actual usage, marker gate and stopping rule | Limited retrieval evidence; configured maximum remains unvalidated |
| [17 Vision smoke test](17-vision-smoke.md) | Selected image, request payload, completion gate and image/report boundary | API smoke test; no semantic image-accuracy score |
| [18 Offline tests and CI](18-offline-test-workflow.md) | Real developer checks versus simulated model-selected tools | 99 tests at the documented baseline; no GPU/model inference required |
| [19 Five fixed agent tasks](19-fixed-agent-test-cases.md) | Exact search, repair and recovery evidence for each fixed fixture | Historical 25/25 repeats five tasks; no real patch/test execution |
| [20 Six tool-routing cases](20-tool-routing-cases.md) | All expected tool decisions, path/identifier rules and no-tool gate | Six public first-decision cases; selected tools never execute |
| [21 Results and evidence](21-results-and-evidence.md) | Report files, denominators, timing populations and provenance | Preserve failures, missing data and historical scorer attribution |

The [results guide](../AGENT_GENERALIZATION_RESULTS.md) includes outcome and latency graphs with scorer/seed attribution. Individual diagrams explain their relevant state, evidence requirements and measurement limits.
