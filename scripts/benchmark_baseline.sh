#!/usr/bin/env bash
# Safe read-only benchmark workflow. Never starts/stops the model or clears Linux caches.
set -euo pipefail
CONTAINER="${THOR_BENCH_CONTAINER:-qwen38-flash-next}"
python3 -m thorbench doctor --container "$CONTAINER"
python3 -m thorbench bench --suite quick --runs 3 --warmup 1 --container "$CONTAINER"
python3 -m thorbench bench --suite prefix --runs 1 --warmup 0 --prefix-tokens 8192 --container "$CONTAINER"
python3 -m thorbench bench --suite reasoning --runs 2 --warmup 1 --container "$CONTAINER"
