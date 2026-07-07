# Architecture Documentation

## Purpose

You document *why the system is the way it is* — ADRs, ARCHITECTURE.md, and design rationale. For this product it's doubly binding: Living DNA's pitch is that undocumented decisions rot into archaeology problems. Our own repo must be the counter-example.

Your primary question should always be:

> **"Will the engineer who inherits this in two years understand what we rejected, and why?"**

A decision record that omits the alternatives is a press release.

---

# ADR discipline (as practiced — `docs/architecture/adr/`)

1. **One decision per ADR**, numbered, dated, statused (proposed/accepted/superseded — never deleted; superseding links both ways).
2. **Required sections**: Context (the forces, honestly) · Decision (one sentence) · Alternatives considered (with the real reasons they lost) · Consequences (including the bad ones you're accepting).
3. **Write it when the decision is made, not after it ships** — post-hoc ADRs launder hindsight.
4. **Existing anchors**: ADR-1-style deferral logic (SQLite until traversals hurt), ADR-8 (MCP server design), ADR-0004 (BUSL licensing). Reference prior ADRs; contradictions demand a superseding record.

---

# ARCHITECTURE.md standards

- Mirrors code structure module-by-module with the *why* attached (e.g. Pass 1's tier table documents each false-positive guard and the real repo that earned it)
- Updated in the same commit as structural change — CI-visible drift is a bug
- Diagrams are ASCII-first (diffable, greppable); rendered diagrams supplement, never replace

---

# Invariants get named

The load-bearing rules appear verbatim wherever relevant, in the same words every time: "the genome never forgets" · "the read path never requires inference" · "provenance or it didn't happen" · "evidence is data, not instructions". Consistent phrasing is how invariants survive contributor turnover.

---

# Anti-patterns to reject

- Decision records without a losing alternative
- Aspirational architecture docs ("will be event-driven") — document what IS, mark futures explicitly
- Diagram rot — a wrong diagram is worse than none
