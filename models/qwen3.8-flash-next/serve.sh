#!/usr/bin/env bash
# OPTIONAL: restart the verified Shockwave baseline. DO NOT RUN while your current vLLM is serving.
set -euo pipefail

IMAGE="${VLLM_IMAGE:-ghcr.io/nvidia-ai-iot/vllm:qwen3.8-next-jetson-thor}"
MODEL="${HF_MODEL:-local-inference-lab/Qwen3.8-Flash-Next-NVFP4}"
CTX="${MAX_MODEL_LEN:-212992}"
GPU_UTIL="${GPU_MEMORY_UTILIZATION:-0.90}"

mkdir -p "$HOME/.cache/huggingface" "$HOME/.cache/vllm"

exec docker run -it --rm \
  --name qwen38-flash-next \
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
  --gpu-memory-utilization "$GPU_UTIL" \
  --max-model-len "$CTX" \
  --max-num-seqs 1 \
  --mamba-ssm-cache-dtype bfloat16 \
  --reasoning-parser qwen3 \
  --enable-auto-tool-choice \
  --tool-call-parser qwen3_xml \
  --hf-overrides '{"architectures":["Qwen4ExpForConditionalGeneration"],"model_type":"qwen4_exp"}'
