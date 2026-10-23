# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-10-23

### Added

- Zero-dependency Python CLI that audits a repository against *The Pragmatic Programmer*.
- 20 core rules covering duplication, configuration, magic values, orthogonality, globals, call chains, inheritance, contracts, resources, coincidence, complexity, naming, comments, broken windows, tests, test hygiene, automation, version control, end-to-end coverage, and documentation.
- Three opt-in rules: small steps, reversibility, and shared state.
- Text, Markdown, and JSON reports.
- Agent review packet with a manual review queue and suggested prompt.
- Inline and file-level suppression with required reasons.
- `.pragmatic-audit.toml` configuration for excludes, thresholds, ignores, and CI gates.
- Portable Agent Skill for Claude Code, Claude Cowork, ChatGPT Work/CoWork, OpenCode, Codex, and generic Agent Skills hosts.
- Example bad and good repositories, a real example report, and reproducible SVG previews.
- GitHub Actions CI with a Python 3.11, 3.12, and 3.13 matrix.
- Apache-2.0 license and `NOTICE`.
- Public documentation site with Open Graph metadata, structured data, sitemap, and targeted guides for auditing AI-generated code, DRY violations, and Pragmatic Programmer reviews.
- PyPI Trusted Publishing workflow.

[Unreleased]: https://github.com/CobaltChaser/pragmatic-audit/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/CobaltChaser/pragmatic-audit/releases/tag/v0.1.0
