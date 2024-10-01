# 🧬 living-dna — walking skeleton (v0)

**Your codebase remembers everything. Now it can tell you.**

This is the runnable v0 of Living Software DNA: point it at any local git repo and get a
queryable Software Genome — DNA profiles, architecture archaeology, bus-factor simulation,
and time travel. **Zero dependencies** (Python 3.10+ stdlib only).

## Quickstart (60 seconds)

```bash
# 1. generate the synthetic demo org (87 commits, 5 services, 4 engineers, 2.5 yrs history)
python3 fixtures/make_fixture.py

# 2. sequence it (passes 1-4: census → structure → history → eras → profiles)
python3 -m dna.cli ingest fixtures/acme-shop

# 3. explore
python3 -m dna.cli profile payments
python3 -m dna.cli ask "why does checkout depend on payments"
python3 -m dna.cli ask "who knows payments"
python3 -m dna.cli ask "what happens if Lena leaves"
python3 -m dna.cli timetravel --at 2024-06-01
python3 -m dna.cli diff --from 2024-06-01 --to now

# 4. Genome Browser UI
python3 -m dna.cli serve            # → http://localhost:8077
```

Or point it at a **real repo**: `python3 -m dna.cli ingest ~/code/your-project`

## What works today

| Capability | Status |
|---|---|
| Census + structure passes (services, languages, dependency edges with provenance) | ✅ |
| Full git history replay → canonical event log (append-only, idempotent) | ✅ |
| Bitemporal graph (valid_from/valid_to + recorded_at on every fact) | ✅ |
| Era detection (activity segmentation per service) | ✅ |
| DNA profiles (born/cause, eras, deps, knowledge, derived risks) — materialized, fast reads | ✅ |
| KNOWS weights + effective owners (entropy-based) + bus-factor simulation | ✅ |
| Time travel + causal diff between any two dates | ✅ |
| Graph-first archaeology Q&A with evidence (works with **no** LLM) | ✅ |
| LLM layer: era packing, decision mining with citation verification, deep answers | ✅ (set `ANTHROPIC_API_KEY`) |
| Web UI: genome map, time scrubber, gene cards, ask box, bus-factor heatmap | ✅ |

## Architecture (v0 = the blueprint, miniaturized)

```
git history ──► canonical events ──► bitemporal mini-graph (SQLite)
                                          │
                     materialized DNA profiles (read path: zero inference)
                                          │
              CLI · JSON API · web UI · (optional) LLM miner with verifier
```

The four design laws from the blueprint, already enforced here:
1. **Write-time understanding, read-time data path** — profiles/timetravel never call an LLM.
2. **Append-only bitemporality** — updates close `valid_to`, never overwrite.
3. **Evidence on everything** — every fact carries provenance; the miner drops uncited claims.
4. **Graph-first answers** — the LLM deepens answers; it is never required for them.

## Layout

```
dna/db.py          bitemporal graph store (SQLite, stdlib)
dna/ingest.py      passes 1-4: census, structure, history, eras
dna/genome_ops.py  profiles, effective owners, bus factor, time travel, ask
dna/ai.py          optional: era packer, decision miner + verifier, deep answers
dna/server.py      JSON API + Genome Browser (http.server)
dna/cli.py         the `dna` command
fixtures/          synthetic demo organization generator
tests/             end-to-end test (17 checks): python3 -m tests.test_skeleton
```

## Next steps

See [BUILDING.md](BUILDING.md) — the step-by-step path from this skeleton to the
Phase-1 MVP in the blueprint (`living-software-dna/14-implementation-roadmap.md`).
