# Shockwave: 25/25 simulated multi-turn agent episodes on B2 (2026-11-08 UTC)

> **Operator-supplied observations**, not independently executed by CI. Qwen3.8 Flash Next NVFP4 on Jetson AGX Thor with the previously documented B2 4 GiB explicit KV / 131,072 maximum-context serving profile. Five *fixed synthetic in-memory repository scenarios*, five repetitions of each. This is **not a real repository coding benchmark**.

## Summary

- **25/25 deterministic task-completion checks passed** in the five-repetition run; earlier smoke run: **5/5**.
- Median end-to-end task latency across 25 episodes: **12.2302 seconds**.
- **67/67 offline unit tests** passed in the operator's working tree.
- **75 model turns** and **55 simulated tool calls** in the 25-episode run, inferred from the reported constant per-scenario turn/call counts. No host tools were executed; tool calls operated only on in-memory fixture state.
- `free -h` immediately after the benchmark reported **2.6 GiB `MemAvailable`**, with swap disabled. One observation does not establish long-run stability.

## Five-repetition task results

Each task has five passes out of five. Per-case token counts are **median total usage summed over all model turns for one episode**, including repeated conversation history on each request—not unique context tokens.

| Scenario | Pass | Median model turns | Median simulated tool calls | Median prompt tokens | Median completion tokens | Median task latency |
|---|---:|---:|---:|---:|---:|---:|
| `trace_symbol` | 5/5 | 3 | 2 | 2,121 | 205 | 10.1127 s |
| `repair_failing_test` | 5/5 | 4 | 4 | 3,515 | 480 | 20.9647 s |
| `missing_document_recovery` | 5/5 | 4 | 3 | 2,999 | 276 | 13.2528 s |
| `transient_error_recovery` | 5/5 | 3 | 2 | 2,106 | 257 | 12.2302 s |
| `no_tool_needed` | 5/5 | 1 | 0 | 622 | 125 | 5.6337 s |

All repeats showed the same number of model turns and simulated tool calls per case. The synthetic failing-test repair had the highest observed median whole-task latency, **20.9647s**, reflecting more simulated interactions and generated tokens; this observation does not isolate model decode speed.

## What is actually validated

The evaluator performs deterministic state checks on an *in-memory* repository and requires grounded final-answer criteria, not merely a claimed success. Episodes cover a search→read investigation, a simulated failing-test→allowed-edit→passing-test sequence, recovery from a missing document, retry after a transient read failure, and answering directly when a tool is unnecessary. All five succeeded across their five repetitions in this observed run.

The evaluator does **not** run real tests, execute generated commands, apply changes to host files, prove arbitrary patch correctness, assess exploit resistance, or establish general coding-agent reliability. The phrase “25/25” describes **25 repeated episodes of five known tasks**, not 25 diverse issues. Deterministic prompts and repeated runs can conceal overfitting; more varied and withheld fixtures are needed.

## Reproduction and provenance

The original operator reports are private and Git-ignored. These public numeric figures were transcribed from:

- First run: `results/20261108T041305Z-agent-multiturn/summary.md` (5/5, median task time 12.80s).
- Repeated run: `results/20261108T041614Z-agent-multiturn/summary.md` (25/25, median 12.23s).
- Source was uncommitted at measurement time on `feat/multiturn-agent-simulator`; the operator's test run reported `Ran 67 tests ... OK`.

To reproduce on a host with its own healthy local OpenAI-compatible vLLM API and the installed benchmark source:

```bash
python3 -m unittest discover -s tests -v
python3 -m thorbench.agent_eval --runs 5
cat "$(ls -td results/*-agent-multiturn | head -1)/summary.md"
```

Do not run either Docker launch script while the serving B2 container remains active. See the [evaluation contract](../AGENT_MULTI_TURN_EVAL.md) and [simulator flow diagram](../diagrams/12-multi-turn-simulator.md).

## Next independent quality gate

Add unseen synthetic fixtures with varied identifiers, sequence paths, and failure conditions; then move to **separately isolated, sandboxed** real-code tasks where actual test execution determines the outcome. Keep simulated and real execution scores separate.
