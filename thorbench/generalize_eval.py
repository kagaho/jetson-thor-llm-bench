"""Seed-varying, in-memory coding-agent benchmark: NEVER executes generated code.

Each episode creates synthetic files and an oracle from a deterministic seed.
The only network requests go to the configured OpenAI-compatible model server.
Generated tool calls cannot access the host filesystem, run shell, or run Python.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import re
import secrets
import statistics
import sys
import time
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


KINDS = ("symbol_origin", "repair_regression", "moved_runbook",
         "transient_read", "environment_disambiguation", "no_tool_needed")
SERVICES = ("ingest", "billing", "alerting", "search", "audit", "telemetry", "gateway", "indexer")
SYMBOLS = ("RETRY_LIMIT", "QUEUE_MAX_DEPTH", "CACHE_TTL_SECONDS", "REQUEST_BUDGET")
# Scoring revisions are independent of the unchanged model/fixture protocol.
SCORER_VERSION = "0.7.2"
PROTOCOL_VERSION = "1"

TOOLS: tuple[dict[str, Any], ...] = (
    {"type": "function", "function": {
        "name": "list_files", "description": "List file paths in the synthetic repository under a directory.",
        "parameters": {"type": "object", "properties": {"directory": {"type": "string"}},
                       "required": ["directory"], "additionalProperties": False}}},
    {"type": "function", "function": {
        "name": "search_repository", "description": "Return paths whose synthetic content or path contains a search term.",
        "parameters": {"type": "object", "properties": {"query": {"type": "string"}},
                       "required": ["query"], "additionalProperties": False}}},
    {"type": "function", "function": {
        "name": "read_file", "description": "Read a synthetic repository-relative file; may return typed errors.",
        "parameters": {"type": "object", "properties": {"path": {"type": "string"}},
                       "required": ["path"], "additionalProperties": False}}},
    {"type": "function", "function": {
        "name": "run_tests", "description": "Simulate deterministic fixture tests; this never runs code.",
        "parameters": {"type": "object", "properties": {"target": {"type": "string"}},
                       "required": ["target"], "additionalProperties": False}}},
    {"type": "function", "function": {
        "name": "replace_text", "description": "Replace one exact, allowlisted fixture assignment only in memory.",
        "parameters": {"type": "object", "properties": {
            "path": {"type": "string"}, "old": {"type": "string"}, "new": {"type": "string"}},
            "required": ["path", "old", "new"], "additionalProperties": False}}},
)
SCHEMAS = {t["function"]["name"]: tuple(t["function"]["parameters"]["required"]) for t in TOOLS}


@dataclass(frozen=True)
class Case:
    kind: str
    instruction: str
    files: dict[str, str]
    target: str | None = None
    secondary: str | None = None
    old_path: str | None = None
    symbol: str | None = None
    expected_value: int | str | None = None
    original_value: int | None = None
    test_target: str | None = None
    injected_failures: int = 0


@dataclass(frozen=True)
class Event:
    name: str
    outcome: str
    path: str | None = None
    matches: tuple[str, ...] = ()


def episode_seed(seed: int, kind: str, repetition: int) -> int:
    """Stable across hosts and Python processes (unlike hash())."""
    if not 0 <= seed < 2**63 or repetition < 1 or kind not in KINDS:
        raise ValueError("Invalid seed, repetition or case kind")
    raw = f"jetson-thor-generalize-v1:{seed}:{kind}:{repetition}".encode()
    return int.from_bytes(hashlib.sha256(raw).digest()[:8], "big")


def generate(kind: str, derived_seed: int) -> Case:
    """Create the fixture and its hidden scoring oracle; do not send oracle to LLM."""
    if kind not in KINDS:
        raise ValueError("Unknown case kind")
    rng = random.Random(derived_seed)
    service = rng.choice(SERVICES)
    symbol = rng.choice(SYMBOLS)
    value = rng.choice((3, 5, 7, 11, 17, 23, 31, 47))
    distractor = value + rng.choice((6, 10, 14))
    path = f"src/{service}/policy_{rng.choice(('core', 'runtime', 'limits'))}.py"
    decoy = f"examples/{service}/policy_sample.py"
    files = {
        "README.md": f"# Synthetic workspace\nServices: {service}; search the repository for active configuration.\n",
        path: f"# ACTIVE production configuration for {service}\nENVIRONMENT = 'production'\n{symbol} = {value}\n",
        decoy: f"# EXAMPLE ONLY; not deployed\nENVIRONMENT = 'example'\n{symbol} = {distractor}\n",
    }
    if kind == "symbol_origin":
        return Case(kind, f"Find the active {service} {symbol} setting. Cite its repository path and numerical value using repository evidence.",
                    files, target=path, secondary=decoy, symbol=symbol, expected_value=value)
    if kind == "repair_regression":
        expected = value + rng.choice((2, 4, 8))
        test_target = f"tests/{service}/test_policy.py"
        files[test_target] = (f"# Synthetic regression case for {service}\n"
                              f"# Expected {symbol} = {expected} in active production policy; run_tests reports the result.\n")
        return Case(kind, f"The {service} configuration regression test is failing. Investigate the synthetic files, fix the active policy with the smallest safe edit, rerun its test, and report the outcome.",
                    files, target=path, secondary=decoy, symbol=symbol, original_value=value,
                    expected_value=expected, test_target=test_target)
    if kind == "moved_runbook":
        retries = rng.choice((1, 2, 3, 4))
        old = f"docs/{service}/retry-v1.md"
        active = f"docs/{service}/runbook-active.md"
        legacy = f"docs/archive/{service}-retry.md"
        files[active] = f"# ACTIVE {service} on-call runbook\nFor HTTP 503, allow at most {retries} retries.\n"
        files[legacy] = f"# RETIRED {service} HTTP 503 retry policy\nLegacy limit: {retries + 3} retries.\n"
        return Case(kind, f"An old link to {old} is broken. Locate the active {service} HTTP 503 retry runbook and report the current retry limit. Do not rely on archived guidance.",
                    files, target=active, secondary=legacy, old_path=old, expected_value=retries)
    if kind == "transient_read":
        incident = f"INC-{rng.randrange(200, 990)}-{rng.randrange(10, 99)}"
        target = f"docs/incidents/{service}-current.md"
        files[target] = f"# Synthetic incident\nService: {service}\nIncident identifier: {incident}\n"
        count = 1 + rng.randrange(2)
        return Case(kind, f"Read {target} and report its incident identifier. Handle temporary read errors if they occur.",
                    files, target=target, expected_value=incident, injected_failures=count)
    if kind == "environment_disambiguation":
        staging = f"src/{service}/staging_policy.py"
        files[staging] = (f"# STAGING ONLY\nENVIRONMENT = 'staging'\n{symbol} = {distractor}\n")
        return Case(kind, f"The {service} {symbol} differs by environment. What is the effective production value? Distinguish it from staging and cite the production file.",
                    files, target=path, secondary=staging, symbol=symbol, expected_value=value)
    return Case(kind, "Without using repository tools, explain briefly why time-to-first-token (TTFT) is different from end-to-end task latency.", files)


class InMemoryRepo:
    """An allowlisted interpreter over a private dictionary; no filesystem API."""

    def __init__(self, case: Case):
        self.case = case
        self.files = dict(case.files)
        self.events: list[Event] = []
        self.remaining_failures = case.injected_failures

    def execute(self, name: str, raw_arguments: Any) -> dict[str, Any]:
        keys = SCHEMAS.get(name)
        if keys is None:
            self.events.append(Event("unknown_tool", "rejected"))
            return {"error": "unknown_tool"}
        if not isinstance(raw_arguments, str) or len(raw_arguments) > 2048:
            args = None
        else:
            try:
                args = json.loads(raw_arguments)
            except (ValueError, TypeError):
                args = None
        if (not isinstance(args, dict) or set(args) != set(keys) or
                any(not isinstance(args[k], str) or len(args[k]) > 256 for k in keys)):
            self.events.append(Event(name, "invalid_arguments"))
            return {"error": "invalid_arguments"}
        if name == "list_files":
            directory = args["directory"].strip().strip("/")
            if directory == ".":
                directory = ""
            elif directory.startswith("./"):
                directory = directory[2:]
            if ".." in directory.split("/") or directory.startswith("~"):
                self.events.append(Event(name, "rejected"))
                return {"error": "invalid_directory"}
            matches = tuple(sorted(p for p in self.files if not directory or p.startswith(directory + "/")))
            self.events.append(Event(name, "ok", matches=matches))
            return {"paths": list(matches[:48]), "truncated": len(matches) > 48}
        if name == "search_repository":
            query = args["query"].strip().lower()
            if not query:
                self.events.append(Event(name, "invalid_arguments"))
                return {"error": "empty_query"}
            matches = tuple(sorted(p for p, data in self.files.items()
                                   if query in p.lower() or query in data.lower()))
            self.events.append(Event(name, "ok", matches=matches))
            return {"paths": list(matches[:48]), "truncated": len(matches) > 48}
        if name == "read_file":
            path = args["path"]
            if path == self.case.target and self.case.kind == "transient_read" and self.remaining_failures:
                self.remaining_failures -= 1
                self.events.append(Event(name, "temporary_unavailable", path))
                return {"error": "temporary_unavailable", "retryable": True}
            if path not in self.files:
                self.events.append(Event(name, "not_found", path))
                return {"error": "file_not_found", "path": path}
            self.events.append(Event(name, "ok", path))
            return {"path": path, "content": self.files[path]}
        if name == "run_tests":
            target = args["target"]
            if target != self.case.test_target or self.case.kind != "repair_regression":
                self.events.append(Event(name, "not_found", target))
                return {"error": "unknown_test_target"}
            expected_line = f"{self.case.symbol} = {self.case.expected_value}"
            passed = expected_line in self.files[self.case.target]
            self.events.append(Event(name, "pass" if passed else "fail", target))
            return {"target": target, "status": "PASS" if passed else "FAIL",
                    "details": f"expected {self.case.symbol} = {self.case.expected_value}"}
        # For replace_text we accept exactly one *generated* single-line assignment.
        path, old, new = args["path"], args["old"].rstrip("\n"), args["new"].rstrip("\n")
        allowed = (self.case.kind == "repair_regression" and path == self.case.target and
                   old == f"{self.case.symbol} = {self.case.original_value}" and
                   new == f"{self.case.symbol} = {self.case.expected_value}")
        if not allowed or old not in self.files[path]:
            self.events.append(Event(name, "rejected"))
            return {"error": "edit_not_allowed_or_stale"}
        self.files[path] = self.files[path].replace(old, new, 1)
        self.events.append(Event(name, "ok", path))
        return {"status": "updated_in_memory_only", "path": path}


def _sequence(events: list[Event], *steps: tuple[str, str, str | None]) -> bool:
    index = 0
    for name, outcome, path in steps:
        while index < len(events) and not (events[index].name == name and
              events[index].outcome == outcome and (path is None or events[index].path == path)):
            index += 1
        if index == len(events):
            return False
        index += 1
    return True


def _num(answer: str, number: int) -> bool:
    return re.search(r"(?<!\w)" + re.escape(str(number)) + r"(?!\w)", answer) is not None


def _discovery_failure(events: list[Event], target: str) -> str | None:
    """Require the discovery that actually returned the target to precede a read."""
    discoveries = [i for i, e in enumerate(events)
                   if e.name in {"list_files", "search_repository"}
                   and e.outcome == "ok" and target in e.matches]
    reads = [i for i, e in enumerate(events)
             if e.name == "read_file" and e.outcome == "ok" and e.path == target]
    if not discoveries:
        return "missing_discovery"
    if not reads:
        return "missing_authoritative_read"
    if min(discoveries) >= max(reads):
        return "discovery_after_read"
    return None


def grade(case: Case, repo: InMemoryRepo, final: str) -> tuple[bool, str]:
    answer = final.lower().strip()
    if not answer:
        return False, "empty_final"
    ev = repo.events
    if case.kind in {"symbol_origin", "moved_runbook"}:
        # A known-broken old link need not be opened; either discovery tool works.
        failure = _discovery_failure(ev, case.target)
        if failure:
            return False, failure
        if case.target not in answer:
            return False, "missing_active_path"
        if case.kind == "moved_runbook" and "503" not in answer:
            return False, "missing_http_status"
        if not _num(answer, case.expected_value):
            return False, "missing_expected_integer"
        ok = True
    elif case.kind == "repair_regression":
        # Either inspecting the source or running the failing test may happen first;
        # only require that both precede the change, and a PASS follows it.
        path_a = _sequence(ev, ("run_tests", "fail", case.test_target),
                           ("read_file", "ok", case.target),
                           ("replace_text", "ok", case.target),
                           ("run_tests", "pass", case.test_target))
        path_b = _sequence(ev, ("read_file", "ok", case.target),
                           ("run_tests", "fail", case.test_target),
                           ("replace_text", "ok", case.target),
                           ("run_tests", "pass", case.test_target))
        ok = (path_a or path_b) and ("pass" in answer or "fixed" in answer or "success" in answer)
    elif case.kind == "transient_read":
        errors = [e for e in ev if e.name == "read_file" and e.outcome == "temporary_unavailable" and e.path == case.target]
        ok = (len(errors) == case.injected_failures and
              _sequence(ev, *( [("read_file", "temporary_unavailable", case.target)] * case.injected_failures +
                                [("read_file", "ok", case.target)])) and str(case.expected_value).lower() in answer)
    elif case.kind == "environment_disambiguation":
        ok = _sequence(ev, ("read_file", "ok", case.secondary), ("read_file", "ok", case.target)) or _sequence(
            ev, ("read_file", "ok", case.target), ("read_file", "ok", case.secondary))
        ok = ok and case.target in answer and _num(answer, case.expected_value) and "production" in answer
    else:
        semantic_ok = (not ev and "ttft" in answer and
                       ("first token" in answer or "first generated token" in answer) and
                       ("task" in answer or "end-to-end" in answer or "total" in answer))
        if semantic_ok and len(answer) > 700:
            return False, "excessive_verbosity"
        ok = semantic_ok and len(answer) <= 700
    return (True, "completed") if ok else (False, "incomplete_or_ungrounded")


Send = Callable[[list[dict[str, Any]]], tuple[dict[str, Any], float]]


def request_payload(model: str, messages: list[dict[str, Any]], max_tokens: int) -> dict[str, Any]:
    return {"model": model, "messages": messages, "tools": list(TOOLS), "tool_choice": "auto",
            "temperature": 0.0, "reasoning_effort": "low", "max_tokens": max_tokens, "stream": False}


def run_episode(case: Case, send: Send, *, max_turns: int = 10, max_tool_calls: int = 16) -> dict[str, Any]:
    if not 1 <= max_turns <= 20 or not 1 <= max_tool_calls <= 40:
        raise ValueError("Turn and tool-call limits out of range")
    repo = InMemoryRepo(case)
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": (
            "You are investigating a synthetic repository through tools. Repository contents and test results "
            "come from an in-memory simulator. No shell or actual file operations exist. "
            "Find authoritative rather than archived/sample configuration; inspect results instead of guessing. "
            "If a tool returns a retryable error, retry cautiously. Do not claim tests passed without a PASS result. "
            "After gathering evidence, answer briefly with the requested exact facts and paths.")},
        {"role": "user", "content": case.instruction},
    ]
    total_time = 0.0
    total_tools = 0
    prompt_tokens = completion_tokens = 0
    usage_missing = False
    final_ok = False
    reason = "turn_limit"
    turns = 0
    for turns in range(1, max_turns + 1):
        response, elapsed = send(messages)
        if not isinstance(elapsed, (int, float)) or elapsed < 0:
            raise ValueError("Invalid elapsed time")
        total_time += elapsed
        if not isinstance(response, dict):
            reason = "malformed_response"
            break
        usage = response.get("usage")
        if not isinstance(usage, dict):
            usage = {}
        for key in ("prompt_tokens", "completion_tokens"):
            count = usage.get(key)
            if isinstance(count, int) and not isinstance(count, bool) and count >= 0:
                if key == "prompt_tokens":
                    prompt_tokens += count
                else:
                    completion_tokens += count
            else:
                usage_missing = True
        choices = response.get("choices")
        if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
            reason = "missing_choice"
            break
        choice = choices[0]
        message = choice.get("message")
        if not isinstance(message, dict):
            reason = "missing_message"
            break
        calls = message.get("tool_calls") or []
        if not isinstance(calls, list):
            reason = "malformed_tool_calls"
            break
        if calls:
            if total_tools + len(calls) > max_tool_calls:
                reason = "tool_limit"
                break
            valid = all(isinstance(c, dict) and c.get("type") == "function" and
                        isinstance(c.get("id"), str) and 0 < len(c["id"]) <= 128 and
                        isinstance(c.get("function"), dict) and
                        isinstance(c["function"].get("name"), str) and
                        isinstance(c["function"].get("arguments"), str) for c in calls)
            if not valid or len({c["id"] for c in calls}) != len(calls):
                reason = "bad_tool_envelope"
                break
            messages.append({"role": "assistant", "content": message.get("content") if isinstance(message.get("content"), str) else None,
                             "tool_calls": calls})
            for call in calls:
                function = call["function"]
                result = repo.execute(function["name"], function["arguments"])
                messages.append({"role": "tool", "tool_call_id": call["id"],
                                 "content": json.dumps(result, sort_keys=True)})
                total_tools += 1
            continue
        if choice.get("finish_reason") not in ("stop", None):
            reason = "nonfinal_finish_reason"
            break
        final = message.get("content")
        final_ok, reason = grade(case, repo, final if isinstance(final, str) else "")
        break
    trace = [e.name + ":" + e.outcome for e in repo.events]
    return {"case": case.kind, "ok": bool(final_ok), "reason": reason,
            "scorer_version": SCORER_VERSION, "protocol_version": PROTOCOL_VERSION,
            "turns": turns, "tool_calls": total_tools,
            "tool_errors": sum(e.outcome in {"invalid_arguments", "rejected", "not_found", "temporary_unavailable"} for e in repo.events),
            "recovered": bool(final_ok and case.kind in {"moved_runbook", "transient_read"}),
            "trace": trace, "elapsed_s": round(total_time, 4),
            "prompt_tokens": None if usage_missing else prompt_tokens,
            "completion_tokens": None if usage_missing else completion_tokens}


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    def metric(group: list[dict[str, Any]], field: str, percentile: float = 0.5) -> float | None:
        nums = sorted(r[field] for r in group if isinstance(r.get(field), (int, float)) and
                      not isinstance(r.get(field), bool))
        if not nums:
            return None
        if percentile == 0.5:
            return round(statistics.median(nums), 4)
        index = (len(nums) - 1) * percentile
        lo, hi = int(index), min(int(index) + 1, len(nums) - 1)
        return round(nums[lo] + (nums[hi] - nums[lo]) * (index - lo), 4)
    cases = {}
    for kind in KINDS:
        group = [r for r in rows if r["case"] == kind]
        cases[kind] = {"passed": sum(bool(r["ok"]) for r in group), "total": len(group),
                       "median_elapsed_s": metric(group, "elapsed_s"), "p90_elapsed_s": metric(group, "elapsed_s", .9),
                       "median_turns": metric(group, "turns"), "median_tool_calls": metric(group, "tool_calls"),
                       "median_prompt_tokens": metric(group, "prompt_tokens"),
                       "median_completion_tokens": metric(group, "completion_tokens"),
                       "recoveries": sum(bool(r.get("recovered")) for r in group)}
    return {"schema_version": 1, "suite": "agent-generalization",
            "scorer_version": SCORER_VERSION, "protocol_version": PROTOCOL_VERSION,
            "failure_reasons": dict(sorted(Counter(r.get("reason", "unspecified")
                                                   for r in rows if not r["ok"]).items())),
            "passed": sum(bool(r["ok"]) for r in rows),
            "total": len(rows), "pass_rate": round(sum(bool(r["ok"]) for r in rows) / len(rows), 4) if rows else None,
            "median_elapsed_s": metric(rows, "elapsed_s"), "p90_elapsed_s": metric(rows, "elapsed_s", .9),
            "cases": cases, "note": "Seed-varying public synthetic fixtures; no real code, shell, host reads, or tests executed."}


def run_live(*, model: str, base_url: str, runs: int, seed: int | None, results_dir: Path,
             max_turns: int = 10, max_tokens: int = 1024, timeout: int = 600) -> tuple[Path, dict[str, Any]]:
    from .client import APIError, VLLMClient
    from .report import new_run_dir
    if not 1 <= runs <= 10 or not 128 <= max_tokens <= 4096 or not 1 <= max_turns <= 20:
        raise ValueError("Invalid --runs, --max-tokens or --max-turns")
    if seed is None:
        seed = secrets.randbits(63)
    if not 0 <= seed < 2**63:
        raise ValueError("Seed must be a nonnegative 63-bit integer")
    client = VLLMClient(base_url, model, timeout)
    if not client.health() or not any(m.get("id") == model for m in client.models()):
        raise ValueError("Requested model is not healthy/available")
    dest = new_run_dir(results_dir, "agent-generalization")
    metadata = {"timestamp_utc": datetime.now(timezone.utc).isoformat(), "model": model,
                "suite": "agent-generalization", "seed": seed, "runs": runs,
                "scorer_version": SCORER_VERSION, "protocol_version": PROTOCOL_VERSION,
                "implementation_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                "scenario_count": len(KINDS), "max_turns": max_turns, "max_tokens": max_tokens,
                "simulated_only": True, "real_tool_execution": False}
    (dest / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    print(f"Seed: {seed} (save to reproduce)", flush=True)
    rows = []
    with (dest / "samples.jsonl").open("w", encoding="utf-8") as stream:
        for repetition in range(1, runs + 1):
            for kind in KINDS:
                scenario = generate(kind, episode_seed(seed, kind, repetition))
                def send(messages: list[dict[str, Any]]) -> tuple[dict[str, Any], float]:
                    start = time.monotonic()
                    with client._request("/v1/chat/completions", request_payload(model, messages, max_tokens)) as response:
                        data = json.load(response)
                    return data, time.monotonic() - start
                started = time.monotonic()
                try:
                    row = run_episode(scenario, send, max_turns=max_turns)
                except (APIError, OSError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
                    row = {"case": kind, "ok": False, "reason": "request_error", "error_type": type(exc).__name__,
                           "turns": 0, "tool_calls": 0, "tool_errors": 0, "recovered": False,
                           "trace": [], "elapsed_s": round(time.monotonic() - started, 4),
                           "prompt_tokens": None, "completion_tokens": None}
                row.update(repetition=repetition, scorer_version=SCORER_VERSION,
                           protocol_version=PROTOCOL_VERSION)
                rows.append(row)
                stream.write(json.dumps(row, sort_keys=True) + "\n")
                stream.flush()
                print(f"  {kind} run={repetition}: {'PASS' if row['ok'] else 'FAIL'} "
                      f"({row['reason']}, {row['turns']} turns, {row['tool_calls']} tools, {row['elapsed_s']}s)", flush=True)
    stats = summarize(rows)
    (dest / "summary.json").write_text(json.dumps(stats, indent=2) + "\n", encoding="utf-8")
    lines = ["# Seed-varying simulated-agent generalization", "",
             "**No model-generated shell commands, code or real tests were executed.**", "",
             f"- Seed: `{seed}` (saved for replay; generated answer keys are not sent to the model)",
             f"- Scorer: `{SCORER_VERSION}`; protocol: `{PROTOCOL_VERSION}`",
             f"- Completed: **{stats['passed']}/{stats['total']}** ({stats['pass_rate']:.1%})",
             "- Failure reasons: " + (", ".join(f"{reason}: {count}" for reason, count in
                                                stats["failure_reasons"].items()) or "none"),
             f"- Median episode latency: **{stats['median_elapsed_s']:.2f}s**", "",
             "| Scenario | Passed | Total | Median turns | Median tools | Median prompt tokens | Median completion tokens | Median latency |",
             "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for name, c in stats["cases"].items():
        def fmt(value: Any) -> str:
            return "n/a" if value is None else str(value)
        lines.append(f"| `{name}` | {c['passed']} | {c['total']} | {fmt(c['median_turns'])} | "
                     f"{fmt(c['median_tool_calls'])} | {fmt(c['median_prompt_tokens'])} | "
                     f"{fmt(c['median_completion_tokens'])} | {fmt(c['median_elapsed_s'])}s |")
    lines += ["", "All tool results are simulated; pass criteria combine evidence order, hidden fixture state, and final-answer heuristics.",
              "These are fresh seed-derived *variants* of public task templates, not independent unseen real-world tasks.",
              "Results are gitignored, with no raw prompts, tool arguments or answer text persisted."]
    (dest / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return dest, stats


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=os.getenv("THOR_BENCH_BASE_URL", "http://127.0.0.1:8000"))
    parser.add_argument("--model", default=os.getenv("THOR_BENCH_MODEL", "Qwen3.8-Flash-Next"))
    parser.add_argument("--runs", type=int, default=1, help="Different synthetic variants per family")
    parser.add_argument("--seed", type=int, default=None, help="Fixed seed for reproducibility (default: random)")
    parser.add_argument("--max-turns", type=int, default=10)
    parser.add_argument("--max-tokens", type=int, default=1024)
    parser.add_argument("--timeout", type=int, default=600)
    parser.add_argument("--results-dir", type=Path, default=Path("results"))
    args = parser.parse_args(argv)
    try:
        path, stats = run_live(model=args.model, base_url=args.base_url, runs=args.runs,
                               seed=args.seed, results_dir=args.results_dir,
                               max_turns=args.max_turns, max_tokens=args.max_tokens, timeout=args.timeout)
    except (ValueError, OSError) as exc:
        print(f"Benchmark setup failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    print(f"Report: {path / 'summary.md'}")
    return 0 if stats["passed"] == stats["total"] else 1


if __name__ == "__main__":
    sys.exit(main())
