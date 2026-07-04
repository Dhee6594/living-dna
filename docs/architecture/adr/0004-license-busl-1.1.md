# ADR-0004: License under Business Source License 1.1

- **Status:** Accepted
- **Date:** 2026-07-04
- **Deciders:** @Dhee6594

## Context

The repository is going public to serve two goals at once: **portfolio/recruiter
visibility** (show engineering craft — code, tests, CI, architecture) and **protecting a
potential commercial product**. ENTERPRISE-ROADMAP §8 flagged the Community-Edition license
as an open founder decision; `pyproject.toml` had deliberately declared `Proprietary` in the
interim.

Three options were weighed:

- **Apache-2.0** (the blueprint §15.1 suggestion) — maximal OSS goodwill, but anyone,
  including a competitor, may commercialize the code.
- **All-rights-reserved** (public, no license) — visible but legally locked; reads as
  "closed" to OSS-minded reviewers.
- **Business Source License 1.1 (BUSL-1.1)** — source-available: fully readable and usable
  non-production / non-competing, but a competitor cannot offer it as a competing hosted or
  embedded commercial product; each version auto-converts to a permissive license after a
  set Change Date.

The engine is not the moat (roadmap §6: "the moat is the cloud control plane, multi-source
enrichment depth, and prediction calibration — not code secrecy"), so total secrecy buys
little. But permissive licensing gives away future commercial optionality for free.

## Decision

License the work under **Business Source License 1.1** with:

- **Change License:** Apache License, Version 2.0 (GPL-compatible per the BSL covenants).
- **Change Date:** 2029-07-04 (four years) for version 0.1.0; set per released version.
- **Additional Use Grant:** production use permitted *except* offering the Licensed Work to
  third parties on a hosted/embedded basis to compete with the Licensor's offerings.

`pyproject.toml` declares `BUSL-1.1`; `README.md` carries a License section; the full text
lives in `LICENSE`.

## Consequences

- Recruiters and engineers can read and run everything — the portfolio goal is fully met.
- Competitors cannot turn the code into a rival commercial service before the Change Date —
  the product goal is protected without hiding anything.
- BUSL is **source-available, not OSI open-source**; some contributors and package
  ecosystems treat that differently. Accepted trade-off; the Apache-2.0 conversion is the
  long-term open-source commitment.
- The CE/EE *edition* split (which features are enterprise-only) is still to be designed as
  those features land; this ADR covers licensing of the current codebase only.
- Supersedes the interim `Proprietary` declaration and closes decision #1 in `GOVERNANCE.md`.
