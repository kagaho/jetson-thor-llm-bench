# Qwen3.8 Flash Next serving profiles

**Operational choice, November 8, 2026:** keep the healthy **B2** container running for the current sequential benchmarks. Its 131,072-token context is sufficient for those tasks. B2 is the preferred profile for this workload; its speed, quality and long-term stability have not been established as superior to A.

The often-copied `0.90` / `212992` command is **baseline A**. The latest live inspection matched **B2**, with `0.88` utilization, an explicit 4 GiB KV cache and `131072` context. A checked-in recipe describes a launch configuration; inspect the running container before deciding which profile is active.

## Profile comparison

| Setting | Baseline A | B2: preferred for current benchmarks |
|---|---|---|
| Launch script | [`serve.sh`](../models/qwen3.8-flash-next/serve.sh) | [`serve-lowmem.sh`](../models/qwen3.8-flash-next/serve-lowmem.sh) |
| Structured recipe | [`launch-profile.json`](../models/qwen3.8-flash-next/launch-profile.json) | [`launch-profile-lowmem.json`](../models/qwen3.8-flash-next/launch-profile-lowmem.json) |
| `--gpu-memory-utilization` | `0.90` | `0.88` |
| `--kv-cache-memory-bytes` | Omitted; automatic sizing | `4294967296` = **4 GiB** |
| `--max-model-len` | `212992` | `131072` |
| `--max-num-seqs` | `1` | `1` |
| Image in recipe | Original mutable tag | Verified image pinned by digest |
| Intended use | Workloads requiring a larger configured context | Current sequential inference and simulated-agent benchmarks |

`--gpu-memory-utilization` sets a memory budget; it does not set GPU compute utilization. Explicit `--kv-cache-memory-bytes` controls KV sizing instead of the automatic budget calculation. In the observed build, the initial utilization-based free-memory check still ran with an explicit KV budget: the first 4 GiB attempt at `0.90` failed that startup check, while B2 at `0.88` started. See the [memory A/B investigation](MEMORY_AB_EXPERIMENT.md).

The context cap covers **prompt plus generated output**. Neither profile has been validated at its configured maximum. B2 passed earlier retrieval probes at 7,992 and 31,652 actual prompt tokens; the larger configured cap alone does not establish long-context reliability. Historical memory snapshots for A and B2 were taken under different conditions, so they do not isolate the effect of these flags.

## Latest verified live observation

Read-only inspection on **2026-11-08 UTC** found:

- Healthy API and available `Qwen3.8-Flash-Next` model; API context limit `131072`.
- Docker flags matching B2's `0.88`, `4294967296`, `131072` and `1` settings above.
- vLLM version `0.28.1rc1.dev580+g385dce36b`.
- Running image repository digest `ghcr.io/nvidia-ai-iot/vllm@sha256:512bf772c7ef221df1a66ab9c95546d77daeba6ba61723692852e6eb0cae7526`.
- Container running, not restarting, OOM flag false and restart count zero.
- Approximately **4.6 GiB available system memory**, no swap, and no requests running or queued at inspection.
- Positive cumulative server-wide prefix-cache query/hit counters; these do not attribute a cache hit to a particular request.

This is a dated snapshot, not a continuously updated status display or a maximum-load guarantee. The inspected container used the public image tag, which resolved to the digest above. The B2 reproduction command below pins that verified digest. A zero restart count does not establish the history of containers previously removed by `--rm`.

The recent [25/30 simulated-agent run](benchmarks/2026-11-08-generalization-followup.md#fresh-versioned-live-run-scorer-072-2530) had five no-tool verbosity failures and no request errors. Those outcomes provide no evidence that a serving restart would fix the failures. Prompt/protocol experiments must remain separately versioned.

## Check what is actually running

Run these read-only checks from the repository root:

```bash
python3 -m thorbench doctor --container qwen38-flash-next
curl -fsS --max-time 10 http://127.0.0.1:8000/health
free -h
docker inspect --format 'running={{.State.Running}} restarting={{.State.Restarting}} oom_killed={{.State.OOMKilled}} restarts={{.RestartCount}}' qwen38-flash-next
```

In doctor output, compare `deployment.vllm_flags` and the API `max_model_len`. `declared_launch_profile` fingerprints the original A recipe; it is **not evidence that A is running**. The inspector reports allowlisted CLI flags, not every resolved engine default. It does not expose raw container environment variables or mounts.

## B2 command: reproduce the current workload profile

**Manual launch only after deliberately stopping the existing server. Do not run this command now while the healthy container is active.** Both profiles use the same name, API port and large model allocation.

This reproduces [`serve-lowmem.sh`](../models/qwen3.8-flash-next/serve-lowmem.sh). Prefer that script for future launches: it checks whether the named container already exists and refuses to start in that case.

```bash
mkdir -p "$HOME/.cache/huggingface" "$HOME/.cache/vllm"

docker run -it --rm \
  --name qwen38-flash-next \
  --runtime=nvidia \
  --gpus all \
  --network host \
  --ipc=host \
  -e NVIDIA_VISIBLE_DEVICES=all \
  -v "$HOME/.cache/huggingface:/root/.cache/huggingface" \
  -v "$HOME/.cache/vllm:/root/.cache/vllm" \
  ghcr.io/nvidia-ai-iot/vllm@sha256:512bf772c7ef221df1a66ab9c95546d77daeba6ba61723692852e6eb0cae7526 \
  local-inference-lab/Qwen3.8-Flash-Next-NVFP4 \
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
```

## Baseline A command: original larger-context recipe

**Manual alternative after deliberately stopping the existing server.** This is the original command supplied by the operator and the default configuration of [`serve.sh`](../models/qwen3.8-flash-next/serve.sh). That script permits environment overrides, so inspect its effective arguments after launch.

```bash
mkdir -p "$HOME/.cache/huggingface" "$HOME/.cache/vllm"

docker run -it --rm \
  --name qwen38-flash-next \
  --runtime=nvidia \
  --gpus all \
  --network host \
  --ipc=host \
  -e NVIDIA_VISIBLE_DEVICES=all \
  -v "$HOME/.cache/huggingface:/root/.cache/huggingface" \
  -v "$HOME/.cache/vllm:/root/.cache/vllm" \
  ghcr.io/nvidia-ai-iot/vllm:qwen3.8-next-jetson-thor \
  local-inference-lab/Qwen3.8-Flash-Next-NVFP4 \
  --host 127.0.0.1 \
  --served-model-name Qwen3.8-Flash-Next \
  --gpu-memory-utilization 0.90 \
  --max-model-len 212992 \
  --max-num-seqs 1 \
  --mamba-ssm-cache-dtype bfloat16 \
  --reasoning-parser qwen3 \
  --enable-auto-tool-choice \
  --tool-call-parser qwen3_xml \
  --hf-overrides '{"architectures":["Qwen4ExpForConditionalGeneration"],"model_type":"qwen4_exp"}'
```

The original image tag can change. For a controlled profile comparison, use the same pinned image digest for both launches and record the checkpoint revision, workload, token usage and runtime conditions. Keep historical measurements attributed to their original configuration.

## Shared features and limits

| Feature | Configuration and meaning |
|---|---|
| Model weights | `local-inference-lab/Qwen3.8-Flash-Next-NVFP4`; mixed NVFP4 quantization |
| Model loading | `--hf-overrides` selects `Qwen4ExpForConditionalGeneration` / `qwen4_exp` |
| GPU access | NVIDIA runtime, `--gpus all` and `NVIDIA_VISIBLE_DEVICES=all` |
| Local API | Host networking with vLLM bound to `127.0.0.1`; default API port 8000 |
| Shared memory | `--ipc=host` uses the host IPC namespace |
| Persistent caches | Hugging Face and vLLM caches are mounted from the standard `$HOME/.cache` directories |
| Container lifecycle | `-it --rm`: interactive foreground process; container removed when it exits; no restart policy configured in these commands |
| Scheduler limit | `--max-num-seqs 1`; the benchmark requests are sequential |
| Mamba SSM precision | `--mamba-ssm-cache-dtype bfloat16` explicitly selects SSM-state precision |
| Attention KV precision | `--kv-cache-dtype` omitted; no explicit precision is established by these commands. NVFP4 weights and BF16 SSM state do not establish attention-KV precision |
| Reasoning parsing | `--reasoning-parser qwen3`; reasoning effort remains a request-level setting |
| Tool calls | `--enable-auto-tool-choice` and `--tool-call-parser qwen3_xml`; the benchmark interprets calls only in its in-memory simulator |
| Prefix caching | No explicit CLI switch in either recipe. The live snapshot had cumulative cache-hit evidence; effective behavior must be measured for a workload |
| Chunked prefill | No explicit CLI switch; effective default remains unverified in this record |
| MTP speculative decoding | No `--speculative-config` in either command; MTP remains disabled for this setup. The previously attempted compatible draft-model shard was missing |
| Vision and maximum context | Not validated by successful chat/tool requests; require separate scored tests |

Argument definitions are described in the [vLLM v0.28.0 engine documentation](https://docs.vllm.ai/en/v0.28.0/configuration/engine_args/). The local image is a development build; its observed startup behavior takes precedence over assumptions from another version's defaults.

## When to revisit the profile

Keep B2 for the current workload while the service stays healthy. Plan a separate configuration experiment if work requires more than 131,072 combined prompt/output tokens, actual memory failures occur, or a different runtime feature needs evaluation. A's larger configured cap still requires validation against the intended workload.

Before any deliberate restart, record health, sanitized flags, image digest, memory and workload metrics. Test one change at a time and retain the previous profile for comparison. Neither the Python benchmark release nor verbosity failures require restarting Docker. Do not start both profiles together or automate cache-dropping loops.

For historical measurements and experiment limits, see the [memory A/B runbook](MEMORY_AB_EXPERIMENT.md), [A/B observations](benchmarks/2026-11-08-shockwave-b2-vs-a.md) and [optimization matrix](OPTIMIZATION_MATRIX.md).
