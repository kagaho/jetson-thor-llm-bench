"""Privacy-preserving live Docker launch fingerprint for reproducible benchmarks.

Only whitelisted serving flags and Docker runtime modes are copied from inspect.
Never persist full docker inspect JSON, environment, mounts, credentials or host paths.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess


# Only values with predictable public-safe formats are recorded.
SAFE_VALUES = {
    "--gpu-memory-utilization": r"(?:0(?:\.\d+)?|1(?:\.0+)?)",
    "--max-model-len": r"\d+",
    "--max-num-seqs": r"\d+",
    "--max-num-batched-tokens": r"\d+",
    "--kv-cache-memory-bytes": r"\d+(?:\.\d+)?[kKmMgGtT]?",
    "--kv-cache-dtype": r"(?:auto|bfloat16|float16|fp8|fp8_e4m3|fp8_e5m2)",
    "--mamba-ssm-cache-dtype": r"(?:float32|bfloat16|float16|auto)",
    "--reasoning-parser": r"[a-z0-9_\-]+",
    "--tool-call-parser": r"[a-z0-9_\-]+",
    "--served-model-name": r"[A-Za-z0-9._\-]+",
    "--port": r"\d{1,5}",
    "--seed": r"\d+",
}
SAFE_SWITCHES = {
    "--enable-auto-tool-choice",
    "--enable-prefix-caching",
    "--no-enable-prefix-caching",
    "--disable-prefix-caching",
    "--enable-chunked-prefill",
    "--disable-chunked-prefill",
    "--enable-prompt-tokens-details",
    "--disable-log-requests",
    "--enforce-eager",
}
KNOWN_SPECULATIVE = {"mtp", "ngram", "eagle", "eagle3", "draft_model"}


def parse_serve_arguments(argv: list[str]) -> dict:
    """Whitelist vLLM flags; unknown values, tokens and paths are never saved."""
    flags: dict = {}
    for index, token in enumerate(argv):
        key, sep, embedded = token.partition("=")
        if key in SAFE_SWITCHES:
            flags[key] = True
        elif key in SAFE_VALUES:
            value = embedded if sep else argv[index + 1] if index + 1 < len(argv) else ""
            flags[key] = value if re.fullmatch(SAFE_VALUES[key], value) else "[redacted]"
        elif key == "--speculative-config":
            raw = embedded if sep else argv[index + 1] if index + 1 < len(argv) else ""
            flags[key] = {"present": True}
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, dict):
                    method = parsed.get("method")
                    n = parsed.get("num_speculative_tokens")
                    if method in KNOWN_SPECULATIVE:
                        flags[key]["method"] = method
                    if type(n) is int and 0 <= n <= 16:
                        flags[key]["num_speculative_tokens"] = n
            except (ValueError, TypeError):
                pass
    return flags


def inspect_container(container: str) -> dict:
    """Observe the *running* container, not just the checked-in recipe."""
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}", container):
        raise ValueError("Invalid container name or ID")
    if not shutil.which("docker"):
        raise ValueError("Docker CLI unavailable; omit --container or run on the serving host")
    try:
        proc = subprocess.run(
            ["docker", "inspect", "--format", "{{json .}}", container],
            text=True, capture_output=True, timeout=8, check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ValueError(f"Docker inspection unavailable: {type(exc).__name__}") from None
    if proc.returncode != 0:
        raise ValueError("Docker inspection failed; ensure the container exists and you have Docker access")
    try:
        raw = json.loads(proc.stdout)
        config = raw.get("Config") or {}
        host = raw.get("HostConfig") or {}
        state = raw.get("State") or {}
        argv = config.get("Cmd") or []
        if not isinstance(argv, list) or not all(isinstance(x, str) for x in argv):
            raise ValueError("Docker inspection returned unexpected Cmd")
    except (ValueError, TypeError, AttributeError):
        raise ValueError("Unexpected Docker inspect format") from None
    flags = parse_serve_arguments(argv)
    # Be explicit: unmentioned flags may be active due to engine defaults.
    prefix = (
        "explicitly_enabled" if flags.get("--enable-prefix-caching") else
        "explicitly_disabled" if flags.get("--no-enable-prefix-caching") or flags.get("--disable-prefix-caching") else
        "not_explicitly_set_check_engine_default"
    )
    image = config.get("Image", "")
    if not isinstance(image, str) or not image.startswith("ghcr.io/nvidia-ai-iot/vllm:"):
        image = "[image not from known public NVIDIA baseline]"
    return {
        "capture_source": "docker_inspect_running_container",
        "container_running": state.get("Running") is True,
        "image": image,
        "docker": {
            "runtime": host.get("Runtime") if host.get("Runtime") in {"nvidia", "runc"} else "other_or_unavailable",
            "network_mode": host.get("NetworkMode") if host.get("NetworkMode") in {"host", "bridge", "none"} else "other_or_unavailable",
            "ipc_mode": host.get("IpcMode") if host.get("IpcMode") in {"host", "private", "none"} else "other_or_unavailable",
        },
        "vllm_flags": flags,
        "prefix_caching_flag": prefix,
        "mtp_flag": "explicitly_enabled" if "--speculative-config" in flags else "not_specified",
        "notes": [
            "Captured CLI flags are not the resolved engine defaults.",
            "No command, environment, bind mounts, host paths or credentials are recorded.",
            "Power mode, clocks, checkpoint revision and image digest still require explicit verification.",
        ],
    }


def checked_in_profile_fingerprint() -> dict | None:
    """Fingerprint the repository's declared Docker profile without storing its contents."""
    location = Path(__file__).resolve().parents[1] / "models" / "qwen3.8-flash-next" / "launch-profile.json"
    if not location.is_file():
        return None  # Installed-as-package users may not have the repository examples.
    contents = location.read_bytes()
    data = json.loads(contents)
    return {
        "path": "models/qwen3.8-flash-next/launch-profile.json",
        "profile": data.get("profile"),
        "sha256": hashlib.sha256(contents).hexdigest(),
        "kind": "declared_recipe_not_live_observation",
    }
