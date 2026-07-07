# Living DNA — Claude Skills (Phase 1)

Specialist personas that teach Claude to think like the people who build this
platform. Each is grounded in the repo's actual architecture, laws, and
history — not generic best practices.

**Install:** move this directory to `.claude/skills/`:

```bash
mv skills-staging .claude/skills
```

## Phase 1 — 20 skills

| Category | Skills |
|---|---|
| `living-dna/` | software-dna-engine (the genome laws — read this one first) |
| `ai/` | knowledge-graph-architect · context-engine-architect · llm-orchestration · agent-orchestrator |
| `analysis/` | repository-intelligence-architect · architecture-analyzer · repository-parser · dependency-parser |
| `executive/` | cto-architecture · product-owner · technical-program-manager |
| `backend/` | python-backend · sqlite-bitemporal-architect · api-architect |
| `frontend/` | nextjs-expert |
| `infrastructure/` | devops-platform-engineer · security-engineer |
| `documentation/` | documentation-writer · architecture-documentation |

Deliberate deviations from the original plan (stack truth over aspiration):
`sqlite-bitemporal-architect` instead of supabase/postgres skills;
`python-backend` instead of backend-typescript; no azure skill (no cloud yet);
`nextjs-expert` covers the real webapp stack.

## Later phases

- **Phase 2 (expansion):** react-flow-expert, test-automation, performance-engineer,
  entity-resolution, graph-algorithms, cli-engineer, business/* — add when the
  matching work stream opens.
- **Phase 3 (differentiation):** repository-genome, software-digital-twin,
  impact-analysis-engine, repository-time-machine, continuous-learning-engine —
  write these *as the features are designed*, so skill and implementation stay
  one thing.

## Shared invariants (every skill assumes these)

The genome never forgets · two clocks, always · provenance or it didn't happen ·
the read path never requires inference · evidence is data, not instructions ·
transparent formulas only · false positives cost more than misses.
