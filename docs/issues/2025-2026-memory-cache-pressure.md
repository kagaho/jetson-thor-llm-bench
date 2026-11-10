# Recurring unified-memory / filesystem-cache pressure during vLLM startup on Jetson AGX Thor (observed 2025 and 2026)

> **Resolved for the current workload through the documented B2 configuration.** Public sanitized facts only. Symptom recurrence across multiple JetPack versions was observed; identical root cause is not established.

## Occurrence across multiple JetPack versions

The operator reports that this issue occurred across **multiple JetPack versions**, rather than only one installation. The preserved early observation is from the Jetson Linux R38.x era, but its exact JetPack package revision was not captured; the later fully recorded environment is JetPack **7.2.1-b49 / Jetson Linux R39.2.1**. Do not infer an exact earlier JetPack version or an identical underlying defect from the recurrence.

## Resolution for the current workload

The startup issue is resolved operationally by the documented **B2 serving configuration**:

```text
--gpu-memory-utilization 0.88
--kv-cache-memory-bytes 4294967296
--max-model-len 131072
--max-num-seqs 1
```

This caps the KV cache at 4 GiB and leaves more startup headroom. The repository records that the initial 0.90 attempt with explicit KV still failed the startup gate, whereas B2 at 0.88 started successfully. Explicit KV sizing does not bypass the startup utilization check. The separate missing MTP shard and context-capacity problems remain distinct from this report.

Evidence: [B2 serving profile](https://github.com/kagaho/jetson-thor-llm-bench/blob/main/docs/SERVING_PROFILES.md#b2-command-memory-fix-with-a-persistent-container), [memory investigation](https://github.com/kagaho/jetson-thor-llm-bench/blob/main/docs/MEMORY_AB_EXPERIMENT.md), and merged configuration/lifecycle changes in [PR #7](https://github.com/kagaho/jetson-thor-llm-bench/pull/7), [PR #13](https://github.com/kagaho/jetson-thor-llm-bench/pull/13), and [PR #17](https://github.com/kagaho/jetson-thor-llm-bench/pull/17).

This closes the project's current startup blocker through configuration; it does not establish an upstream kernel/driver fix, identical cross-release causality, maximum-context capacity, or universal long-term stability. Continuous cache dropping is not required as the standing serving procedure.

## Summary

On Jetson AGX Thor 128 GB unified memory, filesystem caches and other users of system RAM can reduce memory reported as available to CUDA/vLLM during large-model startup. The operator previously found that explicitly reclaiming Linux page cache reduced memory pressure after a vLLM session, and encountered a related free-memory startup gate again on a fresh JetPack 7.2.1 system in November 2026.

This may be normal unified-memory accounting, cache reclamation behavior, or version-specific runtime behavior; it is **not** established to be a kernel leak, driver defect, or hardware failure. An actionable investigation would compare `/proc/meminfo`, GPU allocations, process memory, and the vLLM reservation check across clean cold starts.

## Environment / observations

### September 2025 — historical observation

- Device: Jetson AGX Thor 128 GB; Jetson Linux R38.x era (precise firmware/package revision was not captured in the available report).
- After stopping a vLLM workload, `tegrastats` reportedly showed RAM usage of approximately **62.7 / 125.8 GB**, with `/proc/meminfo` MemAvailable around **62.8 GB**.
- `jtop`/display services were among processes observed holding `nvmap` device nodes; this **does not prove** those processes caused a CUDA leak.
- The operator used `sudo sync` followed by `echo 3 | sudo tee /proc/sys/vm/drop_caches` to reclaim filesystem caches and proceed with further experimentation.
- No full error trace, consistent GPU process snapshot, or reproducible kernel bisect was preserved from that date.

### November 7, 2026 — fresh install

- Device: Jetson AGX Thor 128 GB; Jetson Linux **R39.2.1**, JetPack **7.2.1-b49**, CUDA **13.2**, Ubuntu 24.04 base.
- Workload: Qwen3.8 Flash Next NVFP4 through `ghcr.io/nvidia-ai-iot/vllm:qwen3.8-next-jetson-thor`, 125B MoE checkpoint.
- At `--gpu-memory-utilization 0.93`, vLLM failed its initialization gate:

  ```text
  Free memory on device cuda:0 (112.66/122.8 GiB) on startup
  is less than desired GPU memory utilization (0.93, 114.21 GiB).
  ```

- After dropping caches, the measurement rose to **113.24/122.8 GiB**, still below the 114.21 GiB gate; the cache drop did **not** completely resolve this setting.
- Changing only GPU memory utilization to **0.90** passed that gate. A separate MTP draft-model missing-file problem required MTP to be disabled; another distinct KV-cache limit required setting `--max-model-len 212992` instead of 262144.
- Final state: vLLM started, `/health` returned HTTP 200, and inference succeeded. The operator had also temporarily run repeated `drop_caches` during loading; causality of that step is unproven.

## Expected behavior

When genuinely reclaimable filesystem cache is present, large-model startup should either reclaim it safely or report actionable memory-accounting information. The memory budget should be diagnosable without repeated manual cache clearing. Note that reserving 93% of total device memory while running a desktop GUI may be simply too aggressive.

## Current workaround (not a production recommendation)

```bash
# Diagnose first; only reclaim filesystem caches when needed.
free -h
cat /proc/meminfo | grep -E 'MemTotal|MemAvailable|Cached|SReclaimable|Dirty|Writeback'
sudo sync
sudo sh -c 'echo 3 > /proc/sys/vm/drop_caches'
```

For the observed R39.2.1 Qwen workload, `--gpu-memory-utilization 0.90` was required to pass startup. Avoid a continuous cache-drop loop during ordinary inference or benchmark measurements: it can perturb disk I/O and performance, and it does not free active CUDA allocations.

## Data to collect on recurrence

- Complete `nvidia-smi`, `free -h`, `/proc/meminfo`, `tegrastats`, and process RSS before/after vLLM exit.
- JetPack release, kernel, full image digest, checkpoint revision, model context, MTP setting, power mode.
- Separate filesystem cache from CUDA allocations and other processes using unified memory.
- Reproduce across GUI on/off and clean boot if possible; confirm whether the same vLLM flags succeed without cache clearing.

## Scope / issue classification

- **Confirmed:** 2025 cache-pressure observation and 2026 vLLM free-memory reservation failure, with successful 2026 workaround.
- **Not confirmed:** same root cause, hardware damage, a cross-release kernel regression, NVIDIA driver leak, or a reproducible external upstream defect.
- Related project issues: MTP draft-model path missing and KV-cache/configured-context budget should be tracked independently.
