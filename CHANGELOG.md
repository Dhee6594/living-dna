# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Phase 4 — GitHub connector & continuous intelligence.**
  - `dna/github_connector.py`: connect a repo (public / PAT / org / branch), clone or import,
    initial build, and repository-metadata storage on the `repo:<name>` node. Tokens are never
    persisted. CLI: `dna connect`, `dna repos`.
  - `dna/continuous.py`: incremental ingestion — replay only new commits, rebuild derived facts
    (KNOWS, CO_CHANGES, births) from the full event log, and refresh profiles/eras/structure.
    Byte-identical to a full re-ingest; ~3× faster. CLI: `dna sync [--all]`.
  - `dna/pr_intel.py`: PR impact prediction — affected services, reviewers, architectural-risk
    band, hidden-dependency and documentation impact. CLI: `dna pr`.
  - `dna/timeline.py`: architecture evolution — service births, dependency add/remove history,
    ownership shifts, and a monthly risk-trend series. CLI: `dna timeline`.
  - Server: `GET /api/repos`, `GET /api/timeline`, `POST /api/{connect,sync,pr}`; UI: repo
    onboarding (<2 min), sync, PR-impact panel, timeline sparkline.
  - `tests/test_phase4.py` (18 checks incl. incremental-vs-full accuracy). Validated on
    flask/fastapi. Behavior-preserving refactor of `ingest.history()` (shared `_collect_commits`,
    `rev_range` param). See `PHASE-4.md`.
- **License:** source-available under the Business Source License 1.1 (`LICENSE`), converting
  to Apache-2.0 on 2029-07-04. Recorded in ADR-0004. `pyproject.toml` updated to `BUSL-1.1`.
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
