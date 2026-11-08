"""Unit tests for structured tool routing; no GPU or model server required."""
import json
import unittest

from thorbench.tool_eval import CASES, TOOLS, request_payload, score_response, summarize


def response(tool=None, arguments=None, content=""):
    message = {"content": content}
    if tool is not None:
        message["tool_calls"] = [{"type": "function", "function": {
            "name": tool, "arguments": arguments if arguments is not None else "{}"}}]
    return {"choices": [{"message": message, "finish_reason": "tool_calls" if tool else "stop"}]}


class TestToolEvaluation(unittest.TestCase):
    def test_declared_tools_have_schema(self):
        self.assertEqual({x["function"]["name"] for x in TOOLS},
                         {"read_file", "search_repository", "run_tests"})
        self.assertTrue(all(x["function"]["parameters"]["additionalProperties"] is False for x in TOOLS))

    def test_tool_call_correct(self):
        case = CASES[0]
        result = score_response(response("read_file", json.dumps({"path": case.expected_value})), case)
        self.assertTrue(result["ok"])

    def test_wrong_tool(self):
        self.assertEqual(score_response(response("run_tests", '{"target":"tests/test_cache_metrics.py"}'), CASES[0])["reason"],
                         "wrong_tool")

    def test_bad_arguments(self):
        self.assertEqual(score_response(response("read_file", "{bad"), CASES[0])["reason"],
                         "invalid_json_arguments")

    def test_extra_arguments(self):
        r = response("read_file", '{"path":"models/qwen3.8-flash-next/README.md","debug":true}')
        self.assertEqual(score_response(r, CASES[0])["reason"], "invalid_argument_schema")

    def test_wrong_argument_value(self):
        r = response("read_file", '{"path":"/etc/passwd"}')
        self.assertEqual(score_response(r, CASES[0])["reason"], "wrong_argument_value")

    def test_search_query_contains_identifier(self):
        self.assertTrue(score_response(response("search_repository", '{"query":"class VLLMClient"}'), CASES[1])["ok"])

    def test_negative_control(self):
        self.assertTrue(score_response(response(content="TTFT includes prefill; decoding speed does not."), CASES[-1])["ok"])
        self.assertFalse(score_response(response("read_file", '{}'), CASES[-1])["ok"])
        self.assertFalse(score_response(response(content=""), CASES[-1])["ok"])

    def test_missing_choice_or_multiple_calls(self):
        self.assertEqual(score_response({}, CASES[0])["reason"], "missing_choice")
        r = response("read_file", '{"path":"foo"}')
        r["choices"][0]["message"]["tool_calls"].append(r["choices"][0]["message"]["tool_calls"][0])
        self.assertEqual(score_response(r, CASES[0])["reason"], "expected_exactly_one_tool")

    def test_payload_auto_tool_choice(self):
        x = request_payload(CASES[0], "Qwen3.8-Flash-Next")
        self.assertEqual(x["tool_choice"], "auto")
        self.assertEqual(x["stream"], False)
        self.assertFalse("prompt" in x)

    def test_no_generated_text_persisted_in_score(self):
        r = response("read_file", '{"path":"/private/user.txt"}', content="SENSITIVE STRING")
        result = score_response(r, CASES[0])
        self.assertNotIn("SENSITIVE STRING", json.dumps(result))
        self.assertNotIn("/private/user.txt", json.dumps(result))

    def test_stats_include_failures(self):
        s = summarize([{"case":"x","ok":True,"elapsed_s":1.2},
                       {"case":"x","ok":False,"elapsed_s":2.3}])
        self.assertEqual(s["passed"], 1)
        self.assertEqual(s["total"], 2)
        self.assertEqual(s["pass_rate"], .5)


if __name__ == "__main__":
    unittest.main()
