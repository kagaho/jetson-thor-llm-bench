"""Public-safe metrics reporting. Never store input prompts or model outputs."""
from __future__ import annotations

import json
import statistics
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def new_run_dir(root: Path, suite: str) -> Path:
    now = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    directory = root / f"{now}-{suite}"
    i = 1
    while directory.exists():
        directory = root / f"{now}-{suite}-{i}"
        i += 1
    directory.mkdir(parents=True, exist_ok=False)
    return directory


def save_row(destination: Path, row: dict[str, Any]):
    with (destination / "samples.jsonl").open("a", encoding="utf-8") as fp:
        fp.write(json.dumps(row, sort_keys=True) + "\n")


def summarize(rows: list[dict[str, Any]], destination: Path):
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(row["scenario"], []).append(row)
    lines = [
        "# Benchmark results", "",
        "This report was generated on the benchmark host. **Local results are gitignored.**", "",
        "TTFT: first streamed reasoning/content token; TTFC: first visible content token.",
        "Decode tokens/sec excludes time before TTFT and includes reasoning tokens.",
        "Context sizes are approximate targets; use `prompt_tokens` in samples.jsonl for actual counts.",
        "", "| Scenario | Pass/total | Median latency | Median TTFT | Median TTFC | Median decode tok/s |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    def med(metric: str, records: list[dict[str, Any]], suffix="s") -> str:
        vals = [r[metric] for r in records if isinstance(r.get(metric), (int, float))]
        return f"{statistics.median(vals):.2f}{suffix}" if vals else "n/a"
    structured = {"schema_version": 1, "scenarios": {}}
    def median_value(metric: str, records: list[dict[str, Any]]) -> float | None:
        values = [r[metric] for r in records if isinstance(r.get(metric), (int, float))]
        return round(statistics.median(values), 4) if values else None
    for scenario, items in grouped.items():
        good = [r for r in items if r.get("ok")]
        structured["scenarios"][scenario] = {
            "passes": len(good), "total": len(items),
            "median_elapsed_s": median_value("elapsed_s", good),
            "median_ttft_s": median_value("ttft_s", good),
            "median_ttfc_s": median_value("ttfc_s", good),
            "median_effective_tokens_s": median_value("effective_tokens_s", good),
            "median_decode_tokens_s": median_value("decode_tokens_s", good),
            "median_cached_prompt_tokens": median_value("cached_prompt_tokens", good),
        }
        lines.append(
            f"| `{scenario}` | {len(good)}/{len(items)} | "
            f"{med('elapsed_s', good)} | {med('ttft_s', good)} | "
            f"{med('ttfc_s', good)} | {med('decode_tokens_s', good, '')} |"
        )
    lines += ["", "## Interpretation", "",
        "- `ok` requires successful HTTP completion and `finish_reason=stop`. Context probes also require the target code.",
        "- Successful API output is not a verified quality evaluation of generated code or visual understanding.",
        "- Compare test runs only when model, quantization, clocks, power profile, concurrency, and prompts are comparable.",
        "- Streaming token counts depend on the server returning usage in SSE. `n/a` means unreported, not zero.",
        "- Prefix suite reuses identical prompts within one run; prefix hits and cold-start state must be verified, not assumed.", ""]
    # Pair rows share a unique number within this run. Do not compare different
    # runs as cold-cache reproductions without controlling server/cache state.
    pair_rows: dict[int, dict[str, dict[str, Any]]] = {}
    for row in rows:
        if type(row.get("pair_id")) is int:
            role = row["scenario"].split("_", 1)[-1]
            pair_rows.setdefault(row["pair_id"], {})[role] = row
    if pair_rows:
        pair_values = []
        lines.extend(["", "## Paired first/follow-up observations", "",
                      "**Server cache hits are not established from TTFT alone.** Optional `/metrics` "
                      "counters aggregate all server traffic; use an isolated endpoint for attribution.", "",
                      "| Pair | First TTFT | Repeat/follow-up TTFT | Ratio | Follow-up cache evidence |",
                      "|---:|---:|---:|---:|---|"])
        for pair in sorted(pair_rows):
            pair_obj = pair_rows[pair]
            first = pair_obj.get("first")
            second = pair_obj.get("repeat") or pair_obj.get("followup")
            if not first or not second or not (first.get("ok") and second.get("ok")):
                continue
            ft, st = first.get("ttft_s"), second.get("ttft_s")
            ratio = round(ft / st, 4) if isinstance(ft, (int, float)) and isinstance(st, (int, float)) and st > 0 else None
            pair_values.append({"pair_id": pair, "first_ttft_s": ft, "followup_ttft_s": st,
                                "ttft_ratio": ratio, "followup_cache_evidence": second.get("cache_evidence", "unavailable"),
                                "followup_hit_tokens_delta": second.get("cache_hit_tokens_delta"),
                                "followup_query_tokens_delta": second.get("cache_query_tokens_delta")})
            lines.append(f"| {pair} | {ft:.3f}s | {st:.3f}s | {ratio:.2f}× | "
                         f"{second.get('cache_evidence', 'unavailable')} |" if ratio is not None else
                         f"| {pair} | n/a | n/a | n/a | {second.get('cache_evidence', 'unavailable')} |")
        ttft_ratios = [p["ttft_ratio"] for p in pair_values if p["ttft_ratio"] is not None]
        structured["paired_comparison"] = {
            "valid_pairs": len(pair_values),
            "median_ttft_ratio": round(statistics.median(ttft_ratios), 4) if ttft_ratios else None,
            "pairs": pair_values,
            "limitations": "descriptive only; TTFT reduction does not prove KV-cache hits; counters are server-wide",
        }
        if ttft_ratios:
            lines.extend(["", f"Median per-pair TTFT ratio across {len(ttft_ratios)} pairs: "
                          f"**{statistics.median(ttft_ratios):.2f}×** (descriptive, not proof of caching)."] )
    (destination / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (destination / "summary.json").write_text(json.dumps(structured, indent=2) + "\n", encoding="utf-8")
