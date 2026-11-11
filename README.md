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
