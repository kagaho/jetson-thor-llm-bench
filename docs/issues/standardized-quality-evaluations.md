# Add reproducible public quality benchmark adapters (HumanEval+, IFEval, MMLU-Pro)

## Goal

The v0.2.0 `quick`, `reasoning`, `context`, and `vision` suites are **latency and smoke-test suites**, not standardized quality benchmarks. Add optional adapters for authoritative published datasets so Shockwave's coding, reasoning and instruction-following quality can be meaningfully compared with publicly reported metrics.

## Candidates and official sources

| Benchmark | Task | Canonical source |
|---|---|---|
| HumanEval+ / EvalPlus | Code correctness with enlarged tests | https://github.com/evalplus/evalplus |
| IFEval | Verifiable instruction following | https://github.com/google-research/google-research/tree/master/instruction_following_eval |
| MMLU-Pro | Multidomain knowledge and reasoning | https://github.com/TIGER-AI-Lab/MMLU-Pro |

## Acceptance criteria

- Pin benchmark dataset version, scoring code commit, split, dataset license, exact prompt template, number of samples and random seed.
- Use the same inference endpoint and model revision metadata, include temperature/thinking/max_tokens.
- Record accuracy separately from time-to-first-token and throughput. Do not infer accuracy from a successful HTTP 200 or valid-looking code.
- Execute untrusted generated code **only in a hardened, resource-limited sandbox** with no network access; avoid running it directly on the Jetson host.
- Include tests for answer extraction, failed requests, no-response cases, and deterministic scoring.
- Keep dataset contents, model responses and private prompts out of Git until publication/legal review.
- Never compare a subset with a full-set leaderboard score without explicit labeling.

## Why this is an issue, not part of v0.2.0

Each official benchmark has distinct licensing, scoring, sandboxing and prompt protocols. Copying published accuracy percentages into a performance table without actually running the same protocol would be misleading.
