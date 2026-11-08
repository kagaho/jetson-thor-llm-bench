#!/usr/bin/env bash
# Stage pinned public weights only. Does not build an image or start inference.
set -euo pipefail

NAME="qwen38-fp8-hybrid-download"
IMAGE="ghcr.io/nvidia-ai-iot/vllm@sha256:512bf772c7ef221df1a66ab9c95546d77daeba6ba61723692852e6eb0cae7526"
HF_CACHE="${HF_CACHE:-$HOME/.cache/thorbench-fp8-hybrid}"
if docker container inspect "$NAME" >/dev/null 2>&1; then
  echo "Container $NAME already exists. Inspect its logs; use docker start $NAME to resume an interrupted download." >&2
  exit 2
fi
docker image inspect "$IMAGE" >/dev/null
mkdir -p "$HF_CACHE"

# Use the already cached image for huggingface_hub, without GPU allocation.
# Retain logs and permit resuming with docker start after interruption.
exec docker run -d --restart=no --pull never \
  --name "$NAME" --network host --user "$(id -u):$(id -g)" \
  -v "$HF_CACHE:/hf" -e HF_HOME=/hf \
  -e HF_HUB_DISABLE_XET=1 -e PYTHONUNBUFFERED=1 \
  --entrypoint python3 "$IMAGE" -c '
import hashlib
import json
from pathlib import Path
from huggingface_hub import snapshot_download

base = "RadixArk/Qwen3.8-Flash-Next-NVFP4"
base_rev = "7b719225242aacd3dbd3f9407468c2ee9a9d2594"
delta = "pastoriomarco/Qwen3.8-Flash-Next-NVFP4-FP8-Hybrid-Delta"
delta_rev = "358162ffaaeb4372c79843d9cd1f67d3654593da"
print("Downloading pinned base:", base, base_rev, flush=True)
base_path = snapshot_download(base, revision=base_rev, max_workers=2)
print("Base snapshot complete:", base_path, flush=True)
delta_path = Path("/hf/deltas") / delta.replace("/", "--") / delta_rev
names = {"model-bf16-00001.safetensors", "model-bf16-00010.safetensors",
         "model-bf16-00011.safetensors", "model-bf16-00012.safetensors",
         "model.safetensors.index.json"}
snapshot_download(delta, revision=delta_rev, local_dir=delta_path,
                  allow_patterns=sorted(names | {"fp8-hybrid-manifest.json"}), max_workers=2)
manifest = json.loads((delta_path / "fp8-hybrid-manifest.json").read_text())
if (manifest.get("base_model") != base or manifest.get("base_revision") != base_rev
        or set(manifest.get("files", {})) != names):
    raise SystemExit("Unexpected delta manifest or base revision")
for name in sorted(names):
    path = delta_path / name
    expected = manifest["files"][name]
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    if path.stat().st_size != expected["size"] or digest.hexdigest() != expected["sha256"]:
        raise SystemExit("Delta checksum mismatch: " + name)
    print("Verified:", name, flush=True)
print("Pinned base and verified delta staged. Hybrid assembly and custom runtime build remain.", flush=True)
'
