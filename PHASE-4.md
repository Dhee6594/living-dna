# Phase 4 — GitHub Connector & Continuous Intelligence

This phase turns Living Software DNA from a one-shot analyzer into a **continuously
updating engineering-intelligence platform**: connect a repository, build its genome once,
then keep it current by replaying only new commits — refreshing every insight, predicting
pull-request impact, and showing how the architecture evolved over time.

Built as an **extension** of the existing architecture. No existing pass was rebuilt: the
bitemporal store, event log, profiles, insights engine, and read path are unchanged. The
full pre-existing test suite (97 checks) still passes; Phase 4 adds 18 more.

---

## What was added

| Module | Responsibility |
|--------|----------------|
| `dna/github_connector.py` | Connect a repo (public / PAT / org / branch), clone or import it, run the initial build, store repo metadata on the `repo:<name>` graph node, and drive syncs. |
| `dna/continuous.py` | Incremental ingestion: detect new commits, replay only those into the event log, then rebuild derived aggregates (KNOWS, CO_CHANGES, births) from the **full event log** and refresh profiles/eras/structure. |
| `dna/pr_intel.py` | Predict a PR's affected services, knowledge owners/reviewers, architectural risk, hidden-dependency impact, and documentation impact — before merge. |
| `dna/timeline.py` | Architecture evolution: service births, dependency add/remove history, era starts, ownership shifts, and a monthly risk-trend series. |

Wiring: `dna/cli.py` gains `connect`, `sync`, `repos`, `pr`, `timeline`; `dna/server.py`
gains `GET /api/repos`, `GET /api/timeline`, and `POST /api/{connect,sync,pr}`; `web/index.html`
gains repo onboarding, a repositories list with per-repo **sync**, a PR-impact panel, and a
timeline view with a commits/concentration sparkline.

The only change to existing code is a **safe refactor** of `ingest.history()`: the git-log
parser was extracted into `ingest._collect_commits()` (now shared with the incremental path)
and a `rev_range` parameter was added. Behavior for full ingestion is identical — verified by
the unchanged 97-check suite.

---

## How incremental ingestion stays correct

The KNOWS weight of a person on a service is a decayed, per-service-normalized sum over the
service's whole history. You cannot get it right from just the new commits. The design makes
the **append-only event log the source of truth**:

1. **Detect** — `git rev-list <last_synced_sha>..HEAD` gives exactly the new commits.
2. **Replay** — only those commits are parsed from git and appended to the event log
   (`record_event` is idempotent on `commit:<hash>`, so re-runs are safe).
3. **Rebuild from the log** — `continuous.rebuild_knowledge()` recomputes KNOWS, CO_CHANGES,
   and service-birth facts by reading the *entire* `code.commit` event log (fast, in-SQLite),
   using the exact formulas in `ingest.history()`. Stale edges are **closed** (bitemporal), not
   deleted; every rebuilt edge keeps its git provenance.
4. **Refresh** — dependency structure (working tree), eras, and materialized profiles are
   re-derived. Insights read these, so the health/risk/architecture/recommendation report is
   automatically current.

Because step 3 reads the same events a from-scratch ingest would have produced, an
incrementally-synced genome is **byte-identical** to a full re-ingest. The test suite asserts
this (`test_phase4::accuracy`), and it holds on real repos (below) at `maxdiff = 0.0`.

Design laws preserved: read path never runs an LLM; updates close `valid_to` (append-only);
provenance on every fact.

---

## Repository metadata

Stored as props on the existing `repo:<name>` node (so it is bitemporal and exported like any
other fact): `provider`, `remote_url`, `owner`, `is_org`, `branch`, `clone_path`, `head_sha`,
`private`, `connected_at`, `last_synced_at`, and a `github` sub-object (description, stars,
default branch, language, visibility, license) fetched from the REST API. **Tokens are never
persisted** — clones use an ephemeral auth header and `origin` is reset to the clean URL;
private syncs re-supply the token at call time.

---

## Validation

Two suites, both green:

```
tests/test_skeleton.py   97 checks   (unchanged — proves no regression)
tests/test_phase4.py     18 checks   (connector, incremental accuracy, PR, timeline)
```

Measured on real mirrors (no network required — local clones used as origins):

| Repo | History | Initial build | Incremental sync | Speed-up | Accuracy (KNOWS) |
|------|---------|---------------|------------------|----------|------------------|
| fastapi | 500 commits | 1.72 s | +80 commits → 0.58 s | ~3.0× | identical, `maxdiff 0.0` |
| flask | 2604 commits | 0.87 s | +104 commits → 0.31 s | ~2.8× | identical, `maxdiff 0.0` |

Real-world spot checks from the runs:
- **PR intelligence** on flask correctly surfaced **David Lord** and **pgjones** (the actual
  maintainers) as predicted reviewers; on fastapi, **Sebastián Ramírez** (creator) and
  **Yurii Motov**.
- **Timeline** on the full flask clone spanned **2013-10 → 2026-05** with 60 milestones and a
  125-month risk-trend series.

> **Prometheus (Go):** the third requested validation repo could not be cloned here — this
> sandbox blocks egress to github.com (HTTP 403 at the proxy), so live clone and the REST
> metadata call cannot run in-environment. The connector is transport-agnostic (any git URL or
> local path) and the metadata path degrades gracefully when the API is unreachable; run
> `dna connect prometheus/prometheus` on a networked machine to validate the Go/large-repo path.

---

## UI — onboarding in under two minutes

`dna serve` → the Genome Browser now opens with a **Connect a repository** card (owner/name or
URL, optional branch + token). One click clones, builds, and populates the map, services,
bus-factor heatmap, and timeline. Connected repos appear in a **Repositories** list, each with
a **sync** button. The **PR impact** panel takes a repo + base revision and prints affected
services, predicted reviewers, a risk band, and hidden-coupling/docs warnings. The **Timeline**
card renders milestones plus a commits-per-month / knowledge-concentration sparkline.

---

## CLI reference (Phase 4)

```
dna connect <url> [--token T] [--branch B] [--name N] [--workdir DIR] [--max-commits N]
dna sync [<repo>] [--all] [--token T]
dna repos
dna pr  --repo <name> --base <rev> [--head <rev>]      # or:  dna pr --files a.py b.js
dna timeline [--repo <name>]
```
