# ChangeScribe-Changelog-Action

A GitHub Action for learning about automated changelogs.

## What It Does
This GitHub Action automatically creates changelog entries when you make changes to your repository.

## How It Works
1. A pull request gets created
2. The action looks at what changed
3. It adds an entry to your changelog

## Basic Usage
```yaml
name: Generate Changelog
on:
  pull_request:
jobs:
  changelog:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: Ksinghania2/ChangeScribe-Changelog-Action@v1
```

## Learn More
- Search online for "GitHub Actions changelog"
- Try creating a pull request
- See the changelog update

## Topics
- automation
- GitHub
- scripts

## Author
Learning project

<!-- changescribe:start -->
## Recent changes

This period: 1 fixed, 2 documentation, 2 tests.

## [Unreleased] - 2026-11-23

### Fixed

- Add bug report issue template. ([0658ecc](https://github.com/Ksinghania2/ChangeScribe-Changelog-Action/commit/0658ecc12e4da67bdeb5bb9135a0578db8b4a75d))

### Documentation

- Add comprehensive README.md. ([59d9ab1](https://github.com/Ksinghania2/ChangeScribe-Changelog-Action/commit/59d9ab14ef5f82ddf12e3ac5f5fdd5a2fa50e65f))
- Simplify README for undergraduate audience. ([a842c6b](https://github.com/Ksinghania2/ChangeScribe-Changelog-Action/commit/a842c6bef1ba1486b38097c03dc5dd69d9dba7e8))

### Tests

- Add test CI workflow for GitHub Action. ([d9e59b6](https://github.com/Ksinghania2/ChangeScribe-Changelog-Action/commit/d9e59b6988d71372f815ee211163b1e4e1d54ff3))
- Simplify test CI workflow. ([cc8a19d](https://github.com/Ksinghania2/ChangeScribe-Changelog-Action/commit/cc8a19df03a501cbb5161eb8ca08428ce81de98c))
<!-- changescribe:end -->
