"""Offline publication consistency checks (no GPU or Node required)."""
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]

class PublicationTests(unittest.TestCase):
    def test_headline_and_visuals(self):
        data = json.loads((ROOT / "docs/data/fp8-hybrid-comparison.json").read_text())
        readme = (ROOT / "README.md").read_text()
        for arm in ("b2", "hybrid"):
            a = data[arm]
            self.assertIn(f"{a['forum_c1']['mean_two_pass_end_to_end_tokens_s']:.2f}", readme)
            for suite in ("tool-routing", "agent-multiturn", "agent-generalization"):
                s = a["suites"][suite]["summary"]
                self.assertIn(f"{s['passed']}/{s['total']}", readme)
        manifest = json.loads((ROOT / "docs/figures/publication-sources.json").read_text())
        for f in manifest["figures"]:
            p = ROOT / "docs/figures" / f["path"]
            self.assertTrue(p.is_file(), f["path"])
            if p.suffix == ".gif":
                self.assertEqual(p.read_bytes()[:6], b"GIF89a")
            elif p.suffix == ".png":
                self.assertEqual(p.read_bytes()[:8], b"\x89PNG\r\n\x1a\n")
        self.assertIn("Conceptual reconstruction, not a recording", readme)
