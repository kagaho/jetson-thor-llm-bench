# Qwen3.8 Flash Next FP8 hybrid on Thor

This is the second checkpoint/runtime configuration, using pinned RadixArk NVFP4 routed experts, an FP8 dense-weight delta, and the custom SM110 runtime. See the [benchmark plan and preflight findings](../../docs/FP8_HYBRID_BENCHMARK_PLAN.md). It is the same model family as the NVIDIA-image baseline. Build, load and operational outcomes must remain separate from quality and throughput measurements.

The [completed comparison](../../docs/benchmarks/2026-11-08-fp8-hybrid-comparison.md) measured **41.16 tok/s C1**, versus B2's **24.22**, with mixed workflow outcomes. The [structured H2 profile](launch-profile.json) records actual pins and limits. One retained-container restart passed before measurement; sustained stability remains untested.

## Artifacts and build

The weights and runtime source are pinned in the plan. This repository does not vendor external repositories or redistribute model weights. Fetch source archives into its ignored build cache:

```bash
mkdir -p .cache/forum-runtime/recipe .cache/forum-runtime/upstream
curl -fL --retry 2 \
  https://api.github.com/repos/pastoriomarco/NemoClaw-Thor/tarball/dd07dcc2f5650916e18e2c706144c6fd1f8bf13c \
  -o .cache/forum-runtime/recipe.tar.gz
tar -xzf .cache/forum-runtime/recipe.tar.gz -C .cache/forum-runtime/recipe --strip-components=1
curl -fL --retry 2 \
  https://api.github.com/repos/blazux/qwen3.8-Flash-DGX/tarball/4b723de2e2c465d866738b57ae64bde6e8c07744 \
  -o .cache/forum-runtime/upstream.tar.gz
tar -xzf .cache/forum-runtime/upstream.tar.gz -C .cache/forum-runtime/upstream --strip-components=1
```

Build while inference is stopped. These reproduce the pinned recipe's four build layers; record resulting image IDs:

```bash
docker build --progress=plain --build-arg DET_ARCH=110a \
  -t nemoclaw-thor/qwen38-flash-next-vllm:sm110 .cache/forum-runtime/upstream
docker build --progress=plain \
  -f .cache/forum-runtime/recipe/serving/docker/Dockerfile.qwen38-flash-next-sm110 \
  -t nemoclaw-thor/qwen38-flash-next-vllm:sm110-flashinfer-moe .cache/forum-runtime/recipe
docker build --progress=plain \
  -f .cache/forum-runtime/recipe/serving/docker/Dockerfile.qwen38-flash-next-gdn-sm110 \
  -t nemoclaw-thor/qwen38-flash-next-vllm:sm110-gdn-cuda .cache/forum-runtime/recipe
docker build --progress=plain \
  -f .cache/forum-runtime/recipe/serving/docker/Dockerfile.qwen38-flash-next-fast-v3 \
  -t nemoclaw-thor/qwen38-flash-next-vllm:sm110-fast-v3 .cache/forum-runtime/recipe
```

The [download helper](download.sh) uses the cached NVIDIA image and verifies the pinned base/delta. After its final verification message, assemble using the pinned upstream helper:

```bash
HF_CACHE="$HOME/.cache/thorbench-fp8-hybrid" \
  bash .cache/forum-runtime/recipe/serving/apply-qwen38-flash-next-fp8-delta.sh
```

No local quantization is needed. The apply helper checks every changed file again and preserves the base snapshot. Do not write a `.prepared` marker by hand.

## H2 retained serving profile

H1, the pinned recipe's larger automatic-KV profile, was aborted on this host before API readiness after GPU/display monitoring blocked. H2 uses **0.88 utilization, explicit 4 GiB KV, 131072 context and one sequence**, retaining MTP 3, the fused kernels and the compilation-cache workaround. This is an adapted configuration; it does not establish the forum's original performance claim.

Create once, after stopping other model servers:

```bash
bash models/qwen3.8-flash-next-fp8-hybrid/serve.sh
```

The wrapper verifies the pinned upstream launcher, changes its binding to localhost and adds the explicit KV budget. The cache and image environment variables can be overridden; record overrides when measuring. Existing containers are never replaced automatically.

```bash
docker logs --follow --tail 100 qwen38-flash-next-fast-v3-fp8hybrid-lowmem
# Ctrl+C exits the viewer and leaves serving running.

docker stop --timeout 120 qwen38-flash-next-fast-v3-fp8hybrid-lowmem
docker start qwen38-flash-next-fast-v3-fp8hybrid-lowmem
curl -fsS --max-time 10 http://127.0.0.1:8050/health
```

Wait for initialization after each start. API base: `http://127.0.0.1:8050/v1`; model ID: `qwen3.8-flash-next`. A configured 131072-token cap is not proof of correctness at that length. Finite smoke and benchmark results do not establish sustained-load stability.
