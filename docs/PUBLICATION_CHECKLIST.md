# Public repository and data review

- [ ] Fresh history. No commits imported from private Soundwave repo.
- [ ] `git ls-files` reviewed; no model weights, tokens, cache, `/results` raw files or unreviewed screenshots.
- [ ] `git log --all -p` reviewed for secrets and private identifiers **including earlier commits**.
- [ ] Published model name and checkpoint repository are accurate; the model's license is separate from this tool's MIT license.
- [ ] Public benchmark numbers have source URLs, dates, quantization and a methodology caveat.
- [ ] `python3 -m unittest discover -s tests -v` and `python3 -m thorbench references` pass offline.
- [ ] Preserve historical tags. Release new versions only from reviewed, merged main; see [release workflow](RELEASING.md).
- [ ] Check that new figures reproduce from tracked evidence and identify conceptual versus measured content.
- [ ] Verify the README claims, relative links, scorer versions and dates against the underlying reports.
- [ ] Do not describe simulated tool workflows as real code execution.
- [ ] Main branch protected by PR review and CI when possible.
- [ ] Draft cache-pressure issue says 2025 recurrence, not proven 2025-to-2026 driver regression.
- [ ] GitHub repo description, topics (`jetson`, `thor`, `vllm`, `llm-benchmark`) and MIT license set.
