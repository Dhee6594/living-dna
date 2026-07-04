# Branch protection rulesets

Ready-to-apply [repository ruleset](https://docs.github.com/rest/repos/rules) payloads for
`main` and `develop`, matching the model in
[ADR-0002](../../docs/architecture/adr/0002-adopt-gitflow-branching-model.md).

> **Not yet applied.** Branch protection (classic *and* rulesets) requires **GitHub Pro**
> on a **private** repo, or a **public** repo. Apply once either is true.

## What they enforce

| | `main` (`main.json`) | `develop` (`develop.json`) |
|---|---|---|
| Pull request required | ✅ (0 approvals — solo-friendly; raise to 1 with collaborators) | — (direct pushes allowed) |
| Required status checks (CI, strict/up-to-date) | ✅ | ✅ |
| Linear history | ✅ | — |
| Block force-push (`non_fast_forward`) | ✅ | ✅ |
| Block deletion | ✅ | ✅ |
| Conversation resolution required | ✅ | — |
| Admin bypass (escape hatch) | ✅ `always` | ✅ `always` |

Status-check contexts (`Engine (Python 3.10)`, `Engine (Python 3.12)`, `Web UI`) match the
job names in [`../workflows/ci.yml`](../workflows/ci.yml). If you rename those jobs, update
these files too.

## Apply

Once the repo is public or on GitHub Pro:

```bash
gh api -X POST repos/Dhee6594/living-dna/rulesets --input .github/rulesets/main.json
gh api -X POST repos/Dhee6594/living-dna/rulesets --input .github/rulesets/develop.json

# verify
gh api repos/Dhee6594/living-dna/rulesets
```

To update an existing ruleset later: `PUT repos/Dhee6594/living-dna/rulesets/<id>`.
