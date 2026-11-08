# Seed-varying synthetic agent benchmark — evaluation workflow

```mermaid
flowchart TD
    P[Offline checks and healthy existing server] --> A[Record seed, scorer, protocol and source fingerprint]
    A --> B[Derive family/repetition SHA-256 sub-seed]
    B --> C[Generate in-memory files, decoys, fault conditions and private oracle]
    C --> T[Send only task, tool schemas and permitted observations]
    T --> D[Ask local model for next action with tool_choice auto]
    C -. Hidden oracle stays local .-> I
    D --> E{Structured tool calls?}
    E -->|Yes| F[Validate call envelope and tool-call budget]
    F -->|Valid| G[Validate schema and interpret tool in memory ONLY]
    G --> H[Return typed synthetic tool observation]
    H --> M[Append assistant and tool messages with matching call IDs]
    M --> L{Model turns still available?}
    L -->|Yes| D
    L -->|No| X[FAIL with bounded reason code]
    F -->|Invalid envelope or excessive calls| X
    E -->|Final answer| I[Grade chronological evidence, fixture state and final facts]
    I --> O[PASS or FAIL with scorer-attributed reason]
    D -->|API or transport error| X
    O --> J[Save only numeric metrics and sanitized event categories]
    X --> J
    J --> K[Aggregate every episode by family and repetition]
    K --> R[Review failures and preserve historical scores]
    K --> N[Nonzero suite exit when any episode fails]
```

**Safety invariant:** no model-generated code, shell commands, real tests, host file edits, or external tool calls. Tool names are allowlisted and their effects are simulated. The sole external dependency is the already-running local model API.

**Protocol:** defaults are 10 model turns, 16 tool calls, `tool_choice=auto` and nonstreaming requests. Validly enveloped calls with invalid tool names/arguments receive typed simulator errors and consume budget. Malformed envelopes, exceeding the call budget or exhausting model turns fail the episode; a final answer can still follow exactly 16 calls when model turns remain. The grading oracle is never included in a model request. Raw prompts, answers, arguments and fixture contents are excluded from reports; request errors remain in the denominator.

**Versions:** the released package v0.7.0 contains scorer 0.7.3 / protocol 1. The recorded 25/30 full run used scorer 0.7.2. New grader corrections require demonstrated positive/negative regressions and a new scorer revision; changes to model prompts require a new protocol version. Neither change rewrites older results.

**Evidence limits:** the generator is public and varies task *instances* but not task-family semantics. A high score is not evidence of correct handling of independent unseen coding issues. The next stage must use separately withheld task families and isolated real execution only after security review.

See the [test-family diagram](14-generalization-test-families.md), [result charts](../AGENT_GENERALIZATION_RESULTS.md) and [scoring contract](../AGENT_GENERALIZATION_EVAL.md).
