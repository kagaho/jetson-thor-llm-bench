# v0.6.0 — multi-turn simulated-agent benchmark

This evaluation is the next incremental step after v0.5.0's **30/30 first-decision tool-routing** probes. The model now receives tool observations, can make subsequent decisions, and is graded on reaching a **deterministic synthetic outcome**. No generated command, code, patch, test or file access runs on Shockwave.

For a visual explanation of every fixed task's required trace, see the [five-task map](diagrams/19-fixed-agent-test-cases.md), the [model/tool loop](diagrams/12-multi-turn-simulator.md) and the [complete suite guide](BENCHMARK_VISUAL_GUIDE.md#fixed-multi-turn-simulated-tasks).

## Benchmark contract

| Dimension | Contract |
|---|---|
| Interface | Repeated non-streaming `POST /v1/chat/completions` with `tool_choice=auto`; assistant tool calls and matching `tool_call_id` replies are carried into the next turn |
| Repository | Static, public fixtures loaded into a Python dictionary freshly per task; never the real worktree |
| Tools | `search_repository`, `read_file`, `run_tests`, `replace_text` |
| Execution | All four names are **in-memory simulations**. `run_tests` compares fixture data; `replace_text` changes a single allowlisted string in a Python dictionary. No arbitrary shell, Python execution, filesystem editing, imports of untrusted code, or network beyond the local model API |
| Tasks | Five cases: repository symbol search; failure→edit→retest; missing-document recovery; temporary-error retry; no-tool negative control |
| Scoring | Required **chronological simulator evidence** plus a grounded final answer (simple deterministic phrase checks); tool selection alone or an unsupported declaration of success cannot pass |
| Bounds | Default 8 model turns and 12 tool calls per task; failed/hallucinated calls consume the budget |
| Token accounting | Sum reported `prompt_tokens` and `completion_tokens` **over all model turns** in one task. Prompt tokens repeat history, so this is model API usage, not unique context tokens |
| Reports | Gitignored `results/<timestamp>-agent-multiturn/` with safe verdicts, event categories, token counts, turns, error/recovery counts and latencies; **no raw prompts, model answers, simulated file contents, generated arguments or private files** |

### Exact tasks and quality gates

| Case | Must demonstrate |
|---|---|
| `trace_symbol` | Search discovers `src/cache_policy.py`, read succeeds, answer reports path and `30` |
| `repair_failing_test` | Test FAIL precedes allowed in-memory `30→60` edit, test PASS follows edit, final answer acknowledges success |
| `missing_document_recovery` | Initial `docs/cache-v1.md` not-found, search finds current runbook, read succeeds, answer states 2 retries for HTTP 503 |
| `transient_error_recovery` | Synthetic initial read returns `temporary_unavailable`, next read succeeds, answer reports `INC-42` |
| `no_tool_needed` | No tools selected and a TTFT answer mentioning first-token time, in at most 500 characters |

**Caveats:** These are five small, public, deterministic scenarios. The model could overfit to them. Natural-language grading remains heuristic. A 5/5 or 25/25 score is **not** a SWE-bench score, actual patch correctness, independent model reasoning validation, security certification or a real coding-agent task completion rate. The test only shows completion *in the defined simulator*.

## Run on the existing B2 container — no Docker restart

```bash
cd ~/Documents/jetson-thor-llm-bench
python3 -m unittest discover -s tests -v
curl -fsS http://127.0.0.1:8000/health && echo Healthy
python3 -m thorbench.agent_eval --runs 1
cat "$(ls -td results/*-agent-multiturn | head -1)/summary.md"
```

After inspecting the smoke-run output, optionally repeat with `--runs 5`; that is five repetitions of each of the five fixed synthetic tasks (25 total episodes, each potentially requiring multiple model requests). Preserve the printed failures and report counts if any case cannot complete. The benchmark returns a nonzero exit status when some cases fail; **that is a valid, useful benchmark outcome**, not permission to change the reference answer or quietly skip a task.

For a difficult case, one controlled follow-up is `--runs 1 --max-turns 12 --max-tokens 1536` with the altered limits recorded. Do not retroactively change its original result. Tool calls and request payloads are **never executed locally**. The only writes are the benchmark's own metadata and numeric reports under the ignored results folder.

## Observed Shockwave B2 results (2026-11-08 UTC)

The operator ran `--runs 1` (5/5) followed by `--runs 5` (**25/25**); all five scenario categories passed each repetition. The 25-episode run reported a **12.2302s median whole-task latency** and was accompanied by **67 passing offline tests**. Available system memory after the run was **2.6 GiB**; this is a snapshot, not a sustained-memory stability guarantee. Read the [full aggregate report](benchmarks/2026-11-08-shockwave-multiturn-25-episodes.md) for per-case turns, simulated tool calls and token counts. Raw numeric results stay under Git-ignored `results/`.

These 25 episodes repeat the *same five small deterministic fixtures*, rather than 25 distinct coding tasks. Evidence is limited to their success under this simulation.

## What the benchmark does not do

- It does not use the host repository as agent context, and it cannot change real source files.
- It does not run `pytest`, execute a `run_tests` command or apply model-generated diffs on the OS.
- It does not measure real-world coding quality, costs across different providers, prompt-injection resilience, or completion of arbitrary user issues.
- It is not directly comparable with the prior six-case first-decision test, prefix TTFT measurements, or B2 memory tests.

## Next control gates

1. Publish only reviewed aggregate case results, with prompt/output-token totals and failed cases disclosed.
2. Compare B2 and high-context A only in a separate, controlled restart experiment if necessary; keep the model running for the initial v0.6 benchmark.
3. Add harder hidden/new synthetic fixtures before claiming generalization; vary exact identifiers, tool ordering, and error types.
4. Move to actual coding correctness **only** with explicit container isolation, restricted resources, immutable test fixtures, no secrets/network, and separate approval of the execution sandbox.

See [first-decision tool routing](AGENT_TOOL_EVAL.md), [B2 memory runbook](MEMORY_AB_EXPERIMENT.md), and [multi-turn state-machine diagram](diagrams/12-multi-turn-simulator.md).
