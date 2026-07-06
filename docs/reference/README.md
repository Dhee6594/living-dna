# Reference

Precise reference material for every public surface.

- **[CLI](cli.md)** — every `dna` subcommand and flag
- **[JSON API](api.md)** — all 12 endpoints + the insights document shape
- **[Performance](performance.md)** — measured ingest/latency/memory numbers

Environment variables: `ANTHROPIC_API_KEY` (enables `ask --deep` / `mine`),
`DNA_MODEL` (LLM override), `DNA_API_URL` (webapp → API proxy target).

Ontology quick sheet — node kinds: `Service · Person · Repo · Era · Decision`;
edge kinds: `DEPENDS_ON · KNOWS · CO_CHANGES · PART_OF · HAS_ERA · JUSTIFIES`;
event kinds: `code.commit · code.rename`; export schema: `1.0`
(see [ARCHITECTURE.md](../../ARCHITECTURE.md) for full semantics).
