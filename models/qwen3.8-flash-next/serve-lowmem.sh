#!/usr/bin/env bash
# Reproduce the November 8, 2026 B2 low-memory configuration.
# Do NOT run alongside the existing qwen38-flash-next container.
set -euo pipefail

NAME="qwen38-flash-next"
if docker container inspect "$NAME" >/dev/null 2>&1; then
  echo "Container $NAME already exists. Stop/remove it deliberately before starting this profile." >&2
  exit 2
fi

# Pin the exact same image digest that was used for the successful A and B2 tests.
IMAGE="ghcr.io/nvidia-ai-iot/vllm@sha256:512bf772c7ef221df1a66ab9c95546d77daeba6ba61723692852e6eb0cae7526"
MODEL="local-inference-lab/Qwen3.8-Flash-Next-NVFP4"
mkdir -p "$HOME/.cache/huggingface" "$HOME/.cache/vllm"

exec docker run -it --rm \
  --name "$NAME" \
  --runtime=nvidia \
  --gpus all \
  --network host \
  --ipc=host \
  -e NVIDIA_VISIBLE_DEVICES=all \
  -v "$HOME/.cache/huggingface:/root/.cache/huggingface" \
  -v "$HOME/.cache/vllm:/root/.cache/vllm" \
  "$IMAGE" \
  "$MODEL" \
  --host 127.0.0.1 \
  --served-model-name Qwen3.8-Flash-Next \
  --gpu-memory-utilization 0.88 \
  --kv-cache-memory-bytes 4294967296 \
  --max-model-len 131072 \
  --max-num-seqs 1 \
  --mamba-ssm-cache-dtype bfloat16 \
  --reasoning-parser qwen3 \
  --enable-auto-tool-choice \
  --tool-call-parser qwen3_xml \
  --hf-overrides '{"architectures":["Qwen4ExpForConditionalGeneration"],"model_type":"qwen4_exp"}'
