"""Smoke checks for publicly documented deployment recipes (no Docker required)."""
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
MODEL_DIR = ROOT / "models" / "qwen3.8-flash-next"


class ModelLayoutTests(unittest.TestCase):
    def test_model_recipe_exists_and_uses_verified_baseline(self):
        script = (MODEL_DIR / "serve.sh").read_text()
        self.assertIn("--gpu-memory-utilization", script)
        self.assertIn('GPU_MEMORY_UTILIZATION:-0.90', script)
        self.assertIn('MAX_MODEL_LEN:-212992', script)
        self.assertNotIn("--speculative-config", script)
        self.assertIn('--host 127.0.0.1', script)

    def test_model_guides_and_registry_are_present(self):
        self.assertTrue((ROOT / "models" / "README.md").is_file())
        self.assertTrue((MODEL_DIR / "README.md").is_file())
        self.assertTrue((MODEL_DIR / "baseline.md").is_file())
        self.assertTrue((ROOT / "thorbench" / "data" / "model_catalog.json").is_file())


if __name__ == "__main__":
    unittest.main()
