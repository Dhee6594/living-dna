# 🧬 Living DNA

**Your codebase remembers everything. Now it can tell you.**

Living DNA sequences a git repository into a queryable **Software Genome** — a
bitemporal graph of services, people, knowledge, and decisions — then answers the
three questions GitHub can't:

> **Who really knows this?** · **What breaks if they leave or if we change this?** · **Why was it built this way?**

[![CI](https://github.com/Dhee6594/living-dna/actions/workflows/ci.yml/badge.svg)](https://github.com/Dhee6594/living-dna/actions/workflows/ci.yml)
![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)
![Engine dependencies: zero](https://img.shields.io/badge/engine%20deps-zero-brightgreen)
![License: BUSL-1.1](https://img.shields.io/badge/license-BUSL--1.1-lightgrey)

The analysis engine is **pure Python stdlib** — no pip dependencies, no daemons, no
cloud. One SQLite file holds your genome.

## Five-minute demo

```bash
git clone https://github.com/Dhee6594/living-dna && cd living-dna
./scripts/demo.sh              # generates a demo org, sequences it, starts the browser
# → open http://127.0.0.1:8077
```

Or point it at any repo you have locally:

```bash
pip install -e .
dna ingest ~/code/your-project        # seconds, even on large repos (--max-commits N to cap)
dna insights                          # engineering-intelligence report, ranked actions
dna serve                             # browse the genome at http://127.0.0.1:8077
```

## What you get

**Insight Engine** — findings you can't read off GitHub:

- **Hidden coupling** — services that change together with *no declared dependency*
  (on Prometheus: `mantine-ui ↔ prometheus` co-changed 84× undeclared)
- **Bus factor** — departure simulations with knowledge lost, recovery time, succession pairings
- **Knowledge silos & single points of failure** — who really owns what, with evidence
- **Dependency cycles, architectural drift, volatility** — where the structure is eroding
- **Ranked recommendations** — scored by impact · risk · confidence · effort, never generic
- **Executive reports** — one paragraph each for CTO, EM, Staff Engineer, Platform team

**Architecture archaeology** — evidence-cited Q&A:

```bash
dna ask "who knows payments"
dna ask "why does checkout depend on payments"
dna ask "what happens if Lena leaves"
dna timetravel --at 2024-06-01        # the dependency graph as it was
dna diff --from 2024-06-01            # what changed since, with causes
```

Every answer cites commits, edges, and provenance. Every score's formula is
documented next to it — nothing is a black box, and **no LLM is required** for any
of the above (an optional Anthropic API key enables decision mining and narrative
answers via `dna mine` / `dna ask --deep`).

**Continuous intelligence** — connect a repo once, then keep it live:

```bash
dna connect pallets/flask                       # clone + build + store metadata (< 2 min)
dna connect https://github.com/acme/api --token $GH_TOKEN --branch main   # private / org
dna sync flask                                  # replay ONLY new commits (≈3× faster)
dna sync --all                                  # refresh every connected repo
dna repos                                        # connected repos + metadata

dna pr --repo flask --base HEAD~20              # predict a PR's blast radius before merge
dna timeline --repo flask                        # architecture evolution over time
```

Incremental sync replays only the new commits and rebuilds derived facts from the
event log, so the result is **byte-identical to a full re-ingest** — no drift, no
rebuild. `dna pr` predicts affected services, likely reviewers, an architectural-risk
band, hidden-coupling and documentation impact. `dna timeline` reconstructs service
births, dependency evolution, ownership shifts, and a monthly risk-trend series. All
of it (plus <2-minute repo onboarding) is in the Genome Browser too. See
[PHASE-4.md](PHASE-4.md).

## Web application

Two UIs ship in the box:

- **Genome Browser** (`dna serve`) — zero-dependency single-file UI, perfect for a quick look
- **Intelligence webapp** (`webapp/`) — production Next.js app: interactive genome
  graph, knowledge explorer, time travel, bus-factor simulations, risk and executive
  dashboards, ⌘K search, dark/light

```bash
dna serve                 # terminal 1 — genome API
cd webapp && npm install && npm run dev   # terminal 2 → http://localhost:3000
```

## How it works

```
GitHub connector ─► 4-pass ingest ──► bitemporal graph (SQLite) ──► DNA profiles
 clone · metadata    census · structure         nodes/edges carry         │
        │            history · eras             valid_from/valid_to,      ▼
 incremental sync ──► replay only new           provenance, confidence   insights · ask · busfactor
 (event log = truth)  commits, rebuild                                    timetravel · pr · timeline
                      from the log                                        web UI · export
```

Facts are never overwritten — the genome closes a fact's validity and records its
successor, so you can query the architecture *as it was known at any date*. The full
schema is open: `dna export` dumps every node, edge, and event as JSON.

See [ARCHITECTURE.md](ARCHITECTURE.md) for the deep dive and
[docs/](docs/README.md) for guides, CLI/API reference, and ADRs.

## Performance

Measured on this repo's test hardware (see [docs/reference/performance.md](docs/reference/performance.md)):

| Repo | Commits ingested | Ingest time | Genome size | `dna insights` |
|---|---|---|---|---|
| demo fixture | 97 | < 1 s | < 1 MB | ~5 ms |
| flask | full history | seconds | small | ~10 ms |
| prometheus | 3,000 (capped) | ~4 s | ~40 MB | ~80 ms |

Incremental sync replays only new commits and stays byte-identical to a full re-ingest:

| Repo | Full history | Initial build | Incremental sync | Speed-up | Accuracy |
|---|---|---|---|---|---|
| fastapi | 500 commits | 1.72 s | +80 → 0.58 s | ~3.0× | KNOWS `maxdiff 0.0` |
| flask | 2,604 commits | 0.87 s | +104 → 0.31 s | ~2.8× | KNOWS `maxdiff 0.0` |

## Project status

**Release candidate.** The engine, insight engine, GitHub connector, continuous
(incremental) intelligence, PR prediction, timeline, CLI, API, and both UIs are
tested — a **115-check suite** (97 engine + 18 Phase 4) plus a typed, tested webapp.
Not yet built: PR *thread/review* ingestion, an MCP server, and auth/multi-tenancy —
see [PHASE-4.md](PHASE-4.md) and [docs/](docs/README.md) for the roadmap.

## Contributing & security

- [CONTRIBUTING.md](CONTRIBUTING.md) — dev setup, tests, PR flow (gitflow: PRs target `develop`)
- [SECURITY.md](SECURITY.md) — reporting vulnerabilities
- The server binds `127.0.0.1` by default: the genome contains person-level data
  and v0 has no auth. Expose deliberately with `--host 0.0.0.0`.

## License

[Business Source License 1.1](LICENSE) — source-available; free for production use
except competing hosted offerings; converts to Apache-2.0 on 2029-07-04.
