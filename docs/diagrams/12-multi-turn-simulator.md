# Multi-turn agent evaluation: safe simulator, not shell execution

```mermaid
flowchart TD
    A[Select one of 5 public synthetic tasks] --> B[Fresh in-memory repository fixture]
    B --> C[Send tools + messages to local vLLM]
    C --> D{Structured tool calls returned?}
    D -->|Yes| E{Valid shape and budget?}
    E -->|No| F[Fail with bounded reason code]
    E -->|Yes| G[Allowlisted simulator dispatcher]
    G --> H[Return JSON tool outcome: PASS / FAIL / missing / temporary]
    H --> I[Append assistant and tool messages with matching tool_call_id]
    I --> J{Turns and tool-call limits reached?}
    J -->|Yes| F
    J -->|No| C
    D -->|No| K{Grounded final answer AND required state trace?}
    K -->|Yes| L[PASS synthetic task]
    K -->|No| F
    L --> M[Save numeric metrics / event-category trace only]
    F --> M
```

**Safety boundary:** The dispatcher operates on a Python dictionary of synthetic fixtures. There is no simulated-to-real filesystem bridge. Calls named `run_tests` and `replace_text` never launch a process or write to source files. Tests validate rejecting arbitrary tool names, paths and edited content.

**Measurement boundary:** Total task latency covers all model requests; completion-token count sums all generated tokens across turns, and prompt-token count includes repeated conversation history. An error recovery is counted only when the simulator recorded both an error and a subsequent successful observation. A final declaration without the required tool evidence is a failure.
