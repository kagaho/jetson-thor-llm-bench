"""Offline provenance and public reference tests; no external connections."""
import json
import tempfile
import unittest
from pathlib import Path

from thorbench import __version__
from thorbench.reference import model_metadata, list_references, compare_local_run


class ReferenceTests(unittest.TestCase):
    def test_known_model(self):
        model = model_metadata("Qwen3.8-Flash-Next")
        self.assertEqual(model["checkpoint_repo"], "local-inference-lab/Qwen3.8-Flash-Next-NVFP4")
        self.assertEqual(model["native_context_tokens"], 262144)
        self.assertIsNone(model_metadata("unknown-model"))

    def test_hybrid_alias_preserves_base_and_delta_identity(self):
        baseline = model_metadata("Qwen3.8-Flash-Next")
        hybrid = model_metadata("qwen3.8-flash-next")
        self.assertNotEqual(baseline["checkpoint_repo"], hybrid["checkpoint_repo"])
        self.assertEqual(hybrid["base_checkpoint_repo"], "RadixArk/Qwen3.8-Flash-Next-NVFP4")
        self.assertEqual(hybrid["checkpoint_revision"], hybrid["delta_revision"])
        self.assertIsNone(model_metadata("RadixArk/Qwen3.8-Flash-Next-NVFP4"))

    def test_references_label_protocol_mismatch(self):
        result = list_references()
        self.assertIn("46.7", result)
        self.assertIn("NOT measurements by this project", result)
        self.assertIn("jetson-ai-lab.com", result)

    def test_compare_requires_local_result(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self.assertRaises(ValueError):
                compare_local_run(root)
            (root / "metadata.json").write_text(json.dumps({"model": "Qwen3.8-Flash-Next", "suite": "quick"}))
            (root / "samples.jsonl").write_text(json.dumps({"ok": True, "effective_tokens_s": 22.8, "decode_tokens_s": 24.2})+"\n")
            output = compare_local_run(root)
            self.assertIn("22.80", output)
            self.assertIn("Do not compute speedups", output)
            self.assertIn("46.7", output)

    def test_version(self):
        self.assertEqual(__version__, "0.7.0")

if __name__ == "__main__":
    unittest.main()
