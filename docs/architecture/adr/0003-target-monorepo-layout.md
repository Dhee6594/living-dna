# ADR-0003: Target monorepo layout & staged migration

- **Status:** Accepted
- **Date:** 2026-07-04
- **Deciders:** @Dhee6594

## Context

Blueprint §15.2 defines a target enterprise monorepo layout — `services/` (a dozen
microservices), `packages/` (ui, client-ts/go/py, mcp-server), `cli/`, `web/`, `docs/`,
`deploy/` (compose + helm), `ontology/`, `evals/`, `fixtures/synthetic-org/`, `.github/`.

Today the repository is a **single stdlib Python package** (`dna/`) plus a Next.js UI
(`webapp/`) and a single-file browser UI (`web/`). Most of the services in §15.2 do not
exist yet.

The Enterprise Roadmap is explicit that premature structure is an anti-goal ("Neo4j
migration before traversals demand it. Premature."; "Polish on the single-repo CLI never
produces [enterprise value]"). Creating a dozen empty `services/*` directories would fake a
microservice architecture we haven't built and add churn without value.

## Decision

Adopt the §15.2 layout as the **target**, and migrate toward it in stages driven by real
need — not in one speculative move.

**Now (this change):** add the parts of §15.2 that are real and non-destructive —
`.github/`, governance files, and a `docs/` tree — on the `develop` branch. **Do not**
physically relocate `dna/` or rewrite imports/packaging yet.

**Mapping of current → target (for when each move is justified):**

| Today | Target (§15.2) | Trigger to move |
|---|---|---|
| `dna/` (engine package) | `services/*` + `cli/` + `packages/` | When the engine is split into independently deployable services, or the CLI is extracted. |
| `webapp/` | `web/` | When we consolidate the two UIs; low urgency. |
| `web/index.html` | folded into `web/` or retired | When `webapp/` fully supersedes it. |
| `fixtures/` | `fixtures/synthetic-org/` | With the synthetic demo-org generator work. |
| `tests/` | co-located per package + top-level `evals/` | When the golden-set eval harness lands (Roadmap Stage 1). |
| (new) | `packages/mcp-server/` | Roadmap Stage 1 — the MCP wedge. |
| (new) | `deploy/compose`, `deploy/helm` | Roadmap Stage 3 — self-host/VPC deployment. |
| (new) | `ontology/` | When schema migrations need a home. |

Each physical move is its own PR with its own ADR update, so `git` history (and our own
genome) records why the boundary moved.

## Consequences

- Contributors get an enterprise-grade repo surface (CI, governance, docs, ADRs)
  immediately, without a hollow directory forest.
- The `dna` package keeps working — no import churn, no broken `pyproject.toml` entry point.
- Reorganization becomes incremental and reviewable, each step tied to a roadmap trigger.
- Risk: the tree doesn't yet match §15.2 one-to-one. Accepted — this ADR is the map, and
  the mapping table above is the checklist for closing the gap.
