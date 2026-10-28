# Changelog

All notable changes to this project are documented here.

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
