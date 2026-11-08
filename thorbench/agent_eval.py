"""Safe multi-turn agent evaluation against an in-memory synthetic repository.

Model-generated tool calls are interpreted by a hardcoded simulator: NEVER as
shell commands, filesystem operations, Python execution, or network requests.
Only the benchmark's own calls to the configured model endpoint use the network.
No generated text, prompts, tool arguments, or simulated file contents are saved.
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
from typing import Any, Callable


@dataclass(frozen=True)
class Task:
    id: str
    instruction: str
    kind: str


TASKS: tuple[Task, ...] = (
    Task(
        "trace_symbol",
        "Use repository tools to search for CACHE_TTL_SECONDS, read the file defining it, "
        "then report its repository path and current numerical value.",
        "investigation",
    ),
    Task(
        "repair_failing_test",
        "In the simulated repository, tests/test_cache_policy.py is failing. "
        "Run the test to inspect the failure, read src/cache_policy.py, use replace_text "
        "to change CACHE_TTL_SECONDS from 30 to 60, rerun the test, and report the outcome. "
        "Do not claim success unless the test returns PASS.",
        "repair",
    ),
    Task(
        "missing_document_recovery",
        "First try reading docs/cache-v1.md. It may have moved. If missing, search "
        "the repository for the active cache retry runbook, read it and summarize "
        "how many retries are allowed for HTTP 503.",
        "missing_doc",
    ),
    Task(
        "transient_error_recovery",
        "Read docs/incident.md and report the incident identifier. The simulated "
        "repository may transiently fail; retry the read if the error is temporary.",
        "transient",
    ),
    Task(
        "no_tool_needed",
        "Without using tools, briefly explain what TTFT measures in an LLM response.",
        "no_tool",
    ),
)

# Public, artificial fixtures. Nothing points at a real host repository path.
FIXTURES = {
    "src/cache_policy.py": "CACHE_TTL_SECONDS = 30\n\ndef cache_expired(age_seconds):\n    return age_seconds >= CACHE_TTL_SECONDS\n",
    "tests/test_cache_policy.py": "# Synthetic test fixture: requires CACHE_TTL_SECONDS == 60.\n",
    "docs/cache-runbook.md": (
        "# Active cache retry runbook\n"
        "When an HTTP 503 occurs, retry at most 2 times, using exponential backoff.\n"
    ),
    "docs/incident.md": "# Synthetic incident\nIncident identifier: INC-42.\n",
}

TOOLS: tuple[dict[str, Any], ...] = (
    {"type": "function", "function": {
        "name": "search_repository", "description": "Search public synthetic repository files for a token.",
        "parameters": {"type": "object", "properties": {"query": {"type": "string"}},
                       "required": ["query"], "additionalProperties": False},
    }},
    {"type": "function", "function": {
        "name": "read_file", "description": "Read a synthetic repository-relative path. Can return a typed error.",
        "parameters": {"type": "object", "properties": {"path": {"type": "string"}},
                       "required": ["path"], "additionalProperties": False},
    }},
    {"type": "function", "function": {
        "name": "run_tests", "description": "Simulate tests for an allowlisted synthetic test file; never execute code.",
        "parameters": {"type": "object", "properties": {"target": {"type": "string"}},
                       "required": ["target"], "additionalProperties": False},
    }},
    {"type": "function", "function": {
        "name": "replace_text", "description": "Replace one exact line in a simulated file, only in memory. No real changes.",
        "parameters": {"type": "object", "properties": {
            "path": {"type": "string"}, "old": {"type": "string"}, "new": {"type": "string"}},
            "required": ["path", "old", "new"], "additionalProperties": False},
    }},
)
TOOL_SCHEMAS: dict[str, tuple[str, ...]] = {
    "search_repository": ("query",), "read_file": ("path",),
    "run_tests": ("target",), "replace_text": ("path", "old", "new"),
}


@dataclass(frozen=True)
class Event:
    name: str
    outcome: str
    path: str | None = None
    matches: tuple[str, ...] = ()


class SimulatedRepository:
    """Strictly in-memory tool interpreter with per-episode state and error injection."""

    def __init__(self, task: Task):
        self.task = task
        self.files = dict(FIXTURES)
        self.transient_triggered = False
        self.events: list[Event] = []

    def execute(self, name: str, raw_arguments: Any) -> dict[str, Any]:
        """Return only static JSON-serializable tool observations, never execute commands."""
        args: Any
        if not isinstance(raw_arguments, str) or len(raw_arguments) > 2048:
            args = None
        else:
            try:
                args = json.loads(raw_arguments)
            except (ValueError, TypeError):
                args = None
        keys = TOOL_SCHEMAS.get(name)
        if keys is None:
            self.events.append(Event("unknown_tool", "error"))
            return {"error": "unknown_tool"}
        if (not isinstance(args, dict) or set(args) != set(keys)
                or any(not isinstance(args[k], str) or len(args[k]) > 256 for k in keys)):
            self.events.append(Event(name, "invalid_arguments"))
            return {"error": "invalid_arguments"}

        if name == "search_repository":
            query = args["query"].strip().lower()
            if not query:
                self.events.append(Event(name, "invalid_arguments"))
                return {"error": "empty_query"}
            paths = tuple(sorted(path for path, content in self.files.items()
                                 if query in path.lower() or query in content.lower()))
            self.events.append(Event(name, "ok", matches=paths))
            return {"matches": [{"path": path} for path in paths]}

        if name == "read_file":
            path = args["path"]
            if self.task.kind == "transient" and path == "docs/incident.md" and not self.transient_triggered:
                self.transient_triggered = True
                self.events.append(Event(name, "temporary_unavailable", path))
                return {"error": "temporary_unavailable", "retryable": True}
            if path not in self.files:
                self.events.append(Event(name, "not_found", path))
                return {"error": "file_not_found", "path": path}
            self.events.append(Event(name, "ok", path))
            return {"path": path, "content": self.files[path]}

        if name == "run_tests":
            target = args["target"]
            if target != "tests/test_cache_policy.py":
                self.events.append(Event(name, "not_found", target))
                return {"error": "unknown_test_target"}
            passed = "CACHE_TTL_SECONDS = 60\n" in self.files["src/cache_policy.py"]
            self.events.append(Event(name, "pass" if passed else "fail", target))
            return {"target": target, "status": "PASS" if passed else "FAIL",
                    "details": "cache TTL matches required 60" if passed else "expected 60, observed 30"}

        # replace_text edits ONLY one allowlisted synthetic file and exact assignment.
        path = args["path"]
        old = args["old"]
        new = args["new"]
        # Accept an optional trailing newline in exact-line replacements; do
        # not broaden the edit scope to arbitrary source code or real files.
        normalized_old = old.rstrip("\n")
        normalized_new = new.rstrip("\n")
        allowed = (path == "src/cache_policy.py" and
                   normalized_old == "CACHE_TTL_SECONDS = 30" and
                   normalized_new == "CACHE_TTL_SECONDS = 60")
        if not allowed or normalized_old not in self.files[path]:
            self.events.append(Event(name, "rejected"))
            return {"error": "edit_not_allowed_or_stale"}
        self.files[path] = self.files[path].replace(normalized_old, normalized_new, 1)
        self.events.append(Event(name, "ok", path))
        return {"path": path, "status": "updated_in_memory_only"}


def _has_event(events: list[Event], name: str, outcome: str, path: str | None = None) -> bool:
    return any(e.name == name and e.outcome == outcome and (path is None or e.path == path)
               for e in events)


def _sequence(events: list[Event], *expected: tuple[str, str, str | None]) -> bool:
    """Require evidence in chronological order without persisting raw model arguments."""
    pos = 0
    for name, outcome, path in expected:
        while pos < len(events) and not (events[pos].name == name and events[pos].outcome == outcome
                                         and (path is None or events[pos].path == path)):
            pos += 1
        if pos == len(events):
            return False
        pos += 1
    return True


def grade(task: Task, repo: SimulatedRepository, final: str) -> tuple[bool, str]:
    """Grade actual simulator evidence AND a nonempty user-facing final answer."""
    answer = final.lower().strip()
    if not answer:
        return False, "empty_final_answer"
    ev = repo.events
    if task.kind == "investigation":
        searched = any(e.name == "search_repository" and "src/cache_policy.py" in e.matches for e in ev)
        read = _has_event(ev, "read_file", "ok", "src/cache_policy.py")
        ok = (searched and read and
              _sequence(ev, ("search_repository", "ok", None),
                        ("read_file", "ok", "src/cache_policy.py"))
              and "src/cache_policy.py" in answer and "30" in answer)
    elif task.kind == "repair":
        ok = (_sequence(ev, ("run_tests", "fail", "tests/test_cache_policy.py"),
                        ("read_file", "ok", "src/cache_policy.py"),
                        ("replace_text", "ok", "src/cache_policy.py"),
                        ("run_tests", "pass", "tests/test_cache_policy.py"))
              and "CACHE_TTL_SECONDS = 60\n" in repo.files["src/cache_policy.py"]
              and ("pass" in answer or "success" in answer))
    elif task.kind == "missing_doc":
        searched = any(e.name == "search_repository" and "docs/cache-runbook.md" in e.matches for e in ev)
        ok = (searched and _sequence(ev, ("read_file", "not_found", "docs/cache-v1.md"),
                                     ("search_repository", "ok", None),
                                     ("read_file", "ok", "docs/cache-runbook.md"))
              and "503" in answer and ("2" in answer or "two" in answer))
    elif task.kind == "transient":
        ok = (_sequence(ev, ("read_file", "temporary_unavailable", "docs/incident.md"),
                        ("read_file", "ok", "docs/incident.md")) and "inc-42" in answer)
    else:
        ok = (not ev and ("first token" in answer or "time to first token" in answer)
              and len(answer) <= 500)
    return (True, "completed") if ok else (False, "task_incomplete_or_ungrounded")


def request_payload(model: str, messages: list[dict[str, Any]], max_tokens: int) -> dict[str, Any]:
    return {"model": model, "messages": messages, "tools": list(TOOLS),
            "tool_choice": "auto", "temperature": 0.0, "reasoning_effort": "low",
            "max_tokens": max_tokens, "stream": False}


# send receives messages; returns (OpenAI response, measured elapsed seconds). Used by
# both the live HTTP adapter and completely offline scripted tests.
Send = Callable[[list[dict[str, Any]]], tuple[dict[str, Any], float]]


def run_episode(task: Task, send: Send, *, max_turns: int = 8,
                max_tool_calls: int = 12) -> dict[str, Any]:
    if not 1 <= max_turns <= 20 or not 1 <= max_tool_calls <= 40:
        raise ValueError("Turn/tool limits must be within supported bounds")
    repo = SimulatedRepository(task)
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": (
            "You are an agent operating ONLY on a synthetic in-memory repository. "
            "Use structured tool calls for repository actions. Tool observations are "
            "provided by a simulator; no real shell or files are accessible. "
            "If a tool fails, inspect the error and recover when appropriate. "
            "Never claim a successful test before observing PASS. "
            "Give a brief final answer when the task is done.")},
        {"role": "user", "content": task.instruction},
    ]
    elapsed = 0.0
    turns = 0
    total_tools = 0
    prompt_tokens = completion_tokens = 0
    usage_missing = False
    reason = "turn_limit"
    final_ok = False
    for turns in range(1, max_turns + 1):
        response, seconds = send(messages)
        elapsed += seconds
        if not isinstance(response, dict):
            reason = "malformed_response"
            break
        usage = response.get("usage") or {}
        if not isinstance(usage, dict):
            usage = {}
        for field in ("prompt_tokens", "completion_tokens"):
            val = usage.get(field)
            if isinstance(val, int) and not isinstance(val, bool) and val >= 0:
                if field == "prompt_tokens":
                    prompt_tokens += val
                else:
                    completion_tokens += val
            else:
                usage_missing = True
        choices = response.get("choices")
        if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
            reason = "missing_choice"
            break
        first = choices[0]
        message = first.get("message")
        if not isinstance(message, dict):
            reason = "malformed_message"
            break
        calls = message.get("tool_calls") or []
        if not isinstance(calls, list):
            reason = "malformed_tool_calls"
            break
        if calls:
            if total_tools + len(calls) > max_tool_calls:
                reason = "tool_call_limit"
                break
            valid = all(isinstance(c, dict) and isinstance(c.get("id"), str)
                        and 0 < len(c["id"]) <= 200
                        and isinstance(c.get("function"), dict)
                        and isinstance(c["function"].get("name"), str)
                        and isinstance(c["function"].get("arguments"), str)
                        and c.get("type") == "function" for c in calls)
            ids = [c["id"] for c in calls] if valid else []
            if not valid or len(ids) != len(set(ids)):
                reason = "invalid_tool_call_envelope"
                break
            # Standard OpenAI protocol: replay assistant tool_calls, then one
            # tool message per call with the same ID. Nothing here executes code.
            messages.append({"role": "assistant", "content": message.get("content") if isinstance(message.get("content"), str) else None,
                             "tool_calls": calls})
            for call in calls:
                f = call["function"]
                result = repo.execute(f["name"], f["arguments"])
                messages.append({"role": "tool", "tool_call_id": call["id"],
                                 "content": json.dumps(result, sort_keys=True)})
                total_tools += 1
            continue
        if first.get("finish_reason") not in ("stop", None):
            reason = "nonfinal_finish_reason"
            break
        content = message.get("content")
        final_ok, reason = grade(task, repo, content if isinstance(content, str) else "")
        break

    events = repo.events
    recovered = (task.kind == "missing_doc" and
                 _has_event(events, "read_file", "not_found", "docs/cache-v1.md") and
                 _has_event(events, "read_file", "ok", "docs/cache-runbook.md")) or (
                 task.kind == "transient" and
                 _has_event(events, "read_file", "temporary_unavailable", "docs/incident.md") and
                 _has_event(events, "read_file", "ok", "docs/incident.md"))
    # Restrict stored trace to known event categories. No raw model text, generated
    # arguments, simulated file contents or host paths are written to reports.
    trace = [e.name + ":" + e.outcome for e in events]
    return {"ok": final_ok, "reason": reason, "case": task.id,
            "turns": turns, "tool_calls": total_tools,
            "tool_errors": sum(e.outcome in {"error", "invalid_arguments", "not_found",
                                              "temporary_unavailable", "rejected"} for e in events),
            "recovered": bool(recovered), "trace": trace,
            "elapsed_s": round(elapsed, 4),
            "prompt_tokens": None if usage_missing else prompt_tokens,
            "completion_tokens": None if usage_missing else completion_tokens}


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    case_stats: dict[str, dict[str, Any]] = {}
    for task in TASKS:
        group = [r for r in rows if r["case"] == task.id]
        def med(field: str) -> float | None:
            vals = [r[field] for r in group if isinstance(r.get(field), (float, int))
                    and not isinstance(r.get(field), bool)]
            return round(statistics.median(vals), 4) if vals else None
        case_stats[task.id] = {"passed": sum(r["ok"] for r in group),
                               "total": len(group), "median_elapsed_s": med("elapsed_s"),
                               "median_turns": med("turns"), "median_tool_calls": med("tool_calls"),
                               "median_prompt_tokens": med("prompt_tokens"),
                               "median_completion_tokens": med("completion_tokens"),
                               "recoveries": sum(bool(r.get("recovered")) for r in group)}
    passed = sum(bool(r["ok"]) for r in rows)
    return {"schema_version": 1, "suite": "agent-multiturn", "passed": passed,
            "total": len(rows), "pass_rate": round(passed / len(rows), 4) if rows else None,
            "median_elapsed_s": round(statistics.median(r["elapsed_s"] for r in rows), 4) if rows else None,
            "case_results": case_stats,
            "limitations": "Deterministic in-memory tools; no code execution, real patch, or autonomous deployment."}


def run_live(*, model: str, base_url: str, runs: int, results_dir: Path,
             max_turns: int = 8, max_tokens: int = 1024, timeout: int = 600) -> tuple[Path, dict[str, Any]]:
    from .client import APIError, VLLMClient
    from .report import new_run_dir

    if not 1 <= runs <= 10 or not 128 <= max_tokens <= 4096:
        raise ValueError("--runs must be 1..10; --max-tokens must be 128..4096")
    if not 1 <= max_turns <= 20:
        raise ValueError("--max-turns must be 1..20")
    client = VLLMClient(base_url, model, timeout)
    if not client.health() or not any(m.get("id") == model for m in client.models()):
        raise ValueError("Requested model not healthy/available on local endpoint")

    dest = new_run_dir(results_dir, "agent-multiturn")
    metadata = {"date_utc": datetime.now(timezone.utc).isoformat(), "suite": "agent-multiturn",
                "model": model, "runs": runs, "cases": len(TASKS),
                "max_turns": max_turns, "max_tokens": max_tokens,
                "simulated_only": True, "real_tool_execution": False}
    (dest / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    rows: list[dict[str, Any]] = []
    with (dest / "samples.jsonl").open("w", encoding="utf-8") as f:
        for i in range(1, runs + 1):
            for task in TASKS:
                def send(messages: list[dict[str, Any]]) -> tuple[dict[str, Any], float]:
                    payload = request_payload(model, messages, max_tokens)
                    started = time.monotonic()
                    with client._request("/v1/chat/completions", payload) as res:
                        data = json.load(res)
                    return data, time.monotonic() - started

                started = time.monotonic()
                try:
                    result = run_episode(task, send, max_turns=max_turns)
                except (APIError, OSError, TimeoutError, ValueError, TypeError) as exc:
                    result = {"case": task.id, "ok": False, "reason": "request_error",
                              "error_type": type(exc).__name__, "turns": 0, "tool_calls": 0,
                              "tool_errors": 0, "recovered": False, "trace": [],
                              "elapsed_s": round(time.monotonic() - started, 4),
                              "prompt_tokens": None, "completion_tokens": None}
                row = {"run": i, **result}
                rows.append(row)
                f.write(json.dumps(row, sort_keys=True) + "\n")
                print(f"  {task.id} run={i}: {'PASS' if result['ok'] else 'FAIL'} "
                      f"({result['reason']}, {result['turns']} turns, "
                      f"{result['tool_calls']} simulated tool calls, {result['elapsed_s']}s)", flush=True)

    stats = summarize(rows)
    (dest / "summary.json").write_text(json.dumps(stats, indent=2) + "\n", encoding="utf-8")
    lines = ["# Multi-turn agent completion — simulated repository", "",
             "**No model-generated code, shell commands or real repository edits were executed.**", "",
             f"- Completed: **{stats['passed']}/{stats['total']}** ({stats['pass_rate']:.1%})",
             f"- Median task latency: **{stats['median_elapsed_s']:.2f}s**", "",
             "| Scenario | Passed | Total | Median turns | Median tools | Median input tokens | Median output tokens | Median task latency |",
             "|---|---:|---:|---:|---:|---:|---:|---:|",
             ]
    for task in TASKS:
        group = stats["case_results"][task.id]
        fmt = lambda v: "n/a" if v is None else str(v)
        lines.append(f"| `{task.id}` | {group['passed']} | {group['total']} | "
                     f"{fmt(group['median_turns'])} | {fmt(group['median_tool_calls'])} | "
                     f"{fmt(group['median_prompt_tokens'])} | {fmt(group['median_completion_tokens'])} | "
                     f"{fmt(group['median_elapsed_s'])}s |")
    lines.extend(["", "Pass requires deterministic tool evidence plus a grounded final answer; "
                  "tool selection or a textual assertion alone is insufficient.",
                  "Each episode starts with fresh synthetic state. Missing-file and transient-error "
                  "recoveries are scored explicitly. All outputs are private by default.", ""])
    (dest / "summary.md").write_text("\n".join(lines), encoding="utf-8")
    return dest, stats


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--runs", type=int, default=1, help="Repetitions per five-case task set, 1..10")
    ap.add_argument("--max-turns", type=int, default=8)
    ap.add_argument("--max-tokens", type=int, default=1024)
    ap.add_argument("--timeout", type=int, default=600)
    ap.add_argument("--model", default=os.getenv("THOR_BENCH_MODEL", "Qwen3.8-Flash-Next"))
    ap.add_argument("--base-url", default=os.getenv("THOR_BENCH_BASE_URL", "http://127.0.0.1:8000"))
    ap.add_argument("--results-dir", type=Path, default=Path("results"))
    args = ap.parse_args(argv)
    try:
        directory, stats = run_live(model=args.model, base_url=args.base_url, runs=args.runs,
                                    results_dir=args.results_dir, max_turns=args.max_turns,
                                    max_tokens=args.max_tokens, timeout=args.timeout)
    except (OSError, ValueError) as exc:
        print(f"Benchmark setup failed: {type(exc).__name__}", file=sys.stderr)
        return 2
    print(f"Report: {directory / 'summary.md'}")
    return 0 if stats["passed"] == stats["total"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
