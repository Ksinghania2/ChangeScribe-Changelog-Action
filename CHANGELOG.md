# Changelog

All notable changes to this project are documented here.

## [Unreleased] - 2026-10-26

### Added

- Initial release of ChangeScribe. ([146ae0c](https://github.com/Ksinghania2/ChangeScribe--Automated-README-changelog-generator-from-commit-and-pull-request-history/commit/146ae0c2f5ad9fa5261dfe0112eab8d1a8cd9111))

### Documentation

- Add report builder, diagrams and evaluation assets. ([09a597c](https://github.com/Ksinghania2/ChangeScribe--Automated-README-changelog-generator-from-commit-and-pull-request-history/commit/09a597c692974dc793890d1a8cb59b3c15bde95e))

## [1.0.0] - 2026-10-22

### Added

- GitHub REST collector for merged pull requests, review discussion and direct commits, plus a local `git log` collector.
  - *Why:* The reason for a change usually lives in the PR conversation, not the diff.
- Parser that classifies changes (conventional commits, labels, keywords, file paths), drops noise and extracts "why" sentences.
- Anthropic LLM writer with an offline heuristic fallback so the tool always produces output.
- Changelog and README updaters that are idempotent (managed block between markers).
- Command line interface, Flask web UI, Docker image, GitHub Action and scheduled workflow.
