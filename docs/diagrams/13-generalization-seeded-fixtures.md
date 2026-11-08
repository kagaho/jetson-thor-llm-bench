# Seed-varying synthetic agent benchmark — v0.7.0 candidate

```mermaid
flowchart TD
    A[Record base seed and test configuration] --> B[Derive family/repetition SHA-256 sub-seed]
    B --> C[Generate in-memory files, decoys, fault conditions and private oracle]
    C --> D[Ask model to complete one synthetic request]
    D --> E{Structured tool calls?}
    E -->|Yes| F[Validate tool ID, schema and bounded arguments]
    F --> G[Interpret tool in in-memory dictionary ONLY]
    G --> H[Return typed synthetic tool observation]
    H --> D
    E -->|Final answer| I[Score chronological events, fixture state and final facts]
    I --> J[Store sanitized metrics and event categories]
    J --> K[Aggregate by family, seed and repetition]
    F -->|Invalid or limit| J
```

**Safety invariant:** no model-generated code, shell commands, real tests, host file edits, or external tool calls. Tool names are allowlisted and their effects are simulated. The sole external dependency is the already-running local model API.

**Evidence limits:** the generator is public and varies task *instances* but not task-family semantics. A high score is not evidence of correct handling of independent unseen coding issues. The next stage must use separately withheld task families and isolated real execution only after security review.
