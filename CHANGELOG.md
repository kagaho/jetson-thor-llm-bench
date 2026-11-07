# Changelog

All notable changes follow [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added (v0.4.0 candidate)
- Repeated first/repeat prefix pairs (`--runs` counts pairs) and synthetic agent-like shared-context follow-ups with changing instructions.
- Optional read-only Prometheus `/metrics` cache query/hit counter deltas, including explicit unavailable/zero/reset distinction and attribution caveats.
- Paired comparisons in `summary.md`/`summary.json` with sample counts and clearly qualified TTFT ratios.
- Reviewed numeric case study from two operator-provided Shockwave runs, reproducible SVG figure, table, and Mermaid evidence/agent workflows.
- Published five-pair Shockwave prefix and synthetic-agent results (20/20 successful requests), with a separate TTFT/total-latency figure and qualified server-wide cache-hit evidence.
- Protocol for cache evidence, isolation requirements, and separation of synthetic responsiveness from agent correctness.

## [0.3.0] — 2026-11-07

### Added
- Full, explicit baseline Docker launch profile in JSON alongside the existing reproducible `serve.sh`.
- Optional `doctor --container` / `bench --container` observation of whitelisted running vLLM flags, without storing raw Docker inspect output or credentials.
- Paired synthetic `prefix` benchmark with cached prompt-token reporting when returned by the serving API.
- Feature matrix and six Mermaid diagrams explaining vLLM optimization modes, memory budgeting, tool calling and agentic deployment trade-offs.
- Source-attributed comparison of Marco Pastorio's FP8-hybrid MTP performance and Ryan Johns's real agent workflow, explicitly not an apples-to-apples ranking.


## [0.2.0] — 2026-11-07

### Added
- Per-model directories for the first Qwen3.8 Flash Next integration (guide, launch recipe, observed baseline).
- Machine-readable model provenance, including the exact served name and checkpoint repository.
- Public reference catalog with provenance and warnings against invalid cross-protocol speed comparisons.
- `thorbench references` and `thorbench compare --run ...` offline commands.
- `summary.json` for automation and comparison, alongside existing Markdown reports.
- Issue templates, PR template, release workflow, and a draft reproducible Jetson unified-memory issue.
- Tracking issue draft for standardized HumanEval+, IFEval, and MMLU-Pro quality benchmarks (not yet implemented).
- Contributor workflow, release procedure, version metadata, and an example reproducibility record.

## [0.1.0] — 2026-11-07

### Added
- Standard-library benchmark harness and offline tests.
- Quick, reasoning, context and vision smoke-test suites.
- Jetson Thor Qwen3.8 Flash Next baseline recipe and observed measurements.
- Privacy-preserving result capture and CI.
