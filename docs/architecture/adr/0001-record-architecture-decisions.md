# ADR-0001: Record architecture decisions

- **Status:** Accepted
- **Date:** 2026-07-04
- **Deciders:** @Dhee6594

## Context

Living DNA's entire premise is that a codebase should be able to explain *why* it was
built the way it is. It would be incoherent to sell architectural archaeology while
keeping our own decisions in people's heads. We also need a lightweight, low-friction
place to record decisions that don't warrant a full design doc but do change the system.

## Decision

We record architecturally significant decisions as **Architecture Decision Records
(ADRs)** — one Markdown file per decision under `docs/architecture/adr/`, numbered
`NNNN-title.md`, in the format popularized by Michael Nygard.

ADRs double as our **RFC mechanism** (see `GOVERNANCE.md`): an architectural change is
proposed by opening a PR that adds an ADR with status `Proposed`, discussed on the PR, and
merged as `Accepted` or `Rejected`. We never delete rejected ADRs — the trail is the point.

An architecturally significant decision is one that adds/changes a node, edge, or event
kind; changes storage or schema; introduces a new external boundary (connector, API); or
touches the four design laws in `ARCHITECTURE.md`.

## Consequences

- Decisions are versioned, reviewable, and become part of this repo's own genome
  ("customer zero").
- Small changes stay lightweight (normal PRs); only significant ones need an ADR.
- Requires discipline to actually write them; `CONTRIBUTING.md` and the PR template point
  contributors here.

## Format

```
# ADR-NNNN: <title>
- Status: Proposed | Accepted | Rejected | Superseded by ADR-XXXX
- Date: YYYY-MM-DD
- Deciders: @handles

## Context      (the forces; why a decision is needed)
## Decision     (what we chose, in active voice)
## Consequences (results, trade-offs, follow-ups)
```
