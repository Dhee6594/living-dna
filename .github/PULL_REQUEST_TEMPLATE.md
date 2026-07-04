<!--
  Target `develop` for features/fixes. Only release PRs target `main`. See CONTRIBUTING.md.
-->

## What & why

<!-- What does this change and what problem does it solve? Link the issue: Closes #123 -->

## The four design laws (check the ones this PR must respect — see ARCHITECTURE.md §2)

- [ ] **Write-time understanding, read-time data path** — no LLM / raw-history recompute added to a read path
- [ ] **Append-only bitemporality** — no `UPDATE`/`DELETE` of facts; changes close + insert
- [ ] **Evidence on everything** — new nodes/edges carry `provenance`; unciteable claims dropped
- [ ] **Graph-first answers** — LLM only narrates facts the graph already produced

## Testing

<!-- Commands you ran. New/updated tests? -->

- [ ] `python -m tests.test_skeleton` passes
- [ ] `ruff check .` clean
- [ ] (web) `npm run typecheck && npm run test && npm run build` pass — if `webapp/` touched

## Checklist

- [ ] Branched from and targets `develop`
- [ ] CHANGELOG.md updated under `## [Unreleased]` (for user-facing changes)
- [ ] Docs updated (`docs/`, `ARCHITECTURE.md`, or an ADR for architectural decisions)
- [ ] Commits signed off (`git commit -s`) per the DCO
