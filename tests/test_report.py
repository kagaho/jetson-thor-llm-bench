import tempfile
import unittest
from pathlib import Path
from thorbench.report import new_run_dir, save_row, summarize

class ReportTests(unittest.TestCase):
    def test_report_does_not_contain_prompt(self):
        with tempfile.TemporaryDirectory() as tmp:
            dst = new_run_dir(Path(tmp), "quick")
            row = {"scenario": "quick", "run": 1, "ok": True, "elapsed_s": 11.09,
                   "ttft_s": 0.8, "ttfc_s": 1.3, "decode_tokens_s": 22.8,
                   "finish_reason": "stop"}
            save_row(dst, row)
            summarize([row], dst)
            self.assertIn("22.80", (dst / "summary.md").read_text())
            self.assertNotIn("my_private_prompt", (dst / "samples.jsonl").read_text())

if __name__ == "__main__":
    unittest.main()
