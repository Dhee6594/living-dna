# Living DNA — Web Application

Production web UI for the Software Genome. Next.js 15 (App Router) · React 19 ·
TypeScript strict · Tailwind CSS · React Flow · Framer Motion · Zustand.

## Run

```bash
# 1. Start the genome API (repo root)
dna serve                      # http://127.0.0.1:8077

# 2. Start the app
cd webapp
npm install
npm run dev                    # http://localhost:3000
```

All `/api/*` requests are rewritten to the Python API (`DNA_API_URL` env
overrides the default `http://127.0.0.1:8077`). The frontend holds **zero**
backend logic — every number on screen comes from the genome API.

## Architecture

```
app/                     App Router pages (one route = one product surface)
  page.tsx               Dashboard (org overview)
  genome/                Dependency graph + service profile drawer (React Flow)
  knowledge/             Knowledge-graph explorer (KNOWS weights per person)
  archaeology/           Evidence-cited Q&A
  timetravel/            Bitemporal graph + structural diff
  busfactor/             Org heatmap + departure simulation
  risk/                  Risk intelligence feed
  executive/             Board-level KPIs (client-side aggregation)
  search/                Full-page genome search
  settings/              Theme, motion, repo preferences
  login/                 Auth placeholder (SSO/SAML in Enterprise phase)
components/
  shell.tsx              Sidebar nav, topbar, repo selector, ⌘K palette
  ui.tsx                 Card/Stat/Badge/Skeleton/Empty primitives + motion presets
  genome-graph.tsx       React Flow wrapper, dependency-depth layered layout
  insights.tsx           Insight Engine widgets: useInsights hook, ranked
                         RecommendationList, ScoreRing (used by Dashboard,
                         Risk, Executive — no dedicated insights page by design)
lib/
  api.ts                 Typed client for every backend endpoint
  types.ts               Typed mirror of the Python API schema
  store.ts               Zustand stores (prefs persisted, auth placeholder)
  format.ts              Pure display helpers (unit-tested)
tests/                   Vitest unit tests (api client, stores, formatting)
```

## Conventions

- **Theming:** CSS variables (`--surface`, `--ink`, …) with `.dark`/`.light`
  on `<html>`; Tailwind consumes them as semantic tokens. Never hardcode hex.
- **Accessibility:** focus-visible outlines, aria labels/pressed/current,
  skip-to-content link, `prefers-reduced-motion` honoured globally plus a
  manual toggle in Settings.
- **State:** server data stays in components (fetch-on-mount); only true
  client state (theme, repo filter, auth, prefs) lives in Zustand.
- **Performance:** no client-side data library yet by design — the API is
  local and instant. When the backend moves to Postgres, swap fetch-on-mount
  for TanStack Query without touching page structure.

## Test & build

```bash
npm run typecheck   # strict TS across app/components/lib/tests
npm test            # vitest unit suite
npm run build       # production build
```
