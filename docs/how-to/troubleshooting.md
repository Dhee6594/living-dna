# Troubleshooting & FAQ

## Install / CLI

**`dna: command not found` after `pip install -e .`**
pip installed the script outside your PATH (it warns about this). Either add the
printed directory to PATH, or skip installation entirely:
`python3 -m dna.cli …` is identical to `dna …`.

**`pip install` complains about externally-managed environment**
Use a virtualenv (`python3 -m venv .venv && . .venv/bin/activate`) or
`pip install -e . --break-system-packages`. The engine itself has zero
dependencies — installation only wires the `dna` command.

**Ingest is slow / repo is huge**
Use `dna ingest <repo> --max-commits 3000`. History replay is linear in commits;
3,000 commits of Prometheus ingest in ~4 s. You can re-run with a higher cap
later — re-ingestion is idempotent.

**`git warning:` lines during ingest**
Non-fatal. The engine degrades gracefully on shallow clones, missing tags, and
other non-standard git configurations, and tells you what it skipped.

## Results look wrong

**One giant service / wrong service split**
Run `dna report` — it flags `SINGLE-SERVICE`, `THIN`, and `ISOLATED` anomalies
with explanations. Detection is tiered (manifests → layout → entry-points →
compose → content); each service's profile records `detected_by` so you can see
why it exists.

**The same person appears twice**
Identity resolution merges obvious duplicates automatically. For the rest, add
`<repo>/.dna/identities.json`:
`{"aliases": {"work@corp.com": "personal@gmail.com"}}` and re-ingest.

**A service has no owners**
Knowledge decays with a 12-month half-life; a service untouched for years shows
thin ownership *by design* — that finding is the product working.

**Empty dashboard in the web UI**
The webapp needs the API running: `dna serve` in another terminal. The UI shows
"Couldn't reach the genome API" with the command when it can't connect.

## FAQ

**Does my code leave my machine?** No. Ingest reads local git via subprocess;
the genome is a local SQLite file; the server binds loopback. The only optional
network call is the Anthropic API for `--deep`/`mine`, off by default.

**Do I need an API key?** No. Everything except `dna ask --deep` and `dna mine`
is graph-only and deterministic.

**Which languages are supported?** History-based intelligence (ownership,
bus-factor, co-change, hidden coupling, insights) is language-agnostic.
Import-based dependency edges currently parse Python and JS/TS; other languages
still get manifest- and convention-based detection.

**How is this different from git blame / GitHub insights?** Those show *who
touched lines*. The genome models knowledge decay, co-change coupling,
bitemporal structure, and departure simulation — e.g. it finds service pairs
that change together with no declared dependency, which no GitHub view shows.

**Can I get everything out?** `dna export` dumps the complete genome (schema
v1.0, all history, all provenance) as JSON. No lock-in.
