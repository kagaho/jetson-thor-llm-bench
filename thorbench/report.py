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
        "- Streaming token counts depend on the server returning usage in SSE. `n/a` means unreported, not zero.", ""]
    (destination / "summary.md").write_text("\n".join(lines), encoding="utf-8")

    (destination / "summary.json").write_text(json.dumps(structured, indent=2) + "\n", encoding="utf-8")
