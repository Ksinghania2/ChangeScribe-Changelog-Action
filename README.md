# ChangeScribe-Changelog-Action

A GitHub Action that generates changelog entries from repository changes.

## Overview
This GitHub Action automatically generates changelog entries based on repository events such as pulls, issues, and commits. It integrates with the scribe CLI to provide structured changelog generation.

## Features
- Automatic changelog generation from pull requests
- Support for issue tags and labels
- Integration with scribe for structured output
- CI/CD friendly
- Configurable via action inputs

## Inputs
| Parameter | Description | Required |
|-----------|-------------|----------|
| `github-token` | GitHub token for API access | No |
| `scribe-config` | Path to scribe configuration file | No |

## Usage
```yaml
name: Generate Changelog
on:
  pull_request:
    types: [opened, edited, reopened, closed]
jobs:
  changelog:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Generate Changelog
        uses: Ksinghania2/ChangeScribe-Changelog-Action@v1
        with:
          github-token: ${{ secrets.GITHUB_TOKEN }}
```

## License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Topics
- changelog
- ci-cd
- developer-tools
- github-action
- release-automation
```