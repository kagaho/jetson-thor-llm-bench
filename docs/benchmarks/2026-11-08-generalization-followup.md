# Seeded generalization: local validation and failure investigation

## Verified repository and offline baseline

On 2026-11-08 UTC, local inspection started at `b58a041c1a905141ee8e6883364c93e85bdcb1e8` (the documentation handoff), which includes the test-fixture correction `31ea3e5290b17f493df9c58d089d2028cbf2beaf`. The only untracked file was the operator's `docs/last-test.txt`; it was read and preserved locally, not committed. Fetching `origin` confirmed that `main` remained at `f2f54fb` and PR #9 remained an open draft. PR #10 contains the separate handoff documentation.

The following commands passed locally using **Python 3.12.3**, with **93/93 unit tests**:

```bash
python3 -m compileall -q thorbench tests
python3 -m thorbench references
python3 -m unittest discover -s tests -v
```

This establishes a local baseline in addition to the existing successful GitHub CI on `31ea3e5`. No fixture-fix implementation was repeated. New implementation work branches from `31ea3e5` on `feat/generalization-integrity`, keeping it separate from the handoff documentation.

## Existing wider run: 24/30, retained unchanged

The operator log records `python3 -m thorbench.generalize_eval --runs 5`, seed **2891566386927721173**. Its local artifacts were present at `results/20261108T050906Z-agent-generalization/` and agree with the log:

| Family | Passed / total | Failure category |
|---|---:|---|
| `symbol_origin` | 5/5 | None |
| `repair_regression` | 5/5 | None |
| `moved_runbook` | 4/5 | Repetition 2: `incomplete_or_ungrounded` |
| `transient_read` | 5/5 | None |
| `environment_disambiguation` | 5/5 | None |
| `no_tool_needed` | 0/5 | Five `excessive_verbosity` failures |

Total: **24/30 (80.0%)**, median episode latency **18.5468s**, interpolated p90 **38.2944s**. These are five variants of each of six public synthetic families. The no-tool failures used zero tools but failed the existing brevity gate; they remain failures in the denominator.

The report predates machine-readable scorer/commit identifiers. Its categories are consistent with the corrected v0.7.1 scorer, but its exact source SHA cannot be independently established from its metadata. Its sanitized trace omits read paths and final answers, so the historical runbook failure cannot be diagnosed conclusively. It is preserved as recorded, separately from the earlier original 4/6 and corrected 5/6 runs on seed `6213207535837610165`.

## Separate targeted replay

The existing server passed `curl -fsS --max-time 10 http://127.0.0.1:8000/health`. To investigate the remaining runbook failure without repeating the completed 30-episode run, a process-local diagnostic replay regenerated only:

```python
case = generate("moved_runbook", episode_seed(2891566386927721173, "moved_runbook", 2))
```

It used the unchanged evaluator from `31ea3e5`: `run_episode`, `request_payload` with `max_tokens=1024`, and the existing local `Qwen3.8-Flash-Next` server. A temporary `grade` wrapper inspected the response in memory, printed only Boolean gate results and response length, then delegated to the original grader. It saved no raw model content, tool arguments, oracle or synthetic files.

| Check | New replay observation |
|---|---|
| Discovery before successful active-file read | True |
| Final answer includes active path | True |
| Final answer includes expected integer | True |
| Final answer includes `503` | **False** |
| Final answer length | 893 characters |
| Result | **FAIL**, `incomplete_or_ungrounded` under v0.7.1 |
| Model turns / simulated calls / tool errors | 3 / 6 / 0 |
| Summed prompt / completion tokens | 2,769 / 964 |
| Episode latency | 41.5923s |

This demonstrates a missing required final-answer fact in the **new replay**, not a proven grader false negative. The runbook has no 700-character cap; its length was diagnostic only. The new observation does not establish the historical response's contents, even though the seed and token counts match. No full-suite score is inferred from this one-case replay. Power, clocks, concurrent traffic and cache state were not controlled for a latency comparison; deployment provenance was not recaptured.

## Implementation and remaining work

Independent offline controls exposed a different false positive: `symbol_origin` accepted an unrelated list/search, followed by an active-file read, followed only afterward by the discovery that actually returned that file. Before the fix, all six negative controls (three seeds × two discovery tools) incorrectly passed; their positive counterparts with a subsequent reread passed correctly.

Scorer **0.7.2** fixes that chronology check and adds explicit failure reasons to both discovery families. Tests also cover every new runbook reason with a successful control, unchanged source/final-fact gates, failure denominators, report provenance, and privacy on model and request failures. The [protocol documentation](../AGENT_GENERALIZATION_EVAL.md#v072-scorer-discovery-chronology-and-private-diagnostics) defines these additive report fields and the unchanged protocol 1.

At commit `de44842a07867d0f2a4dacf7dd67eea9e7df0857`, the targeted generalization suite passed **29 tests**; the full offline suite passed **96 tests** on Python 3.12.3. Compileall, offline references and `git diff --check` also passed. These commands should be run against that commit when reviewing it. No v0.7.2 full live-suite score is inferred from the targeted replay.

The validated `thorbench/generalize_eval.py` source fingerprint is `9d76d9625578f95e6cf2b412e24109f092cbf97b897cd19f949969d78decf825` (SHA-256).

Further investigation should use versioned reports for additional independent seeds and scrutinize numeric/final-answer heuristic coincidences. Any prompt change to address verbosity must receive a new protocol version and be measured separately. The oracle, expected values, simulator allowlist, original measurements and 700-character control remain intact. No model-selected shell commands or real tests were executed, and the serving container was not restarted.

## Numeric follow-up: scorer 0.7.3, offline validation

Independent offline characterization then demonstrated numeric false positives in all three numeric-answer families: the old matcher accepted negative and fractional values containing the expected digits, as well as an expected number mentioned only as an unrelated identifier. This was a scorer limitation demonstrated by synthetic controls, not evidence that any particular recorded model answer contained such an error.

Commit `b2cb18c4089ef0fd043fcee8da1828b4e3d59919` corrects numeric token matching with exact `Decimal` comparisons and records scorer **0.7.3**, protocol **1**. The regression was demonstrated before implementation. There are **162 numeric controls** (three seeds × three families × eight positive and ten negative forms), including signs, fractional and grouped values, equivalent decimal/scientific notation, identifier boundaries, sentence punctuation, extreme exponents and a fractional difference too small for a binary float to preserve. All required repository observations remain present in these numeric controls, so an unrelated missing-evidence failure cannot mask the numeric test.

The targeted suite passes **30 tests** and the full offline suite passes **97 tests** on Python 3.12.3. Compileall, references and diff checks pass, and [GitHub CI on the numeric fix](https://github.com/kagaho/jetson-thor-llm-bench/actions/runs/42453465685) succeeded. The evaluator source fingerprint is `26cd39a350a737f37c9b049c89cc3c664572e5290fd207bfc6ef78633a78ba72`.

The unrelated-number case remains an explicit semantic-grounding limitation: token equality alone cannot determine which fact a number describes. It is not claimed fixed. Earlier model responses are not retained and cannot be regraded under the new parser. No full live-suite score is claimed for scorer 0.7.3.

GitHub release and remote-tag inspection confirmed that **v0.6.0 is the latest published package release** at the time of this investigation; there are no v0.7 tags. Scorer revisions 0.7.1, 0.7.2 and 0.7.3 identify development grading behavior, not package releases. The package declarations remain v0.7.0 in development. README and the release workflow now state this distinction; release tags must follow reviewed merges to `main`.

## Fresh versioned live run: scorer 0.7.2, 25/30

A fresh 30-episode run started at `de44842a07867d0f2a4dacf7dd67eea9e7df0857` using the healthy existing server:

```bash
python3 -m thorbench.generalize_eval --runs 5
```

The generated base seed was **3628200930879258838**. The local report is `results/20261108T055906Z-agent-generalization/`; its metadata records scorer **0.7.2**, protocol **1**, the original `9d76d962…decf825` source fingerprint, model `Qwen3.8-Flash-Next`, `max_turns=10` and `max_tokens=1024`. Every sample records scorer 0.7.2. The numeric correction was developed in a separate process while the benchmark continued using its already-loaded original module; the recorded score remains a 0.7.2 measurement.

| Family | Passed / total | Median turns | Median tools | Median prompt tokens | Median completion tokens | Median latency (s) | p90 latency (s) |
|---|---:|---:|---:|---:|---:|---:|---:|
| `symbol_origin` | 5/5 | 3 | 4 | 2,511 | 349 | 17.6038 | 19.6796 |
| `repair_regression` | 5/5 | 7 | 9 | 8,251 | 937 | 45.4402 | 48.8525 |
| `moved_runbook` | 5/5 | 3 | 6 | 2,768 | 573 | 27.3530 | 34.9893 |
| `transient_read` | 5/5 | 3 | 2 | 2,298 | 236 | 12.0280 | 15.0025 |
| `environment_disambiguation` | 5/5 | 3 | 4 | 2,504 | 404 | 20.2361 | 22.7918 |
| `no_tool_needed` | 0/5 | 1 | 0 | 699 | 304 | 13.6914 | 14.2744 |

Total: **25/30 (83.3%)**, median episode latency **18.8132s**, interpolated p90 **41.3457s**. All five failures are `excessive_verbosity` on the no-tool control, with zero tool calls. There were no request errors, missing-discovery failures, or missing-authoritative-read failures. The CLI exited **1** because the five instruction failures remain in the denominator. All six families contributed five samples; no episode was removed.

Across all episodes: **103 model turns**, **136 simulated tool calls**, **7 simulated tool errors**, **98,399 summed prompt tokens** and **14,327 completion tokens**. Summed prompt usage includes repeated conversation history, not unique context tokens.

To regenerate these fixtures with the same scorer, run from a checkout of `de44842`:

```bash
python3 -m thorbench.generalize_eval --runs 5 --seed 3628200930879258838
```

Model outputs and timing may differ on replay. The current branch uses scorer 0.7.3 and would produce a separately attributed run. This run and the earlier 24/30 used different seeds and scorer revisions, so their score difference does not establish a model improvement or isolate the effect of a scorer change. These remain heuristic outcomes on six public synthetic task families, with the numeric and semantic limitations described above; they cannot be regraded from the privacy-minimized artifacts.

The serving container was not restarted. Power, clocks, cache state, other clients and thermal conditions were not controlled or recaptured. Offline development checks ran during the live run; timing is observational and does not support a controlled performance comparison. Only sanitized metrics are copied here; raw prompts, answers, arguments and the operator log remain uncommitted.
