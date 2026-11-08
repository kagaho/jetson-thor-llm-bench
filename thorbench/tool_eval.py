"""Read-only, first-decision tool-routing benchmark for an OpenAI-compatible LLM.

The declared tools are NEVER executed. A model's first structured tool decision
is checked against synthetic, deterministic fixtures. No model-generated text,
arguments, prompts, or tool results are written to disk.
"""
from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

TOOLS: list[dict[str, Any]] = [
    {
        "type": "function", "function": {
            "name": "read_file", "description": "Read one repository-relative file.",
            "parameters": {"type": "object", "properties": {
                "path": {"type": "string", "description": "Repository-relative file path"}},
                "required": ["path"], "additionalProperties": False},
        },
    },
    {
        "type": "function", "function": {
            "name": "search_repository", "description": "Find identifiers in a repository by text search.",
            "parameters": {"type": "object", "properties": {
                "query": {"type": "string", "description": "Identifier to search for"}},
                "required": ["query"], "additionalProperties": False},
        },
    },
    {
        "type": "function", "function": {
            "name": "run_tests", "description": "Request a test run for a named test file (simulated; never executes).",
            "parameters": {"type": "object", "properties": {
                "target": {"type": "string", "description": "Repository-relative test file"}},
                "required": ["target"], "additionalProperties": False},
        },
    },
]


@dataclass(frozen=True)
class Case:
    id: str
    instruction: str
    expected_tool: str | None
    expected_arg: str | None = None
    expected_value: str | None = None
    contains: bool = False


CASES: tuple[Case, ...] = (
    Case("read_model_guide", "Read models/qwen3.8-flash-next/README.md before summarizing the deployment.",
         "read_file", "path", "models/qwen3.8-flash-next/README.md"),
    Case("search_client", "Find the VLLMClient class definition in the repository.",
         "search_repository", "query", "VLLMClient", True),
    Case("run_cache_tests", "Run the tests in tests/test_cache_metrics.py to check for regressions.",
         "run_tests", "target", "tests/test_cache_metrics.py"),
    Case("read_agent_protocol", "Open docs/AGENT_BENCHMARK_PROTOCOL.md to inspect its requirements.",
         "read_file", "path", "docs/AGENT_BENCHMARK_PROTOCOL.md"),
    Case("search_counter_deltas", "Search the repository for the counter_deltas function.",
         "search_repository", "query", "counter_deltas", True),
    Case("no_tool_needed", "Explain in one sentence why decoded tokens/sec is different from TTFT. Do not use tools.",
         None),
)

ALLOWED_NAMES = frozenset(t["function"]["name"] for t in TOOLS)


def request_payload(case: Case, model: str, max_tokens: int = 1024) -> dict[str, Any]:
    return {
        "model": model,
        "messages": [
            {"role": "system", "content": (
                "You are a careful repository coding assistant. Select a tool when the user's "
                "request requires repository access or tests; for conceptual questions answer "
                "directly. Tool calls are evaluated but never executed. Use the stated exact paths."
            )},
            {"role": "user", "content": case.instruction},
        ],
        "tools": TOOLS,
        "tool_choice": "auto",
        "temperature": 0.0,
        "reasoning_effort": "low",
        "max_tokens": max_tokens,
        "stream": False,
    }


def score_response(response: dict[str, Any], case: Case) -> dict[str, Any]:
    """Inspect only structured tool_calls, not textual imitations of function calls."""
    choices = response.get("choices")
    if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
        return {"ok": False, "reason": "missing_choice", "tool": None, "tool_count": 0}
    choice = choices[0]
    message = choice.get("message")
    if not isinstance(message, dict):
        return {"ok": False, "reason": "missing_message", "tool": None, "tool_count": 0}
    calls = message.get("tool_calls") or []
    if not isinstance(calls, list):
        return {"ok": False, "reason": "malformed_tool_calls", "tool": None, "tool_count": 0}
    if case.expected_tool is None:
        content = message.get("content")
        passed = len(calls) == 0 and isinstance(content, str) and bool(content.strip())
        return {"ok": passed, "reason": "correct_no_tool" if passed else "unexpected_tool_or_empty_answer",
                "tool": None, "tool_count": len(calls)}
    if len(calls) != 1 or not isinstance(calls[0], dict):
        return {"ok": False, "reason": "expected_exactly_one_tool", "tool": None, "tool_count": len(calls)}
    func = calls[0].get("function")
    if not isinstance(func, dict):
        return {"ok": False, "reason": "malformed_function", "tool": None, "tool_count": 1}
    name = func.get("name")
    safe_name = name if isinstance(name, str) and name in ALLOWED_NAMES else "<unknown>"
    if name != case.expected_tool:
        return {"ok": False, "reason": "wrong_tool", "tool": safe_name, "tool_count": 1}
    raw_args = func.get("arguments")
    try:
        args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
    except (ValueError, TypeError):
        return {"ok": False, "reason": "invalid_json_arguments", "tool": safe_name, "tool_count": 1}
    if not isinstance(args, dict) or set(args) != {case.expected_arg}:
        return {"ok": False, "reason": "invalid_argument_schema", "tool": safe_name, "tool_count": 1}
    value = args.get(case.expected_arg)
    if not isinstance(value, str):
        return {"ok": False, "reason": "invalid_argument_type", "tool": safe_name, "tool_count": 1}
    matched = case.expected_value in value if case.contains else value == case.expected_value
    return {"ok": bool(matched), "reason": "correct_tool_and_arguments" if matched else "wrong_argument_value",
            "tool": safe_name, "tool_count": 1}


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    ok = sum(bool(x["ok"]) for x in rows)
    latencies = [x["elapsed_s"] for x in rows if isinstance(x.get("elapsed_s"), (float, int))]
    groups: dict[str, dict[str, Any]] = {}
    for r in rows:
        g = groups.setdefault(r["case"], {"passed": 0, "total": 0, "_rows": []})
        g["total"] += 1
        g["passed"] += bool(r["ok"])
        g["_rows"].append(r)
    for g in groups.values():
        members = g.pop("_rows")
        for field in ("elapsed_s", "prompt_tokens", "completion_tokens"):
            vals = [r[field] for r in members
                    if isinstance(r.get(field), (int, float)) and not isinstance(r.get(field), bool)]
            g["median_" + field] = round(statistics.median(vals), 4) if vals else None
    return {"schema_version": 1, "passed": ok, "total": len(rows),
            "pass_rate": round(ok / len(rows), 4) if rows else None,
            "median_elapsed_s": round(statistics.median(latencies), 4) if latencies else None,
            "cases": groups,
            "note": "First structured tool decision only. No tools executed; not an end-to-end coding-agent benchmark."}


def run_live(*, model: str, base_url: str, repeats: int, results_dir: Path,
             max_tokens: int = 1024, timeout: int = 600) -> tuple[Path, dict[str, Any]]:
    # Import lazily so scoring/tests do not contact the inference server.
    from .client import VLLMClient, APIError

    if not 1 <= repeats <= 20:
        raise ValueError("--runs must be 1..20")
    if not 128 <= max_tokens <= 4096:
        raise ValueError("--max-tokens must be 128..4096")
    client = VLLMClient(base_url, model, timeout)
    if not client.health():
        raise ValueError("Local model health check failed")
    if not any(m.get("id") == model for m in client.models()):
        raise ValueError("Requested model not found on server")
    from .report import new_run_dir
    dest = new_run_dir(results_dir, "tool-routing")
    metadata = {"date_utc": datetime.now(timezone.utc).isoformat(), "model": model,
                "suite": "tool-routing", "repetitions": repeats, "max_tokens": max_tokens,
                "case_count": len(CASES), "no_tool_execution": True}
    (dest / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    rows: list[dict[str, Any]] = []
    with (dest / "samples.jsonl").open("w", encoding="utf-8") as f:
        for i in range(1, repeats + 1):
            for case in CASES:
                start = time.monotonic()
                try:
                    with client._request("/v1/chat/completions", request_payload(case, model, max_tokens)) as response:
                        data = json.load(response)
                    elapsed = round(time.monotonic() - start, 4)
                    verdict = score_response(data, case)
                    usage = data.get("usage") or {}
                    row = {"case": case.id, "run": i, **verdict, "elapsed_s": elapsed,
                           "prompt_tokens": usage.get("prompt_tokens"),
                           "completion_tokens": usage.get("completion_tokens")}
                except (APIError, OSError, TimeoutError, ValueError) as exc:
                    row = {"case": case.id, "run": i, "ok": False,
                           "reason": "request_error", "error_type": type(exc).__name__,
                           "elapsed_s": round(time.monotonic() - start, 4)}
                rows.append(row)
                f.write(json.dumps(row, sort_keys=True) + "\n")
                print(f"  {case.id} run={i}: {'PASS' if row['ok'] else 'FAIL'} "
                      f"({row['reason']}, {row.get('elapsed_s')}s)", flush=True)
    stats = summarize(rows)
    (dest / "summary.json").write_text(json.dumps(stats, indent=2) + "\n", encoding="utf-8")
    lines = ["# First-decision tool-routing benchmark", "",
             "**No declared tools were executed.** Only structured tool calls and exact argument values were scored.", "",
             f"- Passes: **{stats['passed']}/{stats['total']}** ({stats['pass_rate']:.1%})",
             f"- Median request latency: **{stats['median_elapsed_s']} seconds**", "",
             "| Case | Passed | Total | Median latency | Median prompt tokens | Median completion tokens |",
             "|---|---:|---:|---:|---:|---:|"]
    def show(value, unit=""):
        return f"{value:.2f}{unit}" if isinstance(value, (int, float)) else "n/a"
    lines.extend(
        f"| `{k}` | {v['passed']} | {v['total']} | "
        f"{show(v['median_elapsed_s'], 's')} | {show(v['median_prompt_tokens'])} | "
        f"{show(v['median_completion_tokens'])} |"
        for k, v in stats["cases"].items()
    )
    lines += ["", "Token counts describe request size and generation length; completion tokens may include reasoning. "
              "Total request latency is not decode-only throughput.", "",
              "Failures count toward the denominator. This suite does not measure ",
              "multi-step planning, real tool execution, code correctness, or task completion.", ""]
    (dest / "summary.md").write_text("\n".join(lines), encoding="utf-8")
    return dest, stats


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Safe tool-routing probe; functions are NEVER executed")
    parser.add_argument("--runs", type=int, default=2, help="Repetitions of six deterministic synthetic cases")
    parser.add_argument("--base-url", default=os.getenv("THOR_BENCH_BASE_URL", "http://127.0.0.1:8000"))
    parser.add_argument("--model", default=os.getenv("THOR_BENCH_MODEL", "Qwen3.8-Flash-Next"))
    parser.add_argument("--results-dir", type=Path, default=Path("results"))
    parser.add_argument("--max-tokens", type=int, default=1024)
    parser.add_argument("--timeout", type=int, default=600)
    args = parser.parse_args(argv)
    from .client import APIError
    try:
        dest, stats = run_live(model=args.model, base_url=args.base_url, repeats=args.runs,
                               results_dir=args.results_dir, max_tokens=args.max_tokens, timeout=args.timeout)
    except (APIError, OSError, ValueError) as exc:
        print(f"Benchmark could not start: {type(exc).__name__}: {exc if isinstance(exc, ValueError) else 'I/O error'}", file=sys.stderr)
        return 2
    print(f"Report: {dest / 'summary.md'}")
    return 0 if stats["passed"] == stats["total"] else 1


if __name__ == "__main__":
    sys.exit(main())
