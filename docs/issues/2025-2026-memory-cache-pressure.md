# Recurring unified-memory / filesystem-cache pressure during vLLM startup on Jetson AGX Thor (observed 2025 and 2026)

> Draft GitHub issue. Public sanitized facts only. **Symptom recurrence has been observed; identical root cause across JetPack releases is NOT established.**

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
