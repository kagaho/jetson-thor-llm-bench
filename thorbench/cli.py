"""CLI entry point; all benchmark traffic runs against an existing local vLLM server."""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from .client import APIError, VLLMClient
from .report import new_run_dir, save_row, summarize
from .reference import model_metadata, list_references, compare_local_run
from . import __version__
from .scenarios import NEEDLE, case_context, case_quick, case_reasoning, case_vision, case_prefix, case_agent
from .system import snapshot
from .deployment import inspect_container, checked_in_profile_fingerprint
from .cache_metrics import counter_deltas


def build_parser():
    parser = argparse.ArgumentParser(prog="thorbench", description="Reproducible vLLM benchmarks for NVIDIA Jetson Thor")
    parser.add_argument("--base-url", default=os.getenv("THOR_BENCH_BASE_URL", "http://127.0.0.1:8000"))
    parser.add_argument("--model", default=os.getenv("THOR_BENCH_MODEL", "Qwen3.8-Flash-Next"))
    parser.add_argument("--timeout", type=int, default=600)
    sub = parser.add_subparsers(dest="command", required=True)
    doctor = sub.add_parser("doctor", help="Check health, models, configured context and optional Docker launch")
    doctor.add_argument("--container", help="Inspect a running Docker container using a strict field allowlist")
    sub.add_parser("references", help="List verified model sources and reported public benchmarks (offline)")
    compare = sub.add_parser("compare", help="Compare a local result with public references; no cross-protocol ratios")
    compare.add_argument("--run", type=Path, required=True, help="Path to a results/<timestamp>-<suite> folder")
    bench = sub.add_parser("bench", help="Run sequential benchmarks and write results")
    bench.add_argument("--suite", choices=["quick", "reasoning", "context", "vision", "prefix", "agent"], default="quick")
    bench.add_argument("--runs", type=int, default=3)
    bench.add_argument("--warmup", type=int, default=1, help="Warmup calls per scenario, not recorded")
    bench.add_argument("--context-sizes", default="1024,4096,8192", help="Approximate context token sizes")
    bench.add_argument("--allow-large-context", action="store_true", help="Required above 32768 approximate tokens")
    bench.add_argument("--image", help="Local JPG/PNG/WEBP for vision suite; never copied to results")
    bench.add_argument("--results-dir", default="results")
    bench.add_argument("--container", help="Record actual sanitized Docker serving flags in metadata.json")
    bench.add_argument("--prefix-tokens", type=int, default=8192, help="Approximate shared context size for prefix/agent suites")
    bench.add_argument("--no-cache-metrics", action="store_true", help="Skip optional /metrics counter snapshots")
    return parser


def run(args) -> int:
    if args.command == "references":
        print(list_references())
        return 0
    if args.command == "compare":
        print(compare_local_run(args.run))
        return 0
    client = VLLMClient(args.base_url, args.model, args.timeout)
    if args.command == "doctor":
        ok = client.health()
        models = client.models()
        selected = next((m for m in models if m.get("id") == args.model), None)
        launch = inspect_container(args.container) if getattr(args, "container", None) else None
        print(json.dumps({
            "healthy": ok, "model_found": selected is not None,
            "model": args.model, "max_model_len": selected.get("max_model_len") if selected else None,
            "model_provenance": model_metadata(args.model),
            "bench_version": __version__,
            "platform": snapshot(),
            "deployment": launch,
            "declared_launch_profile": checked_in_profile_fingerprint(),
        }, indent=2))
        return 0 if ok and selected else 2

    if args.runs < 1 or args.runs > 25 or args.warmup < 0 or args.warmup > 10:
        raise ValueError("--runs must be 1..25; --warmup must be 0..10")
    if args.suite in ("prefix", "agent") and args.warmup != 0:
        raise ValueError("Prefix and agent suites require --warmup 0; --runs counts independent first/repeat pairs")
    if not client.health():
        raise APIError("Health endpoint returned a non-200 status")
    model_info = next((m for m in client.models() if m.get("id") == args.model), None)
    if model_info is None:
        raise APIError(f"Model {args.model!r} is not registered on the server")
    max_model_len = model_info.get("max_model_len")

    cases: list[tuple[str, dict, bool, bool, int | None]] = []
    if args.suite == "quick":
        cases = [("quick", case_quick(), True, False, None)]
    elif args.suite == "reasoning":
        cases = [(f"reasoning_{mode}", case_reasoning(mode), True, False, None) for mode in ("off", "low", "medium")]
    elif args.suite == "context":
        sizes = [int(s.strip()) for s in args.context_sizes.split(",") if s.strip()]
        if not sizes or any(n < 256 or n > 200000 for n in sizes):
            raise ValueError("Each context size must be between 256 and 200000 approximate tokens")
        if max(sizes) > 32768 and not args.allow_large_context:
            raise ValueError("Context tests above 32768 tokens require --allow-large-context")
        if isinstance(max_model_len, int) and max(sizes) >= max_model_len:
            raise ValueError("Context targets must remain below the advertised max_model_len")
        cases = [(f"context_{n}", case_context(n), False, True, None) for n in sizes]
    elif args.suite in ("prefix", "agent"):
        if not 1024 <= args.prefix_tokens <= 32768:
            raise ValueError("--prefix-tokens must be between 1024 and 32768")
        import uuid
        for pair in range(1, args.runs + 1):
            # Unique marker per pair; within a pair the full prefix is shared.
            nonce = uuid.uuid4().hex
            if args.suite == "prefix":
                payload = case_prefix(args.prefix_tokens, nonce)
                cases.extend([
                    ("prefix_first", payload, True, False, pair),
                    ("prefix_repeat", payload, True, False, pair),
                ])
            else:
                cases.extend([
                    ("agent_first", case_agent(args.prefix_tokens, nonce, "first"), True, False, pair),
                    ("agent_followup", case_agent(args.prefix_tokens, nonce, "followup"), True, False, pair),
                ])
    else:
        if not args.image:
            raise ValueError("Vision suite requires --image /path/to/image.jpg")
        cases = [("vision", case_vision(args.image), False, False, None)]

    dest = new_run_dir(Path(args.results_dir), args.suite)
    metadata = {
        "suite": args.suite,
        "date_utc": datetime.now(timezone.utc).isoformat(),
        "model": args.model,
        "model_provenance": model_metadata(args.model),
        "bench_version": __version__,
        "max_model_len": max_model_len,
        "platform": snapshot(),
        "deployment": inspect_container(args.container) if getattr(args, "container", None) else None,
        "declared_launch_profile": checked_in_profile_fingerprint(),
        "runs_per_scenario": 1 if args.suite in ("prefix", "agent") else args.runs,
        "pair_count": args.runs if args.suite in ("prefix", "agent") else None,
        "prefix_evidence_note": "Prometheus /metrics counters are server-wide and require an isolated serving endpoint for attribution; None means unavailable, not zero.",
        "warmup_per_scenario": args.warmup,
        "model_configuration_note": "--container records allowlisted running flags. Verify digest, power mode, clocks, model revision, resolved defaults manually.",
    }
    (dest / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    rows = []
    print(f"Writing private-by-default results to {dest}")
    for scenario, payload, streaming, is_context, pair_id in cases:
        count = 1 if pair_id is not None else args.runs
        print(f"\nScenario: {scenario} | stream={streaming} | runs={count}" +
              (f" | pair={pair_id}" if pair_id is not None else ""), flush=True)
        attempts = [0] if pair_id is not None else range(-args.warmup, args.runs)
        for attempt in attempts:
            warmup = attempt < 0
            measure_cache = pair_id is not None and not getattr(args, "no_cache_metrics", False)
            before = client.prefix_cache_counters() if measure_cache else None
            try:
                sample = client.chat(payload, streaming=streaming)
                metrics = sample.metrics()
                valid = sample.finish_reason == "stop"
                if is_context:
                    valid = valid and NEEDLE in sample.content.strip()
                elif scenario == "vision":
                    valid = valid and bool(sample.content.strip())
                after = client.prefix_cache_counters() if measure_cache else None
                row = {
                    "scenario": scenario, "run": attempt + 1, "ok": valid,
                    "error": None, **metrics,
                }
                if pair_id is not None:
                    row["pair_id"] = pair_id
                    row.update(counter_deltas(before, after))
                    if row["cache_evidence"] == "unavailable" and (row.get("cached_prompt_tokens") or 0) > 0:
                        row["cache_evidence"] = "response_cached_tokens_reported"
                if not valid:
                    row["error"] = "incomplete response or scenario validation failed"
            except (APIError, ValueError, TimeoutError, OSError) as exc:
                row = {"scenario": scenario, "run": attempt + 1, "ok": False,
                       "error": str(exc)[:200]}
                if pair_id is not None:
                    row["pair_id"] = pair_id
                    row.update(counter_deltas(None, None))
            label = "warmup" if warmup else f"pair {pair_id}" if pair_id is not None else f"run {attempt + 1}"
            print(f"  {label}: {'PASS' if row['ok'] else 'FAIL'} | "
                  f"latency={row.get('elapsed_s', 'n/a')}s | "
                  f"TTFT={row.get('ttft_s', 'n/a')}s | "
                  f"decode={row.get('decode_tokens_s', 'n/a')} tok/s", flush=True)
            if not warmup:
                rows.append(row)
                save_row(dest, row)
        # Stop longer context testing after an unsuccessful size to avoid hammering the host.
        if is_context and not all(r["ok"] for r in rows if r["scenario"] == scenario):
            print("Context test failed; not advancing to larger sizes.")
            break
    summarize(rows, dest)
    print(f"\nReport: {dest / 'summary.md'}")
    return 0 if rows and all(r["ok"] for r in rows) else 1


def main():
    parser = build_parser()
    args = parser.parse_args()
    try:
        return run(args)
    except (APIError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
