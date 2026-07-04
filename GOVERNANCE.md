# Governance

Living DNA is, for now, a **BDFL-led project with a public RFC process** — matching the
Phase 1–2 model in the product blueprint (§15.5). This document says who decides what,
and how, so contributors know where a change is headed before they build it.

## Roles

- **BDFL / Lead maintainer** — [@Dhee6594](https://github.com/Dhee6594). Final say on
  architecture, the roadmap, and releases.
- **Maintainers** — merge rights within an area (per `CODEOWNERS`). Added by the BDFL on a
  track record of good reviews and contributions.
- **Contributors** — anyone with a merged PR. The ladder is contributor → triager →
  area maintainer.

As the project grows (blueprint Phase 3+), this moves to a **Technical Steering Committee**
with at least two non-employee maintainers and a versioned public roadmap.

## Decision-making

- **Everyday changes** (bug fixes, small features, docs): normal PR review. One maintainer
  approval + green CI is enough. Target `develop`.
- **Architectural changes** — a new node/edge/event kind, a storage or schema change, a new
  external boundary (connector/API), a change to the four design laws, or an ontology
  extension — require an **RFC** merged before implementation.

## RFC process

1. Open an RFC as a PR adding `docs/architecture/adr/NNNN-title.md` (copy ADR-0001's
   template). ADRs *are* our RFCs — we practice the archaeology we sell, so decisions live
   in the repo and become part of its own genome.
2. Discussion happens on the PR. Aim for consensus; the BDFL breaks ties.
3. Merged with status `Accepted` (or `Rejected`, kept for the record — we never delete the
   trail). Implementation PRs then reference the ADR.

## Open founder decisions (not yet settled — see ENTERPRISE-ROADMAP §8)

These are deliberately **undecided** and should not be resolved unilaterally in a PR:

1. **License / edition split.** `pyproject.toml` currently declares `Proprietary` on
   purpose — the Community-Edition license (the blueprint suggests Apache-2.0) is a founder
   decision that shapes everything downstream. No `LICENSE` file is committed until it's made.
2. **Cloud-first vs. self-host-first** go-to-market ordering.
3. **Smart-model routing** policy for the AI miner (cost vs. reasoning quality).

## Code of Conduct

All participation is governed by [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md).
