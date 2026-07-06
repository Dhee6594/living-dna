# JSON API Reference

Served by `dna serve` (default `http://127.0.0.1:8077`). All endpoints are
`GET`, read-only, and return JSON. The Next.js webapp proxies `/api/*` here.

| Endpoint | Query params | Returns |
|---|---|---|
| `/api/profiles` | — | All materialized DNA profiles |
| `/api/profile/<service>` | — | One profile (404 if unknown) |
| `/api/graph` | `at=YYYY-MM-DD` (optional) | Services + dependency edges as of `at` (default: now) |
| `/api/diff` | `from=YYYY-MM-DD`, `to=YYYY-MM-DD` (both optional, default now) | Structural diff with causes |
| `/api/busfactor` | `person=<name>` (optional) | Org heatmap, or one departure simulation |
| `/api/ask` | `q=<question>` | Evidence-cited answer (graph-only) |
| `/api/insights` | — | Full Insight Engine document (see below) |
| `/api/report` | — | Genome quality report |
| `/api/search` | `q=<text>` | Up to 50 node matches (services, people, eras, decisions) |
| `/api/events` | `service=`, `kind=` (default `code.`), `limit=` (default 200) | Event-log slice, oldest→newest |
| `/api/people` | — | All Person nodes (id, name) |
| `/api/decisions` | — | Mined Decision nodes with confidence + provenance |

## `/api/insights` document shape

```json
{
  "generated_in_ms": 80,
  "overview":   { "services": 10, "complexity_score": 40,
                  "maintainability_score": 71, "maturity_score": 86,
                  "score_formulas": { "...": "documented per score" } },
  "engineering_health":     { "ownership_concentration_gini": 0.61,
                              "churn_hotspots": [], "stable_modules": [],
                              "volatile_modules": [] },
  "architecture":           { "circular_dependencies": [], "hidden_dependencies": [],
                              "coupling": [], "architectural_drift": [],
                              "evolution_timeline": [], "boundary_assessment": "…" },
  "risk_intelligence":      { "single_points_of_failure": [], "unowned_services": [],
                              "scaling_bottlenecks": [], "frequently_changing": [] },
  "knowledge_intelligence": { "knowledge_silos": [], "missing_documentation": [],
                              "critical_contributors": [], "historical_context": [],
                              "decision_mining": {} },
  "recommendations": [ { "action": "…", "why": "…", "impact": 5, "risk": 1,
                         "confidence": 0.9, "effort": "M", "score": 4.0 } ],
  "executive": { "cto": "…", "engineering_manager": "…",
                 "staff_engineer": "…", "platform_team": "…" }
}
```

## Security notes

- Loopback bind by default; no auth in v0 — do not expose to untrusted networks.
- CORS is `*` (the API is expected to be local). Both harden in the Enterprise phase.
- Errors return `{"error": "..."}` with 404/500 status.
