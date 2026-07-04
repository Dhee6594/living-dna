# Contributing to Living DNA

Thanks for helping sequence software genomes. This guide gets you from clone to a
merged PR. Read [`ARCHITECTURE.md`](ARCHITECTURE.md) first — the **four design laws**
in §2 are non-negotiable and most review feedback traces back to them.

## TL;DR

```bash
git clone https://github.com/Dhee6594/living-dna.git
cd living-dna
pip install -e .                 # the engine is pure stdlib; this just wires the `dna` CLI
python -m tests.test_skeleton    # full suite — should be all green
ruff check .                     # lint

git switch develop
git switch -c feat/your-thing    # branch off develop
# ...hack...
git commit -s -m "feat(ingest): ..."   # -s signs off the DCO (see below)
git push -u origin feat/your-thing
# open a PR targeting `develop`
```

## Development environment

- **Python ≥ 3.10.** The engine (`dna/`) has **zero runtime dependencies** — stdlib
  only, SQLite is the whole database. Keep it that way; `dna/db.py` in particular must
  stay dependency-free (it's the swap seam for Postgres/Neo4j).
- **Lint:** `ruff check .` (config in `pyproject.toml`).
- **Optional AI layer** activates only when `ANTHROPIC_API_KEY` is set; nothing else
  requires it.

### Web UI (`webapp/`)

```bash
cd webapp
npm ci
npm run typecheck && npm run test && npm run build
npm run dev      # http://localhost:3000 (expects the engine's API server running)
```

## Branching model (gitflow)

- **`main`** — stable, released. Protected. Only release/hotfix PRs land here.
- **`develop`** — integration branch. **Target your PRs here.**
- **`feat/*`, `fix/*`, `chore/*`, `docs/*`** — branch off `develop`, merge back via PR.

See [ADR-0002](docs/architecture/adr/0002-adopt-gitflow-branching-model.md).

## Commits

- **Conventional Commits:** `type(scope): summary` — e.g. `feat(insights): flag SPOF`.
- **Sign off every commit** with `git commit -s`. We use the
  [Developer Certificate of Origin](https://developercertificate.org/) (DCO), **not** a
  CLA — low friction, but the sign-off line is required and CI/maintainers will check it.

## What makes a PR mergeable

1. `python -m tests.test_skeleton` is green and you **added/updated tests** for behavior
   changes. Correctness is asserted end-to-end here.
2. `ruff check .` is clean.
3. If you touched `webapp/`: typecheck, vitest, and `next build` all pass.
4. You respected the four design laws (the PR template has the checklist).
5. `CHANGELOG.md` updated under `## [Unreleased]` for anything user-facing.
6. Docs updated — and an **ADR** added under `docs/architecture/adr/` for any
   architectural decision (new node/edge kind, storage change, new external boundary).

## Bigger changes need an RFC

New node/edge kinds, ontology changes, new connectors, or anything that shifts the
architecture start as an RFC, not a PR. See [`GOVERNANCE.md`](GOVERNANCE.md).

## Reporting bugs / security

- Bugs: use the issue templates.
- Security: **do not** open a public issue — see [`SECURITY.md`](SECURITY.md).
