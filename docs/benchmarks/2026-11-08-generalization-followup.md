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
