# Seeded generalization: test families and evidence gates

```mermaid
flowchart TD
    S[Base seed plus family and repetition] --> G[Deterministic fixture and local hidden oracle]
    G --> A[Symbol origin]
    G --> B[Regression repair]
    G --> C[Moved runbook]
    G --> D[Transient read]
    G --> E[Environment disambiguation]
    G --> F[No-tool explanation]
    A --> A1[Discover active path then read it]
    A1 --> A2[Final active path and correct numeric value]
    B --> B1[Read active source and observe simulated FAIL]
    B1 --> B2[Allowlisted in-memory edit after both observations]
    B2 --> B3[Observe simulated PASS and report outcome]
    C --> C1[List or search discovers active runbook then read it]
    C1 --> C2[Final active path, HTTP 503 and current retry value]
    D --> D1[One or two injected retryable errors then successful read]
    D1 --> D2[Final exact incident identifier]
    E --> E1[Read both staging and production in either order]
    E1 --> E2[Final production path, environment and numeric value]
    F --> F1[Zero repository tool calls]
    F1 --> F2[TTFT versus task latency explained in at most 700 characters]
```

These gates describe the released **scorer 0.7.3 / protocol 1**. Numeric matching uses exact token values, but a correct number mentioned incidentally can still fool the final-answer heuristic. The test families are public templates with generated variants, not independently held-out coding tasks.

The model receives the task and tool observations; the grading oracle remains local. `run_tests` and `replace_text` inspect or mutate fixture dictionaries only. For the moved runbook, opening a link already identified as broken is optional; discovering and reading the active file is required.

Negative controls cover missing discovery, discovery after the last read, archive-only evidence, missing active path or facts, wrong numeric values, unsupported test-pass claims, unnecessary tools and excessive verbosity. A correct final claim alone cannot replace the required observations.

See the [evaluation workflow](13-generalization-seeded-fixtures.md), [scoring contract](../AGENT_GENERALIZATION_EVAL.md), and [recorded outcome and latency charts](../AGENT_GENERALIZATION_RESULTS.md).
