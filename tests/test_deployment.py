"""Offline Docker launch fingerprint tests: privacy is a contractual requirement."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace

from thorbench.deployment import inspect_container, parse_serve_arguments, checked_in_profile_fingerprint
from thorbench.scenarios import case_prefix

ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / "models/qwen3.8-flash-next"


class DeploymentTests(unittest.TestCase):
    def test_profile_matches_verified_script_and_does_not_enable_mtp(self):
        profile = json.loads((MODEL / "launch-profile.json").read_text())
        argv = profile["vllm_arguments"]
        script = (MODEL / "serve.sh").read_text()
        self.assertEqual(profile["served_model_name"], "Qwen3.8-Flash-Next")
        self.assertEqual(profile["image"], "ghcr.io/nvidia-ai-iot/vllm:qwen3.8-next-jetson-thor")
        self.assertIn("--gpu-memory-utilization", argv)
        self.assertEqual(argv[argv.index("--gpu-memory-utilization") + 1], "0.90")
        self.assertEqual(argv[argv.index("--max-model-len") + 1], "212992")
        self.assertIn("--hf-overrides", argv)
        self.assertNotIn("--speculative-config", argv)
        self.assertIn('GPU_MEMORY_UTILIZATION:-0.90', script)
        self.assertIn('MAX_MODEL_LEN:-212992', script)

    def test_flags_are_strictly_allowlisted(self):
        parsed = parse_serve_arguments([
            "some/checkpoint", "--gpu-memory-utilization", "0.90",
            "--max-model-len=212992", "--enable-auto-tool-choice",
            "--api-key", "very-secret-token",
            "--host", "10.1.2.3",
            "--speculative-config", '{"method":"mtp","num_speculative_tokens":3,"model":"/private/home/secret"}',
            "--foo", "/home/user",
        ])
        raw = json.dumps(parsed)
        self.assertIn("--max-model-len", parsed)
        self.assertEqual(parsed["--gpu-memory-utilization"], "0.90")
        self.assertEqual(parsed["--speculative-config"]["method"], "mtp")
        for secret in ("very-secret-token", "10.1.2.3", "private", "/home/user"):
            self.assertNotIn(secret, raw)

    @patch("thorbench.deployment.shutil.which", return_value="/usr/bin/docker")
    @patch("thorbench.deployment.subprocess.run")
    def test_inspect_redacts_environment_bind_mounts_and_private_image(self, run, _which):
        data = {
            "Config": {"Cmd": ["repo/checkpoint", "--max-model-len", "212992", "--enable-prefix-caching"],
                       "Image": "registry.internal.corp/image:secret", "Env": ["TOKEN=supersecret"]},
            "HostConfig": {"Runtime": "nvidia", "NetworkMode": "host", "IpcMode": "host",
                           "Binds": ["/home/renato/corp:/private"]},
            "State": {"Running": True},
        }
        run.return_value = SimpleNamespace(returncode=0, stdout=json.dumps(data), stderr="")
        observed = inspect_container("qwen38-flash-next")
        dumped = json.dumps(observed)
        self.assertEqual(observed["vllm_flags"]["--max-model-len"], "212992")
        self.assertEqual(observed["prefix_caching_flag"], "explicitly_enabled")
        self.assertNotIn("supersecret", dumped)
        self.assertNotIn("renato", dumped)
        self.assertNotIn("registry.internal.corp", dumped)
        run.assert_called_once()

    def test_prefix_prompt_repeats_deterministically_and_contains_no_secret(self):
        a = case_prefix(2048, "public-random-marker")
        b = case_prefix(2048, "public-random-marker")
        self.assertEqual(a, b)
        self.assertGreater(len(a["messages"][0]["content"]), 2048)
        with self.assertRaises(ValueError):
            case_prefix(200000, "x")

    def test_deployment_profile_is_fingerprinted(self):
        value = checked_in_profile_fingerprint()
        self.assertEqual(len(value["sha256"]), 64)
        self.assertEqual(value["kind"], "declared_recipe_not_live_observation")

    def test_mermaid_pages_exist(self):
        doc = ROOT / "docs" / "diagrams" / "README.md"
        self.assertTrue(doc.is_file())
        for n in range(1, 8):
            matches = list(doc.parent.glob(f"{n:02d}-*.md"))
            self.assertEqual(len(matches), 1)
            self.assertIn("```mermaid", matches[0].read_text())


if __name__ == "__main__":
    unittest.main()
