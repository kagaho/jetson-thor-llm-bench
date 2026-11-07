"""Offline tests of Prometheus counters and their uncertainty semantics."""
import unittest
from thorbench.cache_metrics import counter_deltas, parse_prefix_counters


class PrefixCacheMetricTests(unittest.TestCase):
    def test_aggregates_exporter_counter_series(self):
        raw = '''# HELP vllm:prefix_cache_hits_total x
vllm:prefix_cache_hits_total{model_name="a",engine="0"} 150
vllm:prefix_cache_hits_total{model_name="a",engine="1"} 50
vllm:prefix_cache_queries_total{model_name="a",engine="0"} 300
vllm:prefix_cache_queries_total{model_name="a",engine="1"} 100
'''
        self.assertEqual(parse_prefix_counters(raw), {"hits": 200.0, "queries": 400.0})

    def test_does_not_double_count_total_and_bare(self):
        raw = 'vllm:prefix_cache_hits 5\nvllm:prefix_cache_hits_total 9\nvllm:prefix_cache_queries 10\nvllm:prefix_cache_queries_total 20\n'
        self.assertEqual(parse_prefix_counters(raw), {"hits": 9.0, "queries": 20.0})

    def test_unavailable_is_not_zero(self):
        self.assertIsNone(parse_prefix_counters('vllm:kv_cache_usage_perc 0.04\n'))
        self.assertEqual(counter_deltas(None, None)["cache_evidence"], "unavailable")
        self.assertIsNone(counter_deltas(None, None)["cache_hit_rate"])

    def test_hits_zero_and_reset_are_different(self):
        first = {"hits": 2.0, "queries": 60.0}
        self.assertEqual(counter_deltas(first, {"hits": 32.0, "queries": 160.0})["cache_evidence"], "server_hits_observed")
        self.assertEqual(counter_deltas(first, {"hits": 2.0, "queries": 160.0})["cache_evidence"], "server_zero_hits")
        self.assertEqual(counter_deltas(first, {"hits": 1.0, "queries": 10.0})["cache_evidence"], "counter_reset_or_invalid")


if __name__ == '__main__':
    unittest.main()
