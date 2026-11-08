"""Offline safety and reporting checks for low-memory launch and tool metrics."""
import json
import unittest
from pathlib import Path
from thorbench.tool_eval import summarize

ROOT = Path(__file__).resolve().parents[1]


class MemoryAndOutputTests(unittest.TestCase):
    def test_b2_profile_matches_manual_launch(self):
        profile=json.loads((ROOT/'models/qwen3.8-flash-next/launch-profile-lowmem.json').read_text())
        script=(ROOT/'models/qwen3.8-flash-next/serve-lowmem.sh').read_text()
        self.assertEqual(profile['parameters']['kv_cache_memory_bytes'],4294967296)
        self.assertEqual(profile['parameters']['max_model_len'],131072)
        self.assertEqual(profile['parameters']['gpu_memory_utilization'],.88)
        for text in ('--gpu-memory-utilization 0.88','--kv-cache-memory-bytes 4294967296',
                     '--max-model-len 131072','--max-num-seqs 1',
                     'docker container inspect "$NAME"','exec docker run -d --restart=no'):
            self.assertIn(text,script)
        self.assertNotIn('docker stop',script)
        self.assertNotIn('--rm',script)
        self.assertIn('512bf772c7ef221df1a66ab9c95546d77daeba6ba61723692852e6eb0cae7526',script)

    def test_tool_summary_has_per_case_token_counts(self):
        rows=[{'case':'alpha','ok':True,'elapsed_s':2.0,'prompt_tokens':100,'completion_tokens':58},
              {'case':'alpha','ok':True,'elapsed_s':3.0,'prompt_tokens':102,'completion_tokens':73},
              {'case':'beta','ok':False,'elapsed_s':5.0}]
        stats=summarize(rows)
        self.assertEqual(stats['cases']['alpha']['median_prompt_tokens'],101)
        self.assertEqual(stats['cases']['alpha']['median_completion_tokens'],65.5)
        self.assertEqual(stats['cases']['alpha']['median_elapsed_s'],2.5)
        self.assertIsNone(stats['cases']['beta']['median_completion_tokens'])
        self.assertEqual(stats['total'],3)

    def test_chart_is_reproducible(self):
        from scripts.render_memory_ab import render
        self.assertEqual((ROOT/'docs/figures/shockwave-a-b2-memory-and-tool-latency.svg').read_text(),render())

    def test_b2_document_keeps_context_limit_disclosure(self):
        ab=(ROOT/'docs/benchmarks/2026-11-08-shockwave-b2-vs-a.md').read_text()
        self.assertIn('212,992',ab)
        self.assertIn('131,072',ab)
        self.assertIn('31,652',ab)
        self.assertIn('90',ab)

if __name__ == '__main__':
    unittest.main()
