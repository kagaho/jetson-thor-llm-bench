# CONTEXT.md — Jetson Thor LLM Bench / Codex CLI Handoff

> **Scope (strict):** This handoff applies ONLY to [kagaho/jetson-thor-llm-bench](https://github.com/kagaho/jetson-thor-llm-bench), checked out on Shockwave at `~/Documents/jetson-thor-llm-bench`. Do not access, modify, or create PRs in other repositories.
>
> **Roles:** **Codex CLI is the developer**: it reads code, edits the real repository, runs tests, and prepares branches/PRs. **Qwen3.8 Flash Next is the model under evaluation**, served by local vLLM. Qwen-selected tools in the agent harness are interpreted by an in-memory simulator; they never execute actual shell commands, tests, or host file changes.
>
> **Snapshot:** Based on this development conversation and the actual GitHub repository reviewed November 7–8, 2026. Development branch `feat/seeded-agent-generalization` at `31ea3e5290b17f493df9c58d089d2028cbf2beaf`. [Draft PR #9](https://github.com/kagaho/jetson-thor-llm-bench/pull/9) targets `main` and is not merged. This document is proposed on a separate documentation branch based on that feature branch. Recheck current repository state before editing.
>
> **Evidence labels:** **Verified — source** = reviewed GitHub code/CI. **Verified — operator** = terminal output provided from Shockwave, not reproduced by Codex. **Hypothesis** = untested explanation. **Planned** = unfinished action. A seed reproduces generated fixtures; model answers and timing may still differ.

## 1. Project purpose, architecture, objectives

This project is a lightweight, reproducible, privacy-preserving **Python 3.10+ standard-library benchmark** for local LLM/VLM inference on **NVIDIA Jetson AGX Thor** using an **already-running OpenAI-compatible vLLM server**. setuptools is a build dependency only; the benchmark modules run from the checkout without installing external runtime packages.

Objectives:
- **Inference:** streamed time-to-first-generated-token (TTFT, including reasoning if available), first-visible-content (TTFC), end-to-end latency, prompt/completion/reasoning tokens, estimated decode throughput, finish reasons and warmup.
- **Serving reproducibility:** model/checkpoint/quantization, Docker image digest and declared vs observed vLLM flags, configured context, unified-memory and KV-cache budgeting, system/power/clock confounders.
- **Context/prefix:** approximate-length needle retrieval, independent identical-prefix pairs, synthetic shared-prefix changed-task pairs, optional server-wide cache-hit/query counter evidence.
- **Agent-readiness proxies:** first structured tool decision, multi-turn tool schema compliance, authoritative file discovery vs decoys, error recovery, synthetic failing-test→allowlisted edit→passing-test, no-tool decisions, answer grounding and instruction compliance.
- **Integrity:** deterministic fixture generator, hidden oracle, explicit positive/negative scoring gates, failures in denominators, regression coverage and privacy-safe reports.

Architecture:

~~~text
Codex CLI (development assistant, real Git files/tests/PRs)
  |
  v
thorbench Python package
  |-- cli.py, scenarios.py, client.py, report.py
  |-- deployment.py, cache_metrics.py, system.py, reference.py
  |-- tool_eval.py       six FIXED first-tool-decision cases; NO execution
  |-- agent_eval.py      five FIXED simulated multi-turn tasks
  |-- generalize_eval.py six SEED-VARYING simulated task families
  |      +-- InMemoryRepo: allowed list/search/read/test/replace on dict fixtures
  |
  +--> local http://127.0.0.1:8000 -> vLLM -> Qwen3.8-Flash-Next
  |
  +--> ignored results/<UTC timestamp>-<suite>/
       metadata.json, samples.jsonl, summary.md, summary.json
~~~

**No general real-repository coding correctness or SWE-bench claims.** Model-generated shell commands, code edits and real tests are not executed. A returned HTTP 200, tool call, or synthetic PASS is not a production fix.

## 2. Hardware, model, deployment: historical verified state

**Verified — source / historical operator records:**
- Host: `shockwave-01`, NVIDIA **Jetson AGX Thor Developer Kit with 128 GB unified memory**.
- Baseline OS/software: Jetson Linux **R39.2.1**, kernel **6.8.12-1021-tegra**, JetPack **7.2.1-b49**, CUDA compiler **13.2.86**, Docker **29.1.3**. Check live state before new claims.
- Only locally evaluated model documented here: checkpoint `local-inference-lab/Qwen3.8-Flash-Next-NVFP4`, served as `Qwen3.8-Flash-Next`, mixed **NVFP4** quantization, vLLM architecture/model type overrides `Qwen4ExpForConditionalGeneration` / `qwen4_exp`. Do not mistake external model reports for local measurements.
- Serving image `ghcr.io/nvidia-ai-iot/vllm:qwen3.8-next-jetson-thor`, recorded digest `sha256:512bf772c7ef221df1a66ab9c95546d77daeba6ba61723692852e6eb0cae7526`, historical vLLM version `0.28.1rc1.dev580+g385dce36b`.
- API `http://127.0.0.1:8000`: `/health`, `/v1/models`, `/v1/chat/completions`, optional `/metrics`. Docker container `qwen38-flash-next`. Recipe flags: `--max-num-seqs 1`, `--mamba-ssm-cache-dtype bfloat16`, `--reasoning-parser qwen3`, `--enable-auto-tool-choice`, `--tool-call-parser qwen3_xml`.

Two launch profiles; both are **optional** recipes and benchmarks do not start either:

| Parameter | Baseline A | Experimental B2 |
|---|---|---|
| Script | `models/qwen3.8-flash-next/serve.sh` | `models/qwen3.8-flash-next/serve-lowmem.sh` |
| GPU memory utilization threshold | 0.90 | 0.88 |
| KV budget | auto, observed ~5.26 GiB | explicit 4 GiB / 4294967296 B |
| Configured max context | 212,992 | 131,072 |
| KV token capacity reported | 214,535 | 159,862 |
| Available system memory after workload (different snapshots) | 1.1 GiB | 2.9 GiB |
| Fixed first-decision routing | 30/30 | 30/30 |
| Median tool-decision latency | 2.9165 s | 3.1947 s |

**Verified:** First 4 GiB explicit-KV attempt at 0.90 failed the *startup* utilization memory gate: 109.94 GiB available vs 110.52 GiB required. B2 at 0.88 started; explicit KV allocation did **not** bypass that initial gate. B2 context smoke probes passed at 7,992 actual prompt tokens / 91 completion tokens / 9.8524s and 31,652 prompt tokens / 90 completion tokens / 25.603s. Neither configured maximum context nor long-term stability is validated.

**Hypotheses/limitations:** B2 is not proven faster or better; multiple settings changed, memory measurements were at different times, power/clocks/cache warmth and concurrency were not controlled. Completion lengths rose on some B2 tool cases (no-tool case 94 tokens/4.30s A vs 140/6.44s B2), potentially explaining longer wall time without proving a decode-rate change. Original native 262,144-token context failed KV validation and an earlier 0.93-utilization startup failed. Report actual token lengths and do not attribute differences to KV sizing alone.

**Operational decisions:**
- **Do not restart the healthy vLLM container merely to continue the Python benchmark.**
- Never run A and B2 simultaneously or start scripts while serving container exists; unified-memory headroom is tight.
- MTP speculative decoding remains **disabled**: the observed compatible draft-model safetensors shard was missing.
- Do not automate Linux `drop_caches`; previous manual cache drops were experimental, not a validated general remedy.
- Unspecified prefix caching and chunked-prefill flags imply **unknown effective defaults**, not necessarily OFF.
- Use `python3 -m thorbench doctor --container qwen38-flash-next` for sanitized observed flags; declarations are not proof of all runtime defaults.
- Keep API loopback-bound; use SSH tunnel if needed, not an Internet-exposed inference port.
- External FP8-hybrid/MTP tok/s reports and other agent systems involve different weights/runtime/protocols. No apples-to-apples ranking.

Model documentation: `models/qwen3.8-flash-next/{README.md,baseline.md,launch-profile.json,launch-profile-lowmem.json,serve.sh,serve-lowmem.sh}`; `docs/MEMORY_AB_EXPERIMENT.md`; `docs/benchmarks/2026-11-08-shockwave-b2-vs-a.md`; `docs/benchmarks/2026-11-08-shockwave-b2-output-length-context.md`.

## 3. Repository layout, modules and entry points

**Verified — source:**

~~~text
pyproject.toml                         Python >=3.10; setuptools; version 0.7.0 candidate
Makefile                               test/doctor/quick/reasoning/context
README.md, CHANGELOG.md, SECURITY.md, CONTRIBUTING.md
.github/workflows/ci.yml              Python 3.12, compileall/references/unittest
models/qwen3.8-flash-next/             model docs and A/B launch profiles/scripts
thorbench/
  __main__.py                          python -m thorbench -> cli.main
  cli.py                               doctor, references, compare, bench
  client.py                            VLLMClient: HTTP, SSE streaming, usage
  scenarios.py                         quick/reasoning/context/vision/prefix/agent
  report.py                            timestamped sanitized reports
  system.py                            platform snapshot
  deployment.py                        whitelisted Docker inspection/profile fingerprint
  cache_metrics.py                     Prometheus cache counters/deltas
  reference.py                         public model/reference catalogue
  tool_eval.py                         v0.5 six fixed first-tool choices
  agent_eval.py                        v0.6 fixed simulated multi-turn evaluation
  generalize_eval.py                   v0.7 seed-varying simulated-agent evaluation
  data/model_catalog.json, public_references.json
tests/
  test_generalize_eval.py              generator, grading, safety, protocol, reports
  test_agent_eval.py                   v0.6 simulated workflow
  test_tool_eval.py                    v0.5 structured tool selection
  test_client.py, test_cli_integration.py, test_cache_metrics.py, ...
docs/
  METHODOLOGY.md, AGENT_BENCHMARK_PROTOCOL.md
  AGENT_TOOL_EVAL.md, AGENT_MULTI_TURN_EVAL.md
  AGENT_GENERALIZATION_EVAL.md, MEMORY_AB_EXPERIMENT.md
  OPTIMIZATION_MATRIX.md, benchmarks/, diagrams/, figures/, issues/
  last-test.txt                        operator-provided LOCAL output path (see below)
scripts/benchmark_baseline.sh          read-only smoke workflow
results/                               ignored: local benchmark artifacts
~~~

**Critical local handoff note:** The user reports that **the output of the last tests is in `docs/last-test.txt`**. GitHub inspection returned **404 on both `main` and `feat/seeded-agent-generalization`** for this path, so it is NOT confirmed as a tracked file. **Codex must read it locally FIRST**, if present, and check timestamps/commit and privacy. Do not invent its contents or commit the raw log without review.

Direct commands, from repo root:

~~~bash
python3 -m unittest discover -s tests -v
python3 -m thorbench doctor --container qwen38-flash-next
python3 -m thorbench bench --suite quick --runs 3
python3 -m thorbench bench --suite reasoning --runs 2
python3 -m thorbench bench --suite context --runs 1 --warmup 0
python3 -m thorbench bench --suite prefix --runs 5 --warmup 0 --prefix-tokens 8192
python3 -m thorbench bench --suite agent --runs 5 --warmup 0 --prefix-tokens 8192
python3 -m thorbench.tool_eval --runs 2
python3 -m thorbench.agent_eval --runs 5
python3 -m thorbench.generalize_eval --runs 1 --seed 6213207535837610165
python3 -m thorbench references
python3 -m thorbench compare --run results/<existing-folder>
~~~

The **`agent` suite in `thorbench bench`** is a *responsiveness* shared-prefix test, not a coding-agent tool benchmark. The quality harnesses `tool_eval`, `agent_eval` and `generalize_eval` are **separate module entry points**; there is no `bench --suite agent-generalization`. Runtime standard library only; do not assume pytest, LangGraph, or other frameworks.

## 4. Evaluation methodology, scoring contract, security

- Requests are **sequential**, not concurrency tests; warmups excluded when used.
- TTFT = first **generated** streamed SSE delta (including reasoning if available); TTFC = first **visible** content delta; whole-request latency = wall time. Nonstreaming multi-turn calls do not provide streamed TTFT/TTFC.
- Effective tokens/sec and approximate decode tokens/sec are *different metrics*. Decode estimate in `docs/METHODOLOGY.md` is `(completion_tokens - 1)/(elapsed_s - ttft_s)`; it is not a universal standardized output benchmark. Report prompt/completion/reasoning token usage alongside latency.
- Context and prefix target sizes use approximate character/token heuristics; report **actual** API `prompt_tokens`. A `finish_reason=length` is incomplete, even with some output.
- `prefix` and synthetic `agent` pairs require `--warmup 0`; their `--runs` count **pairs**. Median *paired* TTFT ratio is not necessarily the ratio of two marginal median TTFTs.
- Missing `cached_prompt_tokens`/metrics means **unavailable**, not zero. Positive `vllm:prefix_cache_hits_total` / queries deltas corroborate **server-wide** cache activity, not a specific request when other clients may be active.
- `tool_eval.py` (v0.5) presents `read_file(path)`, `search_repository(query)` and `run_tests(target)`; scores one correct structured decision or no tool. **No selected tools executed.** Keep `tool_choice=auto`: `required` would invalidate the no-tool control.
- `agent_eval.py` (v0.6) presents four simulated tools and five **fixed** tasks: `trace_symbol`, `repair_failing_test`, `missing_document_recovery`, `transient_error_recovery`, `no_tool_needed`. Simulated tests/edits operate only on in-memory state.

### v0.7 generated generalization implementation

**Verified — source:** `thorbench/generalize_eval.py` defines:
- Six `KINDS`: `symbol_origin`, `repair_regression`, `moved_runbook`, `transient_read`, `environment_disambiguation`, `no_tool_needed`.
- `episode_seed(base_seed,kind,repetition)` uses namespaced SHA-256 and first eight digest bytes (not process-randomized Python `hash()`). `generate()` randomizes service, source and decoy paths, active numbers, symbols, incidents, archived values, and transient failure count. **The oracle/answer key is kept locally and not sent to Qwen.**
- Five declared tools: `list_files(directory)`, `search_repository(query)`, `read_file(path)`, `run_tests(target)`, `replace_text(path,old,new)`. `InMemoryRepo.execute()` validates exact JSON schemas and bounded lengths and only interacts with fixture dictionaries. No shell, arbitrary Python, real file read/write, or actual tests are executed.
- Nonstreaming `POST /v1/chat/completions` with `tool_choice=auto`, `temperature=0.0`, `reasoning_effort=low`, default `max_tokens=1024` per model request, max **10 turns** and **16 tool calls**. Replays corresponding tool replies by `tool_call_id`.
- `--runs` 1–10 creates **six synthetic variants per repetition**, from the same six public task families; not six independently unseen task types. Random base seed printed/stored. Replaying a seed may yield different answers/timings.
- `grade()` checks tool-event order, paths, results/fixture state and final-answer **heuristics**. `run_episode()` records sanitized reason, turn/tool/error counts, recovery, event outcome trace, latency and *summed* prompt/completion tokens across all model turns. Summed prompt tokens repeat conversation history, not unique context tokens.
- Reports to ignored `results/<UTC timestamp>-agent-generalization/{metadata.json,samples.jsonl,summary.md,summary.json}`, with **no persisted raw prompts, final answers, tool args or fixture content**. Partial FAIL yields a nonzero exit by design.

| Case | Required evaluator evidence |
|---|---|
| `symbol_origin` | Discover active path via list/search; read it later; answer exact active path and number |
| `repair_regression` | Read active and observe simulated test FAIL in either order; allowlisted replacement after both; observe simulated test PASS; report fix/pass |
| `moved_runbook` **corrected** | Discover active document via list **or** search, then read it; final includes active path, HTTP 503, exact current retry number; need not read known-broken link |
| `transient_read` | Required injected temporary failures before successful read; final reports generated incident identifier |
| `environment_disambiguation` | Read staging and production in either order; final names production file, value and environment |
| `no_tool_needed` | Zero tools; answer mentions TTFT, first token and total/end-to-end/task scope, **≤700 characters**. Otherwise qualifying overlong answer = `excessive_verbosity` |

These are **narrow heuristic gates**, not fully semantic grading. Valid paraphrases may fail and incidental substring/number matches may pass. Fix proven shortcomings with *both* positive and negative regression tests; never loosen an oracle to improve one model's score.

## 5. Development decisions and historical measurements

Decisions and rejected approaches:
1. Prioritize exact serving provenance, measured latency/quality and independent task scoring over raw claims that a model "runs."
2. Keep locally reviewed NVFP4 and public FP8-hybrid/MTP community reports **separate**, because weights, prompt mix, runtime and token rates differ.
3. Avoid conclusions from latency alone: inspect prompt/output length, hidden reasoning, cache state, power/clocks and concurrent traffic.
4. Establish first-decision routing before testing multi-turn agent workflow; keep actual code execution disallowed on the model-serving host.
5. Since v0.6's 25/25 only repeats five fixed tasks, introduce seed-varying fixtures for v0.7, explicitly **not** a benchmark of held-out task templates or real coding issues.
6. Require evidence from authoritative active source, not archived/example/staging decoys, but do **not** force one arbitrary tool path when a shorter grounded path satisfies user intent.
7. Preserve concise instruction following as a separate criterion from factual correctness; do not change the brevity limit to disguise an overlong answer.
8. Do not persist private raw prompts/answers, generated tool args, credentials, model weights, raw Docker env or mounts. Do not publish ignored `results/` wholesale.
9. No `tool_choice=required` workaround for a no-tool scenario, automatic server restart, blind cache-dropping loop, or hardcoded per-seed answer.
10. Future real tests/patch execution would require explicit approval and a **hardened isolated sandbox away from the model-serving Jetson**, not this simulator.

Reviewed earlier outcomes (**source/operator**, distinct benchmark protocols):
- Short baseline coding prompt 253 completion tokens / 47 reasoning / 11.09232s / ~22.8 effective tok/s. Manual DFS/Kahn/cycle answers were not executed or standardized coding tests.
- Five-pair `prefix` and synthetic `agent` measurements: 20/20 requests completed (ten per suite); median paired TTFT ratios **8.23×** identical repeat and **7.18×** changing agent instruction. Prefix first→repeat median TTFT ~4.20→0.51s; synthetic agent ~4.52→0.63s. All ten follow-up pairs had **positive server-wide cache-hit counter deltas**, not proven per-request attribution.
- Fixed first-decision routing **30/30** A, **30/30** B2, six public task cases with no real tools.
- v0.6 multi-turn fixed tasks: first 5/5, then **25/25** across five repetitions of five fixed tasks, median whole episode latency **12.2302s**, 75 model turns and 55 simulated tool calls. Historical offline suite **67/67**. This is **not** 25 unrelated software bugs.

## 6. v0.7 failure investigation — exact evidence

### First run: 4/6, strict original scorer

**Verified — operator**:
- Command: `python3 -m thorbench.generalize_eval --runs 1`.
- Seed: **`6213207535837610165`**.
- Report `results/20261108T044438Z-agent-generalization/summary.md`.
- **4/6 (66.7%)** completed; median episode latency **20.87s**.

| Case | Outcome | Turns | Tools | Latency |
|---|---|---:|---:|---:|
| `symbol_origin` | PASS | 3 | 5 | 19.044s |
| `repair_regression` | PASS | 7 | 9 | 42.1271s |
| `moved_runbook` | FAIL `incomplete_or_ungrounded` | 3 | 6 | 28.2571s |
| `transient_read` | PASS | 3 | 2 | 14.6945s |
| `environment_disambiguation` | PASS | 3 | 6 | 22.7041s |
| `no_tool_needed` | FAIL `incomplete_or_ungrounded` | 1 | 0 | 14.2129s |

Fixture for moved runbook:
- Broken old: `docs/gateway/retry-v1.md`.
- Active: `docs/gateway/runbook-active.md` with HTTP 503 retry limit **1**.
- Retired: `docs/archive/gateway-retry.md` with legacy limit **4**.
- Asked to locate active runbook, report current retry limit, ignore archive.

### Diagnostic model-response replay

**Verified — operator** with same seed and a **temporary process-local monkeypatch of `grade()`** to print responses, without committing them:
- Report `results/20261108T045454Z-agent-generalization/summary.md`, old scorer still 4/6.
- `moved_runbook`: model's **631-character** final response correctly cited active document and **1 retry**, rejected retired **4**, distinguished unrelated policy/example budgets. Event trace: `list_files:ok`, `search_repository:ok`, four `read_file:ok`; **zero tool errors**. Old scorer insisted on `read_file(old_path):not_found → search_repository → read_file(active)`. Because the old link was explicitly stated broken, opening it was unnecessary. **Confirmed false negative / grader bug.**
- `no_tool_needed`: model made **zero tools**, produced a substantively correct TTFT vs end-to-end explanation but **1,237 characters**, above the **700-character** cap. **Confirmed instruction/brevity failure**, not a factual failure. Do **not** turn it into PASS simply because the explanation was correct.

### Scorer correction and live result

**Verified — source:** `thorbench/generalize_eval.py` now accepts `list_files` **or** `search_repository` that discovers the active path, followed by an active `read_file` and exact final path+HTTP503+number. It no longer forces the missing-old-file read. The no-tool cap remains 700; otherwise semantically valid long answers are labeled `excessive_verbosity`. Regression tests added in `tests/test_generalize_eval.py`; docs updated in `docs/AGENT_GENERALIZATION_EVAL.md`.

**Verified — operator**, same seed after scorer update, report `results/20261108T050515Z-agent-generalization/summary.md`:

| Case | Outcome | Turns | Tools | Latency |
|---|---|---:|---:|---:|
| `symbol_origin` | PASS | 3 | 5 | 18.0308s |
| `repair_regression` | PASS | 7 | 9 | 38.4021s |
| `moved_runbook` | **PASS** | 3 | 6 | 24.3078s |
| `transient_read` | PASS | 3 | 2 | 12.3922s |
| `environment_disambiguation` | PASS | 3 | 6 | 19.3346s |
| `no_tool_needed` | **FAIL — excessive_verbosity** | 1 | 0 | 13.0319s |

**Result: 5/6 (83.3%)** on the corrected grader, **not** a 6/6 full instruction-compliance score. Keep original 4/6 and corrected 5/6 as results of **different scorer versions**, and never retroactively overwrite historical outcomes.

### Offline test regression and fix

**Verified — operator:** After first scoring change, `python3 -m unittest discover -s tests -v` ran **93 tests**, with **4 failures**: three `test_successful_generated_cases` subtests (moved runbook seeds 1, 54, 4321) and `test_live_report_path_with_scripted_responses`. They all used `scripted_success(moved_runbook)` whose mocked successful answer omitted the newly required *active path*. This is not evidence that the live model's 5/6 was wrong.

**Verified — source:** Commit **`31ea3e5290b17f493df9c58d089d2028cbf2beaf`** changed **only** the scripted mock final line in `tests/test_generalize_eval.py` to include `Active runbook: {case.target}. Current HTTP 503 limit: {case.expected_value} retries.`. No grader change, no expected-answer change.

**Verified — GitHub CI:** Python checks workflow [run 42449569043](https://github.com/kagaho/jetson-thor-llm-bench/actions/runs/42449569043) on that commit completed **successfully** (compileall, offline reference validation and unit tests). **Not yet verified — local:** No pasted terminal output after that commit establishes the latest local unittest result. User says the last test output is in `docs/last-test.txt`; inspect it first, since it may contain newer information.

## 7. Current Git, known limitations and unresolved questions

**Verified — GitHub at handoff:**
- `main`: released v0.6 code, commit `f2f54fb18651715e5f8fe98345e21ebfc02268d8`.
- `feat/seeded-agent-generalization`: v0.7 implementation + scoring fixes + fixture fix, commit `31ea3e5`; **five commits ahead of main**.
- [PR #9](https://github.com/kagaho/jetson-thor-llm-bench/pull/9): **open draft**, base `main`, includes the initial v0.7 implementation and correction, **not merged**.
- This documentation has a separate branch based on `feat/seeded-agent-generalization`. Do not merge `main` or PR #9 just to start Codex.
- No evidence that `docs/last-test.txt` exists in tracked GitHub; treat as a local handoff artifact pending inspection.

**Known limitations / questions:**
1. Final-answer string/number heuristics are not true semantic correctness: correct synonyms may fail; incidental numbers could match. More negative controls and precise failure reasons may help.
2. Six generated *variants of public templates* are not independent held-out coding tasks, even if `--runs 5` produces 30 episodes.
3. `moved_runbook` now requires discovery→active read and correct final facts but does not explicitly require reading/rejecting the archive; determine whether an extra gate would match the **task semantics**, not just improve a score.
4. `no_tool_needed` is correctly a brevity failure for the observed long response. A future model prompt change to encourage concision is a **different protocol version**, not justification to change this run's score.
5. Additional random seeds may reveal other false negatives, false positives, tool-order mistakes, schema errors or model limitations (**hypothesis**, not a verified outcome).
6. Low Jetson memory, power and temperature, cache warmness, generated response length and repeated prompt history can all confound timing.
7. Real-world coding correctness would require independently curated tasks, a strict isolated execution sandbox and separate ethical/security review; not present.
8. Standardized EvalPlus HumanEval+, IFEval, MMLU-Pro are **roadmap ideas**, not completed benchmark suites.

## 8. Prioritized backlog for Codex CLI

**P0 — Read the latest test output and establish actual local state (FIRST).**
- Open `docs/last-test.txt` locally if it exists, and inspect timestamps, failing tests, SHA and what was actually run. Avoid publishing raw logs.
- Run `git status --short --branch`, `git log -5 --oneline --decorate`, `git fetch origin`, ensure correct repository and feature branch. Preserve uncommitted changes; do not blindly reset/stash them.
- Inspect `thorbench/generalize_eval.py`, `tests/test_generalize_eval.py`, `docs/AGENT_GENERALIZATION_EVAL.md` and PR #9.
- Run `python3 -m compileall -q thorbench tests`; `python3 -m thorbench references`; `python3 -m unittest discover -s tests -v`.
- **Acceptance:** a documented actual local pass/fail tied to commit SHA and Python version. GitHub CI already passed on `31ea3e5`, but that does not substitute for local state.

**P1 — Reproduce and classify the benchmark outcomes.**
- Ensure local `curl -fsS http://127.0.0.1:8000/health` is healthy (no restart).
- Run `python3 -m thorbench.generalize_eval --runs 1 --seed 6213207535837610165`. The same fixture is regenerated, **not necessarily the same output**.
- Read `metadata.json`, `samples.jsonl`, `summary.md`; compare to the previous 4/6 and 5/6 only with scorer/protocol commit/version disclosed. Distinguish model failure, grader bug, transient infrastructure and instruction failure.

**P2 — Correct independently demonstrated grader/implementation bugs.**
- Study `grade()`, `_num()`, `_sequence()`, `InMemoryRepo.execute()` and `run_episode()`.
- For a claimed false negative: demonstrate a grounded alternate trace with correct final answer; for false positive: demonstrate an inadequately grounded answer wrongly accepted. Write a red test before changing scorer.
- Preserve active-source and chronological evidence requirements and the existing oracle; never hardcode one seed or raise the brevity limit merely to make Qwen PASS.
- **Acceptance:** targeted positive **and negative** tests plus unchanged independent integrity gates.

**P3 — Improve regression suite and failure taxonomy.**
- In `tests/test_generalize_eval.py` expand seeded coverage: list-first, search-first, old-path missing→recovery, wrong retry value, archive-only, hallucinated active path, undiscovered active read, production/staging swapping, transient-error counts, tool schema failures, no-tool vs overlong cases, negative numeric coincidences.
- Consider more specific outcome reasons like missing-discovery, missing-authoritative-read, wrong-value, and verbosity without persisting sensitive model answers. Make such changes versioned; update documentation.
- **Acceptance:** offline suite and GitHub CI pass; no model-answer content leaked to public artifacts.

**P4 — Run wider seeded evaluation.**
- On healthy existing server: `python3 -m thorbench.generalize_eval --runs 5`; 5 repetitions × 6 families = **30 synthetic episodes**, not 30 unrelated code tasks. Record seed, scorer commit, per-family results, failures, median/p90, token counts, turns/tool calls, power/cache factors where possible.
- Do not throw out failed seeds or change expected answers after observing results. Use more independent seeds and withheld task families before broader reliability claims.

**P5 — Clean commits and PRs.**
- Before commit: `git diff --check`, compileall, unit tests, `git diff --cached`, inspect for credentials, private infrastructure and raw user/model data.
- Work on **feature branches**, not direct `main` pushes. Open PRs for implementation work. Keep [PR #9](https://github.com/kagaho/jetson-thor-llm-bench/pull/9) unmerged until reviewed. Do not mix unrelated changes with the documentation PR.

**Later:** genuinely withheld task templates; stronger independent graders; official standardized quality protocols (EvalPlus, IFEval, MMLU-Pro) and optionally **separately approved**, hardened, isolated real-code task execution away from the model-serving Thor.

## 9. Local commands and reproducible artifacts

Work from repo root; always inspect uncommitted changes first.

~~~bash
cd ~/Documents/jetson-thor-llm-bench
git status --short --branch
git log -5 --oneline --decorate

# Latest test output, as identified by the operator:
if test -f docs/last-test.txt; then
    sed -n '1,300p' docs/last-test.txt
else
    echo 'docs/last-test.txt not found locally; do not assume its contents.'
fi

# Offline validation (no vLLM required):
python3 -m compileall -q thorbench tests
python3 -m thorbench references
python3 -m unittest discover -s tests -v

# Read-only server check, no Docker restart:
curl -fsS http://127.0.0.1:8000/health && echo Healthy
python3 -m thorbench doctor --container qwen38-flash-next

# Same generated fixture family/seed used in v0.7 investigation:
python3 -m thorbench.generalize_eval --runs 1 --seed 6213207535837610165

# After smoke test analysis, optional new larger run:
python3 -m thorbench.generalize_eval --runs 5
~~~

Historical **local-only, Git-ignored** report paths (may not be present in another clone):
- `results/20261108T044438Z-agent-generalization/summary.md` — original strict 4/6.
- `results/20261108T045454Z-agent-generalization/summary.md` — old-scorer diagnostic replay 4/6.
- `results/20261108T050515Z-agent-generalization/summary.md` — corrected-scorer observed 5/6.
- `results/20261108T041614Z-agent-multiturn/summary.md` — fixed-template v0.6 25/25.
- `docs/last-test.txt` — **operator-reported latest test log location**, locally verify first.

Use a nonzero live-suite exit code to inspect failures; this is expected when a benchmark case fails and is **not** automatic permission to weaken grading.

## 10. Non-negotiable benchmark, safety and Git rules

1. Preserve oracle independence. Never leak generated expected answers or hidden fixture state to the evaluated model.
2. **Never modify expected values or selectively remove failed episodes to manufacture a PASS.**
3. Distinguish **grader false negative**, **genuine agent/model limitation**, **environment/API failure**, and **instruction noncompliance**.
4. Prefer evidence-outcome grading to arbitrary procedural tool order, but do not accept unsupported final answers.
5. Do not hardcode generated file paths, numbers, values, seeds, or answer strings as special-case score fixes.
6. Keep Qwen's tool calls within the allowlisted **in-memory simulator**. Running untrusted generated code/tests on the host requires a separately approved hardened sandbox.
7. Preserve prior metrics by scorer version; do not quietly re-label original 4/6 as 5/6 or suggest 6/6 full compliance.
8. Reports are privacy-minimized; no secrets, private prompts/responses, raw Docker env/mounts, credentials, access tokens, model weights or identifying device data in public commits.
9. Avoid automatic vLLM restarts, aggressive memory experiments or new model downloads during grading work.
10. GitHub operations ONLY in `kagaho/jetson-thor-llm-bench`, on feature branches and PRs. No direct `main` pushes.

## Instructions for the Next Codex CLI Session

Copy or provide this exact prompt to **Codex CLI started from `~/Documents/jetson-thor-llm-bench` on Shockwave**:

> You are the development assistant for ONLY the repository `https://github.com/kagaho/jetson-thor-llm-bench` on `shockwave-01`. **Read `CONTEXT.md` completely first.** Verify the current Git repository, branch, working-tree cleanliness, recent commits and open PRs; **do not touch any other repository**. Inspect `docs/last-test.txt` FIRST for the last operator test output (it may be an untracked local file; do not invent its contents or commit raw logs). Then read `README.md`, `pyproject.toml`, `thorbench/generalize_eval.py`, `tests/test_generalize_eval.py` and `docs/AGENT_GENERALIZATION_EVAL.md`; verify this handoff against actual source.
>
> Check whether the final v0.7 test-fixture fix (`31ea3e5`) is present, note that GitHub CI passed on that commit, and run the offline unittest suite locally. Identify the **highest-priority unfinished task** based on actual tests and local logs. Continue from that point without repeating completed changes. If offline tests pass, check the existing localhost vLLM API without restarting Docker, then optionally replay `--seed 6213207535837610165 --runs 1`. Treat new model outputs as a new run and preserve historical 4/6 and corrected 5/6 records.
>
> **Codex writes code; Qwen is the evaluated model.** Preserve hidden-oracle independence, do not change expected answers merely to get PASS, and never execute Qwen-generated code or shell commands outside the in-memory simulator. Add positive and negative regression tests before any scorer change. Run relevant tests and review diffs/security before committing. Use a **new feature branch and PR**, never push directly to `main`. Keep the work strictly confined to `kagaho/jetson-thor-llm-bench`. Report verified facts, remaining failures, proposed next action, exact commands and any uncertainty.
