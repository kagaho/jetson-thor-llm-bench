# Qwen3.8 Flash Next — Jetson AGX Thor

**Status:** Confirmed to initialize and complete OpenAI-compatible chat requests on one 128 GB Jetson AGX Thor with JetPack 7.2.1. Full advertised context, image understanding accuracy and concurrency are **not yet validated**.

| Property | Verified baseline / source |
|---|---|
| Served name | `Qwen3.8-Flash-Next` |
| Checkpoint | [`local-inference-lab/Qwen3.8-Flash-Next-NVFP4`](https://huggingface.co/local-inference-lab/Qwen3.8-Flash-Next-NVFP4) |
| Architecture | `Qwen4ExpForConditionalGeneration` (runtime override) |
| Quantization | NVFP4 mixed precision |
| Container | `ghcr.io/nvidia-ai-iot/vllm:qwen3.8-next-jetson-thor` (see digest in baseline) |
| Hardware | Jetson AGX Thor Developer Kit, 128 GB unified memory |
| Software | JetPack 7.2.1; CUDA 13.2 |
| `--gpu-memory-utilization` | `0.90` |
| `--max-model-len` | `212992` (configured; not validated at full length) |
| `--max-num-seqs` | `1` |
| MTP | Disabled; draft-model shard was missing in tested image |

Sources: [NVIDIA Jetson AI Lab recipe](https://www.jetson-ai-lab.com/models/qwen3-8-flash-next/), [Hugging Face checkpoint](https://huggingface.co/local-inference-lab/Qwen3.8-Flash-Next-NVFP4), [public comparison caveats](../../docs/PUBLIC_BENCHMARKS.md).

## Serving recipe (optional)

[`serve.sh`](serve.sh) records the **working baseline**, not an automated installer. Requires Docker configured with the NVIDIA runtime and the appropriate access permissions.

```bash
# Run only when the current vLLM server is stopped; does not run from benchmark commands.
./models/qwen3.8-flash-next/serve.sh
```

The recipe starts in the foreground, binds port 8000 on **127.0.0.1**, reuses the standard local Hugging Face cache, and deliberately omits MTP speculative decoding. On the first run, model weights may require over 100 GB of disk space and almost all available shared memory. The model cache must remain untracked by Git.

The original failed attempts used GPU utilization 0.93 (failed the initial free-memory check), MTP with a missing checkpoint shard, and the native 262,144-token context (failed KV-cache validation). The successful recipe uses 0.90, MTP off and 212,992 configured tokens. See [observed baseline](baseline.md) and [issue drafts](../../docs/issues/).

**Do not use a `drop_caches` loop as a general model startup service.** Cache dropping was a manual experimental workaround for pressure on this particular unified-memory setup, is not guaranteed to help, and does not eliminate the need for appropriate memory budgeting.

## Benchmark commands

From the repository root while the API is healthy:

```bash
python3 -m thorbench doctor
python3 -m thorbench bench --suite quick --runs 3
python3 -m thorbench bench --suite reasoning --runs 2
python3 -m thorbench references
```

Results go to ignored `results/` directories and are **not public claims** until independently reviewed and published with their test methodology. See [baseline.md](baseline.md) for the initial manual results.
