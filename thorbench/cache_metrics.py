"""Read public vLLM prefix-cache Prometheus counters without external libraries.

Counters represent the entire server, not a specific user request. The benchmark
therefore labels counter deltas as *suggestive* when other clients may be active.
"""
from __future__ import annotations

import re
from typing import Any

# Prometheus Python exporters expose counter names with _total; deployments may
# also expose names without the suffix. Do not double-count when both exist.
_COUNTER_RE = re.compile(
    r'^vllm:prefix_cache_(hits|queries)(_total)?(?:\{[^}]*\})?\s+'
    r'([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)'
    r'(?:\s|$)'
)


def parse_prefix_counters(text: str) -> dict[str, float] | None:
    """Return server-wide hit/query token counters, or None if not exposed."""
    totals: dict[str, dict[str, float]] = {"hits": {}, "queries": {}}
    for line in text.splitlines():
        match = _COUNTER_RE.match(line)
        if not match:
            continue
        kind, suffix, number = match.groups()
        key = "total" if suffix else "bare"
        try:
            value = float(number)
        except ValueError:
            continue
        if value < 0 or value == float("inf"):
            continue
        totals[kind][key] = totals[kind].get(key, 0.0) + value
    if not totals["hits"] and not totals["queries"]:
        return None
    return {
        kind: values.get("total", values.get("bare"))
        for kind, values in totals.items()
    }


def counter_deltas(before: dict[str, float] | None,
                   after: dict[str, float] | None) -> dict[str, Any]:
    """Never interpret missing or reset counters as zero cache usage."""
    result = {"cache_hit_tokens_delta": None, "cache_query_tokens_delta": None,
              "cache_hit_rate": None, "cache_evidence": "unavailable"}
    if before is None or after is None:
        return result
    hits_before, hits_after = before.get("hits"), after.get("hits")
    queries_before, queries_after = before.get("queries"), after.get("queries")
    if any(v is None for v in (hits_before, hits_after, queries_before, queries_after)):
        return result
    hits = hits_after - hits_before
    queries = queries_after - queries_before
    if hits < 0 or queries < 0:
        result["cache_evidence"] = "counter_reset_or_invalid"
        return result
    result["cache_hit_tokens_delta"] = round(hits)
    result["cache_query_tokens_delta"] = round(queries)
    if queries > 0:
        result["cache_hit_rate"] = round(hits / queries, 4)
        result["cache_evidence"] = "server_hits_observed" if hits > 0 else "server_zero_hits"
    else:
        result["cache_evidence"] = "no_prefix_queries_observed"
    return result
