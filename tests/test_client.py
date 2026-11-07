import io
import json
import unittest
from unittest.mock import patch
from thorbench.client import VLLMClient, _usage, _cached_usage


class FakeResponse(io.BytesIO):
    status = 200


class ClientTests(unittest.TestCase):
    def test_usage(self):
        self.assertEqual(_usage({"usage": {"prompt_tokens": 8, "completion_tokens": 5, "completion_tokens_details": {"reasoning_tokens": 2}}}), (8, 5, 2))
        self.assertEqual(_usage({}), (None, None, None))

    def test_cached_tokens_null_vs_reported(self):
        self.assertIsNone(_cached_usage({"usage": {"prompt_tokens_details": None}}))
        self.assertEqual(_cached_usage({"usage": {"prompt_tokens_details": {"cached_tokens": 128}}}), 128)

    def test_nonstream(self):
        payload = {"choices": [{"message": {"content": "READY"}, "finish_reason": "stop"}],
                   "usage": {"prompt_tokens": 10, "completion_tokens": 4, "completion_tokens_details": {"reasoning_tokens": 1}}}
        with patch("thorbench.client.urlopen", return_value=FakeResponse(json.dumps(payload).encode())):
            sample = VLLMClient("http://127.0.0.1:8000", "demo").chat({"messages": []}, streaming=False)
        self.assertEqual(sample.content, "READY")
        self.assertEqual(sample.metrics()["visible_tokens"], 3)
        self.assertIsNone(sample.ttft_s)

    def test_stream_reasoning_then_content_and_usage(self):
        chunks = [
            {"choices": [{"delta": {"role": "assistant"}}]},
            {"choices": [{"delta": {"reasoning": "think"}}]},
            {"choices": [{"delta": {"content": "answer"}}]},
            {"choices": [{"delta": {}, "finish_reason": "stop"}]},
            {"choices": [], "usage": {"prompt_tokens": 12, "completion_tokens": 8, "completion_tokens_details": {"reasoning_tokens": 4}}},
        ]
        data = b"".join(f"data: {json.dumps(item)}\n\n".encode() for item in chunks) + b"data: [DONE]\n\n"
        with patch("thorbench.client.urlopen", return_value=FakeResponse(data)):
            sample = VLLMClient("http://127.0.0.1:8000", "demo").chat({"messages": []})
        self.assertEqual(sample.content, "answer")
        self.assertEqual(sample.finish_reason, "stop")
        self.assertEqual(sample.prompt_tokens, 12)
        self.assertEqual(sample.completion_tokens, 8)
        self.assertEqual(sample.reasoning_tokens, 4)
        self.assertIsNotNone(sample.ttft_s)
        self.assertIsNotNone(sample.ttfc_s)
        self.assertLessEqual(sample.ttft_s, sample.ttfc_s)

    def test_no_usage_returns_none_not_zero(self):
        data = b'data: {"choices":[{"delta":{"content":"hello"},"finish_reason":"stop"}]}\n\ndata: [DONE]\n\n'
        with patch("thorbench.client.urlopen", return_value=FakeResponse(data)):
            sample = VLLMClient("http://127.0.0.1:8000", "demo").chat({"messages": []})
        self.assertIsNone(sample.metrics()["decode_tokens_s"])


if __name__ == "__main__":
    unittest.main()
