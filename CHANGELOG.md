# Changelog

All notable changes follow [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.2.0] — 2026-11-07 (proposed; release after PR merge)

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
