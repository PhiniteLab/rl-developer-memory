# Changelog

All notable public-facing changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project follows [Semantic Versioning](https://semver.org/).

## [Unreleased]

- No unreleased changes yet.

## [0.1.0] - 2026-04-03

### Changed
- normalized public-facing repository naming by renaming `EXAMPLES/` to `examples/`
- normalized the theorem mapping document name to `docs/THEORY_TO_CODE.md`
- rewrote the main README for clearer install, dependency, and release-readiness guidance
- simplified the docs index, installation guide, usage guide, and dependency notes
- refreshed the examples guide for clearer public-facing language

### Added
- `CODE_OF_CONDUCT.md`
- GitHub tag-based release workflow
- explicit public-facing project metadata and documentation links
- GitHub issue routing config, CODEOWNERS, and Dependabot automation

### Fixed
- tightened the public security reporting policy and response expectations
- removed brittle hard-coded public surface counts from the README
- hardened CI and release automation with Python 3.11 coverage and tag/version validation
- clarified that `examples/results/` contains committed reference snapshots and that local runs should prefer temporary output paths
