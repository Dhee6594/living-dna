# Architecture

- **The map of how the code hangs together:** [`../../ARCHITECTURE.md`](../../ARCHITECTURE.md)
  — module map, the four design laws, write path vs. read path, the bitemporal data model.
- **Where it's going:** [`../../BUILDING.md`](../../BUILDING.md).

## Architecture Decision Records (ADRs)

We keep architectural decisions in the repo and dogfood them into our own genome —
public ADRs are a deliberate openness move (blueprint §15.2). ADRs also serve as our
**RFCs** for architectural changes (see [`../../GOVERNANCE.md`](../../GOVERNANCE.md)).

| ADR | Title | Status |
|---|---|---|
| [0001](adr/0001-record-architecture-decisions.md) | Record architecture decisions | Accepted |
| [0002](adr/0002-adopt-gitflow-branching-model.md) | Adopt a gitflow branching model | Accepted |
| [0003](adr/0003-target-monorepo-layout.md) | Target monorepo layout & staged migration | Accepted |
| [0004](adr/0004-license-busl-1.1.md) | License under Business Source License 1.1 | Accepted |

To propose a change, copy ADR-0001's format into `adr/NNNN-title.md` and open a PR.
