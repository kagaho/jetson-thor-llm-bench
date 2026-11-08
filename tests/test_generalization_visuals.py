"""Protect public numeric evidence and its exported chart attribution (stdlib only)."""
import json
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
SVG_NS = "http://www.w3.org/2000/svg"


class GeneralizationVisualTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads((ROOT / "docs/data/2026-11-08-generalization-observations.json").read_text())

    def test_recorded_run_keeps_provenance_and_failed_episodes(self):
        data, summary = self.data, self.data["summary"]
        self.assertEqual(data["seed"], 3628200930879258838)
        self.assertEqual(data["source_commit"], "de44842a07867d0f2a4dacf7dd67eea9e7df0857")
        self.assertEqual(data["implementation_sha256"],
                         "9d76d9625578f95e6cf2b412e24109f092cbf97b897cd19f949969d78decf825")
        self.assertEqual((data["scorer_version"], data["protocol_version"]), ("0.7.2", "1"))
        self.assertTrue(data["simulated_only"])
        self.assertEqual(set(summary["cases"]), {
            "symbol_origin", "repair_regression", "moved_runbook",
            "transient_read", "environment_disambiguation", "no_tool_needed",
        })
        self.assertEqual((summary["passed"], summary["total"]), (25, 30))
        self.assertAlmostEqual(summary["pass_rate"], 25 / 30, places=4)
        self.assertEqual(summary["failure_reasons"], {"excessive_verbosity": 5})
        self.assertEqual(summary["median_elapsed_s"], 18.8132)
        self.assertEqual(summary["p90_elapsed_s"], 41.3457)
        self.assertEqual(sum(c["total"] for c in summary["cases"].values()), summary["total"])
        self.assertEqual(sum(c["passed"] for c in summary["cases"].values()), summary["passed"])
        for name, case in summary["cases"].items():
            self.assertEqual(case["total"], 5)
            self.assertEqual(case["passed"], 0 if name == "no_tool_needed" else 5)
            self.assertLessEqual(case["median_elapsed_s"], case["p90_elapsed_s"])

    def test_exported_svgs_keep_numeric_labels_and_historical_scorer(self):
        for kind in ("outcomes", "latency"):
            path = ROOT / f"docs/figures/agent-generalization-{kind}-2026-11-08.svg"
            raw = path.read_text()
            root = ET.fromstring(raw)
            text = " ".join(root.itertext())
            self.assertEqual(root.get("role"), "img")
            self.assertIsNotNone(root.find(f"{{{SVG_NS}}}title"))
            self.assertIsNotNone(root.find(f"{{{SVG_NS}}}desc"))
            self.assertIn("scorer 0.7.2", text)
            self.assertIn(str(self.data["seed"]), text)
            self.assertNotIn("/home/", raw)
            self.assertNotIn("PRIVATE_CANARY", raw)
            for name, case in self.data["summary"]["cases"].items():
                if kind == "outcomes":
                    expected = f"{name}: {case['passed']} passed, {case['total'] - case['passed']} failed"
                else:
                    expected = (f"{name}: median {case['median_elapsed_s']:.4f} s, "
                                f"p90 {case['p90_elapsed_s']:.4f} s")
                self.assertIn(expected, text)
            self.assertIn("excessive_verbosity" if kind == "outcomes" else "failures included", text)


if __name__ == "__main__":
    unittest.main()
