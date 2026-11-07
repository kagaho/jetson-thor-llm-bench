# Prefix-cache and coding-agent responsiveness protocol (v0.4.0 candidate)

This protocol is for **single-device local inference**. It tests first-token responsiveness and optional cache evidence, **not** general coding-agent task completion or correctness. Results are private by default.

## Controlled workloads

| Suite | Prompt relationship | `--runs` meaning | Measured result |
|---|---|---|---|
| `prefix` | Fully identical system + user prompt inside each pair; random marker across pairs | Number of independent first/repeat pairs | Time to first streamed token, first visible content, total latency, decode rate, available prefix cache counters |
| `agent` | Identical synthetic repository/system context, **different** user task across the pair | Number of independent first/follow-up pairs | Shared-context reuse under changed instructions; does **not** execute tools, edit code, or test answer quality |

The random marker is not saved. `--prefix-tokens 8192` is a **character-based estimate**; report actual token counts from the API. For these suites set `--warmup 0`. The benchmark runs sequentially, with a unique random marker for each pair. A second request can still be affected by the initial kernel warmup and engine state; report observations rather than asserting causality.

## Run sequence

```bash
cd ~/Documents/jetson-thor-llm-bench
python3 -m unittest discover -s tests -v
python3 -m thorbench doctor --container qwen38-flash-next
# 5 pairs per suite; does NOT restart the running container or alter its flags.
python3 -m thorbench bench --suite prefix --runs 5 --warmup 0 \
  --prefix-tokens 8192 --container qwen38-flash-next
python3 -m thorbench bench --suite agent --runs 5 --warmup 0 \
  --prefix-tokens 8192 --container qwen38-flash-next
```

To view the counters exposed by the server (safe read-only request):

```bash
curl -fsS http://127.0.0.1:8000/metrics | grep -E '^vllm:prefix_cache_(hits|queries)(_total)?(\{|[[:space:]])' | head -20
```

**Important:** vLLM's Prometheus counters are global to their label scope, not guaranteed per-request. A positive `cache_hit_tokens_delta` between scrapes is good **server-side corroboration** only if no other clients accessed the engine. If `/metrics` is disabled, returns 404, or lacks the fields, the suite records *unavailable*, never zero. If counters reset, the measurement is marked invalid. A zero delta with a positive query delta means no hit observed *by those counters during that interval*.

## Reproducible operational metadata

Before judging results, record model checkpoint revision, image digest, JetPack/CUDA, power profile, GPU clocks, prefix-caching effective state, MTP policy, input/output lengths, cache policy, concurrency, and sampling options. `doctor --container` captures **whitelisted CLI flags** but not the engine's resolved defaults. Do not infer that prefix caching is enabled simply because the Docker script omits the disabling flag.

## Acceptance gates for a publishable claim

1. At least five completed first/repeated pairs; report pass rate and per-pair numbers, not just best-case numbers.
2. Confirm `/metrics` hits and query counters if available; otherwise label hit status **unverified**.
3. Repeat with the `agent` suite: shared long system context, changing user request, no claim of full agent correctness.
4. Keep decoding rate, first token, first *visible* token, and total latency separate.
5. Review power mode, container digest and concurrent client activity. If another process uses the model, counters cannot be reliably attributed.
6. To establish actual coding-agent reliability, add a separate task suite with tools, sandboxed execution, tests and human validation (tracked in [quality benchmark issue](issues/standardized-quality-evaluations.md)).

Generated reports under `results/` stay gitignored. Only publish manually reviewed, aggregate or numeric-only data. Never include prompts, responses, Docker environment, host mounts, tokens, addresses, or private repository content.
