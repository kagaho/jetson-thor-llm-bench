"""Protect the provenance of the published, curated numeric-only case study."""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from render_prefix_case_study import render


class PublicCaseStudyTests(unittest.TestCase):
    def test_svg_chart_matches_curated_measurements(self):
        data = json.loads((ROOT / "docs/data/2026-11-07-prefix-observations.json").read_text())
        figure = (ROOT / "docs/figures/shockwave-prefix-ttft-2026-11-07.svg").read_text()
        self.assertEqual(render(data), figure)
        self.assertIn("unavailable in both runs", figure.lower())
        self.assertTrue(all(p["cached_prompt_tokens"] is None for p in data["pairs"]))
        self.assertEqual(len(data["pairs"]), 2)
        self.assertNotIn("/home/", figure)

    def test_new_mermaid_diagrams_are_linked(self):
        readme = (ROOT / "README.md").read_text()
        for name in ("08-prefix-cache-evidence", "09-agent-prefix-sequence"):
            diagram = ROOT / f"docs/diagrams/{name}.md"
            self.assertTrue(diagram.is_file())
            self.assertIn("```mermaid", diagram.read_text())
            self.assertIn(name, readme)


if __name__ == '__main__':
    unittest.main()
