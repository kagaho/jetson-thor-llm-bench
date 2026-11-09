#!/usr/bin/env python3
"""Run the existing nine suites with fixed settings; keep all output private."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
SEED = 3628200930879258838
IMAGE = ROOT / "docs/figures/benchmark-proposal.png"


@contextmanager
def telemetry(destination: Path):
    """Stop only our own read-only sampler when the run exits."""
    if not shutil.which("tegrastats"):
        yield
        return
    with (destination / "tegrastats.log").open("w") as output:
        process = subprocess.Popen(["tegrastats", "--interval", "1000"],
                                   stdout=output, stderr=subprocess.STDOUT)
        try:
            yield
        finally:
            process.terminate()
            process.wait(timeout=10)


def jobs(base_url: str, model: str, container: str, destination: Path):
    common = [sys.executable, "-m", "thorbench", "--base-url", base_url,
              "--model", model, "--timeout", "600"]
    yield "doctor-before", common + ["doctor", "--container", container]
    for suite in ("quick", "reasoning", "context", "vision", "prefix", "agent"):
        command = common + ["bench", "--suite", suite, "--container", container,
                            "--results-dir", str(destination / "suites")]
        if suite in ("prefix", "agent"):
            command += ["--runs", "5", "--warmup", "0", "--prefix-tokens", "8192"]
        else:
            command += ["--runs", "3", "--warmup", "1"]
        if suite == "context":
            command += ["--context-sizes", "8192,32768"]
        if suite == "vision":
            command += ["--image", str(IMAGE)]
        yield suite, command
    for module in ("tool_eval", "agent_eval", "generalize_eval"):
        command = [sys.executable, "-m", "thorbench." + module,
                   "--base-url", base_url, "--model", model, "--runs", "5",
                   "--max-tokens", "1024", "--timeout", "600",
                   "--results-dir", str(destination / "suites")]
        if module == "generalize_eval":
            command += ["--seed", str(SEED), "--max-turns", "10"]
        if module == "agent_eval":
            command += ["--max-turns", "8"]
        yield module, command
    yield "doctor-after", common + ["doctor", "--container", container]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--container", required=True)
    parser.add_argument("--results-dir", type=Path, required=True,
                        help="New directory below this repository's ignored results/")
    parser.add_argument("--checkpoint-revision", required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    destination = args.results_dir.resolve()
    if not destination.is_relative_to(ROOT / "results") or destination == ROOT / "results":
        parser.error("Use a new subdirectory of this repository's results/")
    plan = list(jobs(args.base_url, args.model, args.container, destination))
    if args.dry_run:
        print(json.dumps(plan, indent=2))
        return 0
    destination.mkdir(parents=True, exist_ok=False)
    sources = hashlib.sha256()
    for path in sorted((ROOT / "thorbench").rglob("*.py")):
        sources.update(str(path.relative_to(ROOT)).encode() + b"\0" + path.read_bytes())
    manifest = {
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "runner_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "thorbench_python_sha256": sources.hexdigest(),
        "vision_image_sha256": hashlib.sha256(IMAGE.read_bytes()).hexdigest(),
        "checkpoint_revision": args.checkpoint_revision,
        "container_image_id": subprocess.check_output(
            ["docker", "inspect", "--format", "{{.Image}}", args.container], text=True).strip(),
        "seed": SEED,
        "notes": ["Vision measures API smoke success only.",
                  "Prefix/agent pairs use fresh random markers by design, so their requests are not byte-identical across deployments.",
                  "All suites run sequentially; domain failures remain in their original reports."],
        "jobs": [], "status": "running",
    }
    manifest_path = destination / "comparison-manifest.json"

    def save():
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")

    save()
    with telemetry(destination):
        for name, command in plan:
            print(f"Starting {name}", flush=True)
            began = time.monotonic()
            record = {"suite": name, "command": command, "status": "running"}
            manifest["jobs"].append(record)
            save()
            try:
                with (destination / (name + ".log")).open("w") as output:
                    result = subprocess.run(command, cwd=ROOT, stdout=output, stderr=subprocess.STDOUT)
            except BaseException:
                record["status"] = "interrupted"
                manifest["status"] = "interrupted"
                save()
                raise
            record.update(status="completed", exit_code=result.returncode,
                          elapsed_s=round(time.monotonic() - began, 3))
            save()
            print(f"Finished {name}: exit={result.returncode}", flush=True)
            if name == "doctor-before" and result.returncode:
                manifest["status"] = "preflight_failed"
                save()
                return 1
    manifest.update(status="completed", finished_utc=datetime.now(timezone.utc).isoformat())
    save()
    return int(any(job.get("exit_code") for job in manifest["jobs"]))


if __name__ == "__main__":
    raise SystemExit(main())
