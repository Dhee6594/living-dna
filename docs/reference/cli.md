# CLI Reference

All commands accept `--db PATH` (default `.dna/genome.db`) before the subcommand.
Install with `pip install -e .` for the `dna` entry point, or use
`python3 -m dna.cli` — they are identical.

## `dna ingest <repo> [--max-commits N]`

Sequence a local git repository: census (tiered service detection) → structure
(dependency edges) → history (events, knowledge, co-change, identity resolution)
→ eras → materialized DNA profiles.

- `--max-commits N` — replay only the N most-recent commits (first runs on very
  large repos). `0` (default) = full history.
- Service detection tiers: manifests → `services|apps|packages/` layout →
  entry-points (`Dockerfile`, `main.py`, `main.go`, `*_server.py`, …) →
  docker-compose contexts → content dirs. Each service records `detected_by`.
- Duplicate git identities merge via multi-token name match, GitHub-noreply
  local-part match, or an explicit override file
  `<repo>/.dna/identities.json`: `{"aliases": {"old@x": "canonical@y"}}`.

## `dna insights`

Engineering-intelligence report (JSON): overview scores (complexity,
maintainability, maturity — formulas included in the output), churn hotspots,
stable/volatile modules, hidden coupling, dependency cycles, drift, SPOF,
knowledge silos, missing docs, ranked recommendations
(`score = impact·confidence − 0.5·risk`), and four executive summaries.
Graph-only and deterministic; no network, no LLM.

## `dna profile <service>`

Print one service's DNA profile: dependencies (with since-dates and evidence),
dependents, co-change partners, eras, owners with weights, effective owners,
derived risks, origin commit.

## `dna ask "<question>" [--deep]`

Graph-first archaeology. Recognized shapes: `who knows <svc>`,
`why does <a> depend on <b>`, `why does <svc> exist`,
`what happens if <person> leaves`. Answers cite evidence.
`--deep` adds LLM narrative synthesis (requires `ANTHROPIC_API_KEY`).

## `dna busfactor [--person NAME]`

Without `--person`: org-wide heatmap (everyone × departure blast radius).
With: full simulation — knowledge lost per service, criticality, recovery
estimate, succession pairings.

## `dna timetravel --at YYYY-MM-DD`

The service/dependency graph as it was on that date (bitemporal query).

## `dna diff --from YYYY-MM-DD [--to YYYY-MM-DD]`

Structural diff between two dates: services and dependencies added/removed,
with the commit message that caused each service birth. `--to` defaults to now.

## `dna mine <service> [--era N]`

LLM decision mining over one era's commit record (requires `ANTHROPIC_API_KEY`).
Extracted decisions are citation-verified before being written to the graph;
uncited claims are dropped. Model override: `DNA_MODEL` env var.

## `dna export [--out FILE]`

Full open-schema JSON dump — every node, edge, and event, including closed
(historical) rows, with bitemporal fields and provenance. Schema version 1.0.

## `dna report`

Genome quality report: coverage, bots filtered, renames tracked, and anomaly
flags (`ISOLATED`, `THIN`, `NO-OWNER`) telling you what to inspect after a run.

## `dna serve [--port 8077] [--host 127.0.0.1]`

JSON API + Genome Browser UI. Binds loopback by default (the genome holds
person-level data and v0 has no auth); pass `--host 0.0.0.0` to expose
deliberately.
