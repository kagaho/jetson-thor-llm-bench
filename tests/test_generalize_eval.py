"""Offline quality, safety and protocol tests for seed-varying generalization."""
import io
import json
import re
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from thorbench.generalize_eval import (
    KINDS, TOOLS, InMemoryRepo, episode_seed, generate, grade,
    request_payload, run_episode, run_live, summarize,
)


def call(name, args, number=0):
    return {"type": "function", "id": f"call-{number}",
            "function": {"name": name, "arguments": json.dumps(args)}}


def reply(*tools, text=None):
    return {"choices": [{"finish_reason": "tool_calls" if tools else "stop",
                         "message": {"role": "assistant", "content": text,
                                     "tool_calls": list(tools)}}],
            "usage": {"prompt_tokens": 150, "completion_tokens": 40}}


class Scripted:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.history = []

    def __call__(self, messages):
        self.history.append(json.loads(json.dumps(messages)))
        return next(self.responses), .25


def scripted_success(case):
    if case.kind == "symbol_origin":
        return [reply(call("search_repository", {"query": case.symbol})),
                reply(call("read_file", {"path": case.target})),
                reply(text=f"Active value: {case.expected_value} in {case.target}.")]
    if case.kind == "repair_regression":
        return [reply(call("run_tests", {"target": case.test_target})),
                reply(call("read_file", {"path": case.target})),
                reply(call("replace_text", {"path": case.target,
                                            "old": f"{case.symbol} = {case.original_value}",
                                            "new": f"{case.symbol} = {case.expected_value}"})),
                reply(call("run_tests", {"target": case.test_target})),
                reply(text="Simulated test PASS after edit.")]
    if case.kind == "moved_runbook":
        return [reply(call("read_file", {"path": case.old_path})),
                reply(call("search_repository", {"query": "HTTP 503"})),
                reply(call("read_file", {"path": case.target})),
                reply(text=f"Active runbook: {case.target}. Current HTTP 503 limit: {case.expected_value} retries.")]
    if case.kind == "transient_read":
        return [reply(call("read_file", {"path": case.target}, i)) for i in range(case.injected_failures + 1)] + [reply(text=f"Incident {case.expected_value}.")]
    if case.kind == "environment_disambiguation":
        return [reply(call("read_file", {"path": case.secondary})),
                reply(call("read_file", {"path": case.target})),
                reply(text=f"Production {case.expected_value} in {case.target}, not staging.")]
    return [reply(text="TTFT is time to first token; total end-to-end task latency includes all work.")]


class GeneratorTests(unittest.TestCase):
    def test_seeds_reproducible_independent_of_python_hash(self):
        self.assertEqual(episode_seed(808, "symbol_origin", 1), episode_seed(808, "symbol_origin", 1))
        self.assertNotEqual(episode_seed(808, "symbol_origin", 1), episode_seed(808, "symbol_origin", 2))
        self.assertNotEqual(episode_seed(808, "symbol_origin", 1), episode_seed(809, "symbol_origin", 1))
        self.assertNotEqual(episode_seed(808, "symbol_origin", 1), episode_seed(808, "no_tool_needed", 1))

    def test_generator_variants_and_no_private_paths(self):
        for kind in KINDS:
            case = generate(kind, episode_seed(808, kind, 1))
            same = generate(kind, episode_seed(808, kind, 1))
            self.assertEqual(case, same)
            self.assertIn("README.md", case.files)
            self.assertTrue(all(not path.startswith("/") and ".." not in path for path in case.files))
        values = {generate("symbol_origin", episode_seed(seed, "symbol_origin", 1)).target for seed in range(10)}
        self.assertGreater(len(values), 3)

    def test_input_prompt_does_not_leak_oracle(self):
        for kind in ("symbol_origin", "moved_runbook", "environment_disambiguation"):
            case = generate(kind, episode_seed(2222, kind, 1))
            self.assertIsNone(re.search(r"(?<!\w)" + re.escape(str(case.expected_value)) + r"(?!\w)", case.instruction))

    def test_invalid_seed(self):
        for seed in (-1, 2**63):
            with self.assertRaises(ValueError):
                episode_seed(seed, "symbol_origin", 1)


class SimulatorSafetyTests(unittest.TestCase):
    def setUp(self):
        self.case = generate("repair_regression", episode_seed(4321, "repair_regression", 1))
        self.repo = InMemoryRepo(self.case)

    def test_all_tools_are_simulated_and_schema_allowlisted(self):
        self.assertEqual(len(TOOLS), 5)
        original = dict(self.repo.files)
        self.assertEqual(self.repo.execute("shell", '{"command":"whoami"}')["error"], "unknown_tool")
        self.assertEqual(self.repo.execute("read_file", '{"path":"../../etc/passwd"}')["error"], "file_not_found")
        self.assertEqual(self.repo.execute("list_files", '{"directory":"../.."}')["error"], "invalid_directory")
        self.assertEqual(self.repo.execute("replace_text", '{"path":"../../etc/passwd","old":"x","new":"y"}')["error"], "edit_not_allowed_or_stale")
        self.assertEqual(self.repo.files, original)

    def test_list_root_and_discover_by_listing(self):
        case = generate("symbol_origin", episode_seed(199, "symbol_origin", 1))
        repo = InMemoryRepo(case)
        paths = repo.execute("list_files", '{"directory":"."}')
        self.assertIn(case.target, paths["paths"])
        model = Scripted([reply(call("list_files", {"directory": "."})),
                          reply(call("read_file", {"path": case.target})),
                          reply(text=f"Active setting {case.expected_value} at {case.target}.")])
        self.assertTrue(run_episode(case, model)["ok"])

    def test_cannot_modify_arbitrary_synthetic_files(self):
        for path in (self.case.secondary, "README.md", "/tmp/abs"):
            result = self.repo.execute("replace_text", json.dumps({"path": path, "old": "x", "new": "y"}))
            self.assertEqual(result["error"], "edit_not_allowed_or_stale")
        self.assertIn(f"{self.case.symbol} = {self.case.original_value}", self.repo.files[self.case.target])

    def test_invalid_arguments(self):
        for bad in ('{', '{"path":"README.md","x":"y"}', 'a' * 2500):
            self.assertEqual(self.repo.execute("read_file", bad)["error"], "invalid_arguments")
        self.assertEqual(self.repo.execute("search_repository", '{"query":""}')["error"], "empty_query")

    def test_expected_edit_and_simulated_test(self):
        before = self.repo.execute("run_tests", json.dumps({"target": self.case.test_target}))
        self.assertEqual(before["status"], "FAIL")
        after = self.repo.execute("replace_text", json.dumps({"path": self.case.target,
                       "old": f"{self.case.symbol} = {self.case.original_value}",
                       "new": f"{self.case.symbol} = {self.case.expected_value}"}))
        self.assertEqual(after["status"], "updated_in_memory_only")
        passed = self.repo.execute("run_tests", json.dumps({"target": self.case.test_target}))
        self.assertEqual(passed["status"], "PASS")
        self.assertEqual(self.case.files[self.case.target].splitlines()[-1], f"{self.case.symbol} = {self.case.original_value}")


class EpisodeTests(unittest.TestCase):
    def test_symbol_discovery_must_precede_authoritative_read(self):
        for seed in (1, 54, 4321):
            case = generate("symbol_origin", episode_seed(seed, "symbol_origin", 1))
            for tool, unrelated, discovery in (
                ("list_files", {"directory": "examples"}, {"directory": "src"}),
                ("search_repository", {"query": "README.md"}, {"query": case.symbol}),
            ):
                for reread in (False, True):
                    with self.subTest(seed=seed, tool=tool, reread=reread):
                        responses = [reply(call(tool, unrelated)),
                                     reply(call("read_file", {"path": case.target})),
                                     reply(call(tool, discovery))]
                        if reread:
                            responses.append(reply(call("read_file", {"path": case.target})))
                        responses.append(reply(text=f"{case.target}: {case.expected_value}."))
                        result = run_episode(case, Scripted(responses))
                        self.assertEqual(result["ok"], reread, result)

    def test_runbook_failure_reasons_identify_missing_gate(self):
        for seed in (1, 54, 4321):
            case = generate("moved_runbook", episode_seed(seed, "moved_runbook", 1))
            discovery = reply(call("list_files", {"directory": "."}))
            read = reply(call("read_file", {"path": case.target}))
            answer = f"{case.target}: HTTP 503, {case.expected_value} retries."
            controls = (
                ([read], answer, "missing_discovery"),
                ([discovery, reply(call("read_file", {"path": case.secondary}))],
                 answer, "missing_authoritative_read"),
                ([read, discovery], answer, "discovery_after_read"),
                ([discovery, read], f"HTTP 503, {case.expected_value} retries.", "missing_active_path"),
                ([discovery, read], f"{case.target}: {case.expected_value} retries.", "missing_http_status"),
                ([discovery, read], f"{case.target}: HTTP 503, {case.expected_value + 1} retries.",
                 "missing_expected_integer"),
                ([discovery, read], answer, "completed"),
            )
            for responses, final, reason in controls:
                with self.subTest(seed=seed, reason=reason):
                    result = run_episode(case, Scripted(responses + [reply(text=final)]))
                    self.assertEqual(result["reason"], reason)
                    self.assertEqual(result["ok"], reason == "completed")

    def test_successful_generated_cases(self):
        for seed in (1, 54, 4321):
            for kind in KINDS:
                with self.subTest(seed=seed, kind=kind):
                    case = generate(kind, episode_seed(seed, kind, 1))
                    model = Scripted(scripted_success(case))
                    result = run_episode(case, model)
                    self.assertTrue(result["ok"], result)
                    self.assertEqual(result["prompt_tokens"], 150 * result["turns"])
                    self.assertEqual(result["completion_tokens"], 40 * result["turns"])
                    self.assertNotIn(case.target or "PRIVATE_CANARY", json.dumps(result))

    def test_repair_can_read_source_before_first_failure(self):
        case = self._case("repair_regression")
        model = Scripted([
            reply(call("read_file", {"path": case.target})),
            reply(call("run_tests", {"target": case.test_target})),
            reply(call("replace_text", {"path": case.target,
                "old": f"{case.symbol} = {case.original_value}",
                "new": f"{case.symbol} = {case.expected_value}"})),
            reply(call("run_tests", {"target": case.test_target})),
            reply(text="PASS on rerun after in-memory fix.")])
        self.assertTrue(run_episode(case, model)["ok"])

    def test_moved_runbook_direct_discovery_needs_no_broken_link_read(self):
        case = self._case("moved_runbook")
        model = Scripted([
            reply(call("list_files", {"directory": "."})),
            reply(call("read_file", {"path": case.target})),
            reply(text=f"Active runbook: {case.target}. HTTP 503: {case.expected_value} retries."),
        ])
        result = run_episode(case, model)
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["tool_errors"], 0)

    def test_moved_runbook_search_can_discover_active_file_directly(self):
        case = self._case("moved_runbook")
        model = Scripted([
            reply(call("search_repository", {"query": "HTTP 503"})),
            reply(call("read_file", {"path": case.target})),
            reply(text=f"Active runbook: {case.target}. HTTP 503: {case.expected_value} retries."),
        ])
        self.assertTrue(run_episode(case, model)["ok"])

    def test_moved_runbook_wrong_retry_limit_fails(self):
        case = self._case("moved_runbook")
        model = Scripted([
            reply(call("list_files", {"directory": "."})),
            reply(call("read_file", {"path": case.target})),
            reply(text=f"Active runbook: {case.target}. HTTP 503: {case.expected_value + 1} retries."),
        ])
        self.assertFalse(run_episode(case, model)["ok"])

    def test_moved_runbook_archive_only_and_undiscovered_active_fail(self):
        case = self._case("moved_runbook")
        answer = f"Active runbook: {case.target}. HTTP 503: {case.expected_value} retries."
        archive_only = Scripted([
            reply(call("list_files", {"directory": "."})),
            reply(call("read_file", {"path": case.secondary})),
            reply(text=answer),
        ])
        undiscovered = Scripted([
            reply(call("read_file", {"path": case.target})),
            reply(text=answer),
        ])
        self.assertFalse(run_episode(case, archive_only)["ok"])
        self.assertFalse(run_episode(case, undiscovered)["ok"])

    def test_no_tool_excessive_verbosity_has_distinct_reason(self):
        case = self._case("no_tool_needed")
        answer = ("TTFT is time to first token; end-to-end task latency covers total work. "
                  + "Additional explanation. " * 40)
        self.assertGreater(len(answer), 700)
        self.assertEqual(grade(case, InMemoryRepo(case), answer),
                         (False, "excessive_verbosity"))
        self.assertEqual(grade(case, InMemoryRepo(case),
                               "TTFT is time to first token; end-to-end task latency is total time."),
                         (True, "completed"))

    def test_missing_doc_must_recover(self):
        case = generate("moved_runbook", episode_seed(876, "moved_runbook", 1))
        model = Scripted([reply(call("read_file", {"path": case.old_path})),
                          reply(text=f"HTTP 503: {case.expected_value} retries")])
        result = run_episode(case, model)
        self.assertFalse(result["ok"])
        self.assertEqual(result["tool_errors"], 1)

    def test_cannot_claim_test_passed_without_edit(self):
        case = self._case("repair_regression")
        model = Scripted([reply(call("run_tests", {"target": case.test_target})),
                          reply(text="Test PASS, repaired successfully.")])
        self.assertFalse(run_episode(case, model)["ok"])

    def test_production_must_be_distinguished_from_staging(self):
        case = self._case("environment_disambiguation")
        model = Scripted([reply(call("read_file", {"path": case.target})),
                          reply(text=f"Production {case.expected_value} in {case.target}.")])
        self.assertFalse(run_episode(case, model)["ok"])

    def test_no_tool_negative_control(self):
        case = self._case("no_tool_needed")
        model = Scripted([reply(call("list_files", {"directory": "src"})),
                          reply(text="TTFT is time to first token, not total task latency.")])
        self.assertFalse(run_episode(case, model)["ok"])

    def test_duplicate_call_ids_and_call_limit(self):
        case = self._case("symbol_origin")
        model = Scripted([reply(call("read_file", {"path": case.target}, 1),
                                call("read_file", {"path": case.target}, 1))])
        self.assertEqual(run_episode(case, model)["reason"], "bad_tool_envelope")
        model = Scripted([reply(call("read_file", {"path": case.target}, 1),
                                call("read_file", {"path": case.target}, 2))])
        self.assertEqual(run_episode(case, model, max_tool_calls=1)["reason"], "tool_limit")

    def test_turn_limit_and_safe_trace(self):
        case = self._case("symbol_origin")
        model = Scripted([reply(call("read_file", {"path": "../../SECRET_CANARY"}))])
        result = run_episode(case, model, max_turns=1)
        self.assertFalse(result["ok"])
        self.assertEqual(result["reason"], "turn_limit")
        self.assertNotIn("SECRET_CANARY", json.dumps(result))

    def test_tool_response_messages_use_matching_ids(self):
        case = self._case("symbol_origin")
        model = Scripted([reply(call("search_repository", {"query": case.symbol}, 9)),
                          reply(call("read_file", {"path": case.target}, 10)),
                          reply(text=f"{case.target} has {case.expected_value}.")])
        self.assertTrue(run_episode(case, model)["ok"])
        second = model.history[1]
        self.assertEqual(second[-1]["tool_call_id"], "call-9")
        self.assertEqual(second[-1]["role"], "tool")

    @staticmethod
    def _case(kind):
        return generate(kind, episode_seed(616, kind, 1))


class ReportsTests(unittest.TestCase):
    def test_summary_versions_and_failure_reasons_keep_all_episodes(self):
        rows = [{"case": "moved_runbook", "ok": True, "reason": "completed"},
                {"case": "moved_runbook", "ok": False, "reason": "missing_http_status"},
                {"case": "no_tool_needed", "ok": False, "reason": "excessive_verbosity"},
                {"case": "no_tool_needed", "ok": False, "reason": "excessive_verbosity"},
                {"case": "symbol_origin", "ok": False, "reason": "request_error"}]
        result = summarize(rows)
        self.assertEqual((result["passed"], result["total"], result["pass_rate"]), (1, 5, .2))
        self.assertEqual(result["scorer_version"], "0.7.2")
        self.assertEqual(result["protocol_version"], "1")
        self.assertEqual(result["failure_reasons"],
                         {"missing_http_status": 1, "excessive_verbosity": 2, "request_error": 1})
        self.assertEqual(summarize([])["failure_reasons"], {})

    def test_summary_counts_failures_and_p90(self):
        rows = [{"case": "symbol_origin", "ok": True, "elapsed_s": 2, "turns": 3, "tool_calls": 2,
                 "prompt_tokens": 10, "completion_tokens": 5},
                {"case": "symbol_origin", "ok": False, "elapsed_s": 6, "turns": 4, "tool_calls": 3,
                 "prompt_tokens": 20, "completion_tokens": 10}]
        s = summarize(rows)
        self.assertEqual((s["passed"], s["total"], s["pass_rate"]), (1, 2, .5))
        self.assertEqual(s["median_elapsed_s"], 4)
        self.assertAlmostEqual(s["p90_elapsed_s"], 5.6)
        self.assertEqual(s["cases"]["symbol_origin"]["median_completion_tokens"], 7.5)

    def test_request_contract(self):
        p = request_payload("model", [{"role": "user", "content": "synthetic"}], 1024)
        self.assertEqual(p["tool_choice"], "auto")
        self.assertFalse(p["stream"])
        self.assertEqual(len(p["tools"]), 5)

    def test_live_report_path_with_scripted_responses(self):
        seed = 8989
        cases = {generate(kind, episode_seed(seed, kind, 1)).instruction:
                 generate(kind, episode_seed(seed, kind, 1)) for kind in KINDS}
        scripts = {instruction: scripted_success(case) for instruction, case in cases.items()}
        request_error_instruction = None

        class FakeClient:
            def __init__(self, base_url, model, timeout):
                self.model = model
            def health(self):
                return True
            def models(self):
                return [{"id": self.model}]
            def _request(self, path, payload):
                instruction = payload["messages"][1]["content"]
                if instruction == request_error_instruction:
                    raise OSError("PRIVATE_REQUEST_CANARY")
                turn = sum(m["role"] == "assistant" for m in payload["messages"])
                return io.BytesIO(json.dumps(scripts[instruction][turn]).encode())

        with tempfile.TemporaryDirectory() as folder:
            with patch("thorbench.client.VLLMClient", FakeClient):
                dest, result = run_live(model="mock", base_url="http://127.0.0.1:8000",
                                        seed=seed, runs=1, results_dir=Path(folder))
            self.assertEqual(result["passed"], len(KINDS))
            metadata = json.loads((dest / "metadata.json").read_text())
            self.assertEqual(metadata["seed"], seed)
            self.assertEqual(metadata["scorer_version"], "0.7.2")
            self.assertEqual(metadata["protocol_version"], "1")
            self.assertRegex(metadata["implementation_sha256"], r"^[a-f0-9]{64}$")
            samples = [json.loads(line) for line in (dest / "samples.jsonl").read_text().splitlines()]
            self.assertEqual(len(samples), len(KINDS))
            self.assertEqual(samples[0]["repetition"], 1)
            self.assertIn("6/6", (dest / "summary.md").read_text())
            self.assertIn("0.7.2", (dest / "summary.md").read_text())
            self.assertEqual(samples[0]["scorer_version"], "0.7.2")
            for file in dest.iterdir():
                raw = file.read_text()
                self.assertNotIn("ACTIVE production configuration", raw)
                self.assertNotIn("Synthetic workspace", raw)
                self.assertNotIn("update_in_memory_only", raw)

        no_tool_instruction = next(instruction for instruction, case in cases.items()
                                   if case.kind == "no_tool_needed")
        scripts[no_tool_instruction] = [reply(text=(
            "TTFT is time to first token; total end-to-end task latency includes all work. "
            + "PRIVATE_ANSWER_CANARY " * 40))]
        request_error_instruction = next(instruction for instruction, case in cases.items()
                                         if case.kind == "moved_runbook")
        with tempfile.TemporaryDirectory() as folder:
            with patch("thorbench.client.VLLMClient", FakeClient):
                dest, result = run_live(model="mock", base_url="http://127.0.0.1:8000",
                                        seed=seed, runs=1, results_dir=Path(folder))
            self.assertEqual((result["passed"], result["total"]), (4, 6))
            self.assertEqual(result["failure_reasons"], {"excessive_verbosity": 1, "request_error": 1})
            self.assertIn("excessive_verbosity: 1", (dest / "summary.md").read_text())
            samples = [json.loads(line) for line in (dest / "samples.jsonl").read_text().splitlines()]
            request_error = next(row for row in samples if row["reason"] == "request_error")
            self.assertEqual(request_error["scorer_version"], "0.7.2")
            self.assertEqual(request_error["error_type"], "OSError")
            for file in dest.iterdir():
                self.assertNotIn("PRIVATE_ANSWER_CANARY", file.read_text())
                self.assertNotIn("PRIVATE_REQUEST_CANARY", file.read_text())


if __name__ == "__main__":
    unittest.main()
