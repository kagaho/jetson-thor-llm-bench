# v0.5.0: first-decision coding-agent tool routing (no execution)

**Status: experimental v0.5.0 candidate.** This is a **real model tool-call** test but **not** an end-to-end coding agent. It deliberately does not run model-generated shell commands, apply patches, search real files, or execute tests. Its only purpose is to assess the model's *first structured tool decision* for a small public synthetic fixture set.

## Why start here?

Previous `agent` benchmarks used changing user requests over a shared, synthetic repository prefix. They measure latency and cache behavior, not whether the model can interact with a tool ecosystem. This step measures whether Qwen's OpenAI-compatible API and configured `qwen3_xml` parser return structured `tool_calls` with the expected function name and arguments.

## Evaluation contract

| Item | Details |
|---|---|
| Interface | `POST /v1/chat/completions`, `tools=[...]`, `tool_choice=auto`, non-streamed |
| Tools | `read_file(path)`, `search_repository(query)`, `run_tests(target)` |
| Tool execution | **Never**. Function declarations are only presented to the model |
| Cases | 6 synthetic tasks, including one 'no tool needed' negative control |
| Pass criteria | Exactly one correct structured call with correct argument, or a text answer without tools for the negative control |
| Failure handling | Invalid JSON, wrong function/argument, missing call, extra calls, HTTP errors count as failures |
| Output | Counts, latency, token usage and non-sensitive verdict codes; no prompts, model text, raw arguments, credentials or repository contents saved |
| Limitation | Does not measure task completion, correct patch creation, ability to handle tool errors, or multi-step planning |

**Run on the current Docker container; do not restart vLLM:**

```bash
cd ~/Documents/jetson-thor-llm-bench
python3 -m unittest discover -s tests -v
python3 -m thorbench doctor --container qwen38-flash-next
python3 -m thorbench.tool_eval --runs 2
cat "$(ls -td results/*-tool-routing | head -1)/summary.md"
```

Six cases × two repetitions = 12 requests. `--runs 1` is a quick smoke test. Some models spend hundreds of tokens in internal reasoning before returning a tool call; the default `--max-tokens 1024` is intentional. The output includes a pass rate; do not treat a `tool_calls` response as a completed programming task.

The server must support `tool_choice=auto` and a tool-call parser. The current baseline declares `--enable-auto-tool-choice --tool-call-parser qwen3_xml`; support still needs confirmation from the live run. Do not force `tool_choice=required` as a workaround because it would invalidate the negative control and may mask model-routing failures.

## Progression to an agent benchmark

1. **v0.5.0:** First tool-call selection and arguments, without execution.
2. **Next:** Multi-turn tool observations from a deterministic fake repository simulator (no shell access); score task plans, recovery from tool errors and no-tool decisions.
3. **Later:** Sandboxed code tasks with pinned tests and curated public fixtures. Execute untrusted code only in a hardened isolated environment—not directly on Shockwave or inside the model-serving container.
4. **Eventually:** Real coding-agent task completion, tests passed, wall-clock time, human intervention count, and token/cost measurements under a reproducible protocol.

Use [tool-routing flowchart](diagrams/10-agent-tool-evaluation.md) and [memory experiment runbook](MEMORY_AB_EXPERIMENT.md). Tool-call implementation details are from [vLLM's tool-calling documentation](https://docs.vllm.ai/en/latest/features/tool_calling/).
