# Changelog

All notable changes to this project are documented here.

## [1.0.0] - 2026-10-22

### Added

- GitHub REST collector for merged pull requests, review discussion and direct commits, plus a local `git log` collector.
  - *Why:* The reason for a change usually lives in the PR conversation, not the diff.
- Parser that classifies changes (conventional commits, labels, keywords, file paths), drops noise and extracts "why" sentences.
- Anthropic LLM writer with an offline heuristic fallback so the tool always produces output.
- Changelog and README updaters that are idempotent (managed block between markers).
- Command line interface, Flask web UI, Docker image, GitHub Action and scheduled workflow.
