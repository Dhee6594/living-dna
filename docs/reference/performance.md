# Performance

Measured 2026-07-04 on a sandboxed Linux VM (results scale with disk speed;
your hardware is likely faster). Methodology: `/usr/bin/time` for wall clock +
peak RSS; `curl -w %{time_total}` against a local `dna serve` for API latency.

## Ingest (one-off per repo; re-ingestion is idempotent)

| Repo | Commits | Ingest | Peak memory | Genome size |
|---|---|---|---|---|
| demo fixture (5 services) | 97 | 0.6 s | 19 MB | 112 KB |
| flask (full history) | 2,604 | 2.0 s | 58 MB | 1.1 MB |
| fastapi (shallow clone) | 500 | 3.6 s | 147 MB | 260 KB |
| prometheus (`--max-commits 3000`) | 3,000 | 5.5 s | 159 MB | 1.4 MB |

Ingest is linear in commits. For very large repos, start with
`--max-commits 3000` and raise the cap later.

## API latency (prometheus genome, local loopback)

| Endpoint | Latency |
|---|---|
| `/api/graph` | ~1 ms |
| `/api/profiles` | ~3 ms |
| `/api/busfactor` (org-wide) | ~29 ms |
| `/api/insights` (full engine) | ~95 ms |

The Insight Engine computes everything on demand — no caches to invalidate,
no background jobs. The `generated_in_ms` field in every insights document
reports the server-side cost of that exact call.

## UI

`next build` output: 14 routes, ~102 KB shared first-load JS, all
static-prerendered; data loads client-side from the local API.

## Storage

The genome is one SQLite file (default `.dna/genome.db`). It grows with events
(≈ commits), not with repo size — a 3,000-commit prometheus genome is 1.4 MB.
`dna export` round-trips the entire genome as JSON.
