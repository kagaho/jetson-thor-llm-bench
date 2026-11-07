# Public repository and data review

- [ ] Fresh history. No commits imported from private Soundwave repo.
- [ ] `git ls-files` reviewed; no model weights, tokens, cache, `/results` raw files or screenshots.
- [ ] `git log --all -p` reviewed for secrets and private identifiers **including earlier commits**.
- [ ] Published model name and checkpoint repository are accurate; the model's license is separate from this tool's MIT license.
- [ ] Public benchmark numbers have source URLs, dates, quantization and a methodology caveat.
- [ ] `python3 -m unittest discover -s tests -v` and `python3 -m thorbench references` pass offline.
- [ ] v0.1.0 annotated tag points to initial release; v0.2.0 tag only after merge to main.
- [ ] Main branch protected by PR review and CI when possible.
- [ ] Draft cache-pressure issue says 2025 recurrence, not proven 2025-to-2026 driver regression.
- [ ] GitHub repo description, topics (`jetson`, `thor`, `vllm`, `llm-benchmark`) and MIT license set.
