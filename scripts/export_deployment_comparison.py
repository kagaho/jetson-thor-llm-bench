#!/usr/bin/env python3
"""Export reviewed numeric summaries, never raw prompts, answers or host logs."""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
import statistics

EXPECTED = {"quick": 3, "reasoning": 9, "context": 6, "vision": 3,
            "prefix": 10, "agent": 10, "tool-routing": 30,
            "agent-multiturn": 25, "agent-generalization": 30}


def numeric_only(value):
    if isinstance(value, dict):
        return {key: numeric_only(item) for key, item in value.items()
                if isinstance(item, dict) or type(item) in (int, float, bool) or item is None}
    return value


def telemetry(path):
    if not path.exists():
        return None
    samples = []
    for line in path.read_text().splitlines():
        stamp = re.match(r"(\d{2}-\d{2}-\d{4} \d{2}:\d{2}:\d{2})", line)
        power = re.search(r"\bVIN (\d+)mW", line)
        memory = re.search(r"\bRAM (\d+)/(\d+)MB", line)
        temperature = re.search(r"\bgpu@([\d.]+)C", line)
        if stamp and power and memory and temperature:
            samples.append((datetime.strptime(stamp[1], "%m-%d-%Y %H:%M:%S"),
                            int(power[1]), int(memory[1]), float(temperature[1])))
    if len(samples) < 2:
        return None
    gaps = [(b[0] - a[0]).total_seconds() for a, b in zip(samples, samples[1:])]
    energy = sum((a[1] + b[1]) / 2 * delta for a, b, delta in zip(samples, samples[1:], gaps)) / 3600000
    return {"samples": len(samples), "span_s": (samples[-1][0] - samples[0][0]).total_seconds(),
            "maximum_sample_gap_s": max(gaps),
            "mean_board_input_w": round(statistics.mean(s[1] for s in samples) / 1000, 3),
            "peak_board_input_w": max(s[1] for s in samples) / 1000,
            "estimated_board_input_wh": round(energy, 4),
            "peak_tegrastats_ram_mb": max(s[2] for s in samples),
            "peak_gpu_temperature_c": max(s[3] for s in samples)}


def forum_c1(path):
    text = path.read_text()
    pattern = r"\[(Q&A|Code|JSON|Math|LongCode)\] (\d+) tokens in ([\d.]+)s = [\d.]+ tok/s \(prompt: (\d+)\)"
    rows = [{"category": m[1], "completion_tokens": int(m[2]), "elapsed_s": float(m[3]),
             "prompt_tokens": int(m[4])} for m in re.finditer(pattern, text)]
    completed = "=== Done ===" in text
    result = {"expected_requests": 10, "reported_successes": len(rows), "completed": completed, "requests": rows}
    expected = ["Q&A", "Code", "JSON", "Math", "LongCode"] * 2
    if completed and [row["category"] for row in rows] == expected:
        rates = [sum(row["completion_tokens"] for row in rows[start:start+5]) /
                 sum(row["elapsed_s"] for row in rows[start:start+5]) for start in (0, 5)]
        result.update(mean_two_pass_end_to_end_tokens_s=round(statistics.mean(rates), 6),
                      pooled_end_to_end_tokens_s=round(sum(r["completion_tokens"] for r in rows) /
                                                      sum(r["elapsed_s"] for r in rows), 6),
                      pass_end_to_end_tokens_s=[round(rate, 6) for rate in rates])
    return result


def arm(directory):
    manifest = json.loads((directory / "comparison-manifest.json").read_text())
    if manifest["status"] != "completed":
        raise ValueError("Incomplete process orchestration; retain its original reports")
    suites = {}
    for folder in sorted((directory / "suites").iterdir()):
        metadata = json.loads((folder / "metadata.json").read_text())
        name = metadata["suite"]
        if name in suites or name not in EXPECTED:
            raise ValueError("Unexpected or duplicate suite")
        summary_path = folder / "summary.json"
        summary = json.loads(summary_path.read_text())
        count = sum(s["total"] for s in summary["scenarios"].values()) if "scenarios" in summary else summary["total"]
        if count != EXPECTED[name]:
            raise ValueError("Unexpected denominator: " + name)
        suites[name] = {"summary": numeric_only(summary),
                        "summary_sha256": hashlib.sha256(summary_path.read_bytes()).hexdigest()}
        rows = [json.loads(line) for line in (folder / "samples.jsonl").read_text().splitlines()]
        if len(rows) != count:
            raise ValueError("Row count does not match denominator")
        passed = sum(s["passes"] for s in summary["scenarios"].values()) if "scenarios" in summary else summary["passed"]
        if sum(row.get("ok") is True for row in rows) != passed:
            raise ValueError("Pass count does not match saved outcomes")
        token_counts = {}
        for key in ("prompt_tokens", "completion_tokens"):
            values = [row[key] for row in rows if type(row.get(key)) in (int, float)]
            token_counts[key] = {"reported_samples": len(values), "sum": sum(values),
                                 "median": statistics.median(values) if values else None}
        suites[name]["token_counts"] = token_counts
        if name in ("prefix", "agent"):
            followups = [row for row in rows if row["scenario"].endswith(("repeat", "followup"))]
            suites[name]["followup_cache_evidence"] = dict(Counter(row.get("cache_evidence", "unavailable")
                                                                 for row in followups))
        if name == "agent-generalization":
            suites[name]["scorer_version"] = metadata["scorer_version"]
            suites[name]["protocol_version"] = metadata["protocol_version"]
            suites[name]["seed"] = metadata["seed"]
            suites[name]["implementation_sha256"] = metadata["implementation_sha256"]
            suites[name]["failure_reasons"] = dict(Counter(row["reason"] for row in rows if not row["ok"]))
    if set(suites) != set(EXPECTED):
        raise ValueError("All nine suites are required")
    return {**{key: manifest[key] for key in ("git_commit", "runner_sha256", "thorbench_python_sha256",
             "vision_image_sha256", "checkpoint_revision", "container_image_id", "seed")},
            "job_exit_codes": {job["suite"]: job["exit_code"] for job in manifest["jobs"]},
            "suites": suites, "telemetry": telemetry(directory / "tegrastats.log")}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = {"schema_version": 1, "b2": arm(args.runs / "b2"), "hybrid": arm(args.runs / "hybrid")}
    for key in ("runner_sha256", "thorbench_python_sha256", "vision_image_sha256", "seed"):
        if result["b2"][key] != result["hybrid"][key]:
            raise ValueError("Protocol mismatch: " + key)
    for key in ("scorer_version", "protocol_version", "seed", "implementation_sha256"):
        if result["b2"]["suites"]["agent-generalization"][key] != result["hybrid"]["suites"]["agent-generalization"][key]:
            raise ValueError("Generalization mismatch: " + key)
    for label in ("b2", "hybrid"):
        result[label]["forum_c1"] = forum_c1(args.runs / (label + "-forum-c1.log"))
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print("Exported numeric-only paired summaries:", args.output)


if __name__ == "__main__":
    main()
