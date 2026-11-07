# Initial Shockwave baseline — November 7, 2026

These are **user-observed measurements**, not measurements performed by this repository. They establish the initial configuration only; repeat them using this tool for comparable results.

| Dimension | Initial observed value |
| --- | --- |
| Device | NVIDIA Jetson AGX Thor Developer Kit, 128 GB unified memory |
| Jetson Linux | R39.2.1, kernel 6.8.12-1021-tegra |
| JetPack | 7.2.1-b49 |
| CUDA compiler | 13.2.86 |
| Docker | 29.1.3 |
| Container image | `ghcr.io/nvidia-ai-iot/vllm:qwen3.8-next-jetson-thor` |
| Image digest observed at pull | `sha256:512bf772c7ef221df1a66ab9c95546d77daeba6ba61723692852e6eb0cae7526` |
| Model | `local-inference-lab/Qwen3.8-Flash-Next-NVFP4` |
| Served model name | `Qwen3.8-Flash-Next` |
| GPU memory utilization | `0.90` |
| Configured max context | `212992` tokens (not stress-tested) |
| Max sequences | `1` |
| MTP | Disabled (bundled draft model path missing a safetensors shard) |
| Example short coding request | 253 output tokens, 47 reasoning, `stop` |
| Example short request latency | 11.09232 seconds |
| Short request effective throughput | 22.8 tokens/sec including reasoning and prefill overhead |
| Longer coding request | 1,826 completion tokens, 213 reasoning; server reported ~23–25 tokens/sec during decoding |

The tested model returned correct-looking DFS, Kahn's algorithm, and cycle reconstruction examples. That was a manual review, **not** an executed unit test or standardized code benchmark.

Known issues: MTP `/opt/qwen38-mtp-model/model-00001-of-00034.safetensors` was absent; full 262,144 context required more KV cache than available at `GPU_MEM=0.90`. Repeated Linux cache drops were used during startup on the test system; this project does not automatically drop caches.
