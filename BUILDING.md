# BUILDING.md — from walking skeleton to Phase-1 MVP

Solo full-time pace. Each step ends in something demoable. Blueprint references in parentheses.

## Week 0 — you are here ✅
Skeleton runs end-to-end: ingest → graph → profiles → bus factor → time travel → ask → UI.
61-check test suite green (`python3 -m tests.test_skeleton`).

## Weeks 1–2 — make it true on real repos
1. Run `dna ingest` on 5 real repos you know well (yours + big OSS like `fastapi`, `flask`).
2. Fix what reality breaks: rename tracking, monorepo layout edge cases, merge commits,
   bot authors (dependabot noise → filter), language coverage for imports.
3. Add `dna export` (JSON dump of all nodes/edges/events) — the open-schema promise (§2.4 law 7).
4. **Demo:** profile + bus factor on a repo a friend knows; ask them if it is *correct*. Their
   corrections are your first quality data.

## Weeks 3–4 — the archaeology jump (the product's wow)
1. Wire `ANTHROPIC_API_KEY`; run `dna mine payments --era 2` on the fixture, then on real repos.
2. Build the **golden set** (§13.2): 20 questions about a repo you know, with known-true answers.
   Score every prompt change against it. This harness is more valuable than any single feature.
3. Improve era packing: include PR descriptions (next step's connector), diffs sampled by
   information density, chronological interleaving (§9.4).
4. Add `ask --deep` write-back: verified new facts become Decision nodes (the §6.5.2 loop).
5. **Demo:** "why does X exist" answered with cited commits on a repo you didn't write.

## Weeks 5–7 — GitHub connector (beyond local git) ✅ (Phase 4)
Delivered: `dna/github_connector.py` (connect/clone/import a repo — public / PAT / org /
branch — with metadata storage), `dna/continuous.py` (incremental ingestion + continuous
refresh, byte-identical to a full re-ingest), `dna/pr_intel.py` (PR impact prediction), and
`dna/timeline.py` (architecture evolution over time). CLI: `connect`, `sync`, `repos`, `pr`,
`timeline`; UI: repo onboarding, sync, PR panel, timeline. 18-check `tests/test_phase4.py` +
validation on flask/fastapi. See [PHASE-4.md](PHASE-4.md).

Still open (deferred): PR **thread/review** ingestion via REST (`code.pr` events) and the
KNOWS review-component (§9.6) — the connector currently maps commits + PR *file* impact; PR
discussion mining lands with the archaeology-depth work.

## Weeks 8–10 — productize the read path
1. Swap SQLite → Postgres behind the same `Genome` interface (keep SQLite for `dna` CLI mode).
   Evaluate moving the graph to Neo4j only when traversals demand it (ADR-1; don't rush it).
2. React UI replacing the single-file page; keep the four signature views: gene card, genome
   map, time scrubber, ask (§7.3).
3. MCP server exposing `get_dna_profile`, `ask_genome`, `who_knows`, `blast_radius` (F-10.2) —
   this makes every AI coding agent your distribution channel.
4. **Demo:** Claude Code / Cursor answering "who knows this module" from your genome via MCP.

## Weeks 11–12 — ship Community Edition
1. `docker compose up` one-liner; `dna init` onboarding; docs site with the 30-min quickstart.
2. Run the engine on a famous OSS project; publish "The Architecture Archaeology of <X>" —
   your launch asset (§15.6).
3. Show HN with the hosted demo org. Collect design partners (target: 10).

## Then: follow the roadmap
Phase 2 (Jira/Slack/Confluence fusion, entity resolution, risk engine) onward is sequenced in
`living-software-dna/14-implementation-roadmap.md`, with the ClickUp work breakdown in
section 16 and the repo/community strategy in section 15.

## Working rules (from the blueprint, enforced from day one)
- Every derived fact carries provenance; every prediction gets logged for backtesting.
- Prompts are code: no prompt change merges without a golden-set run.
- Dogfood: this repo's own genome is your first customer. `dna ingest .` after every milestone.
