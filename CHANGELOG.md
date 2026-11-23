# Changelog

All notable changes to this project are documented here.

## [Unreleased] - 2026-11-23

### Fixed

- Add bug report issue template. ([0658ecc](https://github.com/Ksinghania2/ChangeScribe-Changelog-Action/commit/0658ecc12e4da67bdeb5bb9135a0578db8b4a75d))

### Documentation

- Add comprehensive README.md. ([59d9ab1](https://github.com/Ksinghania2/ChangeScribe-Changelog-Action/commit/59d9ab14ef5f82ddf12e3ac5f5fdd5a2fa50e65f))
- Simplify README for undergraduate audience. ([a842c6b](https://github.com/Ksinghania2/ChangeScribe-Changelog-Action/commit/a842c6bef1ba1486b38097c03dc5dd69d9dba7e8))

### Tests

- Add test CI workflow for GitHub Action. ([d9e59b6](https://github.com/Ksinghania2/ChangeScribe-Changelog-Action/commit/d9e59b6988d71372f815ee211163b1e4e1d54ff3))
- Simplify test CI workflow. ([cc8a19d](https://github.com/Ksinghania2/ChangeScribe-Changelog-Action/commit/cc8a19df03a501cbb5161eb8ca08428ce81de98c))

## [1.1.0] - 2026-10-28

### Added

- Config-driven classification heuristics via `changescribe.toml` / `changescribe.json` / `pyproject.toml` (`[tool.changescribe]`), or `CHANGESCRIBE_CONFIG`, with sensible defaults.
- `--since-tag` / `--until-tag` CLI flags (and `resolve_rev_range`) to bound collection by git tags/refs.
- GitHub client `Authorization: token ...` header support; commit de-duplication when collecting PRs + direct commits.
- Web UI redesign: tabbed changelog preview (rendered/Markdown), copy-to-clipboard, theme toggle, preset repositories, security headers.
- `config.py` module exposing `ClassificationConfig` and `load_config()`.

### Changed

- Parser, summarizer and pipeline now accept an optional `ClassificationConfig`.
- Web error responses no longer leak raw exception details.

### Fixed

- Removed accidental BOM from `collector.py`.
- `test_web` now passes on the initial page (preview chrome renders without a result).

"
## [1.0.0] - 2026-10-22

### Added

- GitHub REST collector for merged pull requests, review discussion and direct commits, plus a local `git log` collector.
  - *Why:* The reason for a change usually lives in the PR conversation, not the diff.
- Parser that classifies changes (conventional commits, labels, keywords, file paths), drops noise and extracts "why" sentences.
- Anthropic LLM writer with an offline heuristic fallback so the tool always produces output.
- Changelog and README updaters that are idempotent (managed block between markers).
- Command line interface, Flask web UI, Docker image, GitHub Action and scheduled workflow.
