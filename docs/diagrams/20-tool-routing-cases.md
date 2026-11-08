# Six first-decision tool-routing cases

```mermaid
flowchart TD
    S[One nonstreaming model response for each fixed case]
    S --> A[read_model_guide]
    S --> B[search_client]
    S --> C[run_cache_tests]
    S --> D[read_agent_protocol]
    S --> E[search_counter_deltas]
    S --> F[no_tool_needed]
    A --> A1[read_file with exact models/qwen3.8-flash-next/README.md path]
    B --> B1[search_repository query contains VLLMClient]
    C --> C1[run_tests with exact tests/test_cache_metrics.py target]
    D --> D1[read_file with exact docs/AGENT_BENCHMARK_PROTOCOL.md path]
    E --> E1[search_repository query contains counter_deltas]
    F --> F1[Zero tool calls and nonempty text]
    A1 --> G[Score declared name and the single allowed argument]
    B1 --> G
    C1 --> G
    D1 --> G
    E1 --> G
    F1 --> R[Save numeric verdict and timings only]
    G --> R
```

This is `python3 -m thorbench.tool_eval`. Exactly one structured call is required for each repository-action case. Search queries may include additional text as long as they contain the case-sensitive expected identifier; read/test paths must match exactly. The argument object must contain only the declared expected key with a string value.

**No selected tool executes.** Selecting `run_tests` does not run `tests/test_cache_metrics.py`; even the paths in the task are decision fixtures, not permission for the model to touch the checkout. Malformed/multiple calls, wrong function/arguments and request errors count as failures. A textual function-call imitation does not substitute for structured `tool_calls`.

`tool_choice=auto` preserves the no-tool control. That control checks zero calls and nonempty text, not factual accuracy, one-sentence compliance or the fixed/seeded simulator's character caps. This scorer evaluates the response's tool structure; it does not use the ordinary `bench` suites' `finish_reason=stop` completion gate.

Historical 30/30 runs on A and B2 repeat six public cases five times each. They do not establish multi-step task completion, actual test execution or 30 unrelated fixes. The full-request timings include any internal reasoning, and this nonstreaming suite has no streamed TTFT/TTFC measurement.

See the [decision flow](10-agent-tool-evaluation.md), [routing protocol](../AGENT_TOOL_EVAL.md) and [suite guide](../BENCHMARK_VISUAL_GUIDE.md#first-decision-tool-routing).
