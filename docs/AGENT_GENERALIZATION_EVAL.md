# v0.7.0 candidate — seeded simulated-agent generalization

**Purpose:** test whether a model can complete familiar *types* of tasks when exact synthetic paths, identifiers, values, and error conditions change. v0.6.0's 25/25 was five repetitions each of five **fixed** fixtures. This suite generates six families with **a distinct fixture for each seed and repetition**. It does not claim hidden-template generalization or real-world coding reliability.

## What changes between episodes?

The deterministic fixture generator derives a stable SHA-256 sub-seed from `base_seed`, task-family name, and repetition index. The base seed is random by default (63-bit) and printed and recorded for reproduction of **the generated fixtures**; stochastic model outputs and timing may still differ between reruns. There is no nondeterministic dependence on Python's randomized `hash()`.

- Active production files, services, setting names, and numerical values vary.
- Example, archived, and staging decoys create ambiguity that cannot be solved by grabbing the first search result.
- Simulated test failure requires discovering and editing the correct active assignment, then observing test PASS.
- Moved runbook includes a missing old link and a conflicting retired policy.
- Transient read can fail once or twice before succeeding.
- A no-tool negative control tests avoidance of unnecessary repository access.

| Family | Required event evidence | Final answer gate |
|---|---|---|
| `symbol_origin` | Search or list discovers target; read active policy | Exact active path and integer |
| `repair_regression` | Inspect active source and observe test FAIL before allowlisted edit; then test PASS | Acknowledge pass/fix |
| `moved_runbook` | Discover active doc via list or search → read it (no need to open known-broken old link) | Active path, HTTP 503, and current retry limit |
| `transient_read` | One or two retryable read failures → successful read | Exact incident identifier |
| `environment_disambiguation` | Read both staging and production | Production path, value, and environment |
| `no_tool_needed` | No tools | Correct TTFT versus end-to-end description in ≤700 characters; otherwise `excessive_verbosity` |

## v0.7.1 scoring correction (from the original v0.7 branch)

The original runbook scorer wrongly required attempting the explicitly broken old URL and searching before accepting the active document. The corrected scorer accepts **either listing or searching** that discovers the active path, followed by a successful read and an exact answer. It still rejects archived-only evidence, unverified answers, and incorrect retry values. No tool-simulator, model-server, or fixture changes were made.

The no-tool control still requires a brief answer (≤700 characters). Responses that otherwise satisfy the no-tool and terminology requirements but exceed that cap now receive `excessive_verbosity` rather than the generic `incomplete_or_ungrounded`. Historical v0.7.0 results remain unchanged; distinguish new v0.7.1 scoring from prior scores in reports.

## Safety and request protocol

The model receives OpenAI-compatible nonstreaming `chat/completions` requests with `tool_choice=auto` and `reasoning_effort=low`. Between turns the harness replays the assistant tool calls and synthetic tool response messages with matching `tool_call_id`. The only network traffic is to the configured model API.

**All five tools are interpreted in Python dictionaries**: `list_files`, `search_repository`, `read_file`, `run_tests`, `replace_text`. The last two do **not** execute real tests or edits; they inspect/mutate allowlisted in-memory fixture data. No model-generated Python, shell, external file access, or system process is executed, even for malicious arguments. A tool-call budget (default 16), turn cap (default 10), argument-size checks and exact schemas bound each episode.

The scoring oracle is created locally with the fixture and **is not sent to the model**, although actual tool observations are. Paths/values remain synthetic and harmless. The grading checks event ordering and short final-answer string requirements; this is a controlled heuristic benchmark, **not** semantic grading of unconstrained code or natural language.

## Reproduce on Shockwave B2 without restarting the container

```bash
cd ~/Documents/jetson-thor-llm-bench
python3 -m unittest discover -s tests -v
curl -fsS http://127.0.0.1:8000/health && echo Healthy
python3 -m thorbench.generalize_eval --runs 1
cat "$(ls -td results/*-agent-generalization | head -1)/summary.md"
```

Six cases per repetition. Begin with `--runs 1` and examine failures rather than changing expected answers. After the smoke run, use `--runs 5` for **30 seed-varying episodes** (not 30 unrelated coding issues). Reproduce exactly with `--seed <number>`; the chosen seed and run configuration live in `results/<timestamp>-agent-generalization/metadata.json` (Git-ignored).

Reports include completion/pass counts, median and p90 task latency, cumulative input/output token counts over **all** turns, tool counts, recovery counts and sanitized tool outcome categories. Token totals include repeated conversation history and are not a unique-context measurement. Neither model messages, tool arguments, oracle answers nor synthetic file contents are persisted. Failures count toward the denominator and exit nonzero; record failure types rather than hiding them.

## Interpretation and release gates

1. Compare with v0.6.0 **only as different benchmark protocols**; a lower score is not a proven regression in the underlying model.
2. Report run count, seed, task family distribution, failure categories, token usage, and latency. `--runs 1` is not sufficient for reliability estimates.
3. Do not label generated variants as an independent held-out test set: the generator and task templates are open source, and there are only six families.
4. For stronger future evidence, curate separately withheld task templates, randomize the topology beyond filename/value substitution, add negative/error controls, and evaluate stability across power/clocks.
5. Real code execution, patch correctness and SWE-bench-like claims require separately approved isolation, pinned public tasks, no secrets, and a hardened sandbox **away from the model-serving Jetson host**.

No NVIDIA vLLM image, Docker launch parameters or existing B2 model files are modified by this feature.
