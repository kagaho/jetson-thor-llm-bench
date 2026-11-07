"""Full doctor + benchmark against an ephemeral local mock. Never contacts the web."""
import io
import json
import tempfile
import threading
import unittest
from contextlib import redirect_stdout
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace

from thorbench.cli import run


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_args):
        pass

    def do_GET(self):
        if self.path == "/health":
            self.send_response(200)
            self.end_headers()
        elif self.path == "/v1/models":
            response = {"data": [{"id": "Qwen3.8-Flash-Next", "max_model_len": 212992}]}
            raw = json.dumps(response).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)
        else:
            self.send_error(404)

    def do_POST(self):
        if self.path != "/v1/chat/completions":
            self.send_error(404)
            return
        n = int(self.headers["Content-Length"])
        req = json.loads(self.rfile.read(n))
        if not req.get("stream"):
            self.send_error(400)
            return
        chunks = [
            {"choices": [{"delta": {"reasoning": "thinking"}}]},
            {"choices": [{"delta": {"content": "Here is a function."}}]},
            {"choices": [{"delta": {}, "finish_reason": "stop"}]},
            {"choices": [], "usage": {"prompt_tokens": 42, "completion_tokens": 15, "completion_tokens_details": {"reasoning_tokens": 5}}},
        ]
        body = b"".join(f"data: {json.dumps(c)}\n\n".encode() for c in chunks) + b"data: [DONE]\n\n"
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


class EndToEndTests(unittest.TestCase):
    def test_doctor_and_quick_suite(self):
        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f"http://127.0.0.1:{server.server_port}"
        try:
            with tempfile.TemporaryDirectory() as tmp:
                args = SimpleNamespace(base_url=base, model="Qwen3.8-Flash-Next", timeout=5, command="doctor")
                with redirect_stdout(io.StringIO()):
                    self.assertEqual(run(args), 0)
                args.command = "bench"
                args.suite = "quick"
                args.runs = 1
                args.warmup = 0
                args.results_dir = str(Path(tmp) / "results")
                with redirect_stdout(io.StringIO()):
                    self.assertEqual(run(args), 0)
                report = next((Path(tmp) / "results").glob("*-quick"))
                row = json.loads((report / "samples.jsonl").read_text().splitlines()[0])
                self.assertEqual(row["completion_tokens"], 15)
                self.assertEqual(row["reasoning_tokens"], 5)
                self.assertTrue(row["ok"])
                self.assertTrue((report / "summary.md").is_file())
                self.assertTrue((report / "summary.json").is_file())
                md = json.loads((report / "metadata.json").read_text())
                self.assertEqual(md["model_provenance"]["checkpoint_repo"], "local-inference-lab/Qwen3.8-Flash-Next-NVFP4")
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=3)

if __name__ == "__main__":
    unittest.main()
