# Changelog

All notable public-facing changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project follows [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- Documented the MCP stability and data-safety contract, including atomic migrations, destructive migration archive manifests, pure-read lifecycle status, strict read-only retrieval mode, concurrent-safe backups, and active-server restore guards.
- Added configuration guidance for `RL_DEVELOPER_MEMORY_STRICT_READ_ONLY`, `RL_DEVELOPER_MEMORY_ENABLE_DENSE_CACHE_WRITES`, and `RL_DEVELOPER_MEMORY_ENABLE_TELEMETRY_WRITES`.
- Added focused validation guidance for migration, backup, lifecycle, and read-like retrieval side-effect checks.

### Changed
- Clarified backup/restore operations, lifecycle status semantics, and release-readiness interpretation for shadow-first rollout.

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
