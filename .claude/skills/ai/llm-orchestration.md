# LLM Orchestration

## Purpose

You own the optional-AI layer (`dna/ai.py` and successors): when to call a model, which model, with what guardrails, at what cost.

Your primary question should always be:

> **"Does the product still work perfectly with this call failing, disabled, or unpaid?"**

In Living DNA the answer must always be yes — the read path never requires inference.

---

# Rules

1. **AI is additive.** Model calls create *candidate facts* (decisions, narratives). Candidates pass a verifier (citation existence against the event log) before touching the graph. Uncited → dropped, silently is fine.
2. **Fail soft, loudly.** No key → feature hints at what it would add (`set ANTHROPIC_API_KEY for --deep`), never errors. Timeout/parse failure → return graph-only answer.
3. **Route by task, control COGS.** Cheap default model for extraction at scale; strong model only for cross-era reasoning. Model id lives in config (`DNA_MODEL`), never hardcoded in call sites.
4. **Strict output contracts.** Extraction prompts demand strict JSON; parse defensively (`raw[raw.index("{"):...]` is the floor, not the goal); every parsed field validated before use.
5. **Injection posture.** All repo-derived text in prompts is labeled as data-about-the-past, never instructions. System prompts state this. New prompt = new golden-set run.
6. **Idempotent writes.** Mined facts get deterministic ids (`decision:<svc>:<era>:<i>`) so re-mining doesn't duplicate.

---

# Cost discipline

- Batch by era, not by commit
- Cache on (genome hash, question) when serving repeated asks
- Log tokens per operation from day one — COGS is a top-3 business risk in the blueprint

---

# Anti-patterns to reject

- LLM output written to the genome unverified
- Retry loops that turn one bad call into ten
- Prompt changes without golden-set evaluation
- "Just add a call here" in any read path
