"""Non-identifying platform info only: no hostnames, users, IPs, or serials."""
from __future__ import annotations
import platform
import shutil
import subprocess


def _output(args: list[str]) -> str | None:
    if not shutil.which(args[0]):
        return None
    try:
        return subprocess.run(args, capture_output=True, text=True, timeout=5, check=False).stdout.strip()[:300]
    except (OSError, subprocess.TimeoutExpired):
        return None


def snapshot() -> dict:
    return {
        "architecture": platform.machine(),
        "kernel_release": platform.release(),
        "jetson_release": _output(["cat", "/etc/nv_tegra_release"]),
        "nvcc": _output(["/usr/local/cuda/bin/nvcc", "--version"]),
        "note": "No hostname, IP, username, environment variables, serial numbers, or GPU UUIDs collected.",
    }
