"""Output preservation and preflight gates for live comparison orchestration."""
import contextlib
import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from scripts import run_deployment_benchmarks as runner


class DeploymentComparisonTests(unittest.TestCase):
    def argv(self, destination):
        return ["runner", "--base-url", "http://127.0.0.1:8000", "--model", "test",
                "--container", "test", "--checkpoint-revision", "test",
                "--results-dir", str(destination)]

    def test_existing_output_is_never_overwritten(self):
        with tempfile.TemporaryDirectory(dir=runner.ROOT / "results") as folder:
            marker = Path(folder) / "comparison-manifest.json"
            marker.write_text("preserve")
            with patch("sys.argv", self.argv(folder)), patch.object(runner.subprocess, "check_output") as read:
                with self.assertRaises(FileExistsError):
                    runner.main()
                read.assert_not_called()
            self.assertEqual(marker.read_text(), "preserve")

    def test_unhealthy_preflight_sends_no_benchmark_requests(self):
        with tempfile.TemporaryDirectory(dir=runner.ROOT / "results") as folder:
            destination = Path(folder) / "new"
            with patch("sys.argv", self.argv(destination)), \
                 patch.object(runner, "telemetry"), \
                 patch.object(runner.subprocess, "check_output", return_value="test\n"), \
                 patch.object(runner.subprocess, "run", return_value=subprocess.CompletedProcess([], 2)) as run, \
                 contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(runner.main(), 1)
            self.assertEqual(run.call_count, 1)
            self.assertIn("doctor", run.call_args.args[0])
            manifest = json.loads((destination / "comparison-manifest.json").read_text())
            self.assertEqual(manifest["status"], "preflight_failed")
            self.assertEqual(len(manifest["jobs"]), 1)

    def test_output_must_resolve_inside_private_results(self):
        with tempfile.TemporaryDirectory() as outside:
            with patch("sys.argv", self.argv(Path(outside) / "new")), \
                 contextlib.redirect_stderr(io.StringIO()), \
                 patch.object(runner.subprocess, "run") as run:
                with self.assertRaises(SystemExit):
                    runner.main()
                run.assert_not_called()
            self.assertFalse((Path(outside) / "new").exists())
