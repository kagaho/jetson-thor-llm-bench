# Changelog

All notable changes follow [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- Matched B2/H2 deployment comparison across all nine suites and the pinned forum C1 protocol, with reviewed numeric data, reproducible charts and the unsuccessful H1 startup retained in the report.
- Comparison orchestration with immutable protocol/source fingerprints, private output preservation, preflight gating, board-input telemetry and export checks for complete denominators and matching seeds.
- Pinned conservative FP8-hybrid launcher, model provenance and build/start/stop guide; measured H2 retains MTP 3 with B2's 4 GiB KV, 131072 context and single-sequence limits.
- Pinned FP8-hybrid second benchmark plan and resumable Hugging Face base/delta downloader with manifest and checksum verification; paired measurements remain pending.
- Illustrated guide to all nine benchmark suites and offline CI checks, with Mermaid workflows for streaming/reasoning, context, vision, fixed-agent tasks, tool-routing cases and report interpretation.
- Serving-profile reference with complete A/B2 Docker commands, shared features, dated live observations and guidance to use B2 for the current sequential benchmark workload.
- Seeded-test family and workflow diagrams, plus outcome/latency SVG charts generated from reviewed numeric-only data with historical scorer/seed attribution.

### Changed
- B2 launcher now runs detached and retains its container for manual start/stop, preserving its verified `0.88` utilization, 4 GiB KV cache and 131,072-token context settings.

## [0.7.0] — 2026-11-08

### Added
- Seed-varying, in-memory agent benchmark with six task families, generated repository paths, identifiers, values, decoys, and retryable failures.
- Reproducible fixture seeds, strict allowlisted simulated tools, evidence-ordered completion scoring, and private summary reports including token usage and p90 task latency.
- Offline safety, state, scoring and API-protocol tests; seeded variants are not independently withheld real-world coding tasks.
- Generalization scorer/protocol versions, evaluator source fingerprint, sanitized discovery/final-answer failure categories, and aggregate failure counts including request errors.

### Fixed
- Generalization scorer v0.7.2 rejects symbol-origin traces where an unrelated search precedes the active-file read but actual active-path discovery occurs only afterward; positive and negative seeded controls preserve valid discovery/read traces.
- Generalization scorer 0.7.3 compares complete numeric tokens with exact decimal arithmetic, rejecting wrong signed/fractional/grouped values that previously matched expected integer digits while accepting equivalent numeric notation. Seeded positive and negative controls cover all three affected task families.
- Clarify that scorer revision numbers are separate from package versions, GitHub tags and published releases; package v0.7.0 includes scorer 0.7.3 and protocol 1.
- Document the existing 24/30 seed-varying run separately from the original 4/6 and corrected 5/6 results; no historical outcomes are rescored.

## [0.6.0] — 2026-11-08

### Added
- Multi-turn coding-agent evaluator using an isolated, deterministic in-memory repository with four simulated tools and five task-level outcomes.
- Explicit missing-document and transient-error recovery, synthetic test-fix-retest scoring, and no-tool negative control.
- Private numeric per-task metrics (latency, turns, simulated calls, error/recovery counts, summed prompt/completion tokens) and guarded result limits.
- Offline scripted API protocol, state-machine and path-safety tests. No real source edits, shell execution, model restarts or external model dependencies.

## [0.5.0] — 2026-11-08

### Added
- Read-only first-decision tool routing plus validated experimental B2 KV-memory profile and documented A/B case study.
- Recorded baseline A versus explicit-4-GiB B2 memory allocation, startup gate and prompt/context tradeoffs; two safe sequential launch profiles.
- Added per-case median prompt/output token metrics to first-tool-decision benchmark summaries.
- Added B2 A/B report and reproducible SVG graph documenting 30/30 results on both configurations; no causal speedup claimed.

- Read-only first-decision coding-agent tool-routing benchmark with exact structured function/argument scoring, offline tests, and no tool execution.
- Memory/KV-cache A/B restart runbook with baseline capture, physical memory constraints, and rollback gates; Mermaid decision workflows.

## [0.4.0] — 2026-11-07

### Added
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
- Source-attributed comparison of external FP8-hybrid MTP performance and a coding-agent field report, explicitly not an apples-to-apples ranking.


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
