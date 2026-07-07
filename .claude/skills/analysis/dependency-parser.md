# Dependency Parser

## Purpose

You own how Living DNA discovers services and extracts dependency edges (`dna/ingest.py` passes 1–2): the tiered detector and the import/manifest parsers.

Your primary question should always be:

> **"Will this fire on a repo layout I've never seen — and will it stay quiet on the ones it shouldn't?"**

False positives cost more than misses: a phantom service pollutes every downstream insight.

---

# The tier system (most-trusted first; later tiers never override or nest inside earlier)

1. **manifest** — `package.json`, `pyproject.toml`, `go.mod`, `requirements.txt`, `Cargo.toml`, `pom.xml`, `plugin.json`
2. **layout** — children of `services/ apps/ packages/`
3. **entrypoint** — `Dockerfile`, `Procfile`, `main.py`, `manage.py`, `wsgi/asgi.py`, `main.go`, `main.rs`, `server.js`, `*_server.py` (depth-capped)
4. **compose** — docker-compose `build:`/`context:` targets
5. **content** — top-level dirs ≥ 3 files, ONLY when tiers 1–4 found nothing

Every service records `detected_by`. Extending detection = appending a tier or a filename constant, never special-casing.

---

# False-positive guards (each earned on a real repo)

- `NON_SERVICE_DIRS` (tests, docs, examples, docs_src, fixtures…) applied to ALL tiers — killed flask's `examples/*` phantoms
- Python package trees (`__init__.py` in dir or ancestors) are modules, not services — unless a container file says otherwise — killed `src/flask/sansio`, `fastapi/middleware`
- Sub-repos (own `.git`) pruned entirely; `SKIP_DIRS` pruned during the walk
- Single `os.walk` pass, never repeated `rglob` (that mistake cost minutes on Prometheus)

---

# Dependency edges

- Sources: Python/JS-TS import regexes, `package.json` deps, `dna-deps.txt` convention — matched only against *known sibling services*
- Every edge carries mechanism, since-date (from history), and evidence paths (≤5)
- Caps on files scanned per service are deliberate perf guards; tune with benchmarks, not instinct

---

# Validation matrix

fixture (6 exact) · flask (1) · fastapi (1) · vivek-task (3, incl. Dockerfile-only .NET and `*_server.py`) · prometheus (10). A detector change that shifts these numbers must justify every delta.
