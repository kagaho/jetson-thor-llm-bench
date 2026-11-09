"""Reject incomplete throughput denominators and mismatched paired protocols."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import export_deployment_comparison as exporter


class DeploymentExportTests(unittest.TestCase):
    def test_partial_c1_does_not_publish_success_only_rate(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "c1.log"
            categories = ["Q&A", "Code", "JSON", "Math", "LongCode"] * 2
            path.write_text("\n".join(f"[{name}] 100 tokens in 2.00s = 50.0 tok/s (prompt: 20)"
                                      for name in categories[:-1]))
            result = exporter.forum_c1(path)
            self.assertEqual(result["reported_successes"], 9)
            self.assertEqual(result["expected_requests"], 10)
            self.assertNotIn("pooled_end_to_end_tokens_s", result)
            self.assertNotIn("mean_two_pass_end_to_end_tokens_s", result)

    def test_seed_drift_refuses_to_write_comparison(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "public.json"
            reference = {"runner_sha256": "runner", "thorbench_python_sha256": "source",
                         "vision_image_sha256": "image", "seed": 123}
            candidate = {**reference, "seed": 124}
            with patch("sys.argv", ["export", "--runs", folder, "--output", str(output)]), \
                 patch.object(exporter, "arm", side_effect=[reference, candidate]):
                with self.assertRaisesRegex(ValueError, "Protocol mismatch: seed"):
                    exporter.main()
            self.assertFalse(output.exists())

    def test_interrupted_run_is_rejected_before_export(self):
        with tempfile.TemporaryDirectory() as folder:
            directory = Path(folder)
            (directory / "comparison-manifest.json").write_text(json.dumps({"status": "interrupted"}))
            with self.assertRaisesRegex(ValueError, "Incomplete"):
                exporter.arm(directory)

    def test_summary_cannot_promote_failed_rows_to_passes(self):
        with tempfile.TemporaryDirectory() as folder:
            directory = Path(folder)
            (directory / "comparison-manifest.json").write_text(json.dumps({"status": "completed"}))
            suite = directory / "suites" / "quick"
            suite.mkdir(parents=True)
            (suite / "metadata.json").write_text(json.dumps({"suite": "quick"}))
            (suite / "summary.json").write_text(json.dumps({"scenarios": {"quick": {"passes": 3, "total": 3}}}))
            (suite / "samples.jsonl").write_text('\n'.join(json.dumps({"ok": False}) for _ in range(3)))
            with self.assertRaisesRegex(ValueError, "Pass count"):
                exporter.arm(directory)
