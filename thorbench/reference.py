"""Model provenance and published reference catalog (offline, read-only)."""
from __future__ import annotations

import json
import statistics
from importlib.resources import files
from pathlib import Path
from typing import Any


def _data(name: str) -> dict[str, Any]:
    return json.loads(files("thorbench").joinpath("data", name).read_text(encoding="utf-8"))


def model_metadata(model_name: str) -> dict[str, Any] | None:
    for model in _data("model_catalog.json")["models"]:
        if model["served_model_name"] == model_name or model["checkpoint_repo"] == model_name:
            return model
    return None


def list_references() -> str:
    refs = _data("public_references.json")
    lines = ["# Public model and benchmark references", "", refs["comparison_warning"], "",
             "| Source | Reported metric | Model variant | Source link |", "|---|---|---|---|"]
    for r in refs["references"]:
        value = f'{r["reported_value"]} {r["unit"]}' if r["reported_value"] is not None else "n/a — recipe only"
        lines.append(f'| {r["title"]} | {value} | {r["checkpoint"]} | {r["url"]} |')
    return "\n".join(lines) + "\n"


def compare_local_run(folder: Path) -> str:
    """Display observations side-by-side, explicitly without a cross-protocol speed ratio."""
    metadata_path, samples_path = folder / "metadata.json", folder / "samples.jsonl"
    if not (metadata_path.is_file() and samples_path.is_file()):
        raise ValueError("Run folder must contain metadata.json and samples.jsonl")
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    observations = [json.loads(line) for line in samples_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    values = [r["effective_tokens_s"] for r in observations if r.get("ok") and isinstance(r.get("effective_tokens_s"), (int, float))]
    rates = [r["decode_tokens_s"] for r in observations if r.get("ok") and isinstance(r.get("decode_tokens_s"), (int, float))]
    lines = ["# Local results and public references (non-equivalent protocols)", "",
             f'Local served model: `{metadata.get("model", "unknown")}`; test suite: `{metadata.get("suite", "unknown")}`.',
             f'Local complete requests: {sum(bool(r.get("ok")) for r in observations)}/{len(observations)}.',
             f'Local median effective output rate: {statistics.median(values):.2f} tokens/s (including prefill/TTFT)' if values else 'Local effective output rate: n/a.',
             f'Local median estimated decode rate: {statistics.median(rates):.2f} tokens/s' if rates else 'Local estimated decode rate: n/a.',
             "", "**Do not compute speedups from these rows.** Public reports use different checkpoints, prompts, MTP, and metric definitions.",
             "", list_references()]
    return "\n".join(lines)
