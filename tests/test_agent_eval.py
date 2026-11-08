"""Offline scripted checks; no server, Docker, shell or model endpoint is used."""
import json
import unittest
from pathlib import Path
import io
import tempfile
from unittest.mock import patch

from thorbench.agent_eval import (TASKS, FIXTURES, SimulatedRepository, grade,
                                  request_payload, run_episode, run_live, summarize)


def tool(name, arguments, index=1):
    return {"id": f"call-{index}", "type": "function", "function": {
        "name": name, "arguments": json.dumps(arguments)}}


def response(*calls, text=None, usage=True):
    return {"choices": [{"finish_reason": "tool_calls" if calls else "stop",
                         "message": {"role": "assistant", "content": text,
                                     "tool_calls": list(calls)}}],
            "usage": {"prompt_tokens": 120, "completion_tokens": 25} if usage else {}}


class ScriptedModel:
    def __init__(self, *responses):
        self.responses = list(responses)
        self.messages_seen = []

    def __call__(self, messages):
        self.messages_seen.append(json.loads(json.dumps(messages)))
        if not self.responses:
            raise AssertionError("Unexpected extra model request")
        return self.responses.pop(0), 0.5


def run(task_id, *responses, max_turns=8):
    task = next(t for t in TASKS if t.id == task_id)
    model = ScriptedModel(*responses)
    result = run_episode(task, model, max_turns=max_turns)
    return result, model


class MultiTurnAgentTests(unittest.TestCase):
    def test_investigate_then_ground_final(self):
        r, model = run("trace_symbol",
                       response(tool("search_repository", {"query": "CACHE_TTL_SECONDS"})),
                       response(tool("read_file", {"path": "src/cache_policy.py"})),
                       response(text="src/cache_policy.py defines CACHE_TTL_SECONDS = 30."))
        self.assertTrue(r["ok"], r)
        self.assertEqual(r["turns"], 3)
        self.assertEqual(r["tool_calls"], 2)
        self.assertEqual(r["prompt_tokens"], 360)
        self.assertEqual(r["completion_tokens"], 75)
        # The next request contains the assistant tool call and its matching response.
        self.assertEqual(model.messages_seen[1][-2]["role"], "assistant")
        self.assertEqual(model.messages_seen[1][-1]["tool_call_id"], "call-1")
        self.assertEqual(model.messages_seen[1][-1]["role"], "tool")

    def test_hallucinated_answer_is_not_task_completion(self):
        r, _ = run("trace_symbol", response(text="src/cache_policy.py contains TTL 30."))
        self.assertFalse(r["ok"])
        self.assertEqual(r["reason"], "task_incomplete_or_ungrounded")

    def test_repair_requires_failed_test_then_edit_then_pass(self):
        r, model = run("repair_failing_test",
                       response(tool("run_tests", {"target": "tests/test_cache_policy.py"})),
                       response(tool("read_file", {"path": "src/cache_policy.py"})),
                       response(tool("replace_text", {"path": "src/cache_policy.py",
                                                      "old": "CACHE_TTL_SECONDS = 30",
                                                      "new": "CACHE_TTL_SECONDS = 60"})),
                       response(tool("run_tests", {"target": "tests/test_cache_policy.py"})),
                       response(text="The cache policy tests now PASS."))
        self.assertTrue(r["ok"], r)
        self.assertIn("run_tests:fail", r["trace"])
        self.assertIn("run_tests:pass", r["trace"])
        self.assertEqual(model.messages_seen[1][-1]["role"], "tool")
        self.assertEqual(json.loads(model.messages_seen[1][-1]["content"])["status"], "FAIL")
        self.assertEqual(json.loads(model.messages_seen[-1][-1]["content"])["status"], "PASS")

    def test_repair_without_rerun_is_not_complete(self):
        r, _ = run("repair_failing_test",
                   response(tool("run_tests", {"target": "tests/test_cache_policy.py"})),
                   response(tool("replace_text", {"path": "src/cache_policy.py",
                                                  "old": "CACHE_TTL_SECONDS = 30",
                                                  "new": "CACHE_TTL_SECONDS = 60"})),
                   response(text="Success! Everything passes."))
        self.assertFalse(r["ok"])

    def test_missing_doc_recovery(self):
        r, model = run("missing_document_recovery",
                       response(tool("read_file", {"path": "docs/cache-v1.md"})),
                       response(tool("search_repository", {"query": "retry"})),
                       response(tool("read_file", {"path": "docs/cache-runbook.md"})),
                       response(text="HTTP 503 allows at most 2 retries."))
        self.assertTrue(r["ok"], r)
        self.assertTrue(r["recovered"])
        self.assertEqual(r["tool_errors"], 1)
        self.assertEqual(json.loads(model.messages_seen[1][-1]["content"])["error"], "file_not_found")

    def test_retry_transient_error(self):
        r, model = run("transient_error_recovery",
                       response(tool("read_file", {"path": "docs/incident.md"})),
                       response(tool("read_file", {"path": "docs/incident.md"})),
                       response(text="The incident is INC-42."))
        self.assertTrue(r["ok"], r)
        self.assertTrue(r["recovered"])
        self.assertEqual(r["tool_errors"], 1)
        self.assertTrue(json.loads(model.messages_seen[1][-1]["content"])["retryable"])

    def test_refusing_to_retry_fails(self):
        r, _ = run("transient_error_recovery",
                   response(tool("read_file", {"path": "docs/incident.md"})),
                   response(text="The incident is INC-42."))
        self.assertFalse(r["ok"])

    def test_negative_control_and_violation(self):
        r, _ = run("no_tool_needed", response(text="TTFT is time to first token."))
        self.assertTrue(r["ok"])
        r, _ = run("no_tool_needed",
                   response(tool("search_repository", {"query": "TTFT"})),
                   response(text="TTFT is time to first token."))
        self.assertFalse(r["ok"])

    def test_simulator_rejects_path_traversal_and_arbitrary_edits(self):
        repo = SimulatedRepository(TASKS[1])
        before = dict(repo.files)
        self.assertEqual(repo.execute("read_file", '{"path":"../../etc/passwd"}')["error"], "file_not_found")
        self.assertEqual(repo.execute("replace_text", json.dumps({
            "path": "/tmp/file", "old": "x", "new": "y"}))["error"], "edit_not_allowed_or_stale")
        self.assertEqual(repo.execute("replace_text", json.dumps({
            "path": "src/cache_policy.py", "old": "CACHE_TTL_SECONDS = 30", "new": "import os"}))["error"],
            "edit_not_allowed_or_stale")
        self.assertEqual(repo.files, before)
        self.assertEqual(FIXTURES, before)

    def test_simulator_cannot_execute_model_shell_tool(self):
        repo = SimulatedRepository(TASKS[0])
        self.assertEqual(repo.execute("run_shell", '{"command":"rm -rf /"}')["error"], "unknown_tool")
        self.assertEqual(repo.execute("run_tests", '{"target":"../../etc/passwd"}')["error"], "unknown_test_target")
        self.assertEqual(repo.execute("search_repository", '{"query":"","other":"z"}')["error"],
                         "invalid_arguments")

    def test_missing_invalid_json_is_tool_error_not_execution(self):
        repo = SimulatedRepository(TASKS[0])
        self.assertEqual(repo.execute("read_file", '{bad json')["error"], "invalid_arguments")
        self.assertEqual(repo.execute("read_file", "x" * 3000)["error"], "invalid_arguments")

    def test_multiple_tools_in_one_turn_keep_ids(self):
        m = ScriptedModel(response(
            tool("search_repository", {"query": "CACHE_TTL_SECONDS"}, 1),
            tool("read_file", {"path": "src/cache_policy.py"}, 2)),
            response(text="The value 30 is set in src/cache_policy.py."))
        r = run_episode(TASKS[0], m)
        self.assertTrue(r["ok"], r)
        self.assertEqual([x["tool_call_id"] for x in m.messages_seen[-1][-2:]], ["call-1", "call-2"])

    def test_invalid_duplicate_call_ids(self):
        r, _ = run("trace_symbol", response(tool("read_file", {"path": "src/cache_policy.py"}, 1),
                                            tool("read_file", {"path": "src/cache_policy.py"}, 1)))
        self.assertFalse(r["ok"])
        self.assertEqual(r["reason"], "invalid_tool_call_envelope")

    def test_tool_limit_enforced(self):
        model = ScriptedModel(response(tool("read_file", {"path": "src/cache_policy.py"}, 1),
                                       tool("read_file", {"path": "src/cache_policy.py"}, 2)))
        result = run_episode(TASKS[0], model, max_tool_calls=1)
        self.assertEqual(result["reason"], "tool_call_limit")
        self.assertEqual(result["tool_calls"], 0)

    def test_turn_limit_enforced(self):
        r, _ = run("trace_symbol", response(tool("search_repository", {"query": "ttl"})), max_turns=1)
        self.assertEqual(r["reason"], "turn_limit")
        self.assertFalse(r["ok"])

    def test_private_reports_have_no_raw_content(self):
        r, _ = run("trace_symbol", response(tool("read_file", {"path": "../../super-secret"})),
                   response(text="My secret completion: PRIVATE CANARY"))
        dumped = json.dumps(r)
        self.assertNotIn("../../super-secret", dumped)
        self.assertNotIn("PRIVATE CANARY", dumped)
        self.assertNotIn("cache_expired", dumped)

    def test_live_report_path_offline_with_mocked_model(self):
        """Exercise the full report-writing path without contacting any server."""
        steps = {
            "trace_symbol": [
                response(tool("search_repository", {"query": "CACHE_TTL_SECONDS"})),
                response(tool("read_file", {"path": "src/cache_policy.py"})),
                response(text="src/cache_policy.py sets CACHE_TTL_SECONDS = 30.")],
            "repair_failing_test": [
                response(tool("run_tests", {"target": "tests/test_cache_policy.py"})),
                response(tool("read_file", {"path": "src/cache_policy.py"})),
                response(tool("replace_text", {"path": "src/cache_policy.py",
                                               "old": "CACHE_TTL_SECONDS = 30\n",
                                               "new": "CACHE_TTL_SECONDS = 60\n"})),
                response(tool("run_tests", {"target": "tests/test_cache_policy.py"})),
                response(text="Tests PASS after the simulated fix.")],
            "missing_document_recovery": [
                response(tool("read_file", {"path": "docs/cache-v1.md"})),
                response(tool("search_repository", {"query": "retry"})),
                response(tool("read_file", {"path": "docs/cache-runbook.md"})),
                response(text="HTTP 503 permits two retries.")],
            "transient_error_recovery": [
                response(tool("read_file", {"path": "docs/incident.md"})),
                response(tool("read_file", {"path": "docs/incident.md"})),
                response(text="Incident INC-42.")],
            "no_tool_needed": [response(text="TTFT means time to first token.")],
        }

        class FakeClient:
            def __init__(self, base_url, model, timeout):
                self.model = model

            def health(self):
                return True

            def models(self):
                return [{"id": self.model}]

            def _request(self, path, payload):
                self_instance = self
                task = next(t for t in TASKS if t.instruction == payload["messages"][1]["content"])
                step = sum(m["role"] == "assistant" for m in payload["messages"])
                return io.BytesIO(json.dumps(steps[task.id][step]).encode())

        with tempfile.TemporaryDirectory() as directory:
            with patch("thorbench.client.VLLMClient", FakeClient):
                path, stats = run_live(model="mock", base_url="http://127.0.0.1:8000",
                                       runs=1, results_dir=Path(directory))
            self.assertEqual(stats["passed"], 5)
            rows = [json.loads(line) for line in (path / "samples.jsonl").read_text().splitlines()]
            self.assertEqual(len(rows), 5)
            self.assertTrue(all("trace" in row for row in rows))
            self.assertIn("5/5", (path / "summary.md").read_text())
            for file in path.iterdir():
                data = file.read_text()
                self.assertNotIn("CACHE_TTL_SECONDS = 60\n", data)
                self.assertNotIn("Synthetic incident", data)
                self.assertNotIn("The model says secret", data)

    def test_request_contract_and_summary(self):
        payload = request_payload("Qwen3.8-Flash-Next", [{"role": "user", "content": "test"}], 512)
        self.assertEqual(payload["tool_choice"], "auto")
        self.assertFalse(payload["stream"])
        self.assertEqual(len(payload["tools"]), 4)
        rows = [{"case": "trace_symbol", "ok": True, "elapsed_s": 1.0, "turns": 3,
                 "tool_calls": 2, "recovered": False, "prompt_tokens": 500, "completion_tokens": 100},
                {"case": "trace_symbol", "ok": False, "elapsed_s": 2.0, "turns": 4,
                 "tool_calls": 3, "recovered": False, "prompt_tokens": 600, "completion_tokens": 120}]
        summary = summarize(rows)
        self.assertEqual(summary["passed"], 1)
        self.assertEqual(summary["total"], 2)
        self.assertEqual(summary["case_results"]["trace_symbol"]["median_prompt_tokens"], 550)
        self.assertEqual(summary["case_results"]["trace_symbol"]["median_completion_tokens"], 110)


if __name__ == "__main__":
    unittest.main()
