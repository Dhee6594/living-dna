# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Enterprise repository scaffolding: `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`,
  `SECURITY.md`, `GOVERNANCE.md`, this changelog.
- `.github/` — CI workflow (engine test matrix + web build), issue forms, PR template,
  `CODEOWNERS`, Dependabot.
- `develop` integration branch and a documented gitflow model (ADR-0002).
- `docs/` site skeleton and Architecture Decision Records under
  `docs/architecture/adr/` (ADR-0001…0003).

## [0.1.0] — 2026-07-04

### Added
- Walking-skeleton engine: `dna ingest` → bitemporal graph → materialized DNA profiles →
  bus-factor, time-travel, causal diff, and graph-first archaeology Q&A. Pure Python
  stdlib, SQLite storage.
- Tiered service detection beyond manifests; single-walk census.
- Insight Engine (`dna/insights.py`): hidden coupling, cycles, silos, SPOF, ranked
  recommendations; `/api/insights` and `dna insights` CLI.
- JSON API + Genome Browser UI (`dna/server.py`, `web/index.html`); loopback bind default.
- Next.js intelligence web UI (`webapp/`): 11 routes, React Flow genome, insights panels.

[Unreleased]: https://github.com/Dhee6594/living-dna/compare/v0.1.0...develop
[0.1.0]: https://github.com/Dhee6594/living-dna/releases/tag/v0.1.0
