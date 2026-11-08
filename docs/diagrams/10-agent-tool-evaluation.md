# First tool decision: safe model behavior probe

```mermaid
flowchart TD
    A[Six synthetic public tasks] --> B[Qwen /v1/chat/completions]
    B --> C[tools declared, tool_choice auto]
    C --> D{Structured tool_calls?}
    D -->|One call| E{Tool name and arguments match fixture?}
    D -->|No call| F{No-tool control and text response?}
    D -->|Malformed/multiple| G[Fail: schema or cardinality]
    E -->|Yes| H[Pass: routing decision]
    E -->|No| I[Fail: wrong route/argument]
    F -->|Yes| H
    F -->|No| J[Fail: missing required tool]
    H --> K[Numeric-only private results]
    G --> K
    I --> K
    J --> K
    K --> L[Later: simulated tools then sandboxed code tasks]
```

The three declared tools (`read_file`, `search_repository`, `run_tests`) **are not executed**. The suite tests structured tool-call selection, not end-to-end problem solving or real coding correctness. Unlike the existing latency-oriented `agent` suite, this evaluates the model's decision at an actual tool interface.

See [protocol](../AGENT_TOOL_EVAL.md).
