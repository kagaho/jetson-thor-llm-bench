#!/usr/bin/env bash
# H2: retain the custom kernels/MTP with B2's conservative memory limits.
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
NAME="qwen38-flash-next-fast-v3-fp8hybrid-lowmem"
if docker container inspect "$NAME" >/dev/null 2>&1; then
  echo "Container $NAME already exists. Use docker start $NAME to resume it." >&2
  exit 2
fi
for OTHER in qwen38-flash-next qwen38-flash-next-fast-v3-fp8hybrid; do
  if [[ "$(docker inspect --format '{{.State.Running}}' "$OTHER" 2>/dev/null || true)" == true ]]; then
    echo "Stop $OTHER before loading another model server." >&2
    exit 2
  fi
done

# Keep third-party launch code in an ignored cache, pinned and checksummed.
SOURCE="$ROOT_DIR/.cache/forum-runtime/pinned-hybrid-launcher.sh"
ADAPTED="$ROOT_DIR/.cache/forum-runtime/start-hybrid-lowmem.sh"
EXPECTED="c211030a6007eca0ee11d435b7f2745d8c777f499acf8cd4d9ab274168cb5665"
mkdir -p "$(dirname "$SOURCE")"
if [[ ! -f "$SOURCE" ]]; then
  curl --fail --location --retry 2 \
    https://raw.githubusercontent.com/pastoriomarco/NemoClaw-Thor/dd07dcc2f5650916e18e2c706144c6fd1f8bf13c/serving/start-qwen38-flash-next-fast.sh \
    --output "$SOURCE"
fi
ACTUAL="$(sha256sum "$SOURCE")"
if [[ "${ACTUAL%% *}" != "$EXPECTED" ]]; then
  echo "Pinned launcher checksum mismatch; inspect the cached source." >&2
  exit 2
fi
python3 - "$SOURCE" "$ADAPTED" <<'PY'
from pathlib import Path
import sys
text = Path(sys.argv[1]).read_text()
needle = '--kv-cache-dtype "$FLASHNEXT_KV"'
assert text.count('--host 0.0.0.0') == 1 and text.count(needle) == 1
text = text.replace('--host 0.0.0.0', '--host 127.0.0.1')
text = text.replace(needle, '--kv-cache-memory-bytes 4294967296 ' + needle)
Path(sys.argv[2]).write_text(text)
PY

export HF_CACHE="${HF_CACHE:-$HOME/.cache/thorbench-fp8-hybrid}"
export VLLM_CACHE="${VLLM_CACHE:-$HOME/.cache/thorbench-fp8-hybrid-lowmem-vllm}"
export TORCH_CACHE="${TORCH_CACHE:-$HOME/.cache/thorbench-fp8-hybrid-lowmem-torch}"
export FLASHINFER_CACHE="${FLASHINFER_CACHE:-$HOME/.cache/thorbench-fp8-hybrid-lowmem-flashinfer}"
export FLASHNEXT_IMAGE="${FLASHNEXT_IMAGE:-nemoclaw-thor/qwen38-flash-next-vllm:sm110-fast-v3}"
export FLASHNEXT_CONTAINER="$NAME"
export FLASHNEXT_GPU_MEM=0.88 FLASHNEXT_CONTEXT=131072 FLASHNEXT_MAX_SEQS=1
export FLASHNEXT_DETACH=1 FLASHNEXT_NO_RM=1
docker image inspect "$FLASHNEXT_IMAGE" >/dev/null
exec bash "$ADAPTED"
