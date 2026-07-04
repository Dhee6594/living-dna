# ADR-0002: Adopt a gitflow branching model

- **Status:** Accepted
- **Date:** 2026-07-04
- **Deciders:** @Dhee6594

## Context

The project is moving from a single-developer skeleton toward an enterprise-grade,
contribution-open repository (blueprint §15). That requires a branching model that keeps a
releasable line always green, gives contributors an obvious integration target, and lets
release/hotfix flow stay separate from day-to-day work.

## Decision

Adopt a **gitflow-style model**:

- **`main`** — always releasable. Protected. Only release and hotfix PRs merge here; each
  release is tagged (`vX.Y.Z`).
- **`develop`** — the integration branch. All feature/fix work merges here first. This is
  the default target for contributor PRs.
- **`feat/*`, `fix/*`, `chore/*`, `docs/*`** — short-lived branches cut from `develop` and
  merged back via reviewed PR.
- **`hotfix/*`** — cut from `main` for urgent production fixes, merged to both `main` and
  `develop`.

CI (`.github/workflows/ci.yml`) runs on pushes and PRs to both `main` and `develop`.

### Recommended branch protection (configure in GitHub settings)

- `main`: require PR + passing CI + at least one review; no force-push; linear history.
- `develop`: require PR + passing CI.

## Consequences

- Contributors have one clear answer to "where do I branch from?" (`develop`).
- `main` stays deployable/taggable, which the release notes in `CHANGELOG.md` depend on.
- Slightly more ceremony than trunk-based development — acceptable for an open-contribution
  project with external reviewers. Revisit if the team consolidates and CI gates mature
  enough that trunk-based becomes lower-risk.
