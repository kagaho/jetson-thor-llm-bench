# Publication figure provenance

[Back to README](../README.md)

All publication visuals are offline derivatives of the November 7 and November 8 reports. No new inference was run. The earlier `benchmark-proposal.gif` remains a conceptual suite map. Neither new GIF is a live terminal capture.

| Asset | Source and interpretation |
|---|---|
| [Results overview](figures/results-overview.svg) | [Comparison JSON](data/fp8-hybrid-comparison.json); C1 rate and separate scored synthetic suites |
| [Workload throughput](figures/throughput-by-workload.svg) | Same JSON, mean of two request rates by category |
| [Seeded outcomes](figures/seeded-outcomes.svg) | Same JSON, scorer 0.7.3, five variants per family |
| [Memory and energy](figures/memory-energy.svg) | [Comparison report](benchmarks/2026-11-08-fp8-hybrid-comparison.md) and JSON telemetry; different work and outcomes |
| [Prefix overview](figures/prefix-overview.svg) / [GIF](figures/prefix-responsiveness.gif) | [Five-pair report](benchmarks/2026-11-07-shockwave-five-pair-prefix-agent.md); measured medians, illustrative pacing |
| [Verification workflow](figures/verification-workflow.svg) / [GIF](figures/verification-workflow.gif) | Comparison report; conceptual reconstruction, not exact tool trace or timestamps |
| [Social image](figures/social-preview.png) | Comparison JSON; compact 1600×900 PNG for social use |

Generate with `node scripts/render_publication.cjs` from the repository root. Node is only an optional documentation dependency; the benchmark still requires Python's standard library only. The renderer uses deterministic, dependency-free SVG and raster export. It writes a SHA-256 manifest alongside the figures. The committed [source manifest](figures/publication-sources.json) records Git blob IDs from the source revision; the renderer writes the SHA-256 manifest on regeneration.

Historical raw logs were not available in this offline documentation pass. The two new animations do not contain raw model text, private paths or host details. Future real captures should be sanitized and accompanied by actual elapsed time and source hashes. Do not replace historical figures with new measurements without separate attribution.
