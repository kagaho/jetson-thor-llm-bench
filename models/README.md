# Model-specific benchmark integrations

The `thorbench/` Python package is **model-agnostic**. The `models/` directory contains deployment recipes and published, explicitly labeled observations for individual checkpoints.

Each model directory should include:

- `README.md` — exact model identity, supported device/runtime, citations and reproducibility caveats.
- `serve.sh` — optional, reviewed serving recipe; never invoked automatically by the benchmark harness.
- `baseline.md` — historical manual observations, separate from repeatable `results/` measurements.

The machine-readable registry remains in [`thorbench/data/model_catalog.json`](../thorbench/data/model_catalog.json). Public claims and methodology caveats remain in [`docs/PUBLIC_BENCHMARKS.md`](../docs/PUBLIC_BENCHMARKS.md).

## Current model integrations

- [Qwen3.8 Flash Next NVFP4 on Jetson AGX Thor](qwen3.8-flash-next/README.md)

For new models, add a directory and a registry entry, then benchmark using the same protocol. Do not put Hugging Face tokens, model weights, downloaded checkpoints or private hardware identifiers into Git.
