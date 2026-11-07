# Git workflow, review, releases and tags

Use a **fresh standalone public repository** `jetson-thor-llm-bench`. Do not import old private Soundwave Git history. Prefer squash-merge for clean review history, leaving annotated tags as reproducible release points.

## Branch policy

- `main`: protected; require a PR, one review when collaborators exist, and the `unit-tests` CI check before merge.
- `feat/<topic>`: new commands, features or model support.
- `fix/<issue>`: bugfix and reproducibility corrections.
- `docs/<topic>`: documentation-only work.
- `chore/<topic>`: CI/tooling, release preparation.

Create labels `bug`, `benchmark`, `documentation`, `needs-reproduction`, `jetpack`, `thor`, `model-provenance` using the GitHub UI or `gh label create`.

## Versioning

Use semantic versions `vMAJOR.MINOR.PATCH` as **annotated tags on `main`**. `CHANGELOG.md` is the human-readable changelog. The first release is `v0.1.0`; v0.2.0 adds provenance and workflow controls. GitHub Releases are created from merged, tagged commits. Never tag unmerged feature branches.

## Initial publishing from Shockwave

The following is for a fresh v0.1.0 checkout **without any v0.2.0 changes applied**. If you already applied the patches on a feature branch, do **not** switch to main with uncommitted modifications; complete the local feature branch first and publish only after reviewing the working tree:

```bash
cd ~/Documents/jetson-thor-llm-bench
git status --short
python3 -m unittest discover -s tests -v
git tag -a v0.1.0 -m "v0.1.0: initial Thor benchmark harness"
gh auth login
gh repo create jetson-thor-llm-bench --public --source=. --remote=origin --push
git push origin v0.1.0
```

If the GitHub repository already exists, do not rerun `gh repo create`; check `git remote -v` and push the existing repo instead. If `gh` is missing, install it from your distribution package repositories. **Review `git log -p` and `git ls-files` before making the repository public.**

## v0.2.0 PR

```bash
git switch feat/qwen38-benchmark-integration  # if this branch already exists
# Apply the v0.2.0 patch, then the separate model-layout patch, if not yet applied.
python3 -m unittest discover -s tests -v
python3 -m thorbench references
git add .
git diff --cached --stat
git commit -m "feat: add model provenance, public references and GitHub workflow"
git push -u origin feat/qwen38-benchmark-integration
gh pr create --base main --head feat/qwen38-benchmark-integration \
  --title "feat: model provenance, comparable reference catalog and release workflow" \
  --body "Add Qwen3.8 provenance, documented public results, comparison commands and issue templates. CI: offline unit tests. Baseline remains unchanged."
```

## Create the historical memory issue

After the new repository exists, review the draft at `docs/issues/2025-2026-memory-cache-pressure.md` and publish with:

```bash
gh issue create --title "Recurring memory/cache pressure during vLLM startup on Jetson AGX Thor (2025–2026 observations)" \
  --body-file docs/issues/2025-2026-memory-cache-pressure.md --label bug
```

This is a **tracking issue for observed symptoms**, not a claim of a confirmed driver regression. See `docs/issues/standardized-quality-evaluations.md` for a second proposed issue on standardized public quality benchmarks. Do not close it until there is a reproducible root-cause analysis.

## Tag and release AFTER the PR is merged

```bash
git switch main
git pull --ff-only origin main
python3 -m unittest discover -s tests -v
git tag -a v0.2.0 -m "v0.2.0: model provenance and comparison"
git push origin v0.2.0
gh release create v0.2.0 --title "v0.2.0 — Model provenance and public references" --generate-notes
```

If `v0.1.0` was already tagged, don't recreate it; use `git tag -l`. Configure GitHub **Settings → Rules → Rulesets** for `main` after pushing. Make `unit-tests` a required status check once the first workflow has run and the check name is visible.


## v0.3.0: agent-workload instrumentation / diagrams (proposal)

**Do not move or recreate `v0.2.0`.** From a clean `main` that already contains PR #1:

```bash
git switch main
git pull --ff-only origin main
git switch -c feat/agent-benchmark-runtime-profiles
# Copy the supplied v0.3.0 patch into ~/Downloads (relative to the repo as necessary).
git apply --check ../../Downloads/jetson-thor-llm-bench-v0.3.0.patch
git apply ../../Downloads/jetson-thor-llm-bench-v0.3.0.patch
python3 -m unittest discover -s tests -v
python3 -m thorbench references
git add -A
git diff --cached --check
git diff --cached --stat
git commit -m "feat: capture Thor serving flags and document agent optimizations"
git push -u origin feat/agent-benchmark-runtime-profiles
gh pr create --base main --head feat/agent-benchmark-runtime-profiles \
  --title "feat: runtime launch fingerprints, prefix benchmark and feature diagrams" \
  --body "Add sanitized Docker runtime capture, first/repeat prefix probes, exact baseline launch profile, public comparison and Mermaid workflows. No model restart or weight downloads."
```

Review PR CI and output redaction. After merging, update `main`, create annotated `v0.3.0` tag, and publish release notes through the normal workflow above. This branch does not turn on MTP or modify the known-good `serve.sh`.
